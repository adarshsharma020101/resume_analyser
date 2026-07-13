"""
LinkedIn profile extraction service.
Handles: PDF, pasted text, LinkedIn data export (ZIP/CSV/JSON).
NEVER attempts to contact LinkedIn — all data must come from user uploads.
"""
from __future__ import annotations

import csv
import io
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.logging import get_logger
from app.services.document_parser import ParsedDocument, parse_pdf, parse_txt

log = get_logger(__name__)

LINKEDIN_DISCLAIMER = (
    "LinkedIn ID saved for reference only. "
    "Profile content cannot be analyzed until you upload, export, or paste actual profile data."
)


@dataclass
class LinkedInData:
    headline: Optional[str] = None
    about: Optional[str] = None
    experience: List[Dict[str, Any]] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)
    education: List[Dict[str, Any]] = field(default_factory=list)
    certifications: List[str] = field(default_factory=list)
    projects: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    profile_format: str = "unknown"
    extraction_confidence: float = 0.7

    def to_dict(self) -> Dict[str, Any]:
        return {
            "headline": self.headline,
            "about": self.about,
            "experience": self.experience,
            "skills": self.skills,
            "education": self.education,
            "certifications": self.certifications,
            "projects": self.projects,
            "recommendations": self.recommendations,
            "keywords": self.keywords,
            "profile_format": self.profile_format,
            "extraction_confidence": self.extraction_confidence,
        }


# ── LinkedIn Export ZIP parser ────────────────────────────────────────────────

def _parse_linkedin_export_zip(
    extracted_files: Dict[str, bytes]
) -> LinkedInData:
    """
    Parse LinkedIn's official data export ZIP.
    Handles the standard CSV files: Profile.csv, Positions.csv, Skills.csv, Education.csv, Certifications.csv
    """
    data = LinkedInData(profile_format="export_zip")

    def read_csv(file_bytes: bytes) -> List[Dict[str, str]]:
        text = file_bytes.decode("utf-8-sig", errors="replace")
        reader = csv.DictReader(io.StringIO(text))
        return [row for row in reader]

    # Profile.csv
    profile_bytes = extracted_files.get("Profile.csv") or extracted_files.get("profile.csv")
    if profile_bytes:
        rows = read_csv(profile_bytes)
        if rows:
            row = rows[0]
            data.headline = row.get("Headline") or row.get("headline")
            data.about = row.get("Summary") or row.get("summary")

    # Positions.csv / Experience
    pos_bytes = extracted_files.get("Positions.csv") or extracted_files.get("positions.csv")
    if pos_bytes:
        rows = read_csv(pos_bytes)
        for row in rows:
            exp_entry = {
                "title": row.get("Title") or row.get("title"),
                "company": row.get("Company Name") or row.get("company_name"),
                "dates": f"{row.get('Started On', '')} - {row.get('Finished On', 'Present')}".strip(" -"),
                "description": row.get("Description") or row.get("description"),
            }
            data.experience.append(exp_entry)

    # Skills.csv
    skills_bytes = extracted_files.get("Skills.csv") or extracted_files.get("skills.csv")
    if skills_bytes:
        rows = read_csv(skills_bytes)
        for row in rows:
            skill = row.get("Name") or row.get("name") or row.get("Skill")
            if skill:
                data.skills.append(str(skill).strip())

    # Education.csv
    edu_bytes = extracted_files.get("Education.csv") or extracted_files.get("education.csv")
    if edu_bytes:
        rows = read_csv(edu_bytes)
        for row in rows:
            edu_entry = {
                "degree": row.get("Degree Name") or row.get("degree_name"),
                "field": row.get("Field Of Study") or row.get("field_of_study"),
                "institution": row.get("School Name") or row.get("school_name"),
                "dates": f"{row.get('Start Date', '')} - {row.get('End Date', '')}".strip(" -"),
            }
            data.education.append(edu_entry)

    # Certifications.csv
    cert_bytes = extracted_files.get("Certifications.csv") or extracted_files.get("certifications.csv")
    if cert_bytes:
        rows = read_csv(cert_bytes)
        for row in rows:
            cert = row.get("Name") or row.get("name")
            if cert:
                data.certifications.append(str(cert).strip())

    # Collect keywords
    all_text = " ".join(
        [data.headline or "", data.about or ""]
        + [e.get("title", "") + " " + e.get("company", "") for e in data.experience]
        + data.skills
        + [e.get("degree", "") for e in data.education]
        + data.certifications
    )
    data.keywords = list(dict.fromkeys(
        w for w in re.findall(r"\b[A-Za-z][A-Za-z+#./\-]{2,30}\b", all_text)
        if len(w) > 2
    ))[:150]

    data.extraction_confidence = 0.95
    return data


# ── LinkedIn PDF parser ────────────────────────────────────────────────────────

def _parse_linkedin_pdf(raw_text: str) -> LinkedInData:
    """Parse a LinkedIn-generated PDF profile."""
    data = LinkedInData(profile_format="pdf")
    lines = [l.strip() for l in raw_text.splitlines() if l.strip()]

    current_section = None
    current_block: List[str] = []
    experience_entry: Optional[Dict[str, Any]] = None

    for i, line in enumerate(lines):
        low = line.lower()

        # Detect section headers
        if low in ("experience", "work experience"):
            current_section = "experience"
            if experience_entry:
                data.experience.append(experience_entry)
                experience_entry = None
            continue
        elif low in ("education",):
            current_section = "education"
            continue
        elif low in ("skills", "top skills"):
            current_section = "skills"
            continue
        elif low in ("certifications", "licenses & certifications"):
            current_section = "certifications"
            continue
        elif low in ("projects",):
            current_section = "projects"
            continue
        elif low in ("recommendations received",):
            current_section = "recommendations"
            continue
        elif low in ("summary", "about"):
            current_section = "about"
            current_block = []
            continue

        # Section content parsing
        if current_section == "about":
            current_block.append(line)
            data.about = " ".join(current_block)
        elif current_section == "skills":
            # Skills appear one per line
            if len(line) < 60 and not line.startswith("•"):
                data.skills.append(line)
        elif current_section == "certifications":
            if len(line) < 200:
                data.certifications.append(line)
        elif current_section == "recommendations":
            data.recommendations.append(line)
        elif current_section == "experience":
            # Heuristic: date ranges signal a new experience entry
            if re.search(r"\d{4}", line) and ("-" in line or "–" in line or "present" in low):
                if experience_entry:
                    data.experience.append(experience_entry)
                experience_entry = {"title": None, "company": None, "dates": line, "bullets": []}
            elif experience_entry:
                if experience_entry["title"] is None:
                    experience_entry["title"] = line
                elif experience_entry["company"] is None:
                    experience_entry["company"] = line
                else:
                    experience_entry["bullets"].append(line)

    if experience_entry:
        data.experience.append(experience_entry)

    # Headline is typically the second non-empty line
    if len(lines) >= 2:
        data.headline = lines[1] if len(lines[1]) < 200 else None

    # Keywords
    all_text = " ".join([
        data.headline or "", data.about or "",
        " ".join(data.skills), " ".join(data.certifications)
    ])
    data.keywords = list(dict.fromkeys(
        w for w in re.findall(r"\b[A-Za-z][A-Za-z+#./\-]{2,30}\b", all_text)
        if len(w) > 2
    ))[:150]

    data.extraction_confidence = 0.7
    return data


# ── Pasted text parser ────────────────────────────────────────────────────────

def parse_linkedin_pasted_text(text: str) -> LinkedInData:
    """Parse raw pasted LinkedIn profile text."""
    parsed = ParsedDocument(raw_text=text, pages=[], page_count=1, file_extension=".txt")
    data = _parse_linkedin_pdf(text)
    data.profile_format = "pasted"
    return data


# ── JSON export parser ────────────────────────────────────────────────────────

def _parse_linkedin_json(data_bytes: bytes) -> LinkedInData:
    """Parse a user-exported LinkedIn JSON file."""
    obj = json.loads(data_bytes.decode("utf-8", errors="replace"))
    li = LinkedInData(profile_format="json")

    # Handle common LinkedIn JSON export shapes
    profile = obj.get("profile", obj)
    li.headline = profile.get("headline") or profile.get("summary")
    li.about = profile.get("about") or profile.get("description")

    for exp in profile.get("experience", []):
        li.experience.append({
            "title": exp.get("title"),
            "company": exp.get("company") or exp.get("companyName"),
            "dates": f"{exp.get('startDate', '')} - {exp.get('endDate', 'Present')}",
            "description": exp.get("description"),
        })

    for sk in profile.get("skills", []):
        name = sk.get("name") if isinstance(sk, dict) else str(sk)
        if name:
            li.skills.append(name)

    for edu in profile.get("education", []):
        li.education.append({
            "degree": edu.get("degreeName") or edu.get("degree"),
            "institution": edu.get("schoolName") or edu.get("school"),
            "dates": f"{edu.get('startDate', '')} - {edu.get('endDate', '')}",
        })

    for cert in profile.get("certifications", []):
        name = cert.get("name") if isinstance(cert, dict) else str(cert)
        if name:
            li.certifications.append(name)

    li.extraction_confidence = 0.9
    return li


# ── Dispatcher ────────────────────────────────────────────────────────────────

def parse_linkedin_content(
    data: bytes,
    file_extension: str,
    extracted_zip_files: Optional[Dict[str, bytes]] = None,
) -> LinkedInData:
    """Route LinkedIn content to the right parser."""
    ext = file_extension.lower()

    if ext == ".zip" and extracted_zip_files:
        return _parse_linkedin_export_zip(extracted_zip_files)
    elif ext == ".pdf":
        parsed = parse_pdf(data)
        return _parse_linkedin_pdf(parsed.raw_text)
    elif ext in (".txt",):
        text = data.decode("utf-8", errors="replace")
        return parse_linkedin_pasted_text(text)
    elif ext == ".json":
        return _parse_linkedin_json(data)
    elif ext == ".csv":
        # Single CSV file — treat as skills or positions
        li = LinkedInData(profile_format="csv")
        text = data.decode("utf-8-sig", errors="replace")
        reader = csv.DictReader(io.StringIO(text))
        for row in reader:
            skill = row.get("Name") or row.get("Skill")
            if skill:
                li.skills.append(str(skill).strip())
        li.extraction_confidence = 0.6
        return li
    else:
        raise ValueError(f"Unsupported LinkedIn file extension: {ext}")

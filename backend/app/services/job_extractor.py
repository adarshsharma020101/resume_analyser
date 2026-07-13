"""
Job description and dataset extraction service.
Handles: paste text, PDF, DOCX, TXT, CSV, JSON.
No external calls — all local.
"""
from __future__ import annotations

import csv
import io
import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from app.core.logging import get_logger
from app.services.document_parser import parse_document

log = get_logger(__name__)


@dataclass
class JobData:
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    raw_text: str = ""
    requirements: List[str] = field(default_factory=list)
    skills_required: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    source_file: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "raw_text": self.raw_text,
            "requirements": self.requirements,
            "skills_required": self.skills_required,
            "keywords": self.keywords,
            "source_file": self.source_file,
        }


# ── Text extraction utilities ─────────────────────────────────────────────────

REQUIREMENT_PATTERNS = [
    re.compile(r"(?i)(required|requirements?|must\s+have|must\s+be)"),
    re.compile(r"(?i)(qualifications?|what\s+you.?ll\s+(need|bring|have))"),
]

SKILL_SECTION_PATTERNS = [
    re.compile(r"(?i)(skills?\s*(required|needed|&\s*qualifications?)?:?)"),
    re.compile(r"(?i)(technical\s+skills?|technologies|tools?|stack)"),
]

COMMON_WORDS = {
    "the", "and", "for", "with", "this", "that", "have", "from", "was",
    "are", "been", "has", "had", "its", "our", "their", "your", "you",
    "we", "they", "will", "can", "may", "also", "all", "more", "than",
    "job", "role", "position", "team", "company", "work", "join",
    "looking", "opportunity", "candidate", "experience",
}


def _extract_keywords_from_text(text: str) -> List[str]:
    words = re.findall(r"\b[A-Za-z][A-Za-z+#./\-]{2,30}\b", text)
    return list(dict.fromkeys(
        w for w in words if w.lower() not in COMMON_WORDS
    ))[:200]


def _extract_requirements(text: str) -> Tuple[List[str], List[str]]:
    """
    Extract requirement bullets and skills from job text.
    Returns (requirements, skills_required).
    """
    lines = text.splitlines()
    requirements: List[str] = []
    skills: List[str] = []
    in_requirements = False
    in_skills = False

    for line in lines:
        stripped = line.strip().strip("•·-–* ")
        if not stripped:
            continue
        lower = stripped.lower()

        # Detect section transitions
        if any(p.search(lower) for p in REQUIREMENT_PATTERNS):
            in_requirements = True
            in_skills = False
            continue
        if any(p.search(lower) for p in SKILL_SECTION_PATTERNS):
            in_skills = True
            in_requirements = False
            continue
        if re.match(r"(?i)(responsibilities|duties|what\s+you.?ll\s+do|about\s+the\s+role)", lower):
            in_requirements = False
            in_skills = False
            continue

        # Collect bullets in requirement sections
        if in_requirements and len(stripped) > 10:
            requirements.append(stripped)
        if in_skills and 2 < len(stripped) < 80:
            skills.append(stripped)

    # If no structured sections found, collect all bulleted items
    if not requirements:
        for line in lines:
            stripped = line.strip()
            if stripped.startswith(("•", "·", "-", "–", "*")) and len(stripped) > 10:
                requirements.append(stripped.lstrip("•·-–* "))

    return requirements[:50], skills[:50]


def _infer_title_company(text: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Try to extract title, company, location from the top of the job text."""
    lines = [l.strip() for l in text.splitlines()[:20] if l.strip()]
    title = lines[0] if lines else None
    company = None
    location = None

    for line in lines[1:6]:
        if re.search(r"\b(Inc\.|LLC|Ltd\.|Corp\.|Co\.|GmbH|Company|Group)\b", line):
            company = line
        if re.search(r"\b(Remote|Hybrid|On-site|[A-Z][a-z]+,\s*[A-Z]{2})\b", line):
            location = line

    return title, company, location


def extract_job_from_text(text: str, source_file: Optional[str] = None) -> JobData:
    """Extract structured job data from raw text."""
    job = JobData(raw_text=text, source_file=source_file)
    job.title, job.company, job.location = _infer_title_company(text)
    job.requirements, job.skills_required = _extract_requirements(text)
    job.keywords = _extract_keywords_from_text(text)
    return job


# ── CSV dataset parser ────────────────────────────────────────────────────────

def parse_jobs_csv(data: bytes, source_file: str) -> List[JobData]:
    """
    Parse a CSV file of job listings.
    Handles common column names flexibly.
    """
    text = data.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    jobs: List[JobData] = []
    warnings: List[str] = []

    for i, row in enumerate(reader):
        # Flexible column mapping
        title = (
            row.get("title") or row.get("job_title") or row.get("Title") or
            row.get("Job Title") or row.get("position")
        )
        company = (
            row.get("company") or row.get("Company") or row.get("employer") or
            row.get("organization")
        )
        location = (
            row.get("location") or row.get("Location") or row.get("city") or
            row.get("remote")
        )
        description = (
            row.get("description") or row.get("Description") or
            row.get("job_description") or row.get("Job Description") or
            row.get("requirements") or row.get("content")
        )

        if not description and not title:
            warnings.append(f"Row {i+1}: no usable content found.")
            continue

        raw_text = "\n".join(filter(None, [title, company, location, description]))
        job = JobData(
            title=str(title).strip() if title else None,
            company=str(company).strip() if company else None,
            location=str(location).strip() if location else None,
            raw_text=raw_text,
            source_file=source_file,
        )
        job.requirements, job.skills_required = _extract_requirements(raw_text)
        job.keywords = _extract_keywords_from_text(raw_text)
        jobs.append(job)

    return jobs


# ── JSON dataset parser ───────────────────────────────────────────────────────

def parse_jobs_json(data: bytes, source_file: str) -> List[JobData]:
    """Parse a JSON array or object of job listings."""
    obj = json.loads(data.decode("utf-8", errors="replace"))

    # Accept: list, {"jobs": [...]}, {"data": [...]}
    if isinstance(obj, list):
        items = obj
    elif isinstance(obj, dict):
        items = obj.get("jobs") or obj.get("data") or obj.get("listings") or [obj]
    else:
        items = [{"description": str(obj)}]

    jobs: List[JobData] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        description = (
            item.get("description") or item.get("job_description") or
            item.get("text") or item.get("content") or ""
        )
        title = item.get("title") or item.get("job_title") or item.get("role")
        company = item.get("company") or item.get("employer")
        location = item.get("location") or item.get("city")
        raw_text = "\n".join(filter(None, [title, company, location, description]))

        job = JobData(
            title=str(title).strip() if title else None,
            company=str(company).strip() if company else None,
            location=str(location).strip() if location else None,
            raw_text=raw_text,
            source_file=source_file,
        )
        job.requirements, job.skills_required = _extract_requirements(raw_text)
        job.keywords = _extract_keywords_from_text(raw_text)
        jobs.append(job)

    return jobs


# ── Dispatcher for single job ─────────────────────────────────────────────────

def parse_job_from_file(data: bytes, file_extension: str, source_file: str) -> JobData:
    """Parse a single job description from an uploaded file."""
    ext = file_extension.lower()
    if ext in (".pdf", ".docx", ".txt"):
        parsed = parse_document(data, ext)
        return extract_job_from_text(parsed.raw_text, source_file=source_file)
    else:
        raise ValueError(f"Unsupported job file extension: {ext}")


# ── Dispatcher for job dataset ────────────────────────────────────────────────

def parse_job_dataset(
    data: bytes,
    file_extension: str,
    source_file: str,
) -> Tuple[List[JobData], List[str]]:
    """
    Parse a batch of jobs from CSV, JSON, or document.
    Returns (jobs, warnings).
    """
    ext = file_extension.lower()
    warnings: List[str] = []

    if ext == ".csv":
        jobs = parse_jobs_csv(data, source_file)
    elif ext == ".json":
        jobs = parse_jobs_json(data, source_file)
    elif ext in (".pdf", ".docx", ".txt"):
        # Single job document — return as a one-item list
        parsed = parse_document(data, ext)
        jobs = [extract_job_from_text(parsed.raw_text, source_file=source_file)]
    else:
        raise ValueError(f"Unsupported dataset file extension: {ext}")

    if not jobs:
        warnings.append("No jobs could be extracted from the uploaded file.")

    return jobs, warnings

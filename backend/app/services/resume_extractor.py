"""
Resume structure extraction service.
Uses rule-based NLP first, then uses Ollama LLM for structured extraction.
Returns a validated ResumeData dict with full provenance.
All values are from the document — nothing is invented.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from app.core.logging import get_logger
from app.services.document_parser import ParsedDocument

log = get_logger(__name__)

# ── Section heading patterns ──────────────────────────────────────────────────

SECTION_PATTERNS: Dict[str, List[str]] = {
    "summary": [
        r"(?i)^(professional\s+)?summary",
        r"(?i)^objective",
        r"(?i)^profile",
        r"(?i)^about\s+me",
        r"(?i)^career\s+(summary|objective)",
    ],
    "experience": [
        r"(?i)^(work\s+)?(experience|history)",
        r"(?i)^employment(\s+history)?",
        r"(?i)^professional\s+experience",
        r"(?i)^career\s+history",
    ],
    "education": [
        r"(?i)^education",
        r"(?i)^academic(\s+background)?",
        r"(?i)^qualifications",
    ],
    "skills": [
        r"(?i)^(technical\s+)?skills",
        r"(?i)^competencies",
        r"(?i)^core\s+(competencies|skills)",
        r"(?i)^technologies",
    ],
    "certifications": [
        r"(?i)^certifications?",
        r"(?i)^licenses?\s+(and\s+certifications?)?",
        r"(?i)^credentials",
    ],
    "projects": [
        r"(?i)^projects?",
        r"(?i)^personal\s+projects?",
        r"(?i)^portfolio",
    ],
    "achievements": [
        r"(?i)^achievements?",
        r"(?i)^accomplishments?",
        r"(?i)^awards?",
        r"(?i)^honors?",
    ],
}

CONTACT_PATTERNS = {
    "email": re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]{2,}"),
    "phone": re.compile(r"(\+?\d[\d\s.\-()]{7,}\d)"),
    "linkedin_url": re.compile(r"linkedin\.com/in/[\w\-]+", re.IGNORECASE),
}

SKILL_STOPWORDS = {
    "and", "or", "with", "using", "the", "a", "an", "of", "to", "in", "for",
    "on", "at", "by", "is", "are", "was", "were",
}


@dataclass
class ResumeData:
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    linkedin_url: Optional[str] = None
    summary: Optional[str] = None
    skills: List[str] = field(default_factory=list)
    experience: List[Dict[str, Any]] = field(default_factory=list)
    education: List[Dict[str, Any]] = field(default_factory=list)
    certifications: List[str] = field(default_factory=list)
    projects: List[Dict[str, Any]] = field(default_factory=list)
    achievements: List[str] = field(default_factory=list)
    section_headings: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    parsing_risks: List[str] = field(default_factory=list)
    completeness_score: float = 0.0
    extraction_confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "full_name": self.full_name,
            "email": self.email,
            "phone": self.phone,
            "location": self.location,
            "linkedin_url": self.linkedin_url,
            "summary": self.summary,
            "skills": self.skills,
            "experience": self.experience,
            "education": self.education,
            "certifications": self.certifications,
            "projects": self.projects,
            "achievements": self.achievements,
            "section_headings": self.section_headings,
            "keywords": self.keywords,
            "parsing_risks": self.parsing_risks,
            "completeness_score": self.completeness_score,
            "extraction_confidence": self.extraction_confidence,
        }


# ── Rule-based extraction ─────────────────────────────────────────────────────

def _extract_contact_rule(text: str) -> Dict[str, Optional[str]]:
    contact: Dict[str, Optional[str]] = {
        "email": None, "phone": None, "linkedin_url": None
    }
    for field_name, pattern in CONTACT_PATTERNS.items():
        m = pattern.search(text)
        if m:
            contact[field_name] = m.group(0).strip()
    return contact


def _split_sections(text: str) -> Dict[str, str]:
    """Split document into named sections using heading detection."""
    lines = text.splitlines()
    sections: Dict[str, str] = {}
    current_section = "header"
    section_lines: List[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            section_lines.append("")
            continue

        matched_section = None
        for section_name, patterns in SECTION_PATTERNS.items():
            for pat in patterns:
                if re.match(pat, stripped) and len(stripped) < 60:
                    matched_section = section_name
                    break
            if matched_section:
                break

        if matched_section:
            # Save previous section
            sections[current_section] = "\n".join(section_lines).strip()
            current_section = matched_section
            section_lines = []
        else:
            section_lines.append(line)

    sections[current_section] = "\n".join(section_lines).strip()
    return sections


def _extract_skills_rule(skills_text: str) -> List[str]:
    """Extract skills from a skills section using punctuation splitting."""
    if not skills_text:
        return []
    # Split on commas, pipes, bullets, newlines, semicolons
    raw = re.split(r"[,|•·\n;/]", skills_text)
    skills = []
    for item in raw:
        item = item.strip().strip("•·-– ")
        # Keep reasonable skill tokens (2-60 chars, not stopwords)
        if 2 <= len(item) <= 60 and item.lower() not in SKILL_STOPWORDS:
            skills.append(item)
    return list(dict.fromkeys(skills))  # deduplicate preserving order


def _compute_completeness(data: ResumeData) -> float:
    """Score 0.0-1.0 based on how many key fields are populated."""
    fields = {
        "email": bool(data.email),
        "phone": bool(data.phone),
        "summary": bool(data.summary),
        "skills": bool(data.skills),
        "experience": bool(data.experience),
        "education": bool(data.education),
        "location": bool(data.location),
        "full_name": bool(data.full_name),
    }
    filled = sum(1 for v in fields.values() if v)
    return round(filled / len(fields), 2)


def extract_resume_rule_based(parsed: ParsedDocument) -> ResumeData:
    """Fast rule-based extraction pass. Always runs before LLM."""
    text = parsed.raw_text
    data = ResumeData()
    data.parsing_risks = list(parsed.parsing_warnings)

    # Contact info from header area (first 500 chars)
    header_text = text[:500]
    contact = _extract_contact_rule(header_text)
    # Also check full text if not found in header
    if not any(contact.values()):
        contact = _extract_contact_rule(text)
    data.email = contact["email"]
    data.phone = contact["phone"]
    data.linkedin_url = contact["linkedin_url"]

    # Sections
    sections = _split_sections(text)
    data.section_headings = [s for s in sections.keys() if s != "header"]

    # Summary
    summary_text = sections.get("summary", "")
    if summary_text and len(summary_text) > 20:
        data.summary = summary_text[:2000]

    # Skills
    skills_text = sections.get("skills", "")
    data.skills = _extract_skills_rule(skills_text) if skills_text else []

    # Certifications
    cert_text = sections.get("certifications", "")
    if cert_text:
        data.certifications = [
            l.strip().strip("•·-– ") for l in cert_text.splitlines()
            if l.strip() and len(l.strip()) > 3
        ]

    # Achievements
    ach_text = sections.get("achievements", "")
    if ach_text:
        data.achievements = [
            l.strip().strip("•·-– ") for l in ach_text.splitlines()
            if l.strip() and len(l.strip()) > 3
        ]

    # All keywords (union of section headings, skills, words from experience)
    experience_text = sections.get("experience", "")
    all_words = re.findall(r"\b[A-Za-z][A-Za-z+#./\-]{2,30}\b", text)
    # Filter to meaningful keywords (not common English)
    COMMON_WORDS = {
        "the", "and", "for", "with", "this", "that", "have", "from", "was",
        "are", "been", "has", "had", "its", "our", "their", "your", "you",
        "we", "they", "will", "can", "may", "also", "all", "more", "than",
    }
    data.keywords = list(dict.fromkeys(
        w for w in all_words if w.lower() not in COMMON_WORDS
    ))[:200]

    data.completeness_score = _compute_completeness(data)
    return data


# ── LLM-enhanced extraction ───────────────────────────────────────────────────

async def extract_resume_llm(
    parsed: ParsedDocument,
    rule_data: ResumeData,
    ollama_client: Any,
    model: str,
) -> ResumeData:
    """
    Structured extraction using Ollama LLM.
    Receives the document text in a constrained prompt.
    Returns ONLY what is in the document — any missing field stays null.
    """
    # Truncate text to stay within context window
    text_for_llm = parsed.raw_text[:6000]

    system_prompt = """You are a resume parsing assistant. Extract structured information ONLY from the provided resume text.
Rules:
- Return ONLY valid JSON matching the schema below.
- If a field is not present in the text, return null for that field.
- NEVER invent, guess, or assume information not explicitly written in the resume.
- Do not add commentary, explanation, or any text outside the JSON.
- For experience and education, extract only what is written — do not calculate durations.
- For skills, extract individual skill names as they appear.
- full_name: the person's name if found near the top, else null.
- location: city/state/country if present, else null.

JSON Schema:
{
  "full_name": string | null,
  "location": string | null,
  "summary": string | null,
  "skills": [string],
  "experience": [{"title": string|null, "company": string|null, "dates": string|null, "bullets": [string]}],
  "education": [{"degree": string|null, "institution": string|null, "dates": string|null, "gpa": string|null}],
  "certifications": [string],
  "projects": [{"name": string|null, "description": string|null, "technologies": [string]}],
  "achievements": [string]
}"""

    user_prompt = f"Resume text:\n\n{text_for_llm}\n\nExtract the structured resume data now."

    try:
        response = await ollama_client.chat(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            options={"temperature": 0.0},
        )
        content = response["message"]["content"].strip()

        # Extract JSON from response (handle markdown code blocks)
        json_match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", content)
        if json_match:
            content = json_match.group(1)

        extracted = json.loads(content)

        # Merge with rule-based data — LLM fills what rules missed
        if extracted.get("full_name") and not rule_data.full_name:
            rule_data.full_name = str(extracted["full_name"])[:256]
        if extracted.get("location") and not rule_data.location:
            rule_data.location = str(extracted["location"])[:256]
        if extracted.get("summary") and not rule_data.summary:
            rule_data.summary = str(extracted["summary"])[:2000]

        # Skills: merge rule + LLM
        llm_skills = [str(s).strip() for s in extracted.get("skills", []) if s]
        merged_skills = list(dict.fromkeys(rule_data.skills + llm_skills))
        rule_data.skills = merged_skills[:100]

        # Experience (LLM is better at this)
        if extracted.get("experience"):
            rule_data.experience = [
                {
                    "title": e.get("title"),
                    "company": e.get("company"),
                    "dates": e.get("dates"),
                    "bullets": [b for b in (e.get("bullets") or []) if b],
                }
                for e in extracted["experience"]
                if isinstance(e, dict)
            ][:20]

        # Education
        if extracted.get("education"):
            rule_data.education = [
                {
                    "degree": e.get("degree"),
                    "institution": e.get("institution"),
                    "dates": e.get("dates"),
                    "gpa": e.get("gpa"),
                }
                for e in extracted["education"]
                if isinstance(e, dict)
            ][:10]

        # Certifications
        if extracted.get("certifications"):
            llm_certs = [str(c).strip() for c in extracted["certifications"] if c]
            rule_data.certifications = list(dict.fromkeys(
                rule_data.certifications + llm_certs
            ))[:30]

        # Projects
        if extracted.get("projects"):
            rule_data.projects = [
                {
                    "name": p.get("name"),
                    "description": p.get("description"),
                    "technologies": [t for t in (p.get("technologies") or []) if t],
                }
                for p in extracted["projects"]
                if isinstance(p, dict)
            ][:20]

        # Achievements
        if extracted.get("achievements"):
            llm_ach = [str(a).strip() for a in extracted["achievements"] if a]
            rule_data.achievements = list(dict.fromkeys(
                rule_data.achievements + llm_ach
            ))[:30]

        rule_data.extraction_confidence = 0.9

    except (json.JSONDecodeError, KeyError, TypeError) as e:
        log.warning("LLM extraction JSON parse failed: %s — using rule-based only.", e)
        rule_data.extraction_confidence = 0.6

    rule_data.completeness_score = _compute_completeness(rule_data)
    return rule_data

"""
Deterministic ATS Readiness Scoring Engine.

All numeric scores are computed by deterministic code — NOT by LLM.
The LLM is only used afterwards to generate natural-language explanations
of each deduction, and those explanations are clearly labeled.

Score components (configurable via .env):
  parseability          20 pts
  section_structure     10 pts
  contact_completeness   5 pts
  keyword_coverage      25 pts  (requires target job description)
  experience_alignment  15 pts
  achievement_quality   10 pts
  readability           10 pts
  linkedin_consistency   5 pts
  ─────────────────────────
  Total                100 pts
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
log = get_logger(__name__)


# ── Data containers ────────────────────────────────────────────────────────────

@dataclass
class ScoreComponent:
    name: str
    max_points: float
    earned_points: float
    deductions: List[str] = field(default_factory=list)   # cited evidence
    evidence: List[str] = field(default_factory=list)


@dataclass
class ATSScoreResult:
    total_score: float
    score_type: str           # "general" | "job_specific"
    components: List[ScoreComponent] = field(default_factory=list)
    disclaimer: str = (
        "This is an ATS Readiness Estimate based on transparent, deterministic scoring rules. "
        "Proprietary ATS systems vary significantly and may score differently. "
        "This estimate does not guarantee how any specific employer's system will process your resume."
    )

    def component_dict(self) -> Dict[str, float]:
        return {c.name: c.earned_points for c in self.components}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _normalize_skill(skill: str) -> str:
    """Lowercase, strip punctuation for comparison."""
    return re.sub(r"[^a-z0-9#+.]", " ", skill.lower()).strip()


def _keyword_overlap(
    resume_keywords: List[str],
    job_keywords: List[str],
) -> Tuple[float, List[str], List[str]]:
    """
    Returns (overlap_ratio, matched, missing).
    Exact + substring matching with normalization.
    """
    if not job_keywords:
        return 0.0, [], []

    norm_resume = {_normalize_skill(k) for k in resume_keywords if k}
    matched: List[str] = []
    missing: List[str] = []

    for kw in job_keywords:
        norm_kw = _normalize_skill(kw)
        if not norm_kw:
            continue
        # Check exact or substring match
        found = norm_kw in norm_resume or any(
            norm_kw in r or r in norm_kw
            for r in norm_resume
            if len(r) > 3
        )
        if found:
            matched.append(kw)
        else:
            missing.append(kw)

    ratio = len(matched) / len(job_keywords) if job_keywords else 0.0
    return ratio, matched, missing


STANDARD_SECTIONS = {
    "Contact Information": ["email", "phone", "@", "contact"],
    "Summary / Objective": ["summary", "objective", "profile", "about"],
    "Work Experience": ["experience", "employment", "work", "career", "history"],
    "Education": ["education", "degree", "university", "college", "bachelor", "master", "phd"],
    "Skills": ["skills", "technical", "competencies", "proficiency"],
}

QUANTIFIED_PATTERN = re.compile(
    r"(\d+[\%\+\$]|increased?|decreased?|reduced?|improved?|saved?|generated?|"
    r"led\s|managed\s|built\s|delivered?|achieved?|grew\s|grew\s|scaled\s)",
    re.IGNORECASE,
)

WEAK_PATTERNS = re.compile(
    r"(?i)(^responsible for|^duties include|^worked on|^helped with|^assisted in)",
)

ATS_RISKY_FORMATTING = [
    "Multi-column layout",
    "Tables detected",
    "Scanned or image-based PDF",
    "Images found in document",
    "text inside images",
]


# ── Component scorers ──────────────────────────────────────────────────────────

def _score_parseability(
    parsing_risks: List[str],
    max_pts: float,
) -> ScoreComponent:
    comp = ScoreComponent("parseability", max_pts, max_pts)
    deduction_per_risk = max_pts / max(len(ATS_RISKY_FORMATTING), 1)

    for risk in parsing_risks:
        for risky in ATS_RISKY_FORMATTING:
            if risky.lower() in risk.lower():
                penalty = min(deduction_per_risk * 1.5, max_pts * 0.35)
                comp.earned_points = max(0.0, comp.earned_points - penalty)
                comp.deductions.append(f"Deduction ({penalty:.1f} pts): {risk}")
                break

    comp.earned_points = round(max(0.0, comp.earned_points), 2)
    return comp


def _score_section_structure(
    section_headings: List[str],
    raw_text: str,
    max_pts: float,
) -> ScoreComponent:
    comp = ScoreComponent("section_structure", max_pts, 0.0)
    lower_text = raw_text.lower()
    pts_per_section = max_pts / len(STANDARD_SECTIONS)

    for section_name, keywords in STANDARD_SECTIONS.items():
        found = any(kw in lower_text for kw in keywords)
        if found:
            comp.earned_points += pts_per_section
            comp.evidence.append(f"Found: {section_name}")
        else:
            comp.deductions.append(
                f"Missing section '{section_name}' — standard ATS sections improve parse accuracy."
            )

    comp.earned_points = round(min(comp.earned_points, max_pts), 2)
    return comp


def _score_contact_completeness(
    email: Optional[str],
    phone: Optional[str],
    linkedin_url: Optional[str],
    location: Optional[str],
    max_pts: float,
) -> ScoreComponent:
    comp = ScoreComponent("contact_completeness", max_pts, 0.0)
    weights = {"email": 0.45, "phone": 0.30, "location": 0.15, "linkedin_url": 0.10}

    if email:
        comp.earned_points += max_pts * weights["email"]
        comp.evidence.append("Email found")
    else:
        comp.deductions.append("No email found — ATS systems require a valid email address.")

    if phone:
        comp.earned_points += max_pts * weights["phone"]
        comp.evidence.append("Phone found")
    else:
        comp.deductions.append("No phone number found.")

    if location:
        comp.earned_points += max_pts * weights["location"]
        comp.evidence.append("Location found")
    else:
        comp.deductions.append("No location found — some ATS systems filter by location.")

    if linkedin_url:
        comp.earned_points += max_pts * weights["linkedin_url"]
        comp.evidence.append("LinkedIn URL found")

    comp.earned_points = round(min(comp.earned_points, max_pts), 2)
    return comp


def _score_keyword_coverage(
    resume_keywords: List[str],
    resume_skills: List[str],
    job_keywords: Optional[List[str]],
    job_skills: Optional[List[str]],
    max_pts: float,
) -> Tuple[ScoreComponent, List[str], List[str]]:
    """Returns component plus (matched_keywords, missing_keywords)."""
    comp = ScoreComponent("keyword_coverage", max_pts, 0.0)

    if not job_keywords and not job_skills:
        comp.earned_points = max_pts * 0.5  # no target JD — partial credit
        comp.deductions.append(
            "No target job description provided — keyword coverage estimate is general only."
        )
        return comp, [], []

    # Combine resume and job keyword pools
    all_resume_kw = list({_normalize_skill(k) for k in (resume_keywords + resume_skills) if k})
    all_job_kw = (job_keywords or []) + (job_skills or [])
    all_job_kw = list(dict.fromkeys(all_job_kw))  # deduplicate

    ratio, matched, missing = _keyword_overlap(all_resume_kw, all_job_kw)
    comp.earned_points = round(ratio * max_pts, 2)
    comp.evidence = [f"Matched keyword: {m}" for m in matched[:20]]
    comp.deductions = [
        f"Missing keyword found in job description: '{m}'" for m in missing[:20]
    ]

    return comp, matched, missing


def _score_experience_alignment(
    experience: List[Dict[str, Any]],
    job_keywords: Optional[List[str]],
    max_pts: float,
) -> ScoreComponent:
    comp = ScoreComponent("experience_alignment", max_pts, 0.0)

    if not experience:
        comp.deductions.append("No work experience entries found in resume.")
        return comp

    # Base: having experience entries
    base_pts = max_pts * 0.4
    comp.earned_points += base_pts
    comp.evidence.append(f"Found {len(experience)} experience entries.")

    # Bonus: job title/description mentions job keywords
    if job_keywords:
        exp_text = " ".join(
            " ".join(filter(None, [e.get("title", ""), e.get("company", "")] +
                           [b for b in e.get("bullets", [])]))
            for e in experience
        ).lower()
        kw_matches = sum(
            1 for kw in job_keywords
            if _normalize_skill(kw) in exp_text
        )
        if job_keywords:
            alignment_ratio = kw_matches / len(job_keywords)
            comp.earned_points += alignment_ratio * (max_pts * 0.6)
            if alignment_ratio < 0.3:
                comp.deductions.append(
                    "Few job description keywords appear in experience descriptions — "
                    "consider tailoring experience bullets to the target role."
                )
    else:
        comp.earned_points += max_pts * 0.3  # partial credit without JD

    comp.earned_points = round(min(comp.earned_points, max_pts), 2)
    return comp


def _score_achievement_quality(
    experience: List[Dict[str, Any]],
    achievements: List[str],
    max_pts: float,
) -> ScoreComponent:
    comp = ScoreComponent("achievement_quality", max_pts, 0.0)

    all_bullets = [
        b for e in experience for b in e.get("bullets", []) if b
    ] + achievements

    if not all_bullets:
        comp.deductions.append("No bullet points or achievements found to evaluate.")
        return comp

    quantified = sum(1 for b in all_bullets if QUANTIFIED_PATTERN.search(b))
    weak = sum(1 for b in all_bullets if WEAK_PATTERNS.search(b))
    total = len(all_bullets)

    quantified_ratio = quantified / total if total else 0.0
    weak_ratio = weak / total if total else 0.0

    comp.earned_points = round(quantified_ratio * max_pts, 2)
    comp.evidence.append(f"{quantified}/{total} bullets contain measurable outcomes or action verbs.")

    if weak_ratio > 0.3:
        penalty = min(max_pts * 0.3, weak_ratio * max_pts)
        comp.earned_points = max(0.0, comp.earned_points - penalty)
        comp.deductions.append(
            f"{weak} bullet(s) start with weak phrases like 'Responsible for' or 'Duties include' — "
            "use strong action verbs with quantified outcomes."
        )

    comp.earned_points = round(min(comp.earned_points, max_pts), 2)
    return comp


def _score_readability(
    raw_text: str,
    section_headings: List[str],
    max_pts: float,
) -> ScoreComponent:
    comp = ScoreComponent("readability", max_pts, comp.earned_points if False else 0.0)
    comp = ScoreComponent("readability", max_pts, 0.0)

    lines = [l for l in raw_text.splitlines() if l.strip()]
    if not lines:
        comp.deductions.append("No readable text found.")
        return comp

    # Length check: 400–900 words is typical
    word_count = len(raw_text.split())
    if 300 <= word_count <= 1200:
        comp.earned_points += max_pts * 0.4
        comp.evidence.append(f"Word count ({word_count}) is within a reasonable range.")
    elif word_count < 150:
        comp.deductions.append(f"Very short resume ({word_count} words) — may lack detail.")
    elif word_count > 1500:
        comp.deductions.append(f"Very long resume ({word_count} words) — consider condensing to 1-2 pages.")
        comp.earned_points += max_pts * 0.2

    # Bullet usage
    bullet_lines = sum(1 for l in lines if l.strip().startswith(("•", "·", "-", "–", "*")))
    if bullet_lines > 3:
        comp.earned_points += max_pts * 0.3
        comp.evidence.append(f"{bullet_lines} bullet points found — good structure for ATS.")
    else:
        comp.deductions.append("Few or no bullet points — ATS and recruiters prefer bulleted experience.")

    # Section headings present
    if len(section_headings) >= 3:
        comp.earned_points += max_pts * 0.3
        comp.evidence.append(f"{len(section_headings)} section headings detected.")
    else:
        comp.deductions.append("Few clear section headings detected.")

    comp.earned_points = round(min(comp.earned_points, max_pts), 2)
    return comp


def _score_linkedin_consistency(
    resume_data: Dict[str, Any],
    linkedin_data: Optional[Dict[str, Any]],
    max_pts: float,
) -> Tuple[ScoreComponent, List[str]]:
    """Returns (component, inconsistency_flags)."""
    comp = ScoreComponent("linkedin_consistency", max_pts, max_pts)
    inconsistencies: List[str] = []

    if not linkedin_data:
        comp.earned_points = max_pts  # no deduction without data
        comp.evidence.append("No LinkedIn profile provided — consistency check skipped.")
        return comp, []

    # Title comparison (most recent experience)
    resume_exp = resume_data.get("experience") or []
    li_exp = linkedin_data.get("experience") or []

    resume_titles = {e.get("title", "").lower() for e in resume_exp if e.get("title")}
    li_titles = {e.get("title", "").lower() for e in li_exp if e.get("title")}

    if resume_titles and li_titles:
        title_overlap = resume_titles & li_titles
        if not title_overlap and resume_titles and li_titles:
            inconsistencies.append(
                "Job titles in resume do not exactly match LinkedIn profile titles — "
                "please verify for consistency."
            )
            comp.earned_points -= max_pts * 0.4

    # Employer comparison
    resume_employers = {e.get("company", "").lower() for e in resume_exp if e.get("company")}
    li_employers = {e.get("company", "").lower() for e in li_exp if e.get("company")}
    if resume_employers and li_employers:
        employer_diff = resume_employers.symmetric_difference(li_employers)
        if employer_diff:
            inconsistencies.append(
                f"Employer name differences detected between resume and LinkedIn: "
                f"{', '.join(list(employer_diff)[:3])} — verify accuracy."
            )
            comp.earned_points -= max_pts * 0.3

    # Skills comparison
    resume_skills = {_normalize_skill(s) for s in (resume_data.get("skills") or [])}
    li_skills = {_normalize_skill(s) for s in (linkedin_data.get("skills") or [])}
    li_only = li_skills - resume_skills
    resume_only = resume_skills - li_skills

    if len(li_only) > 3:
        inconsistencies.append(
            f"{len(li_only)} skills present on LinkedIn but not in resume: "
            f"{', '.join(list(li_only)[:5])}..."
        )
    if len(resume_only) > 3:
        inconsistencies.append(
            f"{len(resume_only)} skills in resume but not on LinkedIn: "
            f"{', '.join(list(resume_only)[:5])}..."
        )

    comp.earned_points = round(max(0.0, min(comp.earned_points, max_pts)), 2)
    return comp, inconsistencies


# ── Main scoring function ──────────────────────────────────────────────────────

def compute_ats_score(
    resume_data: Dict[str, Any],
    parsing_risks: List[str],
    job_data: Optional[Dict[str, Any]] = None,
    linkedin_data: Optional[Dict[str, Any]] = None,
) -> Tuple[ATSScoreResult, List[str], List[str], List[str]]:
    """
    Compute full ATS score deterministically.

    Returns:
        (ATSScoreResult, matched_keywords, missing_keywords, inconsistencies)
    """
    # Weight config from settings
    W = {
        "parseability": float(settings.ATS_WEIGHT_PARSEABILITY),
        "section_structure": float(settings.ATS_WEIGHT_SECTION_STRUCTURE),
        "contact_completeness": float(settings.ATS_WEIGHT_CONTACT_COMPLETENESS),
        "keyword_coverage": float(settings.ATS_WEIGHT_KEYWORD_COVERAGE),
        "experience_alignment": float(settings.ATS_WEIGHT_EXPERIENCE_ALIGNMENT),
        "achievement_quality": float(settings.ATS_WEIGHT_ACHIEVEMENT_QUALITY),
        "readability": float(settings.ATS_WEIGHT_READABILITY),
        "linkedin_consistency": float(settings.ATS_WEIGHT_LINKEDIN_CONSISTENCY),
    }

    raw_text = resume_data.get("raw_text", "")
    experience = resume_data.get("experience") or []
    achievements = resume_data.get("achievements") or []
    skills = resume_data.get("skills") or []
    keywords = resume_data.get("keywords") or []
    section_headings = resume_data.get("section_headings") or []
    parsing_risks_list = parsing_risks or []

    job_keywords = None
    job_skills = None
    if job_data:
        job_keywords = job_data.get("keywords") or []
        job_skills = job_data.get("skills_required") or []

    # Score each component
    c_parseability = _score_parseability(parsing_risks_list, W["parseability"])
    c_sections = _score_section_structure(section_headings, raw_text, W["section_structure"])
    c_contact = _score_contact_completeness(
        resume_data.get("email"),
        resume_data.get("phone"),
        resume_data.get("linkedin_url"),
        resume_data.get("location"),
        W["contact_completeness"],
    )
    c_keywords, matched_kw, missing_kw = _score_keyword_coverage(
        keywords, skills, job_keywords, job_skills, W["keyword_coverage"]
    )
    c_experience = _score_experience_alignment(experience, job_keywords, W["experience_alignment"])
    c_achievement = _score_achievement_quality(experience, achievements, W["achievement_quality"])
    c_readability = _score_readability(raw_text, section_headings, W["readability"])
    c_linkedin, inconsistencies = _score_linkedin_consistency(
        resume_data, linkedin_data, W["linkedin_consistency"]
    )

    components = [
        c_parseability, c_sections, c_contact, c_keywords,
        c_experience, c_achievement, c_readability, c_linkedin,
    ]

    total = round(sum(c.earned_points for c in components), 2)
    score_type = "job_specific" if job_data else "general"

    result = ATSScoreResult(
        total_score=total,
        score_type=score_type,
        components=components,
    )

    return result, matched_kw, missing_kw, inconsistencies

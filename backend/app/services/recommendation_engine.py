"""
Evidence-based recommendation engine.
Every recommendation has:
  - A reason cited from the uploaded document or job description
  - A priority level: critical | high | medium | optional
  - An optional LLM-generated draft suggestion (always labeled as draft)
  - confidence level
  - source citations

No recommendations are fabricated — all are derived from scoring evidence.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.core.logging import get_logger
from app.services.ats_scorer import ATSScoreResult, WEAK_PATTERNS, QUANTIFIED_PATTERN

log = get_logger(__name__)


@dataclass
class Recommendation:
    priority: str              # critical | high | medium | optional
    category: str              # keyword | formatting | section | content | consistency | completeness
    title: str
    why_it_matters: str
    evidence_from_resume: Optional[str]
    evidence_from_job: Optional[str]
    suggested_action: str
    draft_suggestion: Optional[str] = None  # always marked as draft
    is_draft: bool = True
    confidence: float = 1.0
    source_citations: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "priority": self.priority,
            "category": self.category,
            "title": self.title,
            "why_it_matters": self.why_it_matters,
            "evidence_from_resume": self.evidence_from_resume,
            "evidence_from_job": self.evidence_from_job,
            "suggested_action": self.suggested_action,
            "draft_suggestion": self.draft_suggestion,
            "is_draft": self.is_draft,
            "confidence": self.confidence,
            "source_citations": self.source_citations,
            "_draft_notice": (
                "Draft suggestions must be verified for accuracy before use. "
                "Never add skills, jobs, or credentials you do not have."
            ) if self.draft_suggestion else None,
        }


def _cite(source_type: str, file_name: str, excerpt: Optional[str] = None) -> Dict[str, Any]:
    return {
        "source_type": source_type,
        "source_file_name": file_name,
        "excerpt": excerpt or "N/A",
    }


# ── Recommendation generators ──────────────────────────────────────────────────

def _recs_from_parseability(
    score_result: ATSScoreResult,
    parsing_risks: List[str],
    resume_filename: str,
) -> List[Recommendation]:
    recs: List[Recommendation] = []
    comp = next((c for c in score_result.components if c.name == "parseability"), None)
    if not comp:
        return recs

    for risk in parsing_risks:
        risk_lower = risk.lower()
        if "multi-column" in risk_lower:
            recs.append(Recommendation(
                priority="critical",
                category="formatting",
                title="Remove multi-column layout",
                why_it_matters=(
                    "Multi-column layouts cause many ATS systems to read columns left-to-right "
                    "across columns, producing garbled output."
                ),
                evidence_from_resume=risk,
                evidence_from_job=None,
                suggested_action="Convert to a single-column format using a plain DOCX or plain-text template.",
                confidence=0.95,
                source_citations=[_cite("resume", resume_filename, risk)],
            ))
        elif "scanned" in risk_lower or "ocr" in risk_lower:
            recs.append(Recommendation(
                priority="critical",
                category="formatting",
                title="Replace scanned PDF with a text-based document",
                why_it_matters=(
                    "Scanned PDFs are image files — ATS systems cannot read them without OCR, "
                    "which introduces errors. OCR was used here but accuracy is not guaranteed."
                ),
                evidence_from_resume=risk,
                evidence_from_job=None,
                suggested_action="Save or re-export the resume as a native text-based PDF or DOCX.",
                confidence=0.95,
                source_citations=[_cite("resume", resume_filename, risk)],
            ))
        elif "table" in risk_lower:
            recs.append(Recommendation(
                priority="high",
                category="formatting",
                title="Remove tables from resume",
                why_it_matters=(
                    "Tables are frequently mis-parsed by ATS systems, "
                    "causing skills and experience to be dropped or scrambled."
                ),
                evidence_from_resume=risk,
                evidence_from_job=None,
                suggested_action="Replace table-formatted sections with plain bulleted lists.",
                confidence=0.9,
                source_citations=[_cite("resume", resume_filename, risk)],
            ))
        elif "image" in risk_lower:
            recs.append(Recommendation(
                priority="medium",
                category="formatting",
                title="Remove or replace image-embedded text",
                why_it_matters="Text inside images cannot be read by ATS parsers.",
                evidence_from_resume=risk,
                evidence_from_job=None,
                suggested_action="Ensure all text is typed, not embedded in images or graphics.",
                confidence=0.85,
                source_citations=[_cite("resume", resume_filename, risk)],
            ))

    return recs


def _recs_from_sections(
    score_result: ATSScoreResult,
    resume_filename: str,
) -> List[Recommendation]:
    comp = next((c for c in score_result.components if c.name == "section_structure"), None)
    if not comp:
        return []
    recs: List[Recommendation] = []
    for deduction in comp.deductions:
        section_match = re.search(r"Missing section '([^']+)'", deduction)
        if section_match:
            section = section_match.group(1)
            recs.append(Recommendation(
                priority="high" if section in ("Work Experience", "Skills") else "medium",
                category="section",
                title=f"Add a '{section}' section",
                why_it_matters=(
                    f"ATS systems look for standard section headings to categorize your information. "
                    f"Missing '{section}' may cause the section's content to be ignored."
                ),
                evidence_from_resume=f"Section heading not detected: {section}",
                evidence_from_job=None,
                suggested_action=f"Add a clearly labeled '{section}' heading to your resume.",
                confidence=0.9,
                source_citations=[_cite("resume", resume_filename, deduction)],
            ))
    return recs


def _recs_from_contact(
    score_result: ATSScoreResult,
    resume_filename: str,
) -> List[Recommendation]:
    comp = next((c for c in score_result.components if c.name == "contact_completeness"), None)
    if not comp:
        return []
    recs: List[Recommendation] = []
    for deduction in comp.deductions:
        if "email" in deduction.lower():
            recs.append(Recommendation(
                priority="critical",
                category="completeness",
                title="Add an email address",
                why_it_matters="ATS and recruiters require a reachable email address.",
                evidence_from_resume="No email address found in extracted document text.",
                evidence_from_job=None,
                suggested_action="Add your professional email address to the contact section.",
                confidence=0.98,
                source_citations=[_cite("resume", resume_filename, "No email found")],
            ))
        elif "phone" in deduction.lower():
            recs.append(Recommendation(
                priority="high",
                category="completeness",
                title="Add a phone number",
                why_it_matters="Many recruiters prefer to call candidates directly.",
                evidence_from_resume="No phone number found in extracted document text.",
                evidence_from_job=None,
                suggested_action="Add your phone number to the contact section.",
                confidence=0.95,
                source_citations=[_cite("resume", resume_filename, "No phone found")],
            ))
    return recs


def _recs_from_keywords(
    missing_keywords: List[str],
    matched_keywords: List[str],
    job_filename: Optional[str],
    resume_filename: str,
) -> List[Recommendation]:
    if not missing_keywords:
        return []
    recs: List[Recommendation] = []
    # Group into one recommendation with all missing keywords cited
    missing_sample = missing_keywords[:10]
    recs.append(Recommendation(
        priority="critical" if len(missing_keywords) > 10 else "high",
        category="keyword",
        title=f"Add {len(missing_keywords)} missing keyword(s) from the job description",
        why_it_matters=(
            "ATS keyword matching is the primary filter before human review. "
            f"Your resume is missing {len(missing_keywords)} keywords found in the target job description."
        ),
        evidence_from_resume=(
            f"Matched {len(matched_keywords)} of {len(matched_keywords) + len(missing_keywords)} "
            f"job description keywords."
        ),
        evidence_from_job=(
            f"Keywords found in job description but not in resume: "
            f"{', '.join(missing_sample)}"
            + (f" ... and {len(missing_keywords) - len(missing_sample)} more." if len(missing_keywords) > 10 else ".")
        ),
        suggested_action=(
            "Review the job description and add relevant missing keywords to your skills, "
            "experience bullets, or summary — but only if they accurately reflect your experience."
        ),
        confidence=0.95,
        source_citations=[
            _cite("resume", resume_filename),
            _cite("job_description", job_filename or "provided job description"),
        ],
    ))
    return recs


def _recs_from_achievements(
    experience: List[Dict[str, Any]],
    score_result: ATSScoreResult,
    resume_filename: str,
) -> List[Recommendation]:
    comp = next((c for c in score_result.components if c.name == "achievement_quality"), None)
    if not comp:
        return []

    recs: List[Recommendation] = []

    # Find weak bullets as evidence
    weak_bullets = []
    for exp in experience:
        for bullet in exp.get("bullets", []):
            if bullet and WEAK_PATTERNS.search(bullet):
                weak_bullets.append(bullet[:120])

    if weak_bullets:
        recs.append(Recommendation(
            priority="high",
            category="content",
            title="Rewrite weak bullet points with action verbs and measurable results",
            why_it_matters=(
                "Bullets starting with 'Responsible for' or 'Duties include' are passive "
                "and do not demonstrate impact. ATS systems and recruiters respond better to "
                "strong action verbs with quantified outcomes."
            ),
            evidence_from_resume=(
                f"Example weak bullets found: {'; '.join(weak_bullets[:3])}"
            ),
            evidence_from_job=None,
            suggested_action=(
                "Rewrite bullets using the format: [Action verb] + [what you did] + [measurable result]. "
                "Example: 'Led migration of 3 legacy services to AWS, reducing latency by 40%.'"
            ),
            draft_suggestion=(
                "DRAFT SUGGESTION — verify accuracy before using:\n"
                "Replace 'Responsible for managing team' → 'Managed a team of [X] engineers to deliver [outcome]'"
            ),
            is_draft=True,
            confidence=0.88,
            source_citations=[_cite("resume", resume_filename, weak_bullets[0] if weak_bullets else "")],
        ))

    # Find bullets lacking quantification
    all_bullets = [b for e in experience for b in e.get("bullets", []) if b]
    unquantified = [b for b in all_bullets if not QUANTIFIED_PATTERN.search(b)]
    if unquantified and len(unquantified) > len(all_bullets) * 0.5:
        recs.append(Recommendation(
            priority="medium",
            category="content",
            title="Add quantified results to experience bullets",
            why_it_matters=(
                "Quantified accomplishments (%, $, numbers) stand out to both ATS and human reviewers "
                "and provide verifiable evidence of impact."
            ),
            evidence_from_resume=(
                f"{len(unquantified)} of {len(all_bullets)} bullets lack measurable outcomes."
            ),
            evidence_from_job=None,
            suggested_action=(
                "Add numbers, percentages, or scale to your bullets where possible. "
                "Examples: team size, revenue impact, efficiency gain, project count."
            ),
            confidence=0.85,
            source_citations=[_cite("resume", resume_filename)],
        ))

    return recs


def _recs_from_linkedin_consistency(
    inconsistencies: List[str],
    resume_filename: str,
    linkedin_filename: str,
) -> List[Recommendation]:
    if not inconsistencies:
        return []
    recs: List[Recommendation] = []
    for issue in inconsistencies:
        recs.append(Recommendation(
            priority="medium",
            category="consistency",
            title="Resolve resume / LinkedIn inconsistency",
            why_it_matters=(
                "Recruiters compare your resume to your LinkedIn profile. "
                "Inconsistencies may raise concerns — but we cannot determine which version is correct."
            ),
            evidence_from_resume=issue,
            evidence_from_job=None,
            suggested_action=(
                "Review the flagged difference and update either your resume or LinkedIn profile "
                "so they are consistent. Only you can determine which version is accurate."
            ),
            confidence=0.80,
            source_citations=[
                _cite("resume", resume_filename),
                _cite("linkedin_pdf", linkedin_filename),
            ],
        ))
    return recs


def _recs_summary_quality(
    summary: Optional[str],
    score_result: ATSScoreResult,
    resume_filename: str,
) -> List[Recommendation]:
    recs: List[Recommendation] = []
    if not summary:
        recs.append(Recommendation(
            priority="medium",
            category="content",
            title="Add a professional summary",
            why_it_matters=(
                "A strong summary gives ATS systems and recruiters immediate context about "
                "your experience level and target role."
            ),
            evidence_from_resume="No summary section found in uploaded resume.",
            evidence_from_job=None,
            suggested_action=(
                "Add a 2-4 sentence professional summary at the top of your resume "
                "highlighting your key experience, skills, and career goal."
            ),
            confidence=0.9,
            source_citations=[_cite("resume", resume_filename, "No summary section detected")],
        ))
    elif len(summary.split()) < 20:
        recs.append(Recommendation(
            priority="optional",
            category="content",
            title="Expand the professional summary",
            why_it_matters="The current summary is very short and may not give enough context.",
            evidence_from_resume=f"Summary found but very short: '{summary[:100]}'",
            evidence_from_job=None,
            suggested_action="Expand the summary to 2-4 sentences covering your experience, skills, and goals.",
            confidence=0.75,
            source_citations=[_cite("resume", resume_filename, summary[:100])],
        ))
    return recs


def _recs_li_skills_in_resume(
    resume_skills: List[str],
    linkedin_skills: List[str],
    resume_filename: str,
    linkedin_filename: str,
) -> List[Recommendation]:
    """Flag skills on LinkedIn not in resume, and vice versa."""
    if not linkedin_skills:
        return []
    recs: List[Recommendation] = []
    norm_resume = {s.lower().strip() for s in resume_skills}
    norm_li = {s.lower().strip() for s in linkedin_skills}

    li_only = [s for s in linkedin_skills if s.lower().strip() not in norm_resume]
    resume_only = [s for s in resume_skills if s.lower().strip() not in norm_li]

    if li_only:
        recs.append(Recommendation(
            priority="medium",
            category="consistency",
            title=f"{len(li_only)} skill(s) on LinkedIn not found in resume",
            why_it_matters=(
                "If these skills are relevant to your target roles, "
                "adding them to your resume improves keyword coverage."
            ),
            evidence_from_resume="Skills not found in uploaded resume.",
            evidence_from_job=None,
            suggested_action=(
                f"Consider adding these to your resume skills section if accurate: "
                f"{', '.join(li_only[:10])}"
            ),
            confidence=0.85,
            source_citations=[
                _cite("resume", resume_filename),
                _cite("linkedin_pdf", linkedin_filename, f"LinkedIn skills: {', '.join(li_only[:5])}"),
            ],
        ))

    if resume_only:
        recs.append(Recommendation(
            priority="optional",
            category="consistency",
            title=f"{len(resume_only)} skill(s) in resume not found on LinkedIn",
            why_it_matters=(
                "Recruiters may check LinkedIn for skill verification. "
                "Adding these to LinkedIn improves profile completeness."
            ),
            evidence_from_resume=f"Resume skills not on LinkedIn: {', '.join(resume_only[:5])}",
            evidence_from_job=None,
            suggested_action=(
                f"Consider adding these skills to your LinkedIn profile: {', '.join(resume_only[:10])}"
            ),
            confidence=0.75,
            source_citations=[
                _cite("resume", resume_filename, f"Resume skills: {', '.join(resume_only[:5])}"),
                _cite("linkedin_pdf", linkedin_filename),
            ],
        ))

    return recs


# ── Main entry point ───────────────────────────────────────────────────────────

def generate_recommendations(
    score_result: ATSScoreResult,
    resume_data: Dict[str, Any],
    parsing_risks: List[str],
    matched_keywords: List[str],
    missing_keywords: List[str],
    inconsistencies: List[str],
    resume_filename: str,
    job_filename: Optional[str] = None,
    linkedin_filename: Optional[str] = None,
    linkedin_data: Optional[Dict[str, Any]] = None,
) -> List[Recommendation]:
    """
    Generate all evidence-backed recommendations from scoring results.
    Returns sorted list: critical → high → medium → optional.
    """
    all_recs: List[Recommendation] = []

    # Formatting / parseability
    all_recs += _recs_from_parseability(score_result, parsing_risks, resume_filename)

    # Missing sections
    all_recs += _recs_from_sections(score_result, resume_filename)

    # Contact completeness
    all_recs += _recs_from_contact(score_result, resume_filename)

    # Missing keywords
    if missing_keywords:
        all_recs += _recs_from_keywords(
            missing_keywords, matched_keywords, job_filename, resume_filename
        )

    # Achievement quality
    experience = resume_data.get("experience") or []
    all_recs += _recs_from_achievements(experience, score_result, resume_filename)

    # Summary quality
    all_recs += _recs_summary_quality(
        resume_data.get("summary"), score_result, resume_filename
    )

    # LinkedIn consistency
    if inconsistencies and linkedin_filename:
        all_recs += _recs_from_linkedin_consistency(
            inconsistencies, resume_filename, linkedin_filename
        )

    # LinkedIn ↔ Resume skill gaps
    if linkedin_data and linkedin_filename:
        all_recs += _recs_li_skills_in_resume(
            resume_data.get("skills") or [],
            linkedin_data.get("skills") or [],
            resume_filename,
            linkedin_filename,
        )

    # Sort by priority
    priority_order = {"critical": 0, "high": 1, "medium": 2, "optional": 3}
    all_recs.sort(key=lambda r: priority_order.get(r.priority, 99))

    return all_recs

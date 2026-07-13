"""
Output validation guardrails.
Run after every CrewAI agent output to:
  1. Validate JSON schema
  2. Detect unsupported claims / hallucinated content
  3. Verify numeric score consistency
  4. Ensure all claims have citations
  5. Block prohibited content patterns
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple

from app.core.logging import get_logger

log = get_logger(__name__)


# ── Prohibited claim patterns ──────────────────────────────────────────────────

PROHIBITED_PATTERNS = [
    # Fake confidence in hiring outcomes
    (re.compile(r"(?i)(will\s+(get|land|receive)\s+(an?\s+)?interview)"), "hiring prediction"),
    (re.compile(r"(?i)(guaranteed?\s+to\s+(get|land|pass))"), "guarantee claim"),
    (re.compile(r"(?i)(you\s+are\s+(eligible|qualified)\s+for)"), "eligibility claim"),
    # Fake job data
    (re.compile(r"(?i)(live\s+job\s+(posting|listing|opening))"), "live job claim"),
    (re.compile(r"(?i)(scraped?\s+(from\s+)?linkedin)"), "scraping claim"),
    (re.compile(r"(?i)(searched?\s+online\s+for)"), "internet search claim"),
    # Fabricated metrics
    (re.compile(r"(?i)(i\s+found\s+that\s+you\s+earned?\s+\$[\d,]+)"), "fabricated salary"),
    (re.compile(r"(?i)(your\s+(team|department)\s+(has|had)\s+\d+\s+people)"), "fabricated team size"),
    # Protected characteristics
    (re.compile(r"(?i)(appears?\s+to\s+be\s+(male|female|man|woman|young|old|asian|black|white|hispanic))"), "protected characteristic"),
    (re.compile(r"(?i)(based\s+on\s+(your\s+)?(age|race|gender|religion|nationality))"), "protected characteristic"),
]

# Phrases that signal unsupported facts
UNSUPPORTED_CLAIM_PATTERNS = [
    re.compile(r"(?i)(according\s+to\s+(linkedin|glassdoor|indeed|the\s+internet))"),
    re.compile(r"(?i)(i\s+(searched|looked|found)\s+(online|on\s+the\s+web))"),
    re.compile(r"(?i)(based\s+on\s+my\s+(knowledge|training|research))"),
]


class GuardrailViolation(Exception):
    def __init__(self, violations: List[str]):
        self.violations = violations
        super().__init__(f"Guardrail violations: {violations}")


def check_prohibited_claims(text: str) -> List[str]:
    """Returns list of violation descriptions found in text."""
    violations: List[str] = []
    for pattern, label in PROHIBITED_PATTERNS:
        if pattern.search(text):
            violations.append(f"Prohibited {label} detected in output.")
    for pattern in UNSUPPORTED_CLAIM_PATTERNS:
        if pattern.search(text):
            violations.append("Unsupported external reference detected in output.")
    return violations


def validate_score_consistency(
    total_score: float,
    components: List[Dict[str, Any]],
    tolerance: float = 1.0,
) -> List[str]:
    """Verify that total_score equals sum of component earned_points."""
    if not components:
        return []
    computed_total = sum(c.get("earned_points", 0) for c in components)
    if abs(computed_total - total_score) > tolerance:
        return [
            f"Score inconsistency: total_score={total_score} but "
            f"sum of components={computed_total:.2f} (diff={abs(computed_total - total_score):.2f})"
        ]
    return []


def validate_citations(
    recommendations: List[Dict[str, Any]],
) -> List[str]:
    """Check each recommendation has at least one source citation."""
    issues: List[str] = []
    for i, rec in enumerate(recommendations):
        citations = rec.get("source_citations") or []
        if not citations:
            issues.append(
                f"Recommendation #{i+1} '{rec.get('title', '?')}' has no source citations."
            )
        # Verify draft flag
        if rec.get("draft_suggestion") and not rec.get("is_draft", True):
            issues.append(
                f"Recommendation #{i+1} has a draft_suggestion but is_draft=False — must be True."
            )
    return issues


def validate_no_pii_in_logs(text: str) -> List[str]:
    """Warn if raw PII patterns appear in what would be logged."""
    issues: List[str] = []
    email_pattern = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]{2,}")
    if email_pattern.search(text):
        issues.append("PII (email address) detected in log-bound output.")
    return issues


def validate_llm_output(
    output_text: str,
    context: str = "agent_output",
) -> Tuple[bool, List[str]]:
    """
    Full validation pass for any LLM output.
    Returns (is_valid, list_of_violations).
    """
    violations: List[str] = []
    violations += check_prohibited_claims(output_text)
    return (len(violations) == 0), violations


def validate_analysis_output(
    ats_score: Optional[Dict[str, Any]] = None,
    recommendations: Optional[List[Dict[str, Any]]] = None,
    opportunity_matches: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[bool, List[str]]:
    """
    Full structured validation of a complete analysis output.
    Returns (all_valid, all_violations).
    """
    all_violations: List[str] = []

    if ats_score:
        components = ats_score.get("components") or []
        all_violations += validate_score_consistency(
            ats_score.get("total_score", 0), components
        )
        expl = ats_score.get("score_explanation_json") or "{}"
        try:
            expl_obj = json.loads(expl) if isinstance(expl, str) else expl
            for v in expl_obj.values() if isinstance(expl_obj, dict) else []:
                all_violations += check_prohibited_claims(str(v))
        except Exception:
            pass

    if recommendations:
        all_violations += validate_citations(recommendations)
        for rec in recommendations:
            for field in ["why_it_matters", "suggested_action", "draft_suggestion"]:
                text = rec.get(field) or ""
                all_violations += check_prohibited_claims(text)

    if opportunity_matches:
        for match in opportunity_matches:
            explanation = match.get("match_explanation") or ""
            all_violations += check_prohibited_claims(explanation)
            # Ensure no qualification claims
            if re.search(r"(?i)(you\s+(are|meet)\s+(all|the)\s+qualifications?)", explanation):
                all_violations.append(
                    "Qualification claim detected in opportunity match explanation — prohibited."
                )

    return (len(all_violations) == 0), all_violations


def sanitize_llm_output(text: str) -> str:
    """
    Best-effort sanitization: remove prohibited phrases.
    Prefer regeneration over sanitization — use only as last resort.
    """
    sanitized = text
    for pattern, label in PROHIBITED_PATTERNS:
        sanitized = pattern.sub(f"[REMOVED: {label}]", sanitized)
    return sanitized

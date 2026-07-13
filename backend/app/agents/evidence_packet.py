"""
Evidence Packet Builder.

Constructs a structured, source-cited context block that is passed to
every agent before LLM generation. Agents receive ONLY this packet —
they never have unrestricted access to raw files or the internet.

The packet enforces:
  - Every fact is tagged with its source
  - Missing data is explicitly stated as "Not found"
  - No inferred data is presented as fact
  - Hallucination guardrails are embedded in the prompt
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional


GROUNDING_RULES = """
=== GROUNDING RULES — YOU MUST FOLLOW THESE EXACTLY ===
1. Only use facts explicitly provided in the Evidence Packet below.
2. If a fact is marked "Not found in uploaded documents", do NOT invent a value.
3. Never infer protected characteristics: age, race, gender, religion, nationality, disability.
4. Never predict interview likelihood, hiring probability, or eligibility.
5. Never invent metrics, percentages, revenue, team sizes, or years of experience.
6. All draft resume rewrites MUST be labeled: "DRAFT SUGGESTION — verify accuracy before using."
7. Distinguish clearly: [EXTRACTED FACT] vs [INFERENCE] vs [RECOMMENDATION] vs [DRAFT].
8. When recommending a keyword, cite the exact job description it came from.
9. If confidence is low, say "Low confidence:" before the statement.
10. Do not access the internet. Do not reference external sources.
=== END GROUNDING RULES ===
"""


def build_evidence_packet(
    resume_data: Optional[Dict[str, Any]] = None,
    linkedin_data: Optional[Dict[str, Any]] = None,
    job_data: Optional[Dict[str, Any]] = None,
    ats_score_result: Optional[Dict[str, Any]] = None,
    matched_keywords: Optional[List[str]] = None,
    missing_keywords: Optional[List[str]] = None,
    inconsistencies: Optional[List[str]] = None,
    resume_filename: str = "resume",
    linkedin_filename: Optional[str] = None,
    job_filename: Optional[str] = None,
) -> str:
    """
    Build a structured evidence packet string to prepend to every agent prompt.
    """
    lines: List[str] = [GROUNDING_RULES, "\n=== EVIDENCE PACKET ===\n"]

    # ── Resume facts ────────────────────────────────────────────────────────
    if resume_data:
        lines.append(f"[SOURCE: resume | file: {resume_filename}]")
        lines.append(f"  Name: {resume_data.get('full_name') or 'Not found in uploaded documents'}")
        lines.append(f"  Email: {resume_data.get('email') or 'Not found in uploaded documents'}")
        lines.append(f"  Phone: {resume_data.get('phone') or 'Not found in uploaded documents'}")
        lines.append(f"  Location: {resume_data.get('location') or 'Not found in uploaded documents'}")
        lines.append(f"  LinkedIn URL: {resume_data.get('linkedin_url') or 'Not found in uploaded documents'}")
        lines.append(f"  Summary: {(resume_data.get('summary') or 'Not found')[:300]}")

        skills = resume_data.get("skills") or []
        lines.append(f"  Skills ({len(skills)}): {', '.join(skills[:30]) or 'Not found'}")

        experience = resume_data.get("experience") or []
        lines.append(f"  Experience entries: {len(experience)}")
        for i, exp in enumerate(experience[:5]):
            lines.append(
                f"    [{i+1}] Title: {exp.get('title') or 'N/A'} | "
                f"Company: {exp.get('company') or 'N/A'} | "
                f"Dates: {exp.get('dates') or 'N/A'}"
            )

        education = resume_data.get("education") or []
        lines.append(f"  Education entries: {len(education)}")
        for edu in education[:3]:
            lines.append(
                f"    - {edu.get('degree') or 'N/A'} at {edu.get('institution') or 'N/A'}"
            )

        certs = resume_data.get("certifications") or []
        lines.append(f"  Certifications: {', '.join(certs[:10]) or 'Not found'}")

        risks = resume_data.get("parsing_risks") or []
        lines.append(f"  Parsing risks: {'; '.join(risks[:5]) or 'None detected'}")

    else:
        lines.append("[RESUME: Not provided]")

    # ── LinkedIn facts ───────────────────────────────────────────────────────
    lines.append("")
    if linkedin_data:
        lines.append(f"[SOURCE: linkedin | file: {linkedin_filename or 'linkedin profile'}]")
        lines.append(f"  Headline: {linkedin_data.get('headline') or 'Not found'}")
        lines.append(f"  About: {(linkedin_data.get('about') or 'Not found')[:200]}")
        li_skills = linkedin_data.get("skills") or []
        lines.append(f"  Skills ({len(li_skills)}): {', '.join(li_skills[:20]) or 'Not found'}")
        li_exp = linkedin_data.get("experience") or []
        lines.append(f"  Experience entries: {len(li_exp)}")
        for exp in li_exp[:3]:
            lines.append(
                f"    - {exp.get('title') or 'N/A'} at {exp.get('company') or 'N/A'}"
            )
    else:
        lines.append("[LINKEDIN: Not provided — no LinkedIn content to analyze]")

    # ── Job description facts ────────────────────────────────────────────────
    lines.append("")
    if job_data:
        lines.append(f"[SOURCE: job_description | file: {job_filename or 'job description'}]")
        lines.append(f"  Title: {job_data.get('title') or 'Not extracted'}")
        lines.append(f"  Company: {job_data.get('company') or 'Not extracted'}")
        job_kw = (job_data.get("keywords") or []) + (job_data.get("skills_required") or [])
        lines.append(f"  Keywords/requirements ({len(job_kw)}): {', '.join(job_kw[:30])}")
        reqs = job_data.get("requirements") or []
        lines.append(f"  Requirements ({len(reqs)}):")
        for req in reqs[:10]:
            lines.append(f"    - {req}")
    else:
        lines.append("[JOB DESCRIPTION: Not provided — general analysis only]")

    # ── Scoring facts ────────────────────────────────────────────────────────
    lines.append("")
    if ats_score_result:
        lines.append("[ATS SCORE — DETERMINISTIC, NOT LLM-GENERATED]")
        lines.append(f"  Total: {ats_score_result.get('total_score', 0):.1f}/100")
        lines.append(f"  Type: {ats_score_result.get('score_type', 'general')}")
        for comp in (ats_score_result.get("components") or []):
            lines.append(
                f"  {comp.get('name', '')}: {comp.get('earned_points', 0):.1f}/"
                f"{comp.get('max_points', 0):.1f}"
            )

    # ── Keyword analysis ─────────────────────────────────────────────────────
    if matched_keywords is not None:
        lines.append(f"\n[KEYWORD MATCH]")
        lines.append(f"  Matched: {', '.join(matched_keywords[:20]) or 'None'}")
        lines.append(f"  Missing: {', '.join((missing_keywords or [])[:20]) or 'None'}")

    # ── Inconsistencies ──────────────────────────────────────────────────────
    if inconsistencies:
        lines.append(f"\n[RESUME/LINKEDIN INCONSISTENCIES]")
        for issue in inconsistencies:
            lines.append(f"  - {issue}")

    lines.append("\n=== END EVIDENCE PACKET ===\n")
    return "\n".join(lines)

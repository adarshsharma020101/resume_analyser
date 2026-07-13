"""
Analysis orchestrator — ties together scoring, agents, and matching
into a single AnalysisSession stored in the database.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.crew import run_ats_analysis_crew, run_opportunity_explanation_crew
from app.agents.evidence_packet import build_evidence_packet
from app.agents.guardrails import validate_analysis_output
from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.analysis import (
    AnalysisSession, ATSScore, ATSScoreComponent,
    ModelRun, OpportunityMatch, Recommendation
)
from app.models.document import Document
from app.models.job import JobDescription, JobOpportunity
from app.models.profile import LinkedInProfile, ResumeProfile
from app.services.ats_scorer import compute_ats_score
from app.services.opportunity_matcher import match_opportunities
from app.services.recommendation_engine import generate_recommendations
from app.services.vector_store import query_similar

settings = get_settings()
log = get_logger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def run_full_analysis(
    db: AsyncSession,
    session_id: str,
    user_id: str,
    resume_doc_id: str,
    linkedin_doc_id: Optional[str] = None,
    target_job_id: Optional[str] = None,
    job_ids_to_match: Optional[List[str]] = None,
) -> AnalysisSession:
    """
    Full analysis pipeline:
    1. Load resume profile + raw text
    2. Optionally load LinkedIn profile
    3. Optionally load target job description
    4. Compute deterministic ATS score
    5. Generate deterministic recommendations
    6. Run CrewAI agents for explanations (grounded in evidence packet)
    7. Run opportunity matching against local jobs
    8. Validate all outputs
    9. Persist results to DB
    """
    session = await db.get(AnalysisSession, session_id)
    if not session:
        raise ValueError(f"Analysis session {session_id} not found.")

    session.status = "running"
    session.updated_at = _utcnow() if hasattr(session, "updated_at") else None
    await db.flush()

    try:
        # ── Load Resume ──────────────────────────────────────────────────────
        resume_doc = await db.get(Document, resume_doc_id)
        resume_profile = await _get_resume_profile(db, resume_doc_id)
        if not resume_profile:
            raise ValueError(f"No resume profile found for document {resume_doc_id}")

        resume_data = _profile_to_dict(resume_profile)
        resume_data["raw_text"] = await _get_document_raw_text(db, resume_doc_id)
        parsing_risks = json.loads(resume_profile.parsing_risks_json or "[]")

        # ── Load LinkedIn ────────────────────────────────────────────────────
        linkedin_data: Optional[Dict[str, Any]] = None
        linkedin_doc = None
        if linkedin_doc_id:
            linkedin_doc = await db.get(Document, linkedin_doc_id)
            linkedin_profile = await _get_linkedin_profile(db, linkedin_doc_id)
            if linkedin_profile:
                linkedin_data = _li_profile_to_dict(linkedin_profile)

        # ── Load Target Job ──────────────────────────────────────────────────
        job_data: Optional[Dict[str, Any]] = None
        job_doc = None
        if target_job_id:
            job_desc = await db.get(JobDescription, target_job_id)
            if job_desc:
                job_data = {
                    "title": job_desc.title,
                    "company": job_desc.company,
                    "raw_text": job_desc.raw_text,
                    "requirements": json.loads(job_desc.requirements_json or "[]"),
                    "skills_required": json.loads(job_desc.skills_required_json or "[]"),
                    "keywords": json.loads(job_desc.keywords_json or "[]"),
                }

        # ── ATS Score (deterministic) ────────────────────────────────────────
        score_result, matched_kw, missing_kw, inconsistencies = compute_ats_score(
            resume_data=resume_data,
            parsing_risks=parsing_risks,
            job_data=job_data,
            linkedin_data=linkedin_data,
        )

        # ── Recommendations (deterministic) ──────────────────────────────────
        det_recs = generate_recommendations(
            score_result=score_result,
            resume_data=resume_data,
            parsing_risks=parsing_risks,
            matched_keywords=matched_kw,
            missing_keywords=missing_kw,
            inconsistencies=inconsistencies,
            resume_filename=resume_doc.original_filename if resume_doc else "resume",
            job_filename=job_data.get("title") if job_data else None,
            linkedin_filename=linkedin_doc.original_filename if linkedin_doc else None,
            linkedin_data=linkedin_data,
        )
        det_recs_dicts = [r.to_dict() for r in det_recs]

        # ── CrewAI Agents (explanations only, grounded) ───────────────────────
        score_result_dict = {
            "total_score": score_result.total_score,
            "score_type": score_result.score_type,
            "components": [
                {"name": c.name, "max_points": c.max_points, "earned_points": c.earned_points}
                for c in score_result.components
            ],
        }

        crew_result = await run_ats_analysis_crew(
            resume_data=resume_data,
            parsing_risks=parsing_risks,
            job_data=job_data,
            linkedin_data=linkedin_data,
            ats_score_result=score_result_dict,
            deterministic_recs=det_recs_dicts,
            matched_keywords=matched_kw,
            missing_keywords=missing_kw,
            inconsistencies=inconsistencies,
            resume_filename=resume_doc.original_filename if resume_doc else "resume",
            job_filename=job_data.get("title") if job_data else None,
            linkedin_filename=linkedin_doc.original_filename if linkedin_doc else None,
        )

        enhanced_recs = crew_result.get("enhanced_recommendations", det_recs_dicts)
        score_explanations = crew_result.get("score_explanations", {})
        qa_report = crew_result.get("qa_report", {})

        # ── Validate outputs ──────────────────────────────────────────────────
        is_valid, violations = validate_analysis_output(
            ats_score=score_result_dict,
            recommendations=enhanced_recs,
        )
        if not is_valid:
            log.warning("Analysis output violations: %s", violations)
            # Use deterministic-only recs as fallback
            enhanced_recs = det_recs_dicts

        # ── Store ATS Score ───────────────────────────────────────────────────
        comp_dict = {c.name: c for c in score_result.components}
        ats_score_record = ATSScore(
            session_id=session_id,
            total_score=score_result.total_score,
            score_type=score_result.score_type,
            disclaimer=score_result.disclaimer,
            parseability_score=comp_dict.get("parseability", _dummy()).earned_points,
            section_structure_score=comp_dict.get("section_structure", _dummy()).earned_points,
            contact_completeness_score=comp_dict.get("contact_completeness", _dummy()).earned_points,
            keyword_coverage_score=comp_dict.get("keyword_coverage", _dummy()).earned_points,
            experience_alignment_score=comp_dict.get("experience_alignment", _dummy()).earned_points,
            achievement_quality_score=comp_dict.get("achievement_quality", _dummy()).earned_points,
            readability_score=comp_dict.get("readability", _dummy()).earned_points,
            linkedin_consistency_score=comp_dict.get("linkedin_consistency", _dummy()).earned_points,
            score_explanation_json=json.dumps(score_explanations),
            created_at=_utcnow(),
        )
        db.add(ats_score_record)
        await db.flush()

        # Store score components
        for comp in score_result.components:
            db.add(ATSScoreComponent(
                ats_score_id=ats_score_record.id,
                component_name=comp.name,
                max_points=comp.max_points,
                earned_points=comp.earned_points,
                deduction_reason="\n".join(comp.deductions[:10]) if comp.deductions else None,
                evidence_json=json.dumps(comp.evidence[:10]),
                created_at=_utcnow(),
            ))

        # Store recommendations
        for rec_dict in enhanced_recs:
            db.add(Recommendation(
                session_id=session_id,
                priority=rec_dict.get("priority", "medium"),
                category=rec_dict.get("category", "content"),
                title=rec_dict.get("title", "")[:256],
                why_it_matters=rec_dict.get("why_it_matters", ""),
                evidence_from_resume=rec_dict.get("evidence_from_resume"),
                evidence_from_job=rec_dict.get("evidence_from_job"),
                suggested_action=rec_dict.get("suggested_action", ""),
                draft_suggestion=rec_dict.get("draft_suggestion"),
                is_draft=rec_dict.get("is_draft", True),
                confidence=rec_dict.get("confidence", 0.8),
                source_citations_json=json.dumps(rec_dict.get("source_citations", [])),
                created_at=_utcnow(),
            ))

        # ── Opportunity Matching ──────────────────────────────────────────────
        if job_ids_to_match:
            await _run_opportunity_matching(
                db=db,
                session_id=session_id,
                user_id=user_id,
                job_ids=job_ids_to_match,
                resume_data=resume_data,
                linkedin_data=linkedin_data,
            )

        # ── Log model run ─────────────────────────────────────────────────────
        db.add(ModelRun(
            session_id=session_id,
            model_name=settings.OLLAMA_LLM_MODEL,
            task_name="ats_analysis_crew",
            success=True,
            created_at=_utcnow(),
        ))

        session.status = "completed"
        session.completed_at = _utcnow()
        await db.flush()
        return session

    except Exception as e:
        log.error("Analysis session %s failed: %s", session_id, e)
        session.status = "failed"
        session.error_message = str(e)[:1000]
        await db.flush()
        raise


# ── Helpers ────────────────────────────────────────────────────────────────────

class _dummy:
    earned_points = 0.0


async def _get_resume_profile(db: AsyncSession, document_id: str) -> Optional[ResumeProfile]:
    stmt = select(ResumeProfile).where(ResumeProfile.document_id == document_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def _get_linkedin_profile(db: AsyncSession, document_id: str) -> Optional[LinkedInProfile]:
    stmt = select(LinkedInProfile).where(LinkedInProfile.document_id == document_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def _get_document_raw_text(db: AsyncSession, document_id: str) -> str:
    from app.models.document import DocumentVersion
    stmt = (
        select(DocumentVersion.raw_text)
        .where(DocumentVersion.document_id == document_id)
        .order_by(DocumentVersion.version_number.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()
    return row or ""


def _profile_to_dict(profile: ResumeProfile) -> Dict[str, Any]:
    return {
        "full_name": profile.full_name,
        "email": profile.email,
        "phone": profile.phone,
        "location": profile.location,
        "linkedin_url": profile.linkedin_url,
        "summary": profile.summary,
        "skills": json.loads(profile.skills_json or "[]"),
        "experience": json.loads(profile.experience_json or "[]"),
        "education": json.loads(profile.education_json or "[]"),
        "certifications": json.loads(profile.certifications_json or "[]"),
        "projects": json.loads(profile.projects_json or "[]"),
        "achievements": json.loads(profile.achievements_json or "[]"),
        "section_headings": json.loads(profile.section_headings_json or "[]"),
        "keywords": json.loads(profile.keywords_json or "[]"),
        "parsing_risks": json.loads(profile.parsing_risks_json or "[]"),
    }


def _li_profile_to_dict(profile: LinkedInProfile) -> Dict[str, Any]:
    return {
        "headline": profile.headline,
        "about": profile.about,
        "experience": json.loads(profile.experience_json or "[]"),
        "skills": json.loads(profile.skills_json or "[]"),
        "education": json.loads(profile.education_json or "[]"),
        "certifications": json.loads(profile.certifications_json or "[]"),
        "projects": json.loads(profile.projects_json or "[]"),
        "recommendations": json.loads(profile.recommendations_json or "[]"),
        "keywords": json.loads(profile.keywords_json or "[]"),
    }


async def _run_opportunity_matching(
    db: AsyncSession,
    session_id: str,
    user_id: str,
    job_ids: List[str],
    resume_data: Dict[str, Any],
    linkedin_data: Optional[Dict[str, Any]],
) -> None:
    """Match resume against specified job opportunities and store results."""
    from sqlalchemy import select
    stmt = select(JobOpportunity).where(
        JobOpportunity.id.in_(job_ids),
        JobOpportunity.user_id == user_id,
    )
    result = await db.execute(stmt)
    opportunities = result.scalars().all()

    opp_dicts = [
        {
            "id": o.id,
            "title": o.title,
            "company": o.company,
            "location": o.location,
            "source_file": o.source_file,
            "raw_text": o.raw_text or "",
            "keywords_json": o.keywords_json,
            "skills_required_json": o.skills_required_json,
            "requirements_json": o.requirements_json,
        }
        for o in opportunities
    ]

    match_results = await match_opportunities(
        resume_data=resume_data,
        opportunities=opp_dicts,
        linkedin_data=linkedin_data,
        user_id=user_id,
    )

    # Get LLM explanations
    match_summaries = [r.to_dict() for r in match_results[:10]]
    evidence_packet = build_evidence_packet(
        resume_data=resume_data,
        linkedin_data=linkedin_data,
    )
    explained = await run_opportunity_explanation_crew(evidence_packet, match_summaries)
    exp_by_id = {e.get("opportunity_id"): e.get("match_explanation") for e in explained}

    for match in match_results:
        db.add(OpportunityMatch(
            session_id=session_id,
            opportunity_id=match.opportunity_id,
            keyword_overlap_score=match.keyword_overlap_score,
            embedding_similarity_score=match.embedding_similarity_score,
            bm25_score=match.bm25_score,
            final_match_score=match.final_match_score,
            matched_skills_json=json.dumps(match.matched_skills),
            missing_requirements_json=json.dumps(match.missing_requirements),
            resume_evidence_json=json.dumps(match.resume_evidence),
            linkedin_evidence_json=json.dumps(match.linkedin_evidence),
            match_explanation=exp_by_id.get(match.opportunity_id),
            ranking_reasons_json=json.dumps(match.ranking_reasons),
            confidence=match.confidence,
            match_label=match.match_label,
            created_at=_utcnow(),
        ))

"""Analysis routes — trigger analysis, get results, get provenance."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.base import get_db
from app.models.analysis import AnalysisSession, ATSScore, ATSScoreComponent, Recommendation, OpportunityMatch
from app.models.document import EvidenceReference
from app.models.user import User
from app.services.analysis_orchestrator import run_full_analysis

router = APIRouter(prefix="/analysis", tags=["analysis"])


class StartAnalysisRequest(BaseModel):
    resume_document_id: str
    linkedin_document_id: Optional[str] = None
    target_job_id: Optional[str] = None
    job_ids_to_match: Optional[List[str]] = None


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def start_analysis(
    body: StartAnalysisRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Kick off a full analysis session (runs in background)."""
    session = AnalysisSession(
        id=str(uuid4()),
        user_id=current_user.id,
        resume_document_id=body.resume_document_id,
        linkedin_document_id=body.linkedin_document_id,
        target_job_id=body.target_job_id,
        status="pending",
        analysis_type="job_specific" if body.target_job_id else "general",
        created_at=datetime.now(timezone.utc),
    )
    db.add(session)
    await db.flush()
    session_id = session.id

    background_tasks.add_task(
        _run_analysis_task,
        session_id=session_id,
        user_id=current_user.id,
        resume_doc_id=body.resume_document_id,
        linkedin_doc_id=body.linkedin_document_id,
        target_job_id=body.target_job_id,
        job_ids_to_match=body.job_ids_to_match,
    )

    return {"session_id": session_id, "status": "pending", "message": "Analysis started"}


async def _run_analysis_task(**kwargs):
    """Background task wrapper that creates its own DB session."""
    from app.db.base import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        await run_full_analysis(db=db, **kwargs)


@router.get("/{session_id}")
async def get_analysis_result(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get full analysis result for a session."""
    session = await db.get(AnalysisSession, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found")

    result: dict = {
        "session_id": session_id,
        "status": session.status,
        "analysis_type": session.analysis_type,
        "created_at": session.created_at.isoformat(),
        "completed_at": session.completed_at.isoformat() if session.completed_at else None,
        "error_message": session.error_message,
    }

    if session.status == "completed":
        # ATS Score
        stmt = select(ATSScore).where(ATSScore.session_id == session_id)
        ats = (await db.execute(stmt)).scalar_one_or_none()
        if ats:
            comp_stmt = select(ATSScoreComponent).where(ATSScoreComponent.ats_score_id == ats.id)
            comps = (await db.execute(comp_stmt)).scalars().all()
            result["ats_score"] = {
                "total_score": ats.total_score,
                "score_type": ats.score_type,
                "disclaimer": ats.disclaimer,
                "parseability": ats.parseability_score,
                "section_structure": ats.section_structure_score,
                "contact_completeness": ats.contact_completeness_score,
                "keyword_coverage": ats.keyword_coverage_score,
                "experience_alignment": ats.experience_alignment_score,
                "achievement_quality": ats.achievement_quality_score,
                "readability": ats.readability_score,
                "linkedin_consistency": ats.linkedin_consistency_score,
                "score_explanations": json.loads(ats.score_explanation_json or "{}"),
            }
            result["score_components"] = [
                {
                    "component_name": c.component_name,
                    "max_points": c.max_points,
                    "earned_points": c.earned_points,
                    "deduction_reason": c.deduction_reason,
                    "evidence": json.loads(c.evidence_json or "[]"),
                }
                for c in comps
            ]

        # Recommendations
        rec_stmt = (
            select(Recommendation)
            .where(Recommendation.session_id == session_id)
            .order_by(Recommendation.priority)
        )
        recs = (await db.execute(rec_stmt)).scalars().all()
        result["recommendations"] = [
            {
                "id": r.id,
                "priority": r.priority,
                "category": r.category,
                "title": r.title,
                "why_it_matters": r.why_it_matters,
                "evidence_from_resume": r.evidence_from_resume,
                "evidence_from_job": r.evidence_from_job,
                "suggested_action": r.suggested_action,
                "draft_suggestion": r.draft_suggestion,
                "is_draft": r.is_draft,
                "confidence": r.confidence,
                "source_citations": json.loads(r.source_citations_json or "[]"),
                "_draft_notice": (
                    "DRAFT SUGGESTION — verify accuracy before using. "
                    "Never add credentials you do not have."
                ) if r.draft_suggestion else None,
            }
            for r in recs
        ]

        # Opportunity matches
        match_stmt = (
            select(OpportunityMatch)
            .where(OpportunityMatch.session_id == session_id)
            .order_by(OpportunityMatch.final_match_score.desc())
        )
        matches = (await db.execute(match_stmt)).scalars().all()
        result["opportunity_matches"] = [
            {
                "id": m.id,
                "opportunity_id": m.opportunity_id,
                "keyword_overlap_score": m.keyword_overlap_score,
                "embedding_similarity_score": m.embedding_similarity_score,
                "bm25_score": m.bm25_score,
                "final_match_score": m.final_match_score,
                "match_label": m.match_label,
                "matched_skills": json.loads(m.matched_skills_json or "[]"),
                "missing_requirements": json.loads(m.missing_requirements_json or "[]"),
                "resume_evidence": json.loads(m.resume_evidence_json or "[]"),
                "linkedin_evidence": json.loads(m.linkedin_evidence_json or "[]"),
                "match_explanation": m.match_explanation,
                "ranking_reasons": json.loads(m.ranking_reasons_json or "[]"),
                "confidence": m.confidence,
            }
            for m in matches
        ]

    return result


@router.get("/{session_id}/provenance")
async def get_provenance(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return full provenance chain — every claim with source, excerpt, page, confidence, hash."""
    session = await db.get(AnalysisSession, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found")

    stmt = select(EvidenceReference).where(EvidenceReference.analysis_session_id == session_id)
    refs = (await db.execute(stmt)).scalars().all()

    return {
        "session_id": session_id,
        "evidence_references": [
            {
                "id": r.id,
                "claim_text": r.claim_text,
                "source_type": r.source_type,
                "source_document_id": r.source_document_id,
                "source_file_name": r.source_file_name,
                "source_page": r.source_page,
                "source_excerpt": r.source_excerpt,
                "document_hash": r.document_hash,
                "confidence": r.confidence,
                "created_at": r.created_at.isoformat(),
            }
            for r in refs
        ],
        "total_references": len(refs),
    }


@router.get("")
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all analysis sessions for current user."""
    stmt = (
        select(AnalysisSession)
        .where(AnalysisSession.user_id == current_user.id)
        .order_by(AnalysisSession.created_at.desc())
        .limit(50)
    )
    sessions = (await db.execute(stmt)).scalars().all()
    return [
        {
            "session_id": s.id,
            "status": s.status,
            "analysis_type": s.analysis_type,
            "created_at": s.created_at.isoformat(),
            "completed_at": s.completed_at.isoformat() if s.completed_at else None,
        }
        for s in sessions
    ]

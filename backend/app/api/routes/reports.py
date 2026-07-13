"""Report generation and download routes."""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.base import get_db
from app.models.analysis import AnalysisSession, ATSScore, ATSScoreComponent, OpportunityMatch, Recommendation
from app.models.user import User
from app.services.report_generator import (
    generate_report_html, generate_report_json, generate_pdf_report, save_report
)

router = APIRouter(prefix="/reports", tags=["reports"])


class GenerateReportRequest(BaseModel):
    session_id: str
    format: str = "json"   # json | html | pdf


@router.post("/generate")
async def generate_report(
    body: GenerateReportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate and save a report for an analysis session."""
    session = await db.get(AnalysisSession, body.session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status != "completed":
        raise HTTPException(status_code=400, detail=f"Session is not completed (status: {session.status})")

    # Gather data
    data = await _gather_report_data(db, body.session_id)

    fmt = body.format.lower()
    if fmt == "json":
        content = generate_report_json(data)
        file_path = save_report(content, body.session_id, "json")
    elif fmt == "html":
        content = generate_report_html(data)
        file_path = save_report(content, body.session_id, "html")
    elif fmt == "pdf":
        html_content = generate_report_html(data)
        file_path = await generate_pdf_report(html_content, body.session_id)
    else:
        raise HTTPException(status_code=400, detail="format must be json, html, or pdf")

    return {
        "file_path": str(file_path),
        "format": fmt,
        "session_id": body.session_id,
        "download_url": f"/api/reports/download/{body.session_id}/{fmt}",
    }


@router.get("/download/{session_id}/{fmt}")
async def download_report(
    session_id: str,
    fmt: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Download a previously generated report file."""
    from app.core.config import get_settings
    settings = get_settings()
    file_path = settings.REPORTS_DIR / f"report_{session_id}.{fmt}"

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Report not found — generate it first")

    media_types = {
        "json": "application/json",
        "html": "text/html",
        "pdf": "application/pdf",
    }
    return FileResponse(
        path=str(file_path),
        media_type=media_types.get(fmt, "application/octet-stream"),
        filename=f"ats_report_{session_id}.{fmt}",
    )


async def _gather_report_data(db: AsyncSession, session_id: str) -> dict:
    session = await db.get(AnalysisSession, session_id)

    stmt = select(ATSScore).where(ATSScore.session_id == session_id)
    ats = (await db.execute(stmt)).scalar_one_or_none()

    score_components = []
    if ats:
        comp_stmt = select(ATSScoreComponent).where(ATSScoreComponent.ats_score_id == ats.id)
        score_components = (await db.execute(comp_stmt)).scalars().all()

    rec_stmt = select(Recommendation).where(Recommendation.session_id == session_id)
    recs = (await db.execute(rec_stmt)).scalars().all()

    match_stmt = (
        select(OpportunityMatch)
        .where(OpportunityMatch.session_id == session_id)
        .order_by(OpportunityMatch.final_match_score.desc())
    )
    matches = (await db.execute(match_stmt)).scalars().all()

    return {
        "session_id": session_id,
        "ats_score": {
            "total_score": ats.total_score if ats else 0,
            "score_type": ats.score_type if ats else "general",
            "disclaimer": ats.disclaimer if ats else "",
        } if ats else {},
        "score_components": [
            {
                "component_name": c.component_name,
                "max_points": c.max_points,
                "earned_points": c.earned_points,
                "deduction_reason": c.deduction_reason,
            }
            for c in score_components
        ],
        "score_explanations": json.loads(ats.score_explanation_json or "{}") if ats else {},
        "recommendations": [
            {
                "priority": r.priority,
                "category": r.category,
                "title": r.title,
                "why_it_matters": r.why_it_matters,
                "evidence_from_resume": r.evidence_from_resume,
                "evidence_from_job": r.evidence_from_job,
                "suggested_action": r.suggested_action,
                "draft_suggestion": r.draft_suggestion,
                "is_draft": r.is_draft,
                "source_citations": json.loads(r.source_citations_json or "[]"),
            }
            for r in recs
        ],
        "opportunity_matches": [
            {
                "opportunity_id": m.opportunity_id,
                "final_match_score": m.final_match_score,
                "match_label": m.match_label,
                "matched_skills": json.loads(m.matched_skills_json or "[]"),
                "missing_requirements": json.loads(m.missing_requirements_json or "[]"),
                "match_explanation": m.match_explanation,
                "source_file": None,
            }
            for m in matches
        ],
    }

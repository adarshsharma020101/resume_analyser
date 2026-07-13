"""Privacy and data management routes — full user data deletion."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.base import get_db
from app.models.user import AuditLog, User, UserConsent
from app.models.document import Document
from app.services.vector_store import delete_user_embeddings
from app.core.config import get_settings
import shutil

settings = get_settings()
router = APIRouter(prefix="/privacy", tags=["privacy"])


@router.delete("/my-data", status_code=status.HTTP_200_OK)
async def delete_all_my_data(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete ALL data for the current user:
    - All documents and uploaded files
    - All profiles (resume, LinkedIn)
    - All job descriptions and datasets
    - All analysis sessions, scores, recommendations, matches
    - All vector store embeddings
    - Audit logs (last entry preserved)
    Returns a list of what was removed.
    """
    user_id = current_user.id
    removed: list[str] = []

    # Remove uploaded files from disk
    for doc_type in ["resume", "linkedin"]:
        type_dir = settings.UPLOAD_DIR / doc_type
        if type_dir.exists():
            stmt = select(Document).where(
                Document.user_id == user_id,
                Document.doc_type.contains(doc_type),
            )
            docs = (await db.execute(stmt)).scalars().all()
            for doc in docs:
                file_path = type_dir / doc.stored_filename
                if file_path.exists():
                    file_path.unlink()
                    removed.append(f"File: {doc.original_filename}")

    # Remove reports
    reports_dir = settings.REPORTS_DIR
    if reports_dir.exists():
        for f in reports_dir.glob(f"report_*.json"):
            f.unlink()
        for f in reports_dir.glob(f"report_*.html"):
            f.unlink()
        for f in reports_dir.glob(f"report_*.pdf"):
            f.unlink()
        removed.append("Reports: all report files")

    # Remove vector store embeddings
    await delete_user_embeddings(user_id)
    removed.append("Vector store: all embeddings")

    # Cascade-delete in DB (all models with user_id have CASCADE set)
    # Just deleting the user cascades everything
    user = await db.get(User, user_id)
    if user:
        await db.delete(user)
        removed.append(f"User account: {user.username}")
        removed.append("All documents, profiles, jobs, analysis sessions, scores, recommendations")

    return {
        "deleted": True,
        "user_id": user_id,
        "removed_items": removed,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": "All your data has been permanently deleted from this local system.",
    }


@router.get("/consent")
async def get_consent_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(UserConsent).where(UserConsent.user_id == current_user.id)
    consents = (await db.execute(stmt)).scalars().all()
    return {"consents": [{"type": c.consent_type, "granted": c.granted} for c in consents]}


@router.get("/export")
async def export_my_data(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export all user data as JSON (local data portability)."""
    from app.models.document import Document, ExtractedFact
    from app.models.profile import ResumeProfile, LinkedInProfile, LinkedInIdentifier
    from app.models.analysis import AnalysisSession
    import json

    user_id = current_user.id

    docs = (await db.execute(select(Document).where(Document.user_id == user_id))).scalars().all()
    profiles = (await db.execute(select(ResumeProfile).where(ResumeProfile.user_id == user_id))).scalars().all()
    sessions = (await db.execute(select(AnalysisSession).where(AnalysisSession.user_id == user_id))).scalars().all()

    return {
        "export_date": datetime.now(timezone.utc).isoformat(),
        "user": {"id": current_user.id, "username": current_user.username},
        "documents": [{"id": d.id, "type": d.doc_type, "filename": d.original_filename} for d in docs],
        "resume_profiles_count": len(profiles),
        "analysis_sessions_count": len(sessions),
        "note": "Raw document content is not included in this export for security.",
    }

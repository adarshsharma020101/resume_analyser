"""Document upload routes — resume, LinkedIn identifier, LinkedIn profile."""
from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_ollama_client
from app.core.config import get_settings
from app.core.file_security import safe_extract_zip
from app.db.base import get_db
from app.models.document import Document
from app.models.profile import LinkedInIdentifier, ResumeProfile
from app.models.user import User
from app.services.document_intake import (
    ingest_linkedin_identifier, ingest_linkedin_profile, ingest_resume
)
from app.services.vector_store import upsert_document_embedding

settings = get_settings()
router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/resume", status_code=status.HTTP_201_CREATED)
async def upload_resume(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    ollama=Depends(get_ollama_client),
):
    """Upload and parse a resume (PDF, DOCX, TXT)."""
    data = await file.read()
    doc, profile = await ingest_resume(
        db=db,
        user_id=current_user.id,
        file_data=data,
        original_filename=file.filename or "resume.txt",
        ollama_client=ollama,
        llm_model=settings.OLLAMA_LLM_MODEL,
    )

    # Index in vector store for semantic matching
    raw_text = json.loads(profile.keywords_json or "[]")
    combined_text = " ".join([
        profile.summary or "",
        " ".join(json.loads(profile.skills_json or "[]")),
        " ".join(raw_text),
    ])
    await upsert_document_embedding(
        collection_name=settings.CHROMA_COLLECTION_RESUMES,
        doc_id=doc.id,
        text=combined_text,
        metadata={"user_id": current_user.id, "doc_type": "resume"},
    )

    return {
        "document_id": doc.id,
        "filename": doc.original_filename,
        "parsing_status": doc.parsing_status,
        "parsing_warnings": json.loads(doc.parsing_warnings or "[]"),
        "is_duplicate": doc.is_duplicate,
        "profile_summary": {
            "full_name": profile.full_name,
            "skills_count": len(json.loads(profile.skills_json or "[]")),
            "experience_count": len(json.loads(profile.experience_json or "[]")),
            "education_count": len(json.loads(profile.education_json or "[]")),
            "completeness_score": profile.completeness_score,
            "section_headings": json.loads(profile.section_headings_json or "[]"),
        },
    }


@router.post("/linkedin/identifier", status_code=status.HTTP_201_CREATED)
async def add_linkedin_identifier(
    linkedin_url: Optional[str] = Form(None),
    linkedin_id: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Save a LinkedIn URL or ID for reference — profile content cannot be scanned."""
    if not linkedin_url and not linkedin_id:
        raise HTTPException(status_code=400, detail="Provide either linkedin_url or linkedin_id")

    identifier = await ingest_linkedin_identifier(
        db=db,
        user_id=current_user.id,
        linkedin_url=linkedin_url,
        linkedin_id=linkedin_id,
    )
    return {
        "identifier_id": identifier.id,
        "linkedin_url": identifier.linkedin_url,
        "linkedin_id": identifier.linkedin_id,
        "disclaimer": identifier.disclaimer,
        "message": (
            "LinkedIn identifier saved. "
            "Profile content cannot be analyzed until you upload, export, or paste profile data."
        ),
    }


@router.post("/linkedin/profile", status_code=status.HTTP_201_CREATED)
async def upload_linkedin_profile(
    file: UploadFile = File(...),
    profile_format: str = Form("auto"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload LinkedIn profile content (PDF, export ZIP, JSON, CSV, pasted TXT)."""
    data = await file.read()
    filename = file.filename or "linkedin.txt"

    # Handle ZIP export — extract files before passing to intake
    extracted_zip_files = None
    import os
    ext = os.path.splitext(filename)[1].lower()
    if ext == ".zip":
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmpdir:
            extracted = safe_extract_zip(data, Path(tmpdir))
            extracted_zip_files = {}
            for p in extracted:
                extracted_zip_files[p.name] = p.read_bytes()

    doc, profile = await ingest_linkedin_profile(
        db=db,
        user_id=current_user.id,
        file_data=data,
        original_filename=filename,
        profile_format=profile_format,
        extracted_zip_files=extracted_zip_files,
    )

    # Index in vector store
    li_text = " ".join(filter(None, [
        profile.headline or "",
        profile.about or "",
        " ".join(json.loads(profile.skills_json or "[]")),
    ]))
    await upsert_document_embedding(
        collection_name=settings.CHROMA_COLLECTION_LINKEDIN,
        doc_id=doc.id,
        text=li_text,
        metadata={"user_id": current_user.id, "doc_type": "linkedin"},
    )

    return {
        "profile_document_id": doc.id,
        "filename": doc.original_filename,
        "profile_format": profile.profile_format,
        "parsing_status": doc.parsing_status,
        "profile_summary": {
            "headline": profile.headline,
            "skills_count": len(json.loads(profile.skills_json or "[]")),
            "experience_count": len(json.loads(profile.experience_json or "[]")),
            "education_count": len(json.loads(profile.education_json or "[]")),
        },
    }


@router.get("")
async def list_documents(
    doc_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List the current user's documents."""
    stmt = select(Document).where(
        Document.user_id == current_user.id,
        Document.is_deleted == False,
    )
    if doc_type:
        stmt = stmt.where(Document.doc_type == doc_type)
    stmt = stmt.order_by(Document.created_at.desc())
    result = await db.execute(stmt)
    docs = result.scalars().all()
    return [
        {
            "id": d.id,
            "doc_type": d.doc_type,
            "filename": d.original_filename,
            "parsing_status": d.parsing_status,
            "created_at": d.created_at.isoformat(),
            "file_size_bytes": d.file_size_bytes,
        }
        for d in docs
    ]


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Soft-delete a document and remove its embedding."""
    doc = await db.get(Document, document_id)
    if not doc or doc.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Document not found")

    from datetime import datetime, timezone
    doc.is_deleted = True
    doc.deleted_at = datetime.now(timezone.utc)

    # Remove from vector store
    from app.services.vector_store import delete_document_embedding
    await delete_document_embedding(settings.CHROMA_COLLECTION_RESUMES, document_id)
    await delete_document_embedding(settings.CHROMA_COLLECTION_LINKEDIN, document_id)

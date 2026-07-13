"""Job description and dataset routes."""
from __future__ import annotations

import json
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.db.base import get_db
from app.models.job import JobDataset, JobDescription, JobOpportunity
from app.models.user import User
from app.services.document_intake import ingest_job_dataset, ingest_job_description
from app.services.vector_store import upsert_document_embedding

settings = get_settings()
router = APIRouter(prefix="/jobs", tags=["jobs"])


class AddJobTextRequest(BaseModel):
    raw_text: str
    title: Optional[str] = None
    company: Optional[str] = None
    source_metadata: Optional[dict] = None


@router.post("/description", status_code=status.HTTP_201_CREATED)
async def add_job_description(
    body: AddJobTextRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a job description from pasted text."""
    jd = await ingest_job_description(
        db=db,
        user_id=current_user.id,
        raw_text=body.raw_text,
        source_metadata=body.source_metadata,
    )

    # Override extracted title/company if user provided them
    if body.title:
        jd.title = body.title[:512]
    if body.company:
        jd.company = body.company[:256]
    await db.flush()

    # Create a JobOpportunity record so it can be matched
    opp = JobOpportunity(
        user_id=current_user.id,
        job_description_id=jd.id,
        title=jd.title,
        company=jd.company,
        raw_text=jd.raw_text,
        requirements_json=jd.requirements_json,
        skills_required_json=jd.skills_required_json,
        keywords_json=jd.keywords_json,
        source_file="pasted_text",
        content_hash=jd.content_hash,
    )
    db.add(opp)
    await db.flush()

    # Index for semantic matching
    await upsert_document_embedding(
        collection_name=settings.CHROMA_COLLECTION_JOBS,
        doc_id=opp.id,
        text=jd.raw_text,
        metadata={"user_id": current_user.id, "title": jd.title or ""},
    )

    return {
        "job_id": jd.id,
        "opportunity_id": opp.id,
        "title": jd.title,
        "company": jd.company,
        "keywords_count": len(json.loads(jd.keywords_json or "[]")),
        "requirements_count": len(json.loads(jd.requirements_json or "[]")),
    }


@router.post("/description/upload", status_code=status.HTTP_201_CREATED)
async def upload_job_description(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a job description file (PDF, DOCX, TXT)."""
    data = await file.read()
    jd = await ingest_job_description(
        db=db,
        user_id=current_user.id,
        file_data=data,
        original_filename=file.filename or "job.txt",
    )
    opp = JobOpportunity(
        user_id=current_user.id,
        job_description_id=jd.id,
        title=jd.title,
        company=jd.company,
        raw_text=jd.raw_text,
        requirements_json=jd.requirements_json,
        skills_required_json=jd.skills_required_json,
        keywords_json=jd.keywords_json,
        source_file=file.filename,
        content_hash=jd.content_hash,
    )
    db.add(opp)
    await db.flush()
    await upsert_document_embedding(
        collection_name=settings.CHROMA_COLLECTION_JOBS,
        doc_id=opp.id,
        text=jd.raw_text,
        metadata={"user_id": current_user.id, "title": jd.title or ""},
    )
    return {"job_id": jd.id, "opportunity_id": opp.id, "title": jd.title}


@router.post("/dataset", status_code=status.HTTP_201_CREATED)
async def import_job_dataset(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Import a batch of job listings (CSV, JSON, PDF, DOCX, TXT)."""
    data = await file.read()
    dataset, opportunities, warnings = await ingest_job_dataset(
        db=db,
        user_id=current_user.id,
        file_data=data,
        original_filename=file.filename or "jobs.csv",
    )

    # Index all opportunities in vector store
    for opp in opportunities:
        if opp.raw_text:
            await upsert_document_embedding(
                collection_name=settings.CHROMA_COLLECTION_JOBS,
                doc_id=opp.id,
                text=opp.raw_text,
                metadata={
                    "user_id": current_user.id,
                    "dataset_id": dataset.id,
                    "title": opp.title or "",
                },
            )

    return {
        "dataset_id": dataset.id,
        "name": dataset.name,
        "job_count": dataset.job_count,
        "import_warnings": warnings,
        "opportunity_ids": [o.id for o in opportunities[:50]],
    }


@router.get("/opportunities")
async def list_opportunities(
    dataset_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List available job opportunities for matching."""
    stmt = select(JobOpportunity).where(JobOpportunity.user_id == current_user.id)
    if dataset_id:
        stmt = stmt.where(JobOpportunity.dataset_id == dataset_id)
    stmt = stmt.order_by(JobOpportunity.created_at.desc()).limit(200)
    opps = (await db.execute(stmt)).scalars().all()
    return [
        {
            "id": o.id,
            "title": o.title,
            "company": o.company,
            "location": o.location,
            "source_file": o.source_file,
            "dataset_id": o.dataset_id,
        }
        for o in opps
    ]


@router.get("/datasets")
async def list_datasets(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List imported job datasets."""
    stmt = (
        select(JobDataset)
        .where(JobDataset.user_id == current_user.id)
        .order_by(JobDataset.created_at.desc())
    )
    datasets = (await db.execute(stmt)).scalars().all()
    return [
        {
            "id": d.id,
            "name": d.name,
            "job_count": d.job_count,
            "source_file": d.source_file,
            "created_at": d.created_at.isoformat(),
        }
        for d in datasets
    ]


@router.get("/descriptions")
async def list_job_descriptions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = (
        select(JobDescription)
        .where(JobDescription.user_id == current_user.id)
        .order_by(JobDescription.created_at.desc())
        .limit(100)
    )
    jds = (await db.execute(stmt)).scalars().all()
    return [
        {"id": j.id, "title": j.title, "company": j.company, "created_at": j.created_at.isoformat()}
        for j in jds
    ]

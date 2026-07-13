"""
Document intake service — orchestrates:
1. File security validation
2. Duplicate detection
3. Parsing dispatch
4. ExtractedFact storage with provenance
5. Document record creation
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import get_settings
from app.core.file_security import (
    compute_hash, sanitize_filename, validate_extension,
    validate_mime, validate_size, safe_extract_zip,
)
from app.core.logging import get_logger
from app.models.document import Document, DocumentVersion, ExtractedFact
from app.models.profile import ResumeProfile, LinkedInProfile, LinkedInIdentifier
from app.models.job import JobDescription, JobDataset, JobOpportunity
from app.services.document_parser import parse_document
from app.services.resume_extractor import extract_resume_rule_based, extract_resume_llm, ResumeData
from app.services.linkedin_extractor import parse_linkedin_content, LinkedInData, LINKEDIN_DISCLAIMER
from app.services.job_extractor import parse_job_from_file, parse_job_dataset, extract_job_from_text

settings = get_settings()
log = get_logger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _store_file(data: bytes, doc_type: str, original_filename: str) -> Tuple[str, Path]:
    """Write file to upload directory with a unique stored name. Returns (stored_filename, full_path)."""
    ext = Path(original_filename).suffix.lower()
    stored_name = f"{uuid4().hex}{ext}"
    type_dir = settings.UPLOAD_DIR / doc_type
    type_dir.mkdir(parents=True, exist_ok=True)
    file_path = type_dir / stored_name
    file_path.write_bytes(data)
    return stored_name, file_path


async def _check_duplicate(
    db: AsyncSession,
    user_id: str,
    content_hash: str,
) -> Optional[Document]:
    stmt = select(Document).where(
        Document.user_id == user_id,
        Document.content_hash_sha256 == content_hash,
        Document.is_deleted == False,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


def _facts_from_resume(document_id: str, data: ResumeData) -> List[ExtractedFact]:
    """Convert ResumeData fields into ExtractedFact records with provenance."""
    facts: List[ExtractedFact] = []
    now = _utcnow()

    def make_fact(field_name: str, value: Any, confidence: float = 0.9, method: str = "rule") -> ExtractedFact:
        return ExtractedFact(
            document_id=document_id,
            field_name=field_name,
            normalized_value=str(value)[:2000],
            raw_value=str(value)[:2000],
            confidence=confidence,
            extraction_method=method,
            created_at=now,
        )

    if data.full_name:
        facts.append(make_fact("full_name", data.full_name, method="llm"))
    if data.email:
        facts.append(make_fact("email", data.email))
    if data.phone:
        facts.append(make_fact("phone", data.phone))
    if data.location:
        facts.append(make_fact("location", data.location, method="llm"))
    if data.linkedin_url:
        facts.append(make_fact("linkedin_url", data.linkedin_url))
    if data.summary:
        facts.append(make_fact("summary", data.summary[:500], method="llm"))
    for skill in data.skills:
        facts.append(make_fact("skill", skill, confidence=0.85, method="llm"))
    for exp in data.experience:
        if exp.get("title"):
            facts.append(make_fact("job_title", exp["title"], method="llm"))
        if exp.get("company"):
            facts.append(make_fact("employer", exp["company"], method="llm"))
    for edu in data.education:
        if edu.get("degree"):
            facts.append(make_fact("degree", edu["degree"], method="llm"))
        if edu.get("institution"):
            facts.append(make_fact("institution", edu["institution"], method="llm"))
    for cert in data.certifications:
        facts.append(make_fact("certification", cert, method="llm"))

    return facts


# ── Resume intake ─────────────────────────────────────────────────────────────

async def ingest_resume(
    db: AsyncSession,
    user_id: str,
    file_data: bytes,
    original_filename: str,
    ollama_client: Optional[Any] = None,
    llm_model: Optional[str] = None,
) -> Tuple[Document, ResumeProfile]:
    """
    Full pipeline: validate → parse → extract → store.
    Returns (Document, ResumeProfile).
    """
    ext = validate_extension(original_filename, settings.ALLOWED_RESUME_EXTENSIONS)
    validate_size(file_data)
    mime = validate_mime(file_data, ext)
    content_hash = compute_hash(file_data)

    # Duplicate check
    existing = await _check_duplicate(db, user_id, content_hash)
    is_duplicate = existing is not None

    # Store file
    safe_name = sanitize_filename(original_filename)
    stored_name, file_path = _store_file(file_data, "resume", safe_name)

    # Create document record
    doc = Document(
        user_id=user_id,
        doc_type="resume",
        original_filename=safe_name,
        stored_filename=stored_name,
        file_extension=ext,
        file_size_bytes=len(file_data),
        content_hash_sha256=content_hash,
        mime_type=mime,
        is_duplicate=is_duplicate,
        parsing_status="processing",
        created_at=_utcnow(),
        updated_at=_utcnow(),
    )
    db.add(doc)
    await db.flush()

    try:
        # Parse document
        parsed = parse_document(file_data, ext)

        # Rule-based extraction (always runs)
        resume_data = extract_resume_rule_based(parsed)

        # LLM extraction (if Ollama is available)
        if ollama_client and llm_model:
            try:
                resume_data = await extract_resume_llm(parsed, resume_data, ollama_client, llm_model)
            except Exception as e:
                log.warning("LLM extraction failed, using rule-based only: %s", e)

        # Store document version
        version = DocumentVersion(
            document_id=doc.id,
            version_number=1,
            content_hash=content_hash,
            raw_text=parsed.raw_text[:50000],  # stored but never logged
            page_count=parsed.page_count,
            created_at=_utcnow(),
        )
        db.add(version)

        # Store extracted facts
        facts = _facts_from_resume(doc.id, resume_data)
        for fact in facts:
            db.add(fact)

        # Create resume profile
        profile = ResumeProfile(
            document_id=doc.id,
            user_id=user_id,
            full_name=resume_data.full_name,
            email=resume_data.email,
            phone=resume_data.phone,
            location=resume_data.location,
            linkedin_url=resume_data.linkedin_url,
            summary=resume_data.summary,
            skills_json=json.dumps(resume_data.skills),
            experience_json=json.dumps(resume_data.experience),
            education_json=json.dumps(resume_data.education),
            certifications_json=json.dumps(resume_data.certifications),
            projects_json=json.dumps(resume_data.projects),
            achievements_json=json.dumps(resume_data.achievements),
            section_headings_json=json.dumps(resume_data.section_headings),
            keywords_json=json.dumps(resume_data.keywords),
            parsing_risks_json=json.dumps(resume_data.parsing_risks),
            completeness_score=resume_data.completeness_score,
            extraction_model=llm_model or "rule_based",
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )
        db.add(profile)

        doc.parsing_status = "completed"
        doc.parsing_warnings = json.dumps(resume_data.parsing_risks)
        doc.updated_at = _utcnow()
        await db.flush()

        return doc, profile

    except Exception as e:
        doc.parsing_status = "failed"
        doc.parsing_warnings = json.dumps([str(e)])
        doc.updated_at = _utcnow()
        await db.flush()
        raise


# ── LinkedIn profile intake ───────────────────────────────────────────────────

async def ingest_linkedin_identifier(
    db: AsyncSession,
    user_id: str,
    linkedin_url: Optional[str] = None,
    linkedin_id: Optional[str] = None,
) -> LinkedInIdentifier:
    """Store LinkedIn URL/ID only — explicitly state no scanning possible."""
    identifier = LinkedInIdentifier(
        user_id=user_id,
        linkedin_url=linkedin_url,
        linkedin_id=linkedin_id,
        disclaimer=LINKEDIN_DISCLAIMER,
        created_at=_utcnow(),
    )
    db.add(identifier)
    await db.flush()
    return identifier


async def ingest_linkedin_profile(
    db: AsyncSession,
    user_id: str,
    file_data: bytes,
    original_filename: str,
    profile_format: str,
    extracted_zip_files: Optional[Dict[str, bytes]] = None,
) -> Tuple[Document, LinkedInProfile]:
    """Ingest user-provided LinkedIn profile content."""
    ext = validate_extension(original_filename, settings.ALLOWED_LINKEDIN_EXTENSIONS)
    validate_size(file_data)
    mime = validate_mime(file_data, ext)
    content_hash = compute_hash(file_data)

    safe_name = sanitize_filename(original_filename)
    stored_name, file_path = _store_file(file_data, "linkedin", safe_name)

    doc = Document(
        user_id=user_id,
        doc_type="linkedin_pdf" if ext == ".pdf" else "linkedin_export",
        original_filename=safe_name,
        stored_filename=stored_name,
        file_extension=ext,
        file_size_bytes=len(file_data),
        content_hash_sha256=content_hash,
        mime_type=mime,
        parsing_status="processing",
        created_at=_utcnow(),
        updated_at=_utcnow(),
    )
    db.add(doc)
    await db.flush()

    try:
        li_data = parse_linkedin_content(file_data, ext, extracted_zip_files)

        version = DocumentVersion(
            document_id=doc.id,
            version_number=1,
            content_hash=content_hash,
            raw_text=str(li_data.to_dict())[:50000],
            page_count=1,
            created_at=_utcnow(),
        )
        db.add(version)

        profile = LinkedInProfile(
            document_id=doc.id,
            user_id=user_id,
            headline=li_data.headline,
            about=li_data.about,
            experience_json=json.dumps(li_data.experience),
            skills_json=json.dumps(li_data.skills),
            education_json=json.dumps(li_data.education),
            certifications_json=json.dumps(li_data.certifications),
            projects_json=json.dumps(li_data.projects),
            recommendations_json=json.dumps(li_data.recommendations),
            keywords_json=json.dumps(li_data.keywords),
            profile_format=li_data.profile_format,
            extraction_model="rule_based",
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )
        db.add(profile)

        doc.parsing_status = "completed"
        doc.updated_at = _utcnow()
        await db.flush()

        return doc, profile

    except Exception as e:
        doc.parsing_status = "failed"
        doc.parsing_warnings = json.dumps([str(e)])
        doc.updated_at = _utcnow()
        await db.flush()
        raise


# ── Job description intake ────────────────────────────────────────────────────

async def ingest_job_description(
    db: AsyncSession,
    user_id: str,
    raw_text: Optional[str] = None,
    file_data: Optional[bytes] = None,
    original_filename: Optional[str] = None,
    source_metadata: Optional[Dict[str, Any]] = None,
) -> JobDescription:
    """Ingest a single job description from text or file."""
    if file_data and original_filename:
        ext = validate_extension(original_filename, settings.ALLOWED_JOB_EXTENSIONS)
        validate_size(file_data)
        parsed = parse_job_from_file(file_data, ext, original_filename)
        raw_text = parsed.raw_text
        job_data = parsed
    elif raw_text:
        job_data = extract_job_from_text(raw_text)
    else:
        raise ValueError("Either raw_text or file_data must be provided.")

    content_hash = compute_hash(raw_text.encode())

    jd = JobDescription(
        user_id=user_id,
        title=job_data.title,
        company=job_data.company,
        raw_text=raw_text,
        requirements_json=json.dumps(job_data.requirements),
        skills_required_json=json.dumps(job_data.skills_required),
        keywords_json=json.dumps(job_data.keywords),
        source_metadata_json=json.dumps(source_metadata or {}),
        content_hash=content_hash,
        created_at=_utcnow(),
    )
    db.add(jd)
    await db.flush()
    return jd


async def ingest_job_dataset(
    db: AsyncSession,
    user_id: str,
    file_data: bytes,
    original_filename: str,
) -> Tuple[JobDataset, List[JobOpportunity], List[str]]:
    """Ingest a batch of job listings."""
    ext = validate_extension(original_filename, settings.ALLOWED_JOB_EXTENSIONS)
    validate_size(file_data)
    safe_name = sanitize_filename(original_filename)

    jobs, warnings = parse_job_dataset(file_data, ext, safe_name)

    dataset = JobDataset(
        user_id=user_id,
        name=safe_name,
        source_file=safe_name,
        job_count=len(jobs),
        import_warnings_json=json.dumps(warnings),
        created_at=_utcnow(),
    )
    db.add(dataset)
    await db.flush()

    opportunities: List[JobOpportunity] = []
    for job in jobs:
        opp = JobOpportunity(
            user_id=user_id,
            dataset_id=dataset.id,
            title=job.title,
            company=job.company,
            location=job.location,
            source_file=safe_name,
            raw_text=job.raw_text,
            requirements_json=json.dumps(job.requirements),
            skills_required_json=json.dumps(job.skills_required),
            keywords_json=json.dumps(job.keywords),
            content_hash=compute_hash(job.raw_text.encode()),
            created_at=_utcnow(),
        )
        db.add(opp)
        opportunities.append(opp)

    await db.flush()
    return dataset, opportunities, warnings

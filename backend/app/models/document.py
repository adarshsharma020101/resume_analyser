"""Document, version, and extracted fact models."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey, Integer,
    JSON, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    doc_type: Mapped[str] = mapped_column(String(32), nullable=False)  # resume | linkedin_pdf | linkedin_export | job_description | job_dataset
    original_filename: Mapped[str] = mapped_column(String(256), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(256), nullable=False)
    file_extension: Mapped[str] = mapped_column(String(16), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    mime_type: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False)
    parsing_status: Mapped[str] = mapped_column(String(32), default="pending")  # pending | processing | completed | failed
    parsing_warnings: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON list
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    user: Mapped["User"] = relationship(back_populates="documents")  # noqa: F821
    versions: Mapped[List["DocumentVersion"]] = relationship(back_populates="document", cascade="all, delete-orphan")
    extracted_facts: Mapped[List["ExtractedFact"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class DocumentVersion(Base):
    __tablename__ = "document_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Never logged
    page_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    document: Mapped["Document"] = relationship(back_populates="versions")

    __table_args__ = (UniqueConstraint("document_id", "version_number"),)


class ExtractedFact(Base):
    """
    A single fact extracted from a document with full provenance.
    Every AI-generated claim MUST link back to one or more of these.
    """
    __tablename__ = "extracted_facts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    field_name: Mapped[str] = mapped_column(String(128), nullable=False)  # e.g. "skill", "job_title", "employer"
    normalized_value: Mapped[str] = mapped_column(Text, nullable=False)
    raw_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    source_page: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    source_excerpt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_start_offset: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    source_end_offset: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    extraction_method: Mapped[str] = mapped_column(String(32), nullable=False, default="rule")  # rule | llm | ocr
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    document: Mapped["Document"] = relationship(back_populates="extracted_facts")


class EvidenceReference(Base):
    """Links an analysis result component to its source facts."""
    __tablename__ = "evidence_references"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    analysis_session_id: Mapped[str] = mapped_column(String(36), ForeignKey("analysis_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    extracted_fact_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("extracted_facts.id", ondelete="SET NULL"), nullable=True)
    claim_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)  # resume | linkedin_export | pasted_text | job_description
    source_document_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    source_file_name: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    source_page: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    source_excerpt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    document_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

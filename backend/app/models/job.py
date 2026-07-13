"""Job description, dataset, and opportunity models."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class JobDataset(Base):
    """A batch import of multiple job listings."""
    __tablename__ = "job_datasets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    source_file: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    job_count: Mapped[int] = mapped_column(Integer, default=0)
    import_warnings_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    opportunities: Mapped[list["JobOpportunity"]] = relationship(back_populates="dataset", cascade="all, delete-orphan")


class JobOpportunity(Base):
    """A single job listing from any source."""
    __tablename__ = "job_opportunities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    dataset_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("job_datasets.id", ondelete="SET NULL"), nullable=True, index=True)
    job_description_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("job_descriptions.id", ondelete="SET NULL"), nullable=True, index=True)

    title: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    company: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    source_file: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    requirements_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # extracted requirements
    skills_required_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    keywords_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    dataset: Mapped[Optional["JobDataset"]] = relationship(back_populates="opportunities")
    job_description: Mapped[Optional["JobDescription"]] = relationship()
    matches: Mapped[list["OpportunityMatch"]] = relationship(back_populates="opportunity", cascade="all, delete-orphan")


class JobDescription(Base):
    """A single job description added individually."""
    __tablename__ = "job_descriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)

    title: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    company: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    requirements_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    skills_required_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    keywords_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

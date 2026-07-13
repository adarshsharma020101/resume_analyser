"""Resume profile, LinkedIn identifier, and LinkedIn profile models."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ResumeProfile(Base):
    """
    Structured representation extracted from a resume document.
    All fields are extracted facts — nothing is inferred beyond what is in the document.
    """
    __tablename__ = "resume_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Extracted fields (all Optional — absent means "Not found in document")
    full_name: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    linkedin_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    skills_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)       # JSON list
    experience_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)   # JSON list
    education_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)    # JSON list
    certifications_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    projects_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    achievements_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    section_headings_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    keywords_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)     # All keywords extracted

    # Parsing risk flags (JSON list of warning strings)
    parsing_risks_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Completeness metrics (0.0-1.0)
    completeness_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    extraction_model: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class LinkedInIdentifier(Base):
    """
    Stores only the LinkedIn URL/ID as metadata.
    IMPORTANT: This NEVER implies the profile content has been retrieved.
    """
    __tablename__ = "linkedin_identifiers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    linkedin_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    linkedin_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    # Explicit disclaimer stored alongside the identifier
    disclaimer: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default=(
            "LinkedIn ID saved for reference only. Profile content cannot be analyzed "
            "until you upload, export, or paste actual profile data."
        ),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class LinkedInProfile(Base):
    """
    Structured representation extracted from user-uploaded LinkedIn content.
    Only populated when actual content is provided by the user.
    """
    __tablename__ = "linkedin_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    headline: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    about: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    experience_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    skills_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    education_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    certifications_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    projects_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recommendations_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    keywords_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    profile_format: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")  # pdf | export_zip | pasted | csv | json
    extraction_model: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

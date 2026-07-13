"""Analysis session, ATS scores, recommendations, and opportunity matches."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AnalysisSession(Base):
    """Top-level analysis run tying together resume, linkedin, and jobs."""
    __tablename__ = "analysis_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    resume_document_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    linkedin_document_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    target_job_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("job_descriptions.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending | running | completed | failed
    analysis_type: Mapped[str] = mapped_column(String(32), default="general")  # general | job_specific
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="analysis_sessions")  # noqa: F821
    ats_score: Mapped[Optional["ATSScore"]] = relationship(back_populates="session", uselist=False, cascade="all, delete-orphan")
    recommendations: Mapped[list["Recommendation"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    evidence_references: Mapped[list["EvidenceReference"]] = relationship(cascade="all, delete-orphan")  # noqa: F821
    opportunity_matches: Mapped[list["OpportunityMatch"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    model_runs: Mapped[list["ModelRun"]] = relationship(back_populates="session", cascade="all, delete-orphan")


class ATSScore(Base):
    """Overall ATS Readiness Estimate with full score breakdown."""
    __tablename__ = "ats_scores"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("analysis_sessions.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    # Total score 0-100 (deterministic)
    total_score: Mapped[float] = mapped_column(Float, nullable=False)
    score_type: Mapped[str] = mapped_column(String(32), nullable=False)  # general | job_specific
    disclaimer: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default=(
            "This is an ATS Readiness Estimate based on transparent, deterministic scoring. "
            "Proprietary ATS systems vary significantly — this score does not guarantee "
            "how any specific system will process your resume."
        ),
    )

    # Component scores (deterministic, not LLM-derived)
    parseability_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    section_structure_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    contact_completeness_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    keyword_coverage_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    experience_alignment_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    achievement_quality_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    readability_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    linkedin_consistency_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # LLM-generated explanations (marked as explanations, not facts)
    score_explanation_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    session: Mapped["AnalysisSession"] = relationship(back_populates="ats_score")
    components: Mapped[list["ATSScoreComponent"]] = relationship(back_populates="ats_score", cascade="all, delete-orphan")


class ATSScoreComponent(Base):
    """Detailed deduction record for a single ATS score component."""
    __tablename__ = "ats_score_components"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    ats_score_id: Mapped[str] = mapped_column(String(36), ForeignKey("ats_scores.id", ondelete="CASCADE"), nullable=False, index=True)
    component_name: Mapped[str] = mapped_column(String(64), nullable=False)
    max_points: Mapped[float] = mapped_column(Float, nullable=False)
    earned_points: Mapped[float] = mapped_column(Float, nullable=False)
    deduction_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evidence_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # cited source excerpts
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    ats_score: Mapped["ATSScore"] = relationship(back_populates="components")


class Recommendation(Base):
    """An evidence-backed actionable recommendation."""
    __tablename__ = "recommendations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("analysis_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    priority: Mapped[str] = mapped_column(String(16), nullable=False)  # critical | high | medium | optional
    category: Mapped[str] = mapped_column(String(64), nullable=False)  # keyword | formatting | section | content | consistency
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    why_it_matters: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_from_resume: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evidence_from_job: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    suggested_action: Mapped[str] = mapped_column(Text, nullable=False)
    draft_suggestion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Always marked as draft
    is_draft: Mapped[bool] = mapped_column(Boolean, default=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    source_citations_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON list of evidence refs
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    session: Mapped["AnalysisSession"] = relationship(back_populates="recommendations")


class OpportunityMatch(Base):
    """Result of matching a resume against a local job opportunity."""
    __tablename__ = "opportunity_matches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("analysis_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    opportunity_id: Mapped[str] = mapped_column(String(36), ForeignKey("job_opportunities.id", ondelete="CASCADE"), nullable=False, index=True)

    # Deterministic score components
    keyword_overlap_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    embedding_similarity_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    bm25_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    final_match_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)  # Weighted combination

    matched_skills_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    missing_requirements_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resume_evidence_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    linkedin_evidence_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    match_explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # LLM-generated, cited
    ranking_reasons_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    # Disclaimer: never claim qualification
    match_label: Mapped[str] = mapped_column(String(64), nullable=False, default="Potential match")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    session: Mapped["AnalysisSession"] = relationship(back_populates="opportunity_matches")
    opportunity: Mapped["JobOpportunity"] = relationship(back_populates="matches")


class ModelRun(Base):
    """Audit record of each LLM call."""
    __tablename__ = "model_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    session_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("analysis_sessions.id", ondelete="SET NULL"), nullable=True, index=True)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    task_name: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    session: Mapped[Optional["AnalysisSession"]] = relationship(back_populates="model_runs")

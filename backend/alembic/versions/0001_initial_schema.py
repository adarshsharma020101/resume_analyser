"""Initial schema — all tables

Revision ID: 0001
Revises:
Create Date: 2024-01-01 00:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── users ────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("username", sa.String(64), nullable=False),
        sa.Column("hashed_password", sa.String(256), nullable=False),
        sa.Column("email", sa.String(256), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_login", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("username"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_username", "users", ["username"])

    # ── user_consents ─────────────────────────────────────────────────────────
    op.create_table(
        "user_consents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("consent_type", sa.String(64), nullable=False),
        sa.Column("granted", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )

    # ── audit_logs ────────────────────────────────────────────────────────────
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(128), nullable=False),
        sa.Column("resource_type", sa.String(64), nullable=True),
        sa.Column("resource_id", sa.String(36), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])

    # ── documents ─────────────────────────────────────────────────────────────
    op.create_table(
        "documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("doc_type", sa.String(32), nullable=False),
        sa.Column("original_filename", sa.String(256), nullable=False),
        sa.Column("stored_filename", sa.String(256), nullable=False),
        sa.Column("file_extension", sa.String(16), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("content_hash_sha256", sa.String(64), nullable=False),
        sa.Column("mime_type", sa.String(128), nullable=True),
        sa.Column("is_duplicate", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("parsing_status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("parsing_warnings", sa.Text(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_documents_user_id", "documents", ["user_id"])
    op.create_index("ix_documents_content_hash_sha256", "documents", ["content_hash_sha256"])
    op.create_index("ix_documents_created_at", "documents", ["created_at"])

    # ── document_versions ─────────────────────────────────────────────────────
    op.create_table(
        "document_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("document_id", "version_number"),
    )

    # ── extracted_facts ────────────────────────────────────────────────────────
    op.create_table(
        "extracted_facts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("field_name", sa.String(128), nullable=False),
        sa.Column("normalized_value", sa.Text(), nullable=False),
        sa.Column("raw_value", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("source_page", sa.Integer(), nullable=True),
        sa.Column("source_excerpt", sa.Text(), nullable=True),
        sa.Column("source_start_offset", sa.Integer(), nullable=True),
        sa.Column("source_end_offset", sa.Integer(), nullable=True),
        sa.Column("extraction_method", sa.String(32), nullable=False, server_default="rule"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_extracted_facts_document_id", "extracted_facts", ["document_id"])

    # ── resume_profiles ────────────────────────────────────────────────────────
    op.create_table(
        "resume_profiles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("full_name", sa.String(256), nullable=True),
        sa.Column("email", sa.String(256), nullable=True),
        sa.Column("phone", sa.String(64), nullable=True),
        sa.Column("location", sa.String(256), nullable=True),
        sa.Column("linkedin_url", sa.String(512), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("skills_json", sa.Text(), nullable=True),
        sa.Column("experience_json", sa.Text(), nullable=True),
        sa.Column("education_json", sa.Text(), nullable=True),
        sa.Column("certifications_json", sa.Text(), nullable=True),
        sa.Column("projects_json", sa.Text(), nullable=True),
        sa.Column("achievements_json", sa.Text(), nullable=True),
        sa.Column("section_headings_json", sa.Text(), nullable=True),
        sa.Column("keywords_json", sa.Text(), nullable=True),
        sa.Column("parsing_risks_json", sa.Text(), nullable=True),
        sa.Column("completeness_score", sa.Float(), nullable=True),
        sa.Column("extraction_model", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("document_id"),
    )

    # ── linkedin_identifiers ───────────────────────────────────────────────────
    op.create_table(
        "linkedin_identifiers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("linkedin_url", sa.String(512), nullable=True),
        sa.Column("linkedin_id", sa.String(128), nullable=True),
        sa.Column("disclaimer", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # ── linkedin_profiles ──────────────────────────────────────────────────────
    op.create_table(
        "linkedin_profiles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("headline", sa.String(512), nullable=True),
        sa.Column("about", sa.Text(), nullable=True),
        sa.Column("experience_json", sa.Text(), nullable=True),
        sa.Column("skills_json", sa.Text(), nullable=True),
        sa.Column("education_json", sa.Text(), nullable=True),
        sa.Column("certifications_json", sa.Text(), nullable=True),
        sa.Column("projects_json", sa.Text(), nullable=True),
        sa.Column("recommendations_json", sa.Text(), nullable=True),
        sa.Column("keywords_json", sa.Text(), nullable=True),
        sa.Column("profile_format", sa.String(32), nullable=False, server_default="unknown"),
        sa.Column("extraction_model", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("document_id"),
    )

    # ── job_descriptions ───────────────────────────────────────────────────────
    op.create_table(
        "job_descriptions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("documents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(512), nullable=True),
        sa.Column("company", sa.String(256), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("requirements_json", sa.Text(), nullable=True),
        sa.Column("skills_required_json", sa.Text(), nullable=True),
        sa.Column("keywords_json", sa.Text(), nullable=True),
        sa.Column("source_metadata_json", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_job_descriptions_content_hash", "job_descriptions", ["content_hash"])

    # ── job_datasets ───────────────────────────────────────────────────────────
    op.create_table(
        "job_datasets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("documents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("source_file", sa.String(256), nullable=True),
        sa.Column("job_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("import_warnings_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # ── job_opportunities ──────────────────────────────────────────────────────
    op.create_table(
        "job_opportunities",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("dataset_id", sa.String(36), sa.ForeignKey("job_datasets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("job_description_id", sa.String(36), sa.ForeignKey("job_descriptions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(512), nullable=True),
        sa.Column("company", sa.String(256), nullable=True),
        sa.Column("location", sa.String(256), nullable=True),
        sa.Column("source_file", sa.String(256), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("requirements_json", sa.Text(), nullable=True),
        sa.Column("skills_required_json", sa.Text(), nullable=True),
        sa.Column("keywords_json", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_job_opportunities_dataset_id", "job_opportunities", ["dataset_id"])
    op.create_index("ix_job_opportunities_content_hash", "job_opportunities", ["content_hash"])

    # ── analysis_sessions ──────────────────────────────────────────────────────
    op.create_table(
        "analysis_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resume_document_id", sa.String(36), sa.ForeignKey("documents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("linkedin_document_id", sa.String(36), sa.ForeignKey("documents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("target_job_id", sa.String(36), sa.ForeignKey("job_descriptions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("analysis_type", sa.String(32), nullable=False, server_default="general"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_analysis_sessions_user_id", "analysis_sessions", ["user_id"])
    op.create_index("ix_analysis_sessions_created_at", "analysis_sessions", ["created_at"])

    # ── evidence_references ────────────────────────────────────────────────────
    op.create_table(
        "evidence_references",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("analysis_session_id", sa.String(36), sa.ForeignKey("analysis_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("extracted_fact_id", sa.String(36), sa.ForeignKey("extracted_facts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("claim_text", sa.Text(), nullable=False),
        sa.Column("source_type", sa.String(32), nullable=False),
        sa.Column("source_document_id", sa.String(36), nullable=True),
        sa.Column("source_file_name", sa.String(256), nullable=True),
        sa.Column("source_page", sa.Integer(), nullable=True),
        sa.Column("source_excerpt", sa.Text(), nullable=True),
        sa.Column("document_hash", sa.String(64), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # ── ats_scores ─────────────────────────────────────────────────────────────
    op.create_table(
        "ats_scores",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("session_id", sa.String(36), sa.ForeignKey("analysis_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("total_score", sa.Float(), nullable=False),
        sa.Column("score_type", sa.String(32), nullable=False),
        sa.Column("disclaimer", sa.Text(), nullable=False),
        sa.Column("parseability_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("section_structure_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("contact_completeness_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("keyword_coverage_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("experience_alignment_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("achievement_quality_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("readability_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("linkedin_consistency_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("score_explanation_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("session_id"),
    )

    # ── ats_score_components ───────────────────────────────────────────────────
    op.create_table(
        "ats_score_components",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("ats_score_id", sa.String(36), sa.ForeignKey("ats_scores.id", ondelete="CASCADE"), nullable=False),
        sa.Column("component_name", sa.String(64), nullable=False),
        sa.Column("max_points", sa.Float(), nullable=False),
        sa.Column("earned_points", sa.Float(), nullable=False),
        sa.Column("deduction_reason", sa.Text(), nullable=True),
        sa.Column("evidence_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # ── recommendations ────────────────────────────────────────────────────────
    op.create_table(
        "recommendations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("session_id", sa.String(36), sa.ForeignKey("analysis_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("priority", sa.String(16), nullable=False),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column("why_it_matters", sa.Text(), nullable=False),
        sa.Column("evidence_from_resume", sa.Text(), nullable=True),
        sa.Column("evidence_from_job", sa.Text(), nullable=True),
        sa.Column("suggested_action", sa.Text(), nullable=False),
        sa.Column("draft_suggestion", sa.Text(), nullable=True),
        sa.Column("is_draft", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("source_citations_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_recommendations_session_id", "recommendations", ["session_id"])

    # ── opportunity_matches ────────────────────────────────────────────────────
    op.create_table(
        "opportunity_matches",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("session_id", sa.String(36), sa.ForeignKey("analysis_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("opportunity_id", sa.String(36), sa.ForeignKey("job_opportunities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("keyword_overlap_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("embedding_similarity_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("bm25_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("final_match_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("matched_skills_json", sa.Text(), nullable=True),
        sa.Column("missing_requirements_json", sa.Text(), nullable=True),
        sa.Column("resume_evidence_json", sa.Text(), nullable=True),
        sa.Column("linkedin_evidence_json", sa.Text(), nullable=True),
        sa.Column("match_explanation", sa.Text(), nullable=True),
        sa.Column("ranking_reasons_json", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("match_label", sa.String(64), nullable=False, server_default="Potential match"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # ── model_runs ─────────────────────────────────────────────────────────────
    op.create_table(
        "model_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("session_id", sa.String(36), sa.ForeignKey("analysis_sessions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("model_name", sa.String(128), nullable=False),
        sa.Column("task_name", sa.String(128), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    for table in [
        "model_runs", "opportunity_matches", "recommendations",
        "ats_score_components", "ats_scores", "evidence_references",
        "analysis_sessions", "job_opportunities", "job_datasets",
        "job_descriptions", "linkedin_profiles", "linkedin_identifiers",
        "resume_profiles", "extracted_facts", "document_versions",
        "documents", "audit_logs", "user_consents", "users",
    ]:
        op.drop_table(table)

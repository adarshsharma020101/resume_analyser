"""
Application configuration loaded from environment variables.
All sensitive defaults are for local development only.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────────────────────────
    APP_NAME: str = "ATS Analyzer"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"

    # ── Paths ─────────────────────────────────────────────────────────────────
    BASE_DIR: Path = Path(__file__).resolve().parents[3]
    DATA_DIR: Path = Path("/app/data")
    UPLOAD_DIR: Path = Path("/app/data/uploads")
    REPORTS_DIR: Path = Path("/app/data/reports")
    DB_DIR: Path = Path("/app/data/db")
    CHROMA_DIR: Path = Path("/app/data/chroma")
    LOGS_DIR: Path = Path("/app/data/logs")

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite+aiosqlite:////app/data/db/ats_analyzer.db"
    DATABASE_POOL_SIZE: int = 5

    # ── Auth ──────────────────────────────────────────────────────────────────
    SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION_use_openssl_rand_hex_32"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    SINGLE_USER_MODE: bool = True

    # ── Ollama ────────────────────────────────────────────────────────────────
    OLLAMA_BASE_URL: str = "http://ollama:11434"
    OLLAMA_LLM_MODEL: str = "qwen2.5:7b"
    OLLAMA_EMBED_MODEL: str = "nomic-embed-text"
    OLLAMA_REQUEST_TIMEOUT: int = 120
    OLLAMA_MAX_TOKENS: int = 4096
    OLLAMA_TEMPERATURE: float = 0.1  # Low for factual tasks

    # ── File Upload ───────────────────────────────────────────────────────────
    MAX_UPLOAD_SIZE_MB: int = 20
    ALLOWED_RESUME_EXTENSIONS: List[str] = [".pdf", ".docx", ".txt"]
    ALLOWED_JOB_EXTENSIONS: List[str] = [".pdf", ".docx", ".txt", ".csv", ".json"]
    ALLOWED_LINKEDIN_EXTENSIONS: List[str] = [".pdf", ".txt", ".zip", ".csv", ".json"]
    MAX_ZIP_EXTRACTED_SIZE_MB: int = 50

    # ── ChromaDB ──────────────────────────────────────────────────────────────
    CHROMA_COLLECTION_RESUMES: str = "resumes"
    CHROMA_COLLECTION_JOBS: str = "jobs"
    CHROMA_COLLECTION_LINKEDIN: str = "linkedin"

    # ── ATS Scoring Weights (must sum to 100) ─────────────────────────────────
    ATS_WEIGHT_PARSEABILITY: int = 20
    ATS_WEIGHT_SECTION_STRUCTURE: int = 10
    ATS_WEIGHT_CONTACT_COMPLETENESS: int = 5
    ATS_WEIGHT_KEYWORD_COVERAGE: int = 25
    ATS_WEIGHT_EXPERIENCE_ALIGNMENT: int = 15
    ATS_WEIGHT_ACHIEVEMENT_QUALITY: int = 10
    ATS_WEIGHT_READABILITY: int = 10
    ATS_WEIGHT_LINKEDIN_CONSISTENCY: int = 5

    # ── Rate Limiting ─────────────────────────────────────────────────────────
    RATE_LIMIT_PER_MINUTE: int = 60

    # ── Retention ─────────────────────────────────────────────────────────────
    DEFAULT_RETENTION_DAYS: int = 90

    # ── MCP ───────────────────────────────────────────────────────────────────
    MCP_HTTP_PORT: int = 8001
    MCP_HTTP_SECRET: str = "CHANGE_ME_MCP_SECRET"

    # ── Logging ───────────────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    LOG_PII: bool = False  # Never log raw PII

    # ── Network Egress Guard ──────────────────────────────────────────────────
    ALLOWED_HOSTS: List[str] = ["localhost", "127.0.0.1", "ollama", "chromadb"]
    BLOCK_EXTERNAL_NETWORK: bool = True

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    def ensure_dirs(self) -> None:
        """Create required local directories."""
        for d in [
            self.DATA_DIR,
            self.UPLOAD_DIR,
            self.REPORTS_DIR,
            self.DB_DIR,
            self.CHROMA_DIR,
            self.LOGS_DIR,
        ]:
            d.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()

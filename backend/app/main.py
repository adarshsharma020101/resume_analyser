"""
FastAPI application entrypoint.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.routes import auth, documents, analysis, jobs, reports, privacy
from app.core.config import get_settings
from app.core.egress_guard import install_egress_guard
from app.core.logging import configure_logging, get_logger
from app.db.base import init_db

settings = get_settings()
log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    settings.ensure_dirs()
    install_egress_guard()
    await init_db()
    log.info("ATS Analyzer backend started — local-only mode.")
    yield
    log.info("ATS Analyzer backend shutting down.")


limiter = Limiter(key_func=get_remote_address, default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"])

app = FastAPI(
    title="ATS Analyzer API",
    description="Privacy-first local Resume + LinkedIn ATS Analyzer",
    version=settings.APP_VERSION,
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None,
    openapi_url="/api/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS — only allow localhost/frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://frontend:80",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Trusted host middleware — reject requests with unexpected Host headers
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "backend", "*.localhost"],
)

# Routes
app.include_router(auth.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(analysis.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(privacy.router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok", "version": settings.APP_VERSION}


@app.get("/api/settings/scoring-weights")
async def get_scoring_weights():
    """Return current ATS scoring weight configuration."""
    return {
        "parseability": settings.ATS_WEIGHT_PARSEABILITY,
        "section_structure": settings.ATS_WEIGHT_SECTION_STRUCTURE,
        "contact_completeness": settings.ATS_WEIGHT_CONTACT_COMPLETENESS,
        "keyword_coverage": settings.ATS_WEIGHT_KEYWORD_COVERAGE,
        "experience_alignment": settings.ATS_WEIGHT_EXPERIENCE_ALIGNMENT,
        "achievement_quality": settings.ATS_WEIGHT_ACHIEVEMENT_QUALITY,
        "readability": settings.ATS_WEIGHT_READABILITY,
        "linkedin_consistency": settings.ATS_WEIGHT_LINKEDIN_CONSISTENCY,
        "total": sum([
            settings.ATS_WEIGHT_PARSEABILITY,
            settings.ATS_WEIGHT_SECTION_STRUCTURE,
            settings.ATS_WEIGHT_CONTACT_COMPLETENESS,
            settings.ATS_WEIGHT_KEYWORD_COVERAGE,
            settings.ATS_WEIGHT_EXPERIENCE_ALIGNMENT,
            settings.ATS_WEIGHT_ACHIEVEMENT_QUALITY,
            settings.ATS_WEIGHT_READABILITY,
            settings.ATS_WEIGHT_LINKEDIN_CONSISTENCY,
        ]),
    }

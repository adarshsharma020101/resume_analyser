"""
Import all models here so SQLAlchemy metadata is fully populated
before create_all() is called.
"""
from .user import User, UserConsent, AuditLog
from .document import Document, DocumentVersion, ExtractedFact, EvidenceReference
from .profile import ResumeProfile, LinkedInIdentifier, LinkedInProfile
from .job import JobDataset, JobOpportunity, JobDescription
from .analysis import AnalysisSession, ATSScore, ATSScoreComponent, Recommendation, OpportunityMatch, ModelRun

__all__ = [
    "User", "UserConsent", "AuditLog",
    "Document", "DocumentVersion", "ExtractedFact", "EvidenceReference",
    "ResumeProfile", "LinkedInIdentifier", "LinkedInProfile",
    "JobDataset", "JobOpportunity", "JobDescription",
    "AnalysisSession", "ATSScore", "ATSScoreComponent",
    "Recommendation", "OpportunityMatch", "ModelRun",
]

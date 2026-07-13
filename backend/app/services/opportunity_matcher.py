"""
Hybrid opportunity matching engine.
Combines:
  1. Exact keyword overlap (deterministic)
  2. Skill normalization (deterministic)
  3. BM25 lexical ranking (deterministic)
  4. Local embedding similarity via Ollama + ChromaDB (semantic)
  5. Weighted final score (fully configurable, deterministic)

Never claims a user is "qualified" — uses careful wording throughout.
All match data comes from user-imported local job data only.
"""
from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from rank_bm25 import BM25Okapi

from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.ats_scorer import _normalize_skill, _keyword_overlap
from app.services.vector_store import query_similar

settings = get_settings()
log = get_logger(__name__)

# Scoring weights for the hybrid match
MATCH_WEIGHT_KEYWORD = 0.40
MATCH_WEIGHT_BM25 = 0.25
MATCH_WEIGHT_EMBEDDING = 0.35

# Match labels (never claim qualification)
def _match_label(score: float) -> str:
    if score >= 0.75:
        return "Strong skills overlap"
    elif score >= 0.55:
        return "Potential match"
    elif score >= 0.35:
        return "Requirements partially covered"
    else:
        return "Consider reviewing missing requirements"


@dataclass
class MatchResult:
    opportunity_id: str
    title: Optional[str]
    company: Optional[str]
    location: Optional[str]
    source_file: Optional[str]
    keyword_overlap_score: float
    bm25_score: float
    embedding_similarity_score: float
    final_match_score: float
    matched_skills: List[str] = field(default_factory=list)
    missing_requirements: List[str] = field(default_factory=list)
    resume_evidence: List[str] = field(default_factory=list)
    linkedin_evidence: List[str] = field(default_factory=list)
    match_label: str = "Potential match"
    confidence: float = 0.8
    ranking_reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "opportunity_id": self.opportunity_id,
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "source_file": self.source_file,
            "keyword_overlap_score": round(self.keyword_overlap_score, 3),
            "bm25_score": round(self.bm25_score, 3),
            "embedding_similarity_score": round(self.embedding_similarity_score, 3),
            "final_match_score": round(self.final_match_score, 3),
            "matched_skills": self.matched_skills,
            "missing_requirements": self.missing_requirements,
            "resume_evidence": self.resume_evidence,
            "linkedin_evidence": self.linkedin_evidence,
            "match_label": self.match_label,
            "confidence": self.confidence,
            "ranking_reasons": self.ranking_reasons,
        }


# ── Tokenizer ──────────────────────────────────────────────────────────────────

def _tokenize(text: str) -> List[str]:
    """Simple tokenizer for BM25."""
    text = text.lower()
    tokens = re.findall(r"\b[a-z0-9#+.]{2,30}\b", text)
    stopwords = {"the", "and", "for", "with", "this", "that", "have", "from",
                 "are", "been", "has", "its", "our", "will", "can", "may", "job",
                 "role", "position", "company", "team", "looking", "opportunity"}
    return [t for t in tokens if t not in stopwords]


# ── BM25 scoring ──────────────────────────────────────────────────────────────

def _compute_bm25_scores(
    query_text: str,
    job_texts: List[str],
) -> List[float]:
    """Compute BM25 scores for each job against the query (resume text)."""
    if not job_texts:
        return []
    tokenized_corpus = [_tokenize(t) for t in job_texts]
    bm25 = BM25Okapi(tokenized_corpus)
    query_tokens = _tokenize(query_text)
    scores = bm25.get_scores(query_tokens)
    # Normalize to 0-1
    max_score = max(scores) if max(scores) > 0 else 1.0
    return [float(s / max_score) for s in scores]


# ── Keyword matching ───────────────────────────────────────────────────────────

def _compute_keyword_match(
    resume_skills: List[str],
    resume_keywords: List[str],
    job_skills: List[str],
    job_keywords: List[str],
) -> Tuple[float, List[str], List[str]]:
    """
    Returns (score 0-1, matched_list, missing_list).
    Combines skills + keywords for both sides.
    """
    all_resume = list({_normalize_skill(k) for k in resume_skills + resume_keywords if k})
    all_job = list(dict.fromkeys(job_skills + job_keywords))

    if not all_job:
        return 0.0, [], []

    ratio, matched, missing = _keyword_overlap(all_resume, all_job)
    return ratio, matched, missing


# ── Evidence building ──────────────────────────────────────────────────────────

def _build_resume_evidence(
    matched_skills: List[str],
    resume_data: Dict[str, Any],
) -> List[str]:
    """
    Link matched skills back to the resume's experience section.
    Returns citations like "Skill 'Python' found in experience at Company X."
    """
    evidence: List[str] = []
    norm_matched = {_normalize_skill(s) for s in matched_skills}

    for exp in (resume_data.get("experience") or [])[:5]:
        title = exp.get("title") or ""
        company = exp.get("company") or ""
        bullets = exp.get("bullets") or []
        bullets_text = " ".join(bullets).lower()
        for skill in matched_skills:
            if _normalize_skill(skill) in bullets_text or _normalize_skill(skill) in title.lower():
                evidence.append(
                    f"Skill '{skill}' found in experience: {title} at {company}"
                )

    # Also check skills section
    for skill in (resume_data.get("skills") or []):
        if _normalize_skill(skill) in norm_matched:
            evidence.append(f"Skill '{skill}' listed in resume skills section")

    return list(dict.fromkeys(evidence))[:10]


def _build_linkedin_evidence(
    matched_skills: List[str],
    linkedin_data: Optional[Dict[str, Any]],
) -> List[str]:
    if not linkedin_data:
        return []
    evidence: List[str] = []
    li_skills = {_normalize_skill(s) for s in (linkedin_data.get("skills") or [])}
    for skill in matched_skills:
        if _normalize_skill(skill) in li_skills:
            evidence.append(f"Skill '{skill}' also listed on LinkedIn profile")
    return evidence[:5]


# ── Main matching function ────────────────────────────────────────────────────

async def match_opportunities(
    resume_data: Dict[str, Any],
    opportunities: List[Dict[str, Any]],
    linkedin_data: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None,
    use_embeddings: bool = True,
) -> List[MatchResult]:
    """
    Match resume against a list of local job opportunities.
    Returns ranked MatchResult list (highest score first).

    opportunities: list of dicts with keys:
      id, title, company, location, source_file,
      raw_text, keywords_json, skills_required_json, requirements_json
    """
    if not opportunities:
        return []

    resume_text = _build_resume_query_text(resume_data)
    resume_skills = resume_data.get("skills") or []
    resume_keywords = resume_data.get("keywords") or []

    # BM25 over all job texts
    job_texts = [opp.get("raw_text") or "" for opp in opportunities]
    bm25_scores = _compute_bm25_scores(resume_text, job_texts)

    # Embedding similarities
    embedding_scores: List[float] = [0.0] * len(opportunities)
    if use_embeddings and user_id:
        try:
            similar = await query_similar(
                collection_name=settings.CHROMA_COLLECTION_JOBS,
                query_text=resume_text,
                n_results=min(len(opportunities), 50),
                where={"user_id": user_id},
            )
            # Build lookup by doc_id
            sim_by_id = {r["id"]: r["similarity"] for r in similar}
            for i, opp in enumerate(opportunities):
                embedding_scores[i] = sim_by_id.get(opp["id"], 0.0)
        except Exception as e:
            log.warning("Embedding query failed, skipping semantic scoring: %s", e)

    # Build results
    results: List[MatchResult] = []
    for i, opp in enumerate(opportunities):
        job_skills = _parse_json_list(opp.get("skills_required_json"))
        job_keywords = _parse_json_list(opp.get("keywords_json"))
        job_requirements = _parse_json_list(opp.get("requirements_json"))

        kw_score, matched, missing = _compute_keyword_match(
            resume_skills, resume_keywords, job_skills, job_keywords
        )
        bm25 = bm25_scores[i] if i < len(bm25_scores) else 0.0
        embed = embedding_scores[i]

        # Weighted final score
        final = (
            kw_score * MATCH_WEIGHT_KEYWORD +
            bm25 * MATCH_WEIGHT_BM25 +
            embed * MATCH_WEIGHT_EMBEDDING
        )
        final = round(min(1.0, final), 3)

        # Confidence: lower if no job text, few job keywords
        confidence = 0.9
        if not opp.get("raw_text"):
            confidence = 0.5
        elif len(job_keywords) + len(job_skills) < 3:
            confidence = 0.65

        # Build ranking reasons
        ranking_reasons = _build_ranking_reasons(kw_score, bm25, embed, matched, missing)

        # Build evidence
        resume_evidence = _build_resume_evidence(matched, resume_data)
        linkedin_evidence = _build_linkedin_evidence(matched, linkedin_data)

        result = MatchResult(
            opportunity_id=opp["id"],
            title=opp.get("title"),
            company=opp.get("company"),
            location=opp.get("location"),
            source_file=opp.get("source_file"),
            keyword_overlap_score=kw_score,
            bm25_score=bm25,
            embedding_similarity_score=embed,
            final_match_score=final,
            matched_skills=matched[:20],
            missing_requirements=missing[:20],
            resume_evidence=resume_evidence,
            linkedin_evidence=linkedin_evidence,
            match_label=_match_label(final),
            confidence=confidence,
            ranking_reasons=ranking_reasons,
        )
        results.append(result)

    # Sort by final score descending
    results.sort(key=lambda r: r.final_match_score, reverse=True)
    return results


def _build_resume_query_text(resume_data: Dict[str, Any]) -> str:
    """Combine resume fields into a single query string for BM25/embedding."""
    parts = []
    if resume_data.get("summary"):
        parts.append(resume_data["summary"])
    for exp in (resume_data.get("experience") or [])[:5]:
        parts.append(exp.get("title") or "")
        parts.append(exp.get("company") or "")
        parts.extend(exp.get("bullets") or [])
    parts.extend(resume_data.get("skills") or [])
    parts.extend(resume_data.get("keywords") or [])
    return " ".join(p for p in parts if p)[:8000]


def _parse_json_list(value: Any) -> List[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(v) for v in value if v]
    try:
        parsed = json.loads(value)
        return [str(v) for v in parsed if v] if isinstance(parsed, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def _build_ranking_reasons(
    kw_score: float,
    bm25_score: float,
    embed_score: float,
    matched: List[str],
    missing: List[str],
) -> List[str]:
    reasons: List[str] = []
    if kw_score >= 0.7:
        reasons.append(f"High keyword overlap ({kw_score:.0%}) with job requirements.")
    elif kw_score >= 0.4:
        reasons.append(f"Moderate keyword overlap ({kw_score:.0%}) with job requirements.")
    else:
        reasons.append(f"Low keyword overlap ({kw_score:.0%}) — many required skills not found in resume.")

    if bm25_score >= 0.7:
        reasons.append("Strong lexical similarity between resume and job description.")
    if embed_score >= 0.7:
        reasons.append("High semantic similarity between resume content and job description.")

    if matched:
        reasons.append(f"Matched skills: {', '.join(matched[:5])}")
    if missing:
        reasons.append(f"Skills/requirements not found in resume: {', '.join(missing[:5])}")

    return reasons

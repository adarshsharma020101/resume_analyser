"""MCP tools: analyze_profile, match_opportunities, get_provenance."""
from __future__ import annotations

import asyncio
from typing import List, Optional

from app.backend_client import backend_request


async def tool_analyze_profile(
    token: str,
    resume_document_id: str,
    linkedin_document_id: Optional[str] = None,
    target_job_id: Optional[str] = None,
    job_ids_to_match: Optional[List[str]] = None,
) -> dict:
    """
    Run full ATS analysis for a resume.

    Computes:
      - ATS Readiness Estimate (deterministic, 0-100)
      - Score breakdown by component
      - Evidence-backed recommendations
      - Resume/LinkedIn consistency check (if LinkedIn doc provided)
      - Opportunity matching (if job_ids_to_match provided)

    Args:
        token: Auth token
        resume_document_id: ID returned by upload_resume
        linkedin_document_id: Optional ID from upload_linkedin_profile
        target_job_id: Optional job_description_id for job-specific scoring
        job_ids_to_match: Optional list of opportunity_ids for matching

    Returns:
        session_id, status (pending — poll get_analysis_result)
    """
    body = {
        "resume_document_id": resume_document_id,
        "linkedin_document_id": linkedin_document_id,
        "target_job_id": target_job_id,
        "job_ids_to_match": job_ids_to_match or [],
    }
    result = await backend_request(
        method="POST",
        path="/api/analysis",
        token=token,
        json=body,
    )
    return result


async def tool_get_analysis_result(
    token: str,
    session_id: str,
    wait: bool = True,
    max_wait_seconds: int = 120,
) -> dict:
    """
    Get full analysis result for a session.
    If wait=True, polls until completed or timeout.

    Returns:
        Full analysis including ATS score, recommendations, opportunity matches.
        All numeric scores are deterministic. Explanations are LLM-generated and labeled.
    """
    for _ in range(max_wait_seconds if wait else 1):
        result = await backend_request(
            method="GET",
            path=f"/api/analysis/{session_id}",
            token=token,
        )
        status = result.get("status")
        if status in ("completed", "failed") or not wait:
            return result
        await asyncio.sleep(1)

    return {"error": f"Analysis did not complete within {max_wait_seconds} seconds.", "session_id": session_id}


async def tool_match_opportunities(
    token: str,
    resume_document_id: str,
    linkedin_document_id: Optional[str] = None,
    job_ids: Optional[List[str]] = None,
) -> dict:
    """
    Match resume against locally imported job opportunities.

    IMPORTANT: Only matches against jobs YOU have imported locally.
    No live job board queries are made. No internet access.

    Args:
        token: Auth token
        resume_document_id: Resume document ID
        linkedin_document_id: Optional LinkedIn profile document ID
        job_ids: List of opportunity IDs to match against (None = all user's jobs)

    Returns:
        Ranked list of opportunity matches with scores and evidence.
    """
    # List all opportunities if job_ids not specified
    if not job_ids:
        opps = await backend_request(
            method="GET",
            path="/api/jobs/opportunities",
            token=token,
        )
        job_ids = [o["id"] for o in (opps if isinstance(opps, list) else [])]

    if not job_ids:
        return {
            "matches": [],
            "message": "No job opportunities found. Import jobs first using import_jobs.",
        }

    body = {
        "resume_document_id": resume_document_id,
        "linkedin_document_id": linkedin_document_id,
        "job_ids_to_match": job_ids,
    }
    session = await backend_request(
        method="POST",
        path="/api/analysis",
        token=token,
        json=body,
    )
    result = await tool_get_analysis_result(token, session["session_id"], wait=True)
    return {
        "session_id": result.get("session_id"),
        "opportunity_matches": result.get("opportunity_matches", []),
        "match_count": len(result.get("opportunity_matches", [])),
    }


async def tool_get_provenance(
    token: str,
    session_id: str,
) -> dict:
    """
    Get full provenance chain for an analysis session.

    Returns every claim with:
      - source_type (resume | linkedin_export | job_description)
      - source_file_name
      - source_excerpt (the text passage the claim came from)
      - source_page (when applicable)
      - document_hash (SHA-256 of source document)
      - confidence score

    Args:
        token: Auth token
        session_id: Analysis session ID

    Returns:
        Complete provenance chain for all claims in the analysis.
    """
    return await backend_request(
        method="GET",
        path=f"/api/analysis/{session_id}/provenance",
        token=token,
    )

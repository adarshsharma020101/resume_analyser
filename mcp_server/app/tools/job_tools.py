"""MCP tools: add_job_description, import_jobs, generate_report, delete_user_data."""
from __future__ import annotations

import base64
from typing import Optional

from app.backend_client import backend_request, _encode_file


async def tool_add_job_description(
    token: str,
    raw_text: Optional[str] = None,
    file_path: Optional[str] = None,
    file_base64: Optional[str] = None,
    filename: str = "job.txt",
    title: Optional[str] = None,
    company: Optional[str] = None,
) -> dict:
    """
    Add a single job description for analysis and matching.

    Accepts either pasted text or a file (PDF/DOCX/TXT).
    Source is always local — no external job board queries.

    Args:
        token: Auth token
        raw_text: Pasted job description text
        file_path: Path to a local job description file
        file_base64: Base64-encoded file content
        filename: Filename for file upload
        title: Override detected job title
        company: Override detected company name

    Returns:
        job_id, opportunity_id, extracted keywords count
    """
    if raw_text:
        body = {"raw_text": raw_text}
        if title:
            body["title"] = title
        if company:
            body["company"] = company
        return await backend_request(
            method="POST",
            path="/api/jobs/description",
            token=token,
            json=body,
        )

    if file_base64:
        file_bytes = base64.b64decode(file_base64)
    elif file_path:
        file_bytes = _encode_file(file_path=file_path)
    else:
        return {"error": "Provide raw_text, file_path, or file_base64."}

    return await backend_request(
        method="POST",
        path="/api/jobs/description/upload",
        token=token,
        files={"file": (filename, file_bytes, "application/octet-stream")},
    )


async def tool_import_jobs(
    token: str,
    file_path: Optional[str] = None,
    file_base64: Optional[str] = None,
    filename: str = "jobs.csv",
) -> dict:
    """
    Import a batch of job listings from a local file.

    Supported formats:
      - CSV (title, company, location, description columns)
      - JSON (array of job objects)
      - PDF/DOCX/TXT (single job description)

    IMPORTANT: Source must be a local file. No external job APIs.
    For LinkedIn jobs: export using LinkedIn's "Save jobs" feature,
    then import the exported file here.

    Args:
        token: Auth token
        file_path: Path to local jobs file
        file_base64: Base64-encoded file content
        filename: Filename (determines parser strategy)

    Returns:
        dataset_id, job_count, import_warnings, opportunity_ids
    """
    if file_base64:
        file_bytes = base64.b64decode(file_base64)
    elif file_path:
        file_bytes = _encode_file(file_path=file_path)
    else:
        return {"error": "Provide file_path or file_base64."}

    return await backend_request(
        method="POST",
        path="/api/jobs/dataset",
        token=token,
        files={"file": (filename, file_bytes, "application/octet-stream")},
    )


async def tool_generate_report(
    token: str,
    session_id: str,
    format: str = "json",
) -> dict:
    """
    Generate a report for a completed analysis session.

    Report is saved to the local filesystem and a download URL is returned.
    No cloud storage — all files stay on your machine.

    Args:
        token: Auth token
        session_id: Completed analysis session ID
        format: "json" | "html" | "pdf"

    Returns:
        file_path (local), download_url, format
    """
    return await backend_request(
        method="POST",
        path="/api/reports/generate",
        token=token,
        json={"session_id": session_id, "format": format},
    )


async def tool_delete_user_data(
    token: str,
) -> dict:
    """
    Permanently delete ALL data for the authenticated user.

    This removes:
      - All uploaded documents (resume, LinkedIn, jobs)
      - All analysis sessions, scores, recommendations
      - All vector store embeddings
      - The user account itself

    This action is IRREVERSIBLE. All data stays local — nothing is sent anywhere.

    Args:
        token: Auth token

    Returns:
        Confirmation with list of removed items.
    """
    return await backend_request(
        method="DELETE",
        path="/api/privacy/my-data",
        token=token,
    )

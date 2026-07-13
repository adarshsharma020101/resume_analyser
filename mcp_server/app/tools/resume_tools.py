"""MCP tools: upload_resume, add_linkedin_identifier, upload_linkedin_profile."""
from __future__ import annotations

import base64
from typing import Optional

from app.backend_client import backend_request, _encode_file


async def tool_upload_resume(
    token: str,
    file_path: Optional[str] = None,
    file_base64: Optional[str] = None,
    filename: str = "resume.pdf",
) -> dict:
    """
    Upload and parse a resume file.

    Args:
        token: Auth token
        file_path: Local path to resume file (PDF/DOCX/TXT)
        file_base64: Base64-encoded file content (alternative to file_path)
        filename: Original filename (used to determine extension)

    Returns:
        document_id, parsing_warnings, profile_summary
    """
    if file_base64:
        file_bytes = base64.b64decode(file_base64)
    elif file_path:
        file_bytes = _encode_file(file_path=file_path)
    else:
        return {"error": "Either file_path or file_base64 must be provided."}

    result = await backend_request(
        method="POST",
        path="/api/documents/resume",
        token=token,
        files={"file": (filename, file_bytes, "application/octet-stream")},
    )
    return result


async def tool_add_linkedin_identifier(
    token: str,
    linkedin_url: Optional[str] = None,
    linkedin_id: Optional[str] = None,
) -> dict:
    """
    Save a LinkedIn URL or ID for reference only.

    IMPORTANT: This does NOT scan the LinkedIn profile.
    Profile content cannot be analyzed until actual content is uploaded.

    Args:
        token: Auth token
        linkedin_url: Full LinkedIn profile URL
        linkedin_id: LinkedIn username/ID portion only

    Returns:
        identifier_id, disclaimer message
    """
    if not linkedin_url and not linkedin_id:
        return {"error": "Provide either linkedin_url or linkedin_id."}

    data = {}
    if linkedin_url:
        data["linkedin_url"] = linkedin_url
    if linkedin_id:
        data["linkedin_id"] = linkedin_id

    result = await backend_request(
        method="POST",
        path="/api/documents/linkedin/identifier",
        token=token,
        data=data,
    )
    return result


async def tool_upload_linkedin_profile(
    token: str,
    file_path: Optional[str] = None,
    file_base64: Optional[str] = None,
    filename: str = "linkedin.pdf",
    profile_format: str = "auto",
) -> dict:
    """
    Upload LinkedIn profile content for analysis.

    Supported formats:
      - PDF (LinkedIn-generated profile PDF)
      - ZIP (official LinkedIn data export)
      - CSV/JSON (LinkedIn export files)
      - TXT (pasted profile text)

    Args:
        token: Auth token
        file_path: Local path to LinkedIn export/profile file
        file_base64: Base64-encoded file content
        filename: Original filename (determines parsing strategy)
        profile_format: "auto", "pdf", "export_zip", "pasted", "csv", "json"

    Returns:
        profile_document_id, profile_summary, parsing_status
    """
    if file_base64:
        file_bytes = base64.b64decode(file_base64)
    elif file_path:
        file_bytes = _encode_file(file_path=file_path)
    else:
        return {"error": "Either file_path or file_base64 must be provided."}

    result = await backend_request(
        method="POST",
        path="/api/documents/linkedin/profile",
        token=token,
        files={"file": (filename, file_bytes, "application/octet-stream")},
        data={"profile_format": profile_format},
    )
    return result

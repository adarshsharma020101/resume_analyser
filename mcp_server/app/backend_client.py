"""
HTTP client for calling the backend FastAPI service.
All calls are to localhost/Docker-internal only.
"""
from __future__ import annotations

import base64
from typing import Any, Dict, Optional

import httpx

from app.config import get_mcp_settings

settings = get_mcp_settings()

# Shared async client — reuse connections
_client: Optional[httpx.AsyncClient] = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            base_url=settings.BACKEND_URL,
            timeout=120.0,
            follow_redirects=True,
        )
    return _client


async def backend_request(
    method: str,
    path: str,
    token: Optional[str] = None,
    json: Optional[Dict[str, Any]] = None,
    data: Optional[Dict[str, Any]] = None,
    files: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Make an authenticated request to the backend."""
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    client = _get_client()
    response = await client.request(
        method=method,
        url=path,
        headers=headers,
        json=json,
        data=data,
        files=files,
        params=params,
    )
    response.raise_for_status()
    return response.json()


async def get_or_create_token(username: str = "mcp_user", password: str = "mcp_password") -> str:
    """Get a backend auth token for MCP tool calls."""
    client = _get_client()
    try:
        resp = await client.post(
            "/api/auth/login",
            json={"username": username, "password": password},
        )
        if resp.status_code == 200:
            return resp.json()["access_token"]
    except Exception:
        pass

    # Auto-register on first use in single-user mode
    try:
        resp = await client.post(
            "/api/auth/register",
            json={"username": username, "password": password},
        )
        return resp.json()["access_token"]
    except Exception as e:
        raise RuntimeError(f"MCP authentication failed: {e}")


def _encode_file(file_path: Optional[str] = None, file_bytes: Optional[bytes] = None) -> bytes:
    """Load file bytes from path or return provided bytes."""
    if file_bytes:
        return file_bytes
    if file_path:
        with open(file_path, "rb") as f:
            return f.read()
    raise ValueError("Either file_path or file_bytes must be provided.")

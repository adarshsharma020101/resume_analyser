"""
ATS Analyzer MCP Server.

Supports two transports:
  1. stdio  — for local desktop MCP clients (Claude Desktop, Cursor, etc.)
  2. HTTP   — Streamable HTTP for local network/localhost access

Run modes:
  python -m app.main          → stdio mode
  python -m app.main --http   → HTTP server mode on port 8001

Authentication (HTTP mode):
  All HTTP endpoints require: Authorization: Bearer <MCP_HTTP_SECRET>

No external network calls. All tools proxy to the local backend service.
"""
from __future__ import annotations

import asyncio
import sys
from typing import Any, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolResult,
    TextContent,
    Tool,
)
import mcp.types as types
import json

from app.backend_client import get_or_create_token
from app.config import get_mcp_settings
from app.tools.resume_tools import (
    tool_upload_resume,
    tool_add_linkedin_identifier,
    tool_upload_linkedin_profile,
)
from app.tools.analysis_tools import (
    tool_analyze_profile,
    tool_get_analysis_result,
    tool_match_opportunities,
    tool_get_provenance,
)
from app.tools.job_tools import (
    tool_add_job_description,
    tool_import_jobs,
    tool_generate_report,
    tool_delete_user_data,
)

settings = get_mcp_settings()

# ── Tool schemas ───────────────────────────────────────────────────────────────

TOOLS: list[Tool] = [
    Tool(
        name="upload_resume",
        description=(
            "Upload and parse a resume file (PDF, DOCX, or TXT) for ATS analysis. "
            "Returns document_id, parsing warnings, and profile summary. "
            "All processing is local — no data leaves your machine."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Absolute local path to resume file"},
                "file_base64": {"type": "string", "description": "Base64-encoded file content (alternative)"},
                "filename": {"type": "string", "description": "Original filename (e.g. resume.pdf)", "default": "resume.pdf"},
            },
            "oneOf": [{"required": ["file_path"]}, {"required": ["file_base64"]}],
        },
    ),
    Tool(
        name="add_linkedin_identifier",
        description=(
            "Save a LinkedIn URL or ID for reference only. "
            "IMPORTANT: This does NOT scan LinkedIn. Profile content cannot be analyzed "
            "until you use upload_linkedin_profile to provide actual content."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "linkedin_url": {"type": "string", "description": "Full LinkedIn profile URL"},
                "linkedin_id": {"type": "string", "description": "LinkedIn username/ID"},
            },
        },
    ),
    Tool(
        name="upload_linkedin_profile",
        description=(
            "Upload LinkedIn profile content for analysis. "
            "Accepted: LinkedIn PDF, official data export ZIP, CSV/JSON export files, pasted text. "
            "Required before LinkedIn consistency analysis can run."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Local path to LinkedIn export file"},
                "file_base64": {"type": "string", "description": "Base64-encoded file content"},
                "filename": {"type": "string", "default": "linkedin.pdf"},
                "profile_format": {
                    "type": "string",
                    "enum": ["auto", "pdf", "export_zip", "pasted", "csv", "json"],
                    "default": "auto",
                },
            },
            "oneOf": [{"required": ["file_path"]}, {"required": ["file_base64"]}],
        },
    ),
    Tool(
        name="add_job_description",
        description=(
            "Add a job description for ATS scoring and matching. "
            "Accepts pasted text or a local file (PDF/DOCX/TXT). "
            "Source must be local — no external job board queries."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "raw_text": {"type": "string", "description": "Pasted job description text"},
                "file_path": {"type": "string", "description": "Path to local job description file"},
                "file_base64": {"type": "string", "description": "Base64-encoded file content"},
                "filename": {"type": "string", "default": "job.txt"},
                "title": {"type": "string", "description": "Override extracted job title"},
                "company": {"type": "string", "description": "Override extracted company name"},
            },
        },
    ),
    Tool(
        name="import_jobs",
        description=(
            "Import a batch of job listings from a local CSV, JSON, PDF, DOCX, or TXT file. "
            "Use this to import your exported LinkedIn saved jobs, CSV exports, or any local job list. "
            "No internet access — all data must be local."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Local path to jobs file"},
                "file_base64": {"type": "string", "description": "Base64-encoded file content"},
                "filename": {"type": "string", "default": "jobs.csv", "description": "Filename (determines parser)"},
            },
            "oneOf": [{"required": ["file_path"]}, {"required": ["file_base64"]}],
        },
    ),
    Tool(
        name="analyze_profile",
        description=(
            "Run full ATS analysis: scoring, recommendations, and optionally LinkedIn consistency check. "
            "All numeric scores are computed deterministically. "
            "LLM is used only for natural-language explanations, grounded in evidence."
        ),
        inputSchema={
            "type": "object",
            "required": ["resume_document_id"],
            "properties": {
                "resume_document_id": {"type": "string", "description": "ID from upload_resume"},
                "linkedin_document_id": {"type": "string", "description": "Optional ID from upload_linkedin_profile"},
                "target_job_id": {"type": "string", "description": "Optional job_id for job-specific scoring"},
                "job_ids_to_match": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of local opportunity IDs to match against",
                },
                "wait": {"type": "boolean", "default": True, "description": "Wait for completion before returning"},
            },
        },
    ),
    Tool(
        name="match_opportunities",
        description=(
            "Match a resume against locally imported job opportunities. "
            "Uses keyword overlap, BM25 lexical ranking, and local embedding similarity. "
            "ONLY matches against jobs you have imported — no live job board access."
        ),
        inputSchema={
            "type": "object",
            "required": ["resume_document_id"],
            "properties": {
                "resume_document_id": {"type": "string"},
                "linkedin_document_id": {"type": "string"},
                "job_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific opportunity IDs (None = all imported jobs)",
                },
            },
        },
    ),
    Tool(
        name="generate_report",
        description=(
            "Generate a downloadable report for a completed analysis session. "
            "Report is saved locally. Formats: json, html, pdf."
        ),
        inputSchema={
            "type": "object",
            "required": ["session_id"],
            "properties": {
                "session_id": {"type": "string"},
                "format": {"type": "string", "enum": ["json", "html", "pdf"], "default": "json"},
            },
        },
    ),
    Tool(
        name="delete_user_data",
        description=(
            "Permanently delete ALL user data: documents, profiles, analyses, embeddings, account. "
            "This action is irreversible. All data stays local — nothing is sent anywhere."
        ),
        inputSchema={
            "type": "object",
            "properties": {},
        },
    ),
    Tool(
        name="get_provenance",
        description=(
            "Get the full provenance chain for an analysis session. "
            "Returns every claim with source_type, source_file, excerpt, page, document_hash, and confidence. "
            "Use this to verify that every analysis result is grounded in your uploaded documents."
        ),
        inputSchema={
            "type": "object",
            "required": ["session_id"],
            "properties": {
                "session_id": {"type": "string"},
            },
        },
    ),
]


# ── MCP Server ─────────────────────────────────────────────────────────────────

server = Server("ats-analyzer")
_token_cache: dict[str, str] = {}


async def _get_token(username: str = "mcp_user") -> str:
    if username not in _token_cache:
        _token_cache[username] = await get_or_create_token(username)
    return _token_cache[username]


@server.list_tools()
async def list_tools() -> list[Tool]:
    return TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    token = await _get_token()
    try:
        result = await _dispatch_tool(name, arguments, token)
        return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]
    except Exception as e:
        error_result = {"error": str(e), "tool": name}
        return [TextContent(type="text", text=json.dumps(error_result))]


async def _dispatch_tool(name: str, args: dict, token: str) -> Any:
    """Route tool calls to the correct handler."""
    if name == "upload_resume":
        return await tool_upload_resume(token=token, **args)
    elif name == "add_linkedin_identifier":
        return await tool_add_linkedin_identifier(token=token, **args)
    elif name == "upload_linkedin_profile":
        return await tool_upload_linkedin_profile(token=token, **args)
    elif name == "add_job_description":
        return await tool_add_job_description(token=token, **args)
    elif name == "import_jobs":
        return await tool_import_jobs(token=token, **args)
    elif name == "analyze_profile":
        wait = args.pop("wait", True)
        session = await tool_analyze_profile(token=token, **args)
        if wait:
            return await tool_get_analysis_result(token, session["session_id"], wait=True)
        return session
    elif name == "match_opportunities":
        return await tool_match_opportunities(token=token, **args)
    elif name == "generate_report":
        return await tool_generate_report(token=token, **args)
    elif name == "delete_user_data":
        return await tool_delete_user_data(token=token)
    elif name == "get_provenance":
        return await tool_get_provenance(token=token, **args)
    else:
        return {"error": f"Unknown tool: {name}"}


# ── HTTP transport ─────────────────────────────────────────────────────────────

def build_http_app():
    """Build a FastAPI app wrapping the MCP server over Streamable HTTP."""
    from fastapi import FastAPI, HTTPException, Request, Depends
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
    from fastapi.responses import JSONResponse

    http_app = FastAPI(
        title="ATS Analyzer MCP Server",
        description="Local MCP server for ATS Analyzer. HTTP transport.",
        docs_url=None,
    )
    bearer = HTTPBearer()

    def verify_mcp_token(credentials: HTTPAuthorizationCredentials = Depends(bearer)):
        if credentials.credentials != settings.MCP_HTTP_SECRET:
            raise HTTPException(status_code=401, detail="Invalid MCP token")
        return credentials.credentials

    @http_app.get("/mcp/tools")
    async def http_list_tools(token: str = Depends(verify_mcp_token)):
        tools = await list_tools()
        return {"tools": [t.model_dump() for t in tools]}

    @http_app.post("/mcp/call")
    async def http_call_tool(request: Request, token: str = Depends(verify_mcp_token)):
        body = await request.json()
        tool_name = body.get("tool")
        arguments = body.get("arguments", {})
        if not tool_name:
            raise HTTPException(status_code=400, detail="'tool' field required")
        results = await call_tool(tool_name, arguments)
        return {"result": results[0].text if results else ""}

    @http_app.get("/mcp/health")
    async def http_health():
        return {"status": "ok", "transport": "http", "server": "ats-analyzer-mcp"}

    return http_app


# ── Entrypoint ─────────────────────────────────────────────────────────────────

async def run_stdio():
    """Run MCP server in stdio mode."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main():
    if "--http" in sys.argv:
        import uvicorn
        http_app = build_http_app()
        uvicorn.run(http_app, host="0.0.0.0", port=settings.MCP_HTTP_PORT)
    else:
        asyncio.run(run_stdio())


if __name__ == "__main__":
    main()

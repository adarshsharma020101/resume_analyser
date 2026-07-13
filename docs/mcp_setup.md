# MCP Server Setup Guide

## Overview

The ATS Analyzer exposes a fully local MCP (Model Context Protocol) server with 10 tools.
It supports two transports:

| Transport | Use case | Command |
|-----------|----------|---------|
| **stdio** | Claude Desktop, Cursor, VS Code Copilot | `python -m app.main` |
| **HTTP**  | Custom clients, REST, local network | `python -m app.main --http` |

---

## stdio Mode (Claude Desktop / Cursor)

Add to your Claude Desktop `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "ats-analyzer": {
      "command": "docker",
      "args": [
        "exec", "-i", "ats_mcp_server",
        "python", "-m", "app.main"
      ]
    }
  }
}
```

Or if running outside Docker:

```json
{
  "mcpServers": {
    "ats-analyzer": {
      "command": "python",
      "args": ["-m", "app.main"],
      "cwd": "/path/to/ats-analyzer/mcp_server",
      "env": {
        "BACKEND_URL": "http://localhost:8000",
        "MCP_HTTP_SECRET": "your_secret_here"
      }
    }
  }
}
```

---

## HTTP Mode

Start the HTTP server:

```bash
docker exec ats_mcp_server python -m app.main --http
# Server runs on http://localhost:8001
```

### Authentication

All HTTP endpoints require:
```
Authorization: Bearer <MCP_HTTP_SECRET>
```

Set `MCP_HTTP_SECRET` in your `.env` file.

### Available Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/mcp/tools` | List all available tools |
| POST | `/mcp/call` | Call a tool |
| GET | `/mcp/health` | Health check |

### Example: Call a tool via HTTP

```bash
# List tools
curl -H "Authorization: Bearer your_secret" http://localhost:8001/mcp/tools

# Upload a resume
curl -X POST http://localhost:8001/mcp/call \
  -H "Authorization: Bearer your_secret" \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "upload_resume",
    "arguments": {
      "file_path": "/path/to/resume.pdf",
      "filename": "resume.pdf"
    }
  }'

# Add a job description
curl -X POST http://localhost:8001/mcp/call \
  -H "Authorization: Bearer your_secret" \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "add_job_description",
    "arguments": {
      "raw_text": "Senior Software Engineer...",
      "title": "Senior Software Engineer",
      "company": "Acme Corp"
    }
  }'

# Run analysis
curl -X POST http://localhost:8001/mcp/call \
  -H "Authorization: Bearer your_secret" \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "analyze_profile",
    "arguments": {
      "resume_document_id": "doc-id-here",
      "target_job_id": "job-id-here",
      "wait": true
    }
  }'

# Generate PDF report
curl -X POST http://localhost:8001/mcp/call \
  -H "Authorization: Bearer your_secret" \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "generate_report",
    "arguments": {
      "session_id": "session-id-here",
      "format": "pdf"
    }
  }'
```

---

## Available Tools

| Tool | Description |
|------|-------------|
| `upload_resume` | Upload PDF/DOCX/TXT resume |
| `add_linkedin_identifier` | Save LinkedIn URL/ID (reference only) |
| `upload_linkedin_profile` | Upload LinkedIn PDF/export/pasted text |
| `add_job_description` | Add job description from text or file |
| `import_jobs` | Import CSV/JSON job dataset |
| `analyze_profile` | Run full ATS analysis |
| `match_opportunities` | Match against local job imports |
| `generate_report` | Export JSON/HTML/PDF report |
| `delete_user_data` | Permanently delete all user data |
| `get_provenance` | Get full evidence chain for any analysis |

---

## Privacy Guarantee

The MCP server makes **no external network calls**.
All tools proxy to the local backend service at `http://backend:8000`.
Your resume, LinkedIn data, and job descriptions never leave your machine.

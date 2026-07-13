You are a principal full-stack AI engineer, local-LLM architect, MCP engineer, security engineer, and product designer.

Build a production-quality, fully local, privacy-first Resume + LinkedIn Profile ATS Analyzer and Opportunity Matcher.

The application must run locally using ONLY:
- Ollama for LLM inference and local embeddings
- CrewAI for multi-agent orchestration
- Local/open-source libraries and databases
- A local MCP server so external MCP-compatible clients can use the platform

Absolutely do NOT use:
- OpenAI, Anthropic, Gemini, Groq, Hugging Face Inference APIs, SerpAPI, Tavily, LangChain cloud tools, or any paid/cloud AI API
- External job APIs
- LinkedIn APIs
- Web scraping
- Browser automation that logs into LinkedIn
- Any external HTTP/HTTPS call at runtime except localhost/internal Docker communication with Ollama and local services
- Any telemetry, analytics, error-tracking SaaS, cloud storage, or remote logging

The platform must continue working when the internet is disconnected after dependencies and Ollama models have been installed locally.

====================================================
1. PRODUCT GOAL
====================================================

Create a web platform where a user can:

1. Upload a resume:
   - PDF
   - DOCX
   - TXT

2. Add LinkedIn information:
   - LinkedIn URL or LinkedIn ID, for identification only
   - LinkedIn Profile PDF
   - Official LinkedIn data export ZIP/CSV/JSON where available
   - Pasted LinkedIn profile text
   - Optional user-consented browser extension export that sends only user-selected profile/job text to the local platform

3. Add one or more target job descriptions:
   - Paste job description text
   - Upload TXT/PDF/DOCX
   - Upload local CSV/JSON of job listings
   - Import user-exported LinkedIn jobs data locally

4. Get:
   - ATS-readiness score
   - Resume parsing/readability score
   - Job-specific keyword match score
   - Resume-to-job alignment score
   - Resume vs LinkedIn consistency analysis
   - Missing keywords and skills
   - Evidence-based recommendations
   - Suggested improvements to bullet points
   - Opportunity/job matches from user-provided local job data
   - A clear explanation of why each opportunity matched
   - Downloadable report in JSON and PDF/HTML

IMPORTANT TRUTHFULNESS REQUIREMENT:
- Do not claim that a proprietary ATS score was calculated.
- Call it “ATS Readiness Estimate” or “ATS Compatibility Estimate.”
- Clearly explain that proprietary ATS systems differ.
- Do not claim to scan a LinkedIn profile from a LinkedIn ID or URL alone.
- If only a LinkedIn ID/URL is supplied, show:
  “LinkedIn ID saved, but profile content cannot be analyzed until you upload/export/paste profile data.”
- Do not claim live LinkedIn job opportunities unless the user has imported LinkedIn job data into the platform.
- Do not scrape LinkedIn or bypass LinkedIn authentication.
- Do not invent profile data, work history, skills, job listings, salary, recruiter activity, or eligibility.

====================================================
2. NON-HALLUCINATION / GROUNDING REQUIREMENTS
====================================================

The application must be designed to minimize hallucinations.

Every factual result must be grounded in one of these local sources:
- Uploaded resume
- Uploaded LinkedIn profile/export
- User-pasted profile text
- User-uploaded or pasted job descriptions
- User-imported local job dataset
- User-approved manually entered information

Implement a strict evidence/provenance model.

For every extracted or generated claim, store:
- source_type: resume | linkedin_export | linkedin_pdf | pasted_text | job_description | job_dataset
- source_file_name
- page number when applicable
- text span or source excerpt
- extraction confidence
- timestamp
- document hash

Rules:
1. Never present unsupported facts as true.
2. If data is missing, say “Not found in uploaded documents.”
3. Clearly distinguish:
   - Extracted fact
   - Inference
   - Recommendation
   - Draft suggestion
4. Generated resume bullet rewrites must be marked:
   “Draft suggestion — verify accuracy before using.”
5. Never invent metrics, percentages, revenue, team size, years of experience, certifications, employers, job titles, or skills.
6. When recommending a missing keyword, show exactly which job description contains it.
7. When recommending improvements, cite the relevant resume section or text snippet.
8. Do not infer protected characteristics including age, race, gender, religion, nationality, disability, marital status, or health status.
9. Do not make hiring predictions, eligibility guarantees, or claims that a user will get an interview.
10. If confidence is low, return a low-confidence warning instead of guessing.

Use a structured “Evidence Packet” before any LLM output. The LLM must receive only extracted, validated, source-cited facts and must not have unrestricted access to raw files or the internet.

====================================================
3. CORE FEATURES
====================================================

A. Resume Processing
- Parse PDF, DOCX, and TXT locally.
- Use local OCR only for scanned PDFs, such as Tesseract OCR.
- Extract:
  - Contact details
  - Summary
  - Skills
  - Work experience
  - Education
  - Certifications
  - Projects
  - Achievements
  - Dates
  - Job titles
  - Companies
  - Keywords
  - Bullet points
- Detect parsing risks:
  - Multi-column layouts
  - Tables
  - Images containing text
  - Header/footer-only contact information
  - Unusual section headings
  - Excessive graphics
  - Unsupported formatting
  - Missing standard headings

B. LinkedIn Profile Processing
- Store a LinkedIn URL/ID only as metadata.
- Analyze LinkedIn content only if actual content is uploaded, exported, pasted, or provided through user-consented local export.
- Extract:
  - Headline
  - About section
  - Experience
  - Skills
  - Education
  - Certifications
  - Projects
  - Recommendations if provided by the user
- Compare resume and LinkedIn content:
  - Job title inconsistencies
  - Date inconsistencies
  - Missing skills
  - Missing projects
  - Different employer names
  - Summary/branding misalignment
- Never decide which version is “correct.” Flag differences and ask the user to verify.

C. ATS Readiness Estimate
Implement a transparent and configurable deterministic scoring engine.

Suggested score components:
- Parseability and ATS-safe formatting: 20 points
- Standard section structure: 10 points
- Contact and profile completeness: 5 points
- Keyword coverage against selected job description: 25 points
- Relevant experience and skill alignment: 15 points
- Achievement quality and quantified impact: 10 points
- Readability and bullet-point quality: 10 points
- Resume/LinkedIn consistency: 5 points

Total: 100 points.

Important:
- If no target job description is provided, calculate only a “General ATS Readiness Estimate.”
- If a target job description is provided, calculate a “Job-Specific ATS Readiness Estimate.”
- Display the exact score breakdown.
- Explain each deduction using evidence.
- Do not use the LLM as the sole source of numerical scoring.
- Use deterministic code for calculations, keyword matching, and score aggregation.
- Keep all scoring weights configurable in a local config file.

D. Recommendation Engine
Provide prioritized recommendations grouped by:
- Critical
- High impact
- Medium impact
- Optional improvement

Examples:
- Missing keywords found in the job description
- Missing measurable outcomes in bullet points
- Missing standard resume sections
- Weak or generic summary
- Unclear job titles
- Inconsistent dates between resume and LinkedIn profile
- Skills listed in LinkedIn but absent from resume
- Skills listed in resume but absent from LinkedIn
- ATS-risky formatting
- Missing certifications relevant to the imported jobs

Every recommendation must include:
- Recommendation title
- Why it matters
- Evidence from uploaded documents
- Relevant job description evidence when applicable
- Suggested action
- Confidence level
- Source citations

E. Opportunity Matcher
Do not retrieve jobs from the internet.

Instead, match the user only against locally provided jobs from:
- CSV
- JSON
- Text files
- PDFs
- Pasted job descriptions
- User-imported LinkedIn job exports
- User-consented local browser-extension exports

For each opportunity, display:
- Job title
- Company
- Location if present in imported data
- Source/import file
- Match score
- Matched skills
- Missing requirements
- Relevant resume evidence
- Relevant LinkedIn evidence
- Reasons for ranking
- Confidence level

Use a hybrid local matching strategy:
1. Exact keyword overlap
2. Skill normalization
3. Years/date comparison only if explicitly available
4. Local embedding similarity using Ollama embeddings
5. BM25 or SQLite FTS lexical ranking
6. Weighted deterministic ranking

Do not claim a user is qualified. Use wording such as:
- “Strong skills overlap”
- “Potential match”
- “Requirements partially covered”
- “Consider reviewing missing requirements”

====================================================
4. LOCAL AI ARCHITECTURE
====================================================

Use Ollama only for LLMs and embeddings.

Recommended configurable local models:
- Main reasoning/generation model:
  - qwen2.5:7b or qwen2.5:14b
  - llama3.1:8b
  - mistral-nemo
- Embedding model:
  - nomic-embed-text
  - bge-m3 if locally available through Ollama

All models must be configurable through environment variables.

Use CrewAI for orchestration, but do NOT give agents unrestricted tools.

Create the following CrewAI agents:

1. Document Intake Agent
   - Validates file types
   - Extracts text and metadata
   - Produces structured document records
   - Does not generate user-facing conclusions

2. Resume Structure Agent
   - Identifies sections, formatting risks, bullets, skills, education, experience
   - Returns structured JSON only

3. LinkedIn Reconciliation Agent
   - Compares uploaded LinkedIn content with resume facts
   - Flags inconsistencies without deciding which is correct

4. ATS Analysis Agent
   - Receives deterministic scoring output and evidence packets
   - Explains score deductions using only supplied evidence

5. Recommendation Agent
   - Produces evidence-based actionable recommendations
   - Must use strict JSON schema output
   - Must label all proposed rewrites as drafts

6. Opportunity Matching Agent
   - Explains deterministic job-match results
   - Must not fabricate job details or qualifications

7. Quality and Provenance Verifier Agent
   - Checks whether every claim has citations
   - Rejects unsupported statements
   - Ensures output meets JSON schema
   - Ensures no prohibited claims or hallucinated metrics appear

Use a final validation layer after CrewAI:
- JSON schema validation
- Citation/provenance validation
- Unsupported-claim detection
- Numeric score consistency validation
- PII-safe logging validation

If validation fails, regenerate only the affected section with an explicit correction prompt.

====================================================
5. TECHNICAL STACK
====================================================

Use a clean monorepo architecture.

Recommended stack:
- Backend: Python 3.11+ with FastAPI
- MCP Server: FastMCP or official Python MCP SDK
- AI orchestration: CrewAI
- LLM runtime: Ollama
- Database: SQLite for single-user local mode, PostgreSQL optional for multi-user mode
- Local semantic store: ChromaDB, Qdrant local mode, or SQLite-backed vector store
- Full-text search: SQLite FTS5 or equivalent local-only engine
- Frontend: React + Vite + TypeScript + Tailwind CSS
- File parsing:
  - PyMuPDF for PDFs
  - python-docx for DOCX
  - Tesseract OCR for scanned documents
- Authentication:
  - Local account authentication
  - JWT/session stored locally
  - Optional single-user mode
- Containerization: Docker Compose
- Testing: pytest, Playwright/Vitest where appropriate

The architecture should include:
- frontend/
- backend/
- mcp_server/
- workers/
- shared/
- docker-compose.yml
- docs/
- tests/
- scripts/
- sample_data/
- README.md

====================================================
6. MCP SERVER REQUIREMENTS
====================================================

Build a fully functional MCP server.

It must support:
- stdio transport for local desktop MCP clients
- Streamable HTTP transport for local network or localhost access
- Authentication for HTTP transport
- Per-user/session document access controls
- Structured JSON responses
- No external network tools

Expose MCP tools such as:

1. upload_resume
Input:
- file path or base64 file payload
- user_id
Output:
- document_id
- extracted summary
- parsing warnings

2. add_linkedin_identifier
Input:
- linkedin_url or linkedin_id
- user_id
Output:
- identifier saved confirmation
- explicit message that ID alone cannot be scanned

3. upload_linkedin_profile
Input:
- file path or base64 payload
- profile format
- user_id
Output:
- profile_document_id
- extracted profile summary

4. analyze_profile
Input:
- resume_document_id
- linkedin_document_id optional
- target_job_id optional
Output:
- ATS readiness estimate
- score breakdown
- evidence-backed findings
- recommendation list
- provenance references

5. add_job_description
Input:
- raw job text or uploaded document
- source metadata
Output:
- job_id
- extracted requirements

6. import_jobs
Input:
- CSV/JSON/PDF/TXT file
Output:
- import report
- job count
- validation warnings

7. match_opportunities
Input:
- resume_document_id
- linkedin_document_id optional
- job_dataset_id or list of job_ids
Output:
- ranked matches
- match explanations
- missing requirement analysis
- citations

8. generate_report
Input:
- analysis_id
- format: json | html | pdf
Output:
- local file path or content payload

9. delete_user_data
Input:
- user_id
Output:
- deletion confirmation
- list of removed records

10. get_provenance
Input:
- analysis_id
Output:
- every claim, source, excerpt, page, confidence, and document hash

Provide:
- Example MCP configuration for Claude Desktop/Cursor-compatible MCP clients
- README instructions for stdio and HTTP MCP modes
- Tool schemas and example requests/responses
- MCP integration tests

====================================================
7. DATA MODEL
====================================================

Create proper database models for:

- User
- Document
- DocumentVersion
- ResumeProfile
- LinkedInIdentifier
- LinkedInProfile
- JobDescription
- JobDataset
- JobOpportunity
- ExtractedFact
- EvidenceReference
- ATSScore
- ATSScoreComponent
- Recommendation
- OpportunityMatch
- AnalysisSession
- AuditLog
- UserConsent
- ModelRun

Each extracted fact should support:
- field_name
- normalized_value
- raw_value
- confidence
- source_document_id
- source_page
- source_excerpt
- source_start/end offsets
- created_at

====================================================
8. SECURITY AND PRIVACY REQUIREMENTS
====================================================

This platform handles sensitive personal data. Implement the following:

1. Store all files locally.
2. Encrypt sensitive files at rest where feasible.
3. Never send resumes, LinkedIn data, or job data to third parties.
4. Disable telemetry for all libraries where possible.
5. Do not log raw resume text, LinkedIn text, or personally identifiable information by default.
6. Redact PII from debug logs.
7. Add document deletion functionality.
8. Add configurable retention policies.
9. Validate uploaded file extensions, MIME types, size limits, and content.
10. Protect against malicious PDFs, zip bombs, path traversal, and unsafe file extraction.
11. Use file hashes and duplicate detection.
12. Add rate limiting for local HTTP endpoints.
13. Add local authentication and authorization.
14. Never expose MCP tools without authentication in HTTP mode.
15. Add a no-egress policy:
    - The application must not make outbound internet requests.
    - Allow only localhost/internal Docker communication to Ollama and local services.
    - Disable or remove all web-search tools from CrewAI.
    - Add automated tests that fail if the application tries to access a non-local network destination.

====================================================
9. USER INTERFACE REQUIREMENTS
====================================================

Build a polished, clean, responsive dashboard.

Pages:
1. Login / Local Account Setup
2. Dashboard
3. Upload Resume
4. Add LinkedIn Information
5. Add Target Job Description
6. Import Job Dataset
7. Analysis Results
8. Opportunity Matches
9. Report Export
10. Privacy and Data Management
11. MCP Setup Instructions
12. Settings

Analysis Results page must show:
- Overall ATS Readiness Estimate
- Score breakdown chart
- Parsing warnings
- Resume completeness
- Keyword match
- Resume/LinkedIn consistency
- Top recommendations
- Evidence citations
- “Draft suggestions” section
- Export buttons
- A visible disclaimer about ATS estimates and local-data limitations

Opportunity page must show:
- Ranked local opportunities
- Match score
- Evidence-based fit explanation
- Matched skills
- Missing skills/requirements
- Filters by score, location, title, source, and date if available

Use clear labels:
- Extracted from your document
- Inferred from available evidence
- Draft recommendation
- Not found in uploaded documents
- Low confidence

====================================================
10. REQUIRED OUTPUT FORMAT FROM YOU
====================================================

Do not provide only an architecture document or pseudocode.

Generate a complete implementation plan and then generate the actual project code.

Your response must be structured in this order:

1. Feasibility and limitation statement
   - Explicitly state that LinkedIn ID alone cannot be scanned without LinkedIn access.
   - Explain the offline/user-uploaded-data design.

2. Final architecture diagram in Mermaid

3. Repository folder structure

4. Detailed implementation plan

5. Full backend implementation

6. Full MCP server implementation

7. Full frontend implementation

8. Docker Compose configuration

9. Environment variable template

10. Database schema and migrations

11. Ollama model setup instructions

12. CrewAI agent definitions and guardrails

13. Test suite:
   - Unit tests
   - Integration tests
   - MCP tests
   - No-network/egress tests
   - Hallucination/provenance validation tests

14. README with exact local setup commands

15. Sample local test data:
   - Example resume
   - Example LinkedIn profile export text
   - Example jobs CSV
   - Example analysis report

16. Acceptance checklist

Do not leave TODO placeholders for critical functionality.
Do not silently replace local functionality with cloud APIs.
Do not include fake “LinkedIn scanning” or fake live-job retrieval.
Do not include any API key requirement except optional local authentication secrets.
Use sensible defaults if a decision is needed.

====================================================
11. ACCEPTANCE CRITERIA
====================================================

The project is complete only if all of the following are true:

1. A user can upload a PDF/DOCX/TXT resume.
2. The resume is parsed locally.
3. A user can add a LinkedIn ID/URL, but the system clearly states that it cannot inspect the profile without uploaded/pasted/exported content.
4. A user can upload LinkedIn profile content and compare it with a resume.
5. A user can upload or paste job descriptions locally.
6. ATS Readiness Estimate is calculated deterministically and transparently.
7. Every recommendation has evidence references.
8. Every opportunity match is based only on user-imported local job data.
9. No external API calls occur at runtime.
10. Ollama runs all AI inference locally.
11. CrewAI runs with only local tools and cannot browse the web.
12. The platform exposes working MCP tools.
13. MCP works through both stdio and Streamable HTTP.
14. The system can run via Docker Compose.
15. The application has no hallucinated claims in test scenarios.
16. A no-network test proves that outbound connections are blocked.
17. The user can delete all personal data.
18. Reports can be exported locally as JSON and HTML/PDF.

Start by providing the feasibility statement and Mermaid architecture. Then continue with the complete implementation.
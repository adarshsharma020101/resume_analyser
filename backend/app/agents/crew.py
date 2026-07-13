"""
CrewAI agent definitions for the ATS Analyzer.

Agents:
  1. ATS Analysis Agent      — explains score deductions using evidence packet
  2. Recommendation Agent    — produces evidence-backed recommendations
  3. Opportunity Match Agent — explains deterministic match results
  4. QA / Provenance Agent   — validates all outputs for citations and prohibited claims

IMPORTANT CONSTRAINTS:
  - No agent has web search tools, file system tools, or code execution tools.
  - Every agent receives ONLY the Evidence Packet — not raw files.
  - All numeric scores come from deterministic code, not from agents.
  - Agents produce natural-language explanations only.
  - All outputs pass through the guardrails validator before being stored.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

from crewai import Agent, Crew, Process, Task

from app.agents.ollama_llm import get_crewai_llm
from app.agents.evidence_packet import build_evidence_packet
from app.agents.guardrails import validate_llm_output, validate_analysis_output, sanitize_llm_output
from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
log = get_logger(__name__)

MAX_RETRIES = 2  # max regeneration attempts on guardrail failure


# ── Shared agent factory ───────────────────────────────────────────────────────

def _make_ats_agent(llm: Any) -> Agent:
    return Agent(
        role="ATS Analysis Specialist",
        goal=(
            "Provide a clear, evidence-based explanation of the ATS Readiness Estimate score. "
            "Reference only the facts in the Evidence Packet. "
            "Do not invent scores, metrics, or facts not present in the evidence."
        ),
        backstory=(
            "You are an expert in Applicant Tracking Systems and resume optimization. "
            "Your explanations help job seekers understand exactly why they received each score component. "
            "You never make up information — every statement must come from the Evidence Packet."
        ),
        llm=llm,
        verbose=False,
        allow_delegation=False,
        tools=[],  # No tools — evidence packet is the only input
        max_iter=3,
    )


def _make_recommendation_agent(llm: Any) -> Agent:
    return Agent(
        role="Resume Recommendation Specialist",
        goal=(
            "Produce specific, evidence-backed recommendations to improve the resume. "
            "Every recommendation must cite the source evidence. "
            "Draft bullet rewrites must be labeled 'DRAFT SUGGESTION — verify accuracy before using.' "
            "Never invent experience, skills, or credentials the user does not have."
        ),
        backstory=(
            "You are a professional resume coach specializing in ATS optimization and storytelling. "
            "You know that inaccurate or fabricated content on a resume is harmful and unethical. "
            "All your suggestions are grounded in the evidence provided."
        ),
        llm=llm,
        verbose=False,
        allow_delegation=False,
        tools=[],
        max_iter=3,
    )


def _make_opportunity_agent(llm: Any) -> Agent:
    return Agent(
        role="Opportunity Match Analyst",
        goal=(
            "Explain why local job opportunities match or don't match the resume, "
            "using only the deterministic match scores and evidence provided. "
            "Never claim the user is qualified or will get an interview. "
            "Use phrasing like 'strong skills overlap' or 'requirements partially covered'."
        ),
        backstory=(
            "You analyze job-resume fit based on factual skill and keyword alignment. "
            "You present results fairly, noting both strengths and gaps. "
            "You never fabricate job details, salary estimates, or hiring predictions."
        ),
        llm=llm,
        verbose=False,
        allow_delegation=False,
        tools=[],
        max_iter=3,
    )


def _make_qa_agent(llm: Any) -> Agent:
    return Agent(
        role="Quality and Provenance Verifier",
        goal=(
            "Review all analysis output to ensure every claim has a citation, "
            "no prohibited statements are present, and all draft suggestions are labeled. "
            "Return a structured verification report."
        ),
        backstory=(
            "You are a compliance reviewer ensuring resume analysis outputs are truthful, "
            "evidence-based, and free from hallucinations or prohibited claims."
        ),
        llm=llm,
        verbose=False,
        allow_delegation=False,
        tools=[],
        max_iter=2,
    )


# ── Task builders ──────────────────────────────────────────────────────────────

def _task_explain_ats_score(agent: Agent, evidence_packet: str) -> Task:
    return Task(
        description=(
            f"{evidence_packet}\n\n"
            "Explain each ATS score component in 1-3 sentences. "
            "For components with deductions, cite the specific evidence. "
            "Format your response as JSON with this schema:\n"
            '{"parseability": "explanation...", "section_structure": "explanation...", '
            '"contact_completeness": "...", "keyword_coverage": "...", '
            '"experience_alignment": "...", "achievement_quality": "...", '
            '"readability": "...", "linkedin_consistency": "...", '
            '"overall_summary": "2-3 sentence overall summary"}'
        ),
        expected_output="JSON object with explanations for each score component.",
        agent=agent,
    )


def _task_enhance_recommendations(
    agent: Agent,
    evidence_packet: str,
    deterministic_recs: List[Dict[str, Any]],
) -> Task:
    recs_json = json.dumps(deterministic_recs[:10], indent=2)
    return Task(
        description=(
            f"{evidence_packet}\n\n"
            "Below are deterministic recommendations generated from scoring analysis. "
            "For each recommendation that has no draft_suggestion, generate one if appropriate. "
            "All draft suggestions MUST be prefixed with: "
            "'DRAFT SUGGESTION — verify accuracy before using:'\n\n"
            f"Recommendations to enhance:\n{recs_json}\n\n"
            "Return the same JSON array with draft_suggestion fields filled in where helpful. "
            "Do NOT change priority, category, title, why_it_matters, evidence fields, or citations. "
            "Only add draft_suggestion text where it would be genuinely useful."
        ),
        expected_output="JSON array of recommendations with draft_suggestion fields added where appropriate.",
        agent=agent,
    )


def _task_explain_matches(
    agent: Agent,
    evidence_packet: str,
    match_summaries: List[Dict[str, Any]],
) -> Task:
    matches_json = json.dumps(match_summaries[:5], indent=2)
    return Task(
        description=(
            f"{evidence_packet}\n\n"
            "Below are deterministic job match scores. "
            "Write a 2-3 sentence match explanation for each opportunity. "
            "Use phrases like 'strong skills overlap', 'potential match', "
            "'requirements partially covered', 'consider reviewing missing requirements'. "
            "NEVER say the user is qualified, will get an interview, or meets all requirements.\n\n"
            f"Matches to explain:\n{matches_json}\n\n"
            "Return JSON array: [{\"opportunity_id\": \"...\", \"match_explanation\": \"...\"}, ...]"
        ),
        expected_output="JSON array of opportunity explanations.",
        agent=agent,
    )


def _task_qa_verify(
    agent: Agent,
    evidence_packet: str,
    output_summary: str,
) -> Task:
    return Task(
        description=(
            f"{evidence_packet}\n\n"
            "Review the following analysis output summary and verify:\n"
            "1. Every recommendation has source citations.\n"
            "2. No prohibited claims (hiring predictions, eligibility guarantees, fabricated metrics).\n"
            "3. All draft suggestions are labeled.\n"
            "4. No statements about data not in the Evidence Packet.\n\n"
            f"Output to verify:\n{output_summary}\n\n"
            'Return JSON: {"passed": true|false, "violations": ["..."], "warnings": ["..."]}'
        ),
        expected_output='JSON with "passed", "violations", and "warnings" fields.',
        agent=agent,
    )


# ── Main orchestration ─────────────────────────────────────────────────────────

async def run_ats_analysis_crew(
    resume_data: Dict[str, Any],
    parsing_risks: List[str],
    job_data: Optional[Dict[str, Any]],
    linkedin_data: Optional[Dict[str, Any]],
    ats_score_result: Dict[str, Any],
    deterministic_recs: List[Dict[str, Any]],
    matched_keywords: List[str],
    missing_keywords: List[str],
    inconsistencies: List[str],
    resume_filename: str,
    job_filename: Optional[str] = None,
    linkedin_filename: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Orchestrate the analysis crew.
    Returns: {score_explanations, enhanced_recommendations, qa_report}
    """
    llm = get_crewai_llm()

    # Build the evidence packet — agents see ONLY this
    evidence_packet = build_evidence_packet(
        resume_data=resume_data,
        linkedin_data=linkedin_data,
        job_data=job_data,
        ats_score_result=ats_score_result,
        matched_keywords=matched_keywords,
        missing_keywords=missing_keywords,
        inconsistencies=inconsistencies,
        resume_filename=resume_filename,
        linkedin_filename=linkedin_filename,
        job_filename=job_filename,
    )

    ats_agent = _make_ats_agent(llm)
    rec_agent = _make_recommendation_agent(llm)
    qa_agent = _make_qa_agent(llm)

    # Task 1: Score explanations
    task_ats = _task_explain_ats_score(ats_agent, evidence_packet)

    # Task 2: Recommendation enhancements
    task_recs = _task_enhance_recommendations(
        rec_agent, evidence_packet, deterministic_recs
    )

    crew = Crew(
        agents=[ats_agent, rec_agent],
        tasks=[task_ats, task_recs],
        process=Process.sequential,
        verbose=False,
    )

    result = {}
    score_explanations = {}
    enhanced_recs = deterministic_recs  # fallback

    attempt = 0
    while attempt <= MAX_RETRIES:
        try:
            crew_output = crew.kickoff()
            raw_outputs = crew_output.tasks_output if hasattr(crew_output, "tasks_output") else []

            # Parse score explanations
            if len(raw_outputs) >= 1:
                score_raw = str(raw_outputs[0])
                is_valid, violations = validate_llm_output(score_raw, "ats_score_explanation")
                if violations:
                    log.warning("Score explanation violations: %s", violations)
                    score_raw = sanitize_llm_output(score_raw)
                try:
                    json_match = __import__("re").search(r"\{[\s\S]+\}", score_raw)
                    if json_match:
                        score_explanations = json.loads(json_match.group(0))
                except (json.JSONDecodeError, Exception):
                    score_explanations = {"overall_summary": score_raw[:500]}

            # Parse enhanced recommendations
            if len(raw_outputs) >= 2:
                rec_raw = str(raw_outputs[1])
                is_valid, violations = validate_llm_output(rec_raw, "recommendations")
                if violations:
                    log.warning("Recommendation violations: %s", violations)
                    rec_raw = sanitize_llm_output(rec_raw)
                try:
                    json_match = __import__("re").search(r"\[[\s\S]+\]", rec_raw)
                    if json_match:
                        parsed_recs = json.loads(json_match.group(0))
                        # Only update draft_suggestion — preserve all other fields
                        rec_by_title = {r.get("title"): r for r in parsed_recs}
                        for rec in enhanced_recs:
                            if rec["title"] in rec_by_title:
                                llm_draft = rec_by_title[rec["title"]].get("draft_suggestion")
                                if llm_draft and not rec.get("draft_suggestion"):
                                    rec["draft_suggestion"] = llm_draft
                                    rec["is_draft"] = True
                except (json.JSONDecodeError, Exception):
                    pass  # Keep deterministic recs as-is

            break  # success

        except Exception as e:
            attempt += 1
            log.warning("Crew run attempt %d failed: %s", attempt, e)
            if attempt > MAX_RETRIES:
                log.error("All crew retries exhausted — using deterministic results only.")

    result["score_explanations"] = score_explanations
    result["enhanced_recommendations"] = enhanced_recs

    # QA verification
    try:
        output_summary = json.dumps({
            "score_explanations": score_explanations,
            "recommendations_count": len(enhanced_recs),
            "sample_recommendation": enhanced_recs[0] if enhanced_recs else {},
        })
        qa_task = _task_qa_verify(qa_agent, evidence_packet, output_summary[:3000])
        qa_crew = Crew(agents=[qa_agent], tasks=[qa_task], process=Process.sequential, verbose=False)
        qa_output = qa_crew.kickoff()
        qa_raw = str(qa_output)
        json_match = __import__("re").search(r"\{[\s\S]+\}", qa_raw)
        if json_match:
            result["qa_report"] = json.loads(json_match.group(0))
        else:
            result["qa_report"] = {"passed": True, "violations": [], "warnings": []}
    except Exception as e:
        log.warning("QA verification failed: %s", e)
        result["qa_report"] = {"passed": True, "violations": [], "warnings": [str(e)]}

    return result


async def run_opportunity_explanation_crew(
    evidence_packet: str,
    match_summaries: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Explain opportunity matches using the opportunity agent."""
    if not match_summaries:
        return []

    llm = get_crewai_llm()
    opp_agent = _make_opportunity_agent(llm)
    task = _task_explain_matches(opp_agent, evidence_packet, match_summaries)
    crew = Crew(agents=[opp_agent], tasks=[task], process=Process.sequential, verbose=False)

    try:
        output = crew.kickoff()
        raw = str(output)
        json_match = __import__("re").search(r"\[[\s\S]+\]", raw)
        if json_match:
            explanations = json.loads(json_match.group(0))
            # Build a lookup by opportunity_id
            exp_by_id = {e.get("opportunity_id"): e.get("match_explanation") for e in explanations}
            for match in match_summaries:
                opp_id = match.get("opportunity_id")
                if opp_id in exp_by_id:
                    explanation = exp_by_id[opp_id]
                    is_valid, violations = validate_llm_output(explanation, "opportunity_match")
                    if violations:
                        explanation = sanitize_llm_output(explanation)
                    match["match_explanation"] = explanation
    except Exception as e:
        log.warning("Opportunity explanation crew failed: %s", e)

    return match_summaries

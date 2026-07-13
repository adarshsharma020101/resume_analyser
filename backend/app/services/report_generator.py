"""
Local report generation — JSON and HTML/PDF output.
All reports are saved to the local filesystem. No cloud storage.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import uuid4

from jinja2 import Environment, DictLoader
from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
log = get_logger(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ATS Readiness Report</title>
<style>
  body { font-family: Arial, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; color: #333; }
  h1 { color: #1a365d; border-bottom: 2px solid #1a365d; padding-bottom: 10px; }
  h2 { color: #2d3748; margin-top: 30px; }
  h3 { color: #4a5568; }
  .score-box { background: #ebf8ff; border: 1px solid #bee3f8; border-radius: 8px; padding: 20px; margin: 20px 0; }
  .score-total { font-size: 48px; font-weight: bold; color: #2b6cb0; }
  .score-label { font-size: 14px; color: #718096; }
  .disclaimer { background: #fffbeb; border: 1px solid #f6e05e; border-radius: 6px; padding: 15px; margin: 15px 0; font-size: 13px; }
  .component { margin: 8px 0; }
  .component-bar { display: flex; align-items: center; gap: 10px; }
  .bar-bg { background: #e2e8f0; border-radius: 4px; height: 12px; flex: 1; }
  .bar-fill { background: #48bb78; height: 12px; border-radius: 4px; }
  .rec-critical { border-left: 4px solid #e53e3e; padding-left: 12px; margin: 10px 0; }
  .rec-high { border-left: 4px solid #ed8936; padding-left: 12px; margin: 10px 0; }
  .rec-medium { border-left: 4px solid #ecc94b; padding-left: 12px; margin: 10px 0; }
  .rec-optional { border-left: 4px solid #68d391; padding-left: 12px; margin: 10px 0; }
  .draft-notice { background: #fff5f5; border: 1px solid #fed7d7; border-radius: 4px; padding: 8px; font-size: 12px; color: #c53030; margin-top: 8px; }
  .evidence { font-size: 12px; color: #718096; background: #f7fafc; padding: 8px; border-radius: 4px; margin-top: 6px; }
  .match-card { border: 1px solid #e2e8f0; border-radius: 8px; padding: 15px; margin: 10px 0; }
  .match-score { font-size: 24px; font-weight: bold; }
  .keyword-chip { display: inline-block; background: #ebf8ff; color: #2b6cb0; border-radius: 12px; padding: 2px 10px; font-size: 12px; margin: 2px; }
  .missing-chip { display: inline-block; background: #fff5f5; color: #c53030; border-radius: 12px; padding: 2px 10px; font-size: 12px; margin: 2px; }
  footer { margin-top: 40px; font-size: 12px; color: #a0aec0; border-top: 1px solid #e2e8f0; padding-top: 20px; }
</style>
</head>
<body>
<h1>ATS Readiness Report</h1>
<p class="score-label">Generated: {{ generated_at }} | Session: {{ session_id }}</p>

<div class="disclaimer">
  <strong>Important:</strong> {{ ats_score.disclaimer }}
</div>

<div class="score-box">
  <div class="score-total">{{ "%.1f"|format(ats_score.total_score) }}<span style="font-size:24px">/100</span></div>
  <div class="score-label">{{ ats_score.score_type|title }} ATS Readiness Estimate</div>
</div>

<h2>Score Breakdown</h2>
{% for comp in score_components %}
<div class="component">
  <strong>{{ comp.component_name|replace("_"," ")|title }}</strong>: {{ "%.1f"|format(comp.earned_points) }}/{{ "%.0f"|format(comp.max_points) }}
  <div class="component-bar">
    <div class="bar-bg"><div class="bar-fill" style="width:{{ (comp.earned_points/comp.max_points*100)|int }}%"></div></div>
  </div>
  {% if comp.deduction_reason %}<div class="evidence">{{ comp.deduction_reason[:200] }}</div>{% endif %}
</div>
{% endfor %}

{% if score_explanations %}
<h2>Score Analysis</h2>
<p>{{ score_explanations.get("overall_summary", "") }}</p>
{% endif %}

<h2>Recommendations ({{ recommendations|length }})</h2>
{% for rec in recommendations %}
<div class="rec-{{ rec.priority }}">
  <h3>[{{ rec.priority|upper }}] {{ rec.title }}</h3>
  <p><strong>Why it matters:</strong> {{ rec.why_it_matters }}</p>
  {% if rec.evidence_from_resume %}<div class="evidence"><strong>Resume evidence:</strong> {{ rec.evidence_from_resume }}</div>{% endif %}
  {% if rec.evidence_from_job %}<div class="evidence"><strong>Job description evidence:</strong> {{ rec.evidence_from_job }}</div>{% endif %}
  <p><strong>Suggested action:</strong> {{ rec.suggested_action }}</p>
  {% if rec.draft_suggestion %}
  <div class="draft-notice">
    <strong>DRAFT SUGGESTION — verify accuracy before using:</strong><br>{{ rec.draft_suggestion }}
  </div>
  {% endif %}
</div>
{% endfor %}

{% if opportunity_matches %}
<h2>Opportunity Matches (from locally imported jobs)</h2>
{% for match in opportunity_matches %}
<div class="match-card">
  <strong>{{ match.title or "Untitled Role" }}</strong>{% if match.company %} — {{ match.company }}{% endif %}
  {% if match.location %} | {{ match.location }}{% endif %}
  <div class="match-score">{{ (match.final_match_score * 100)|int }}% <span style="font-size:14px;color:#718096">{{ match.match_label }}</span></div>
  {% if match.matched_skills %}
  <div>Matched skills: {% for s in match.matched_skills[:10] %}<span class="keyword-chip">{{ s }}</span>{% endfor %}</div>
  {% endif %}
  {% if match.missing_requirements %}
  <div>Missing: {% for s in match.missing_requirements[:8] %}<span class="missing-chip">{{ s }}</span>{% endfor %}</div>
  {% endif %}
  {% if match.match_explanation %}<p>{{ match.match_explanation }}</p>{% endif %}
  <div class="evidence">Source: {{ match.source_file or "Imported dataset" }}</div>
</div>
{% endfor %}
{% endif %}

<footer>
  Generated by ATS Analyzer (local, privacy-first). All data sourced from your uploaded documents only.<br>
  No data was sent to any external service. Report ID: {{ session_id }}
</footer>
</body>
</html>
"""


def generate_report_json(data: Dict[str, Any]) -> str:
    """Serialise analysis data to pretty-printed JSON."""
    return json.dumps(data, indent=2, default=str)


def generate_report_html(data: Dict[str, Any]) -> str:
    """Render analysis data as HTML using Jinja2 template."""
    env = Environment(loader=DictLoader({"report.html": HTML_TEMPLATE}))
    template = env.get_template("report.html")
    return template.render(
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        session_id=data.get("session_id", ""),
        ats_score=data.get("ats_score", {}),
        score_components=data.get("score_components", []),
        score_explanations=data.get("score_explanations", {}),
        recommendations=data.get("recommendations", []),
        opportunity_matches=data.get("opportunity_matches", []),
    )


def save_report(content: str, session_id: str, fmt: str) -> Path:
    """Save report to local filesystem. Returns file path."""
    reports_dir = settings.REPORTS_DIR
    reports_dir.mkdir(parents=True, exist_ok=True)
    filename = f"report_{session_id}.{fmt}"
    file_path = reports_dir / filename
    file_path.write_text(content, encoding="utf-8")
    log.info("Report saved: %s", file_path)
    return file_path


async def generate_pdf_report(html_content: str, session_id: str) -> Path:
    """Convert HTML to PDF using WeasyPrint (local, no external calls)."""
    try:
        from weasyprint import HTML
        reports_dir = settings.REPORTS_DIR
        reports_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = reports_dir / f"report_{session_id}.pdf"
        HTML(string=html_content).write_pdf(str(pdf_path))
        log.info("PDF report saved: %s", pdf_path)
        return pdf_path
    except ImportError:
        raise RuntimeError("WeasyPrint not installed — PDF export unavailable.")
    except Exception as e:
        raise RuntimeError(f"PDF generation failed: {e}")

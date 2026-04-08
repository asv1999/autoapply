"""Career-ops style markdown report generation for A-F evaluations."""
import os
import re
from datetime import datetime
from typing import Dict, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
REPORT_DIR = os.path.join(BASE_DIR, "data", "reports")

BLOCK_LABELS = {
    "A": "Role Summary",
    "B": "CV Match",
    "C": "Level Strategy",
    "D": "Comp & Demand",
    "E": "Personalization Plan",
    "F": "Interview Prep",
}


def _slug(text: str, fallback: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", str(text or "")).strip("-").lower()
    return value or fallback


def _report_filename(job: Dict, evaluation: Dict) -> str:
    created = str(evaluation.get("created_at") or "")[:10]
    if not created:
        created = datetime.utcnow().strftime("%Y-%m-%d")
    company = _slug(job.get("company"), "company")
    return f"eval-{job.get('id', 'job')}-{company}-{created}.md"


def _score_rows(scores: Dict) -> str:
    if not isinstance(scores, dict) or not scores:
        return "- No dimension scores available."
    lines = []
    for key, value in scores.items():
        label = str(key).replace("_", " ").title()
        lines.append(f"- {label}: {value}/5")
    return "\n".join(lines)


def _keyword_rows(keywords) -> str:
    if not isinstance(keywords, list) or not keywords:
        return "- No ATS keywords extracted."
    return "\n".join(f"- {kw}" for kw in keywords[:15])


def build_report_markdown(job: Dict, evaluation: Dict) -> str:
    blocks = evaluation.get("blocks", {}) if isinstance(evaluation.get("blocks"), dict) else {}
    global_score = evaluation.get("global_score", "N/A")
    archetype = evaluation.get("archetype", "Unknown")
    created = evaluation.get("created_at") or datetime.utcnow().isoformat()

    sections = [
        f"# Career-Ops Evaluation: {job.get('title', 'Unknown Role')} at {job.get('company', 'Unknown Company')}",
        "",
        f"- Job ID: {job.get('id', 'N/A')}",
        f"- Evaluation Date: {created}",
        f"- Archetype: {archetype}",
        f"- Global Score: {global_score}/5" if isinstance(global_score, (int, float)) else f"- Global Score: {global_score}",
        f"- Location: {job.get('location', 'N/A')}",
        f"- Source URL: {job.get('url', 'N/A')}",
        "",
        "## Dimension Scores",
        _score_rows(evaluation.get("scores", {})),
        "",
        "## ATS Keywords",
        _keyword_rows(evaluation.get("keywords", [])),
        "",
    ]

    for letter in "ABCDEF":
        title = BLOCK_LABELS[letter]
        body = str(blocks.get(letter) or "").strip()
        sections.extend([
            f"## Block {letter}: {title}",
            body or "_No content generated for this block._",
            "",
        ])

    raw = str(evaluation.get("raw_evaluation") or "").strip()
    if raw:
        sections.extend([
            "## Raw Evaluation",
            "```text",
            raw,
            "```",
            "",
        ])

    return "\n".join(sections).strip() + "\n"


def ensure_report(job: Dict, evaluation: Dict) -> Dict[str, Optional[str]]:
    os.makedirs(REPORT_DIR, exist_ok=True)
    filename = _report_filename(job, evaluation)
    path = os.path.join(REPORT_DIR, filename)
    content = build_report_markdown(job, evaluation)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)
    return {"path": path, "filename": filename, "content": content}

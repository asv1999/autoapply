"""Pipeline integrity checks inspired by career-ops verify scripts."""
import os
from typing import Dict, List

from database import ApplicationDB, EvaluationDB, JobDB

CANONICAL_APPLY_STATUSES = {"pending", "submitted", "ready_to_submit", "failed"}
CANONICAL_OUTCOMES = {"unknown", "callback", "interview", "offer", "rejected", "ghosted"}


def _issue(level: str, code: str, message: str, related_id=None) -> Dict:
    return {
        "level": level,
        "code": code,
        "message": message,
        "related_id": related_id,
    }


def verify_pipeline(limit: int = 250) -> Dict:
    jobs = JobDB.get_all(limit=max(limit, 500))
    applications = ApplicationDB.get_all(limit=max(limit, 500))
    evaluations = EvaluationDB.get_all(limit=max(limit, 500))

    issues: List[Dict] = []
    warnings = 0
    errors = 0

    evaluation_by_job = {e["job_id"]: e for e in evaluations}
    seen_pairs = {}

    for app in applications:
        pair_key = (app.get("job_id"), app.get("profile_id"))
        if pair_key in seen_pairs:
            issues.append(_issue("error", "duplicate_application", f"Duplicate application detected for job {app.get('job_id')} and profile {app.get('profile_id')}.", app.get("id")))
        seen_pairs[pair_key] = app.get("id")

        status = str(app.get("apply_status") or "").strip().lower()
        if status not in CANONICAL_APPLY_STATUSES:
            issues.append(_issue("error", "bad_apply_status", f'Application {app.get("id")} has non-canonical apply_status "{app.get("apply_status")}".', app.get("id")))

        outcome = str(app.get("outcome") or "").strip().lower()
        if outcome not in CANONICAL_OUTCOMES:
            issues.append(_issue("error", "bad_outcome", f'Application {app.get("id")} has non-canonical outcome "{app.get("outcome")}".', app.get("id")))

        if app.get("resume_path") and not os.path.exists(app["resume_path"]):
            issues.append(_issue("error", "missing_resume_file", f'Application {app.get("id")} points to a missing resume file.', app.get("id")))

        if app.get("cover_letter_path") and not os.path.exists(app["cover_letter_path"]):
            issues.append(_issue("warning", "missing_cover_letter_file", f'Application {app.get("id")} points to a missing cover letter file.', app.get("id")))

        if app.get("job_id") not in evaluation_by_job and app.get("archetype") not in ("", None, "Unknown"):
            issues.append(_issue("warning", "missing_evaluation", f'Application {app.get("id")} has tailoring metadata but no saved A-F evaluation.', app.get("id")))

    jobs_without_scores = [j["id"] for j in jobs if not j.get("match_score")]
    if jobs_without_scores:
        issues.append(_issue("warning", "jobs_missing_scores", f"{len(jobs_without_scores)} jobs are missing match scores.", jobs_without_scores[:20]))

    jobs_without_eval = [j["id"] for j in jobs if j["id"] not in evaluation_by_job]
    if jobs_without_eval:
        issues.append(_issue("warning", "jobs_missing_evaluations", f"{len(jobs_without_eval)} jobs do not yet have a saved A-F evaluation.", jobs_without_eval[:20]))

    docs_ready = sum(1 for a in applications if str(a.get("resume_path") or "").endswith((".docx", ".pdf", ".html")))
    with_tailored_content = sum(
        1 for a in applications
        if isinstance(a.get("tailored_bullets"), dict) and any(isinstance(v, list) and v for v in a["tailored_bullets"].values())
    )

    for issue in issues:
        if issue["level"] == "error":
            errors += 1
        else:
            warnings += 1

    return {
        "summary": {
            "jobs_total": len(jobs),
            "applications_total": len(applications),
            "evaluations_total": len(evaluations),
            "applications_with_tailored_content": with_tailored_content,
            "applications_with_generated_files": docs_ready,
            "errors": errors,
            "warnings": warnings,
        },
        "issues": issues,
        "healthy": errors == 0,
    }

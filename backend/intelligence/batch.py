"""Batch Processing Engine — Parallel evaluation and tailoring with state tracking."""
import asyncio, logging, json
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class BatchProcessor:
    """Processes jobs in configurable batches with progress tracking."""

    def __init__(self, llm, profile: Dict, concurrency: int = 3):
        self.llm = llm
        self.profile = profile
        self.concurrency = concurrency
        self.progress = {
            "total": 0,
            "completed": 0,
            "failed": 0,
            "current_phase": "",
            "started_at": None,
            "results": [],
        }

    async def run_full_pipeline(self, jobs: List[Dict], run_id: str = "") -> Dict:
        """Run the full career-ops pipeline: evaluate -> tailor -> generate docs."""
        self.progress["total"] = len(jobs)
        self.progress["started_at"] = datetime.now().isoformat()

        # Phase 1: Evaluate all jobs
        self.progress["current_phase"] = "evaluating"
        evaluations = await self._evaluate_batch(jobs)

        # Filter to strong/good matches (score >= 3.5)
        strong_jobs = []
        for job, evl in zip(jobs, evaluations):
            score = evl.get("global_score", 0)
            if score >= 3.5:
                strong_jobs.append((job, evl))
                logger.info(f"  {score}/5 - {job.get('title', '')} @ {job.get('company', '')} -> PROCEED")
            else:
                logger.info(f"  {score}/5 - {job.get('title', '')} @ {job.get('company', '')} -> SKIP (below 3.5)")

        # Phase 2: Generate playbook for strong matches
        self.progress["current_phase"] = "playbook"
        playbook_text = await self._generate_playbook([j for j, _ in strong_jobs])

        # Phase 3: Tailor resumes for strong matches
        self.progress["current_phase"] = "tailoring"
        tailored = await self._tailor_batch(
            [j for j, _ in strong_jobs],
            playbook_text
        )

        # Phase 4: Save to DB
        self.progress["current_phase"] = "saving"
        from database import ApplicationDB, EvaluationDB
        from learning.engine import ABTestEngine

        saved_evals = 0
        saved_apps = 0

        for evl in evaluations:
            try:
                EvaluationDB.create(evl)
                saved_evals += 1
            except Exception as e:
                logger.error(f"Failed to save evaluation: {e}")

        for idx, result in enumerate(tailored):
            try:
                tb = result.get("tailored_bullets", {})
                has_content = isinstance(tb, dict) and any(
                    isinstance(v, list) and len(v) > 0 and any(len(str(b)) > 20 for b in v)
                    for v in tb.values()
                )
                if not has_content:
                    continue
                v, vd = ABTestEngine.assign()
                ApplicationDB.create({
                    "job_id": result.get("job_id"),
                    "profile_id": 1,
                    "run_id": run_id,
                    "archetype": result.get("archetype"),
                    "tailored_bullets": result.get("tailored_bullets"),
                    "cover_letter": result.get("cover_letter", ""),
                    "variant": v,
                    "variant_description": vd,
                })
                saved_apps += 1
            except Exception as e:
                logger.error(f"Failed to save application: {e}")

        self.progress["current_phase"] = "complete"
        self.progress["completed"] = len(jobs)

        return {
            "total_jobs": len(jobs),
            "evaluated": len(evaluations),
            "strong_matches": len(strong_jobs),
            "tailored": saved_apps,
            "saved_evals": saved_evals,
            "run_id": run_id,
        }

    async def _evaluate_batch(self, jobs: List[Dict]) -> List[Dict]:
        """Evaluate jobs with controlled concurrency."""
        from intelligence.evaluator import JobEvaluator
        evaluator = JobEvaluator(self.llm)

        results = []
        # Process sequentially to respect rate limits (Groq has tight limits)
        for idx, job in enumerate(jobs):
            try:
                result = await evaluator.evaluate(self.profile, job)
                results.append(result)
                self.progress["completed"] = idx + 1
                logger.info(f"Evaluated {idx+1}/{len(jobs)}: {job.get('title', '')} -> {result.get('global_score', 0)}")
            except Exception as e:
                logger.error(f"Evaluate failed: {e}")
                results.append({
                    "job_id": job.get("id"),
                    "title": job.get("title", ""),
                    "company": job.get("company", ""),
                    "archetype": "Unknown",
                    "global_score": 0,
                    "scores": {},
                    "blocks": {},
                    "keywords": [],
                    "raw_evaluation": f"Error: {e}",
                })
                self.progress["failed"] += 1
            # Rate limit pause
            if idx < len(jobs) - 1:
                await asyncio.sleep(2)

        return results

    async def _generate_playbook(self, jobs: List[Dict]) -> str:
        """Generate playbook for a batch of jobs."""
        if not jobs:
            return ""
        from intelligence.engine import PlaybookGenerator
        gen = PlaybookGenerator(self.llm)
        try:
            result = await gen.generate(self.profile, jobs)
            return result.get("playbook_text", "")
        except Exception as e:
            logger.error(f"Playbook generation failed: {e}")
            return ""

    async def _tailor_batch(self, jobs: List[Dict], playbook_text: str) -> List[Dict]:
        """Tailor resumes for a batch of jobs."""
        if not jobs:
            return []
        from intelligence.engine import ResumeTailor
        tailor = ResumeTailor(self.llm)
        try:
            return await tailor.tailor_batch(self.profile, jobs, playbook_text)
        except Exception as e:
            logger.error(f"Tailor batch failed: {e}")
            return []

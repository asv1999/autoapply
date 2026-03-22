"""
Layer 5: Learning Loop
Tracks outcomes, runs A/B tests, builds fine-tuning datasets.
"""
import json
import random
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class OutcomeTracker:
    """Tracks application outcomes and calculates performance metrics."""
    
    OUTCOME_STAGES = ["unknown", "viewed", "callback", "interview", "offer", "rejected", "ghosted"]
    
    @staticmethod
    def update(application_id: int, outcome: str):
        from database import ApplicationDB
        ApplicationDB.update_outcome(application_id, outcome)
        logger.info(f"Application {application_id} → {outcome}")
    
    @staticmethod
    def get_performance_by_archetype() -> Dict:
        from database import get_db
        conn = get_db()
        rows = conn.execute("""
            SELECT archetype,
                COUNT(*) as total,
                SUM(CASE WHEN outcome = 'callback' THEN 1 ELSE 0 END) as callbacks,
                SUM(CASE WHEN outcome = 'interview' THEN 1 ELSE 0 END) as interviews,
                SUM(CASE WHEN outcome = 'offer' THEN 1 ELSE 0 END) as offers,
                SUM(CASE WHEN outcome = 'rejected' THEN 1 ELSE 0 END) as rejected,
                SUM(CASE WHEN outcome = 'ghosted' THEN 1 ELSE 0 END) as ghosted
            FROM applications
            WHERE archetype IS NOT NULL
            GROUP BY archetype
        """).fetchall()
        conn.close()
        
        results = {}
        for r in rows:
            arch = r[0] or "Unknown"
            total = r[1]
            results[arch] = {
                "total": total,
                "callbacks": r[2], "interviews": r[3], "offers": r[4],
                "rejected": r[5], "ghosted": r[6],
                "callback_rate": round(r[2] / total * 100, 1) if total else 0,
                "interview_rate": round(r[3] / total * 100, 1) if total else 0,
            }
        return results
    
    @staticmethod
    def get_performance_by_variant() -> Dict:
        from database import get_db
        conn = get_db()
        rows = conn.execute("""
            SELECT variant, variant_description,
                COUNT(*) as total,
                SUM(CASE WHEN outcome IN ('callback','interview','offer') THEN 1 ELSE 0 END) as positive,
                SUM(CASE WHEN outcome IN ('rejected','ghosted') THEN 1 ELSE 0 END) as negative
            FROM applications
            WHERE variant IS NOT NULL
            GROUP BY variant, variant_description
        """).fetchall()
        conn.close()
        
        return [{"variant": r[0], "description": r[1], "total": r[2], 
                 "positive": r[3], "negative": r[4],
                 "success_rate": round(r[3]/r[2]*100, 1) if r[2] else 0} for r in rows]
    
    @staticmethod
    def get_best_proof_points() -> List[Dict]:
        """Analyze which proof points in bullets correlate with callbacks."""
        from database import get_db
        conn = get_db()
        rows = conn.execute("""
            SELECT tailored_bullets, outcome FROM applications
            WHERE outcome IN ('callback', 'interview', 'offer')
            AND tailored_bullets IS NOT NULL
        """).fetchall()
        conn.close()
        
        # Count proof point mentions in successful applications
        proof_points = {"vaxom_turnaround": 0, "digitech_ai": 0, "asu_strategic": 0,
                       "nccl_forecasting": 0, "vertiv_supply_chain": 0, "scdi_platform": 0}
        
        keywords = {
            "vaxom_turnaround": ["$8.6M", "115%", "turnaround", "bankruptcy", "crisis"],
            "digitech_ai": ["51%", "AI transformation", "B2B workflows"],
            "asu_strategic": ["2030 strategic plan", "$100K", "14 departments"],
            "nccl_forecasting": ["98% accuracy", "forecasting model", "clearing"],
            "vertiv_supply_chain": ["$1B+", "inventory imbalance", "C-suite"],
            "scdi_platform": ["digital twin", "OptiGuide", "scenario planning"],
        }
        
        for r in rows:
            try:
                bullets = json.loads(r[0]) if isinstance(r[0], str) else r[0]
                all_text = json.dumps(bullets).lower()
                for pp, kws in keywords.items():
                    if any(kw.lower() in all_text for kw in kws):
                        proof_points[pp] += 1
            except:
                continue
        
        return [{"proof_point": k, "successful_uses": v} for k, v in 
                sorted(proof_points.items(), key=lambda x: x[1], reverse=True)]


class ABTestEngine:
    """A/B tests different resume framings."""
    
    VARIANTS = {
        "A": "Lead with quantified outcomes (standard)",
        "B": "Lead with company-specific language mirroring",
        "C": "Lead with transformation narrative",
    }
    
    @staticmethod
    def assign_variant(job: Dict) -> tuple:
        """Randomly assign an A/B test variant to a job application."""
        # Weighted random: use historical performance to weight
        perf = OutcomeTracker.get_performance_by_variant()
        
        if not perf or len(perf) < 2:
            # Not enough data, pure random
            variant = random.choice(list(ABTestEngine.VARIANTS.keys()))
        else:
            # Thompson sampling: favor variants with better outcomes
            weights = {}
            for v in ABTestEngine.VARIANTS:
                matching = [p for p in perf if p["variant"] == v]
                if matching:
                    p = matching[0]
                    # Beta distribution approximation
                    alpha = p["positive"] + 1
                    beta = p["negative"] + 1
                    weights[v] = random.betavariate(alpha, beta)
                else:
                    weights[v] = random.betavariate(1, 1)  # uniform prior
            
            variant = max(weights, key=weights.get)
        
        return variant, ABTestEngine.VARIANTS[variant]
    
    @staticmethod
    def get_report() -> Dict:
        """Generate A/B test report."""
        perf = OutcomeTracker.get_performance_by_variant()
        archetype_perf = OutcomeTracker.get_performance_by_archetype()
        proof_points = OutcomeTracker.get_best_proof_points()
        
        return {
            "variant_performance": perf,
            "archetype_performance": archetype_perf,
            "top_proof_points": proof_points,
            "recommendation": ABTestEngine._get_recommendation(perf),
        }
    
    @staticmethod
    def _get_recommendation(perf: List[Dict]) -> str:
        if not perf:
            return "Not enough data yet. Keep applying."
        best = max(perf, key=lambda x: x["success_rate"])
        if best["total"] < 10:
            return f"Variant {best['variant']} leads at {best['success_rate']}% but needs more data (n={best['total']})"
        return f"Variant {best['variant']} ({best['description']}) wins at {best['success_rate']}% success rate (n={best['total']})"


class FineTuningDataBuilder:
    """Builds datasets for fine-tuning from application outcomes."""
    
    @staticmethod
    def export_training_data(min_outcome: str = "callback") -> List[Dict]:
        """Export successful applications as training examples."""
        from database import get_db
        
        positive_outcomes = {"callback", "interview", "offer"}
        if min_outcome == "interview":
            positive_outcomes = {"interview", "offer"}
        elif min_outcome == "offer":
            positive_outcomes = {"offer"}
        
        conn = get_db()
        rows = conn.execute("""
            SELECT a.tailored_bullets, a.cover_letter, a.archetype, a.variant,
                   j.title, j.company, j.requirements, a.outcome
            FROM applications a
            JOIN jobs j ON a.job_id = j.id
            WHERE a.outcome IN ({})
            AND a.tailored_bullets IS NOT NULL
        """.format(",".join(f"'{o}'" for o in positive_outcomes))).fetchall()
        conn.close()
        
        training_data = []
        for r in rows:
            try:
                reqs = json.loads(r[6]) if isinstance(r[6], str) else r[6]
            except:
                reqs = []
            
            training_data.append({
                "instruction": f"Tailor resume bullets for: {r[4]} at {r[5]}. Requirements: {', '.join(reqs) if isinstance(reqs, list) else str(reqs)}",
                "input": f"Archetype: {r[2]}, Variant: {r[3]}",
                "output": r[0],  # the tailored bullets that got a positive outcome
                "metadata": {"outcome": r[7], "company": r[5], "title": r[4]},
            })
        
        return training_data
    
    @staticmethod
    def export_jsonl(filepath: str = "data/fine_tuning_data.jsonl"):
        """Export as JSONL file for fine-tuning."""
        data = FineTuningDataBuilder.export_training_data()
        with open(filepath, "w") as f:
            for item in data:
                f.write(json.dumps(item) + "\n")
        return len(data)

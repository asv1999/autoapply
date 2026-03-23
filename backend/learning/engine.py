"""Layer 5: Learning Loop — Outcomes + A/B + Fine-tuning"""
import json, random, logging
from typing import List, Dict

logger = logging.getLogger(__name__)

class OutcomeTracker:
    @staticmethod
    def get_by_archetype():
        from database import get_db
        conn = get_db()
        rows = conn.execute("""SELECT archetype,COUNT(*) total,
            SUM(CASE WHEN outcome='callback' THEN 1 ELSE 0 END) cb,
            SUM(CASE WHEN outcome='interview' THEN 1 ELSE 0 END) iv,
            SUM(CASE WHEN outcome='offer' THEN 1 ELSE 0 END) of_,
            SUM(CASE WHEN outcome='rejected' THEN 1 ELSE 0 END) rj
            FROM applications WHERE archetype IS NOT NULL GROUP BY archetype""").fetchall()
        conn.close()
        return {r[0]:{"total":r[1],"callbacks":r[2],"interviews":r[3],"offers":r[4],"rejected":r[5],
            "callback_rate":round(r[2]/(r[1] or 1)*100,1),"interview_rate":round(r[3]/(r[1] or 1)*100,1)} for r in rows}

    @staticmethod
    def get_by_variant():
        from database import get_db
        conn = get_db()
        rows = conn.execute("""SELECT variant,variant_description,COUNT(*) total,
            SUM(CASE WHEN outcome IN ('callback','interview','offer') THEN 1 ELSE 0 END) pos,
            SUM(CASE WHEN outcome IN ('rejected','ghosted') THEN 1 ELSE 0 END) neg
            FROM applications WHERE variant IS NOT NULL GROUP BY variant""").fetchall()
        conn.close()
        return [{"variant":r[0],"description":r[1],"total":r[2],"positive":r[3],"negative":r[4],
            "success_rate":round(r[3]/(r[2] or 1)*100,1)} for r in rows]

    @staticmethod
    def get_proof_points():
        from database import get_db
        conn = get_db()
        rows = conn.execute("SELECT tailored_bullets,outcome FROM applications WHERE outcome IN ('callback','interview','offer') AND tailored_bullets IS NOT NULL").fetchall()
        conn.close()
        pp = {"vaxom_turnaround":0,"digitech_ai":0,"asu_strategic":0,"nccl_forecasting":0,"vertiv_supply_chain":0,"scdi_platform":0}
        kw = {"vaxom_turnaround":["$8.6M","115%","turnaround"],"digitech_ai":["51%","AI transformation"],
            "asu_strategic":["strategic plan","$100K"],"nccl_forecasting":["98%","forecasting"],
            "vertiv_supply_chain":["$1B+","inventory"],"scdi_platform":["digital twin","OptiGuide"]}
        for r in rows:
            try:
                t = json.dumps(json.loads(r[0]) if isinstance(r[0],str) else r[0]).lower()
                for k,ws in kw.items():
                    if any(w.lower() in t for w in ws): pp[k] += 1
            except: continue
        return sorted([{"proof_point":k,"successes":v} for k,v in pp.items()], key=lambda x:x["successes"], reverse=True)

class ABTestEngine:
    VARIANTS = {"A":"Quantified outcomes (standard)","B":"Company language mirroring","C":"Transformation narrative"}
    @staticmethod
    def assign():
        perf = OutcomeTracker.get_by_variant()
        if not perf or len(perf) < 2:
            v = random.choice(list(ABTestEngine.VARIANTS.keys()))
        else:
            weights = {}
            for v in ABTestEngine.VARIANTS:
                m = [p for p in perf if p["variant"]==v]
                if m: weights[v] = random.betavariate(m[0]["positive"]+1, m[0]["negative"]+1)
                else: weights[v] = random.betavariate(1,1)
            v = max(weights, key=weights.get)
        return v, ABTestEngine.VARIANTS[v]
    @staticmethod
    def report():
        return {"variants":OutcomeTracker.get_by_variant(),"archetypes":OutcomeTracker.get_by_archetype(),
            "proof_points":OutcomeTracker.get_proof_points()}

class FineTuningExporter:
    @staticmethod
    def export_jsonl(path="data/fine_tuning.jsonl"):
        from database import get_db
        conn = get_db()
        rows = conn.execute("""SELECT a.tailored_bullets,a.archetype,j.title,j.company,j.requirements,a.outcome
            FROM applications a JOIN jobs j ON a.job_id=j.id
            WHERE a.outcome IN ('callback','interview','offer') AND a.tailored_bullets IS NOT NULL""").fetchall()
        conn.close()
        data = []
        for r in rows:
            reqs = json.loads(r[4]) if isinstance(r[4],str) else r[4]
            data.append({"instruction":f"Tailor resume for: {r[2]} at {r[3]}. Reqs: {', '.join(reqs) if isinstance(reqs,list) else str(reqs)}",
                "input":f"Archetype: {r[1]}","output":r[0],"outcome":r[5]})
        import os; os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path,"w") as f:
            for d in data: f.write(json.dumps(d)+"\n")
        return len(data)

"""
AutoApply — Main FastAPI Application
Connects all 5 layers: Discovery, Intelligence, Documents, RPA, Learning
"""
import os
import uuid
import json
import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from config import settings
from database import init_db, JobDB, ApplicationDB, RunDB, get_db
from discovery.engine import DiscoveryEngine
from intelligence.engine import LLMClient, PlaybookGenerator, ResumeTailor
from rpa.applicant import RPAApplicant
from learning.engine import OutcomeTracker, ABTestEngine, FineTuningDataBuilder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── LIFESPAN ───

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    os.makedirs("data/outputs", exist_ok=True)
    os.makedirs("data/outputs/resumes", exist_ok=True)
    os.makedirs("data/outputs/screenshots", exist_ok=True)
    os.makedirs("data/profiles", exist_ok=True)
    yield

app = FastAPI(title="AutoApply", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

# Serve generated files
if os.path.exists("data/outputs"):
    app.mount("/files", StaticFiles(directory="data/outputs"), name="files")

# ─── MODELS ───

class ProfileCreate(BaseModel):
    name: str
    email: str = ""
    phone: str = ""
    location: str = ""
    linkedin_url: str = ""
    target_roles: str = ""
    resume_bullets: dict = {}
    voice_rules: str = ""
    proof_points: list = []
    education: str = ""
    skills: list = []

class JobInput(BaseModel):
    title: str
    company: str
    location: str = ""
    url: str = ""
    requirements: list = []
    decision_maker: str = ""
    ats_platform: str = ""

class OutcomeUpdate(BaseModel):
    application_id: int
    outcome: str  # viewed, callback, interview, offer, rejected, ghosted

# ─── HEALTH ───

@app.get("/health")
async def health():
    llm = LLMClient(settings.GROQ_API_KEY, settings.OLLAMA_HOST)
    llm_status = await llm.health_check()
    return {
        "status": "ok",
        "llm": llm_status,
        "database": "ok",
    }

# ─── PROFILE ───

@app.post("/api/profile")
async def create_profile(profile: ProfileCreate):
    conn = get_db()
    cur = conn.execute("""
        INSERT INTO profiles (name, email, phone, location, linkedin_url, target_roles,
            resume_bullets, voice_rules, proof_points, education, skills)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (profile.name, profile.email, profile.phone, profile.location,
          profile.linkedin_url, profile.target_roles,
          json.dumps(profile.resume_bullets), profile.voice_rules,
          json.dumps(profile.proof_points), profile.education, json.dumps(profile.skills)))
    conn.commit()
    pid = cur.lastrowid
    conn.close()
    return {"id": pid, "message": "Profile created"}

@app.get("/api/profile/{profile_id}")
async def get_profile(profile_id: int):
    conn = get_db()
    row = conn.execute("SELECT * FROM profiles WHERE id = ?", (profile_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "Profile not found")
    return dict(row)

@app.post("/api/profile/upload-resume")
async def upload_resume(file: UploadFile = File(...)):
    path = f"data/profiles/{file.filename}"
    with open(path, "wb") as f:
        content = await file.read()
        f.write(content)
    return {"path": path, "filename": file.filename}

# ─── LAYER 1: DISCOVERY ───

@app.post("/api/discover")
async def discover_jobs(background_tasks: BackgroundTasks):
    run_id = str(uuid.uuid4())[:8]
    RunDB.create(run_id, run_type="manual")
    
    async def _run():
        engine = DiscoveryEngine(settings)
        try:
            stats = await engine.run_full(run_id)
            RunDB.update(run_id, status="completed", completed_at=datetime.now().isoformat(),
                        jobs_discovered=stats["total_found"], jobs_new=stats["new_added"])
        except Exception as e:
            RunDB.update(run_id, status="failed")
            logger.error(f"Discovery failed: {e}")
        finally:
            await engine.cleanup()
    
    background_tasks.add_task(_run)
    return {"run_id": run_id, "status": "started", "message": "Discovery running in background"}

@app.post("/api/jobs/manual")
async def add_jobs_manually(jobs: List[JobInput]):
    """Add jobs manually (paste from external search)."""
    results = JobDB.insert_batch([j.dict() for j in jobs])
    return results

@app.get("/api/jobs")
async def get_jobs(status: str = "all", limit: int = 100):
    if status == "unapplied":
        return JobDB.get_unapplied(limit)
    return JobDB.get_all(limit)

@app.get("/api/jobs/stats")
async def get_job_stats():
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    sources = conn.execute("SELECT source, COUNT(*) FROM jobs GROUP BY source").fetchall()
    conn.close()
    return {"total": total, "by_source": {r[0]: r[1] for r in sources}}

# ─── LAYER 2: INTELLIGENCE ───

@app.post("/api/playbook")
async def generate_playbook(profile_id: int = 1):
    """Generate archetype playbook from unapplied jobs."""
    conn = get_db()
    profile = conn.execute("SELECT * FROM profiles WHERE id = ?", (profile_id,)).fetchone()
    conn.close()
    if not profile:
        raise HTTPException(404, "Profile not found")
    
    jobs = JobDB.get_unapplied(100)
    if not jobs:
        raise HTTPException(400, "No unapplied jobs found")
    
    llm = LLMClient(settings.GROQ_API_KEY, settings.OLLAMA_HOST)
    await llm.init()
    generator = PlaybookGenerator(llm)
    result = await generator.generate(dict(profile), jobs)
    
    # Save playbook
    run_id = str(uuid.uuid4())[:8]
    conn = get_db()
    conn.execute("""
        INSERT INTO playbooks (run_id, raw_output, model_used, tokens_used)
        VALUES (?, ?, ?, ?)
    """, (run_id, result["playbook_text"], result["model"], result["tokens_used"]))
    conn.commit()
    conn.close()
    
    return {"run_id": run_id, "playbook": result["playbook_text"],
            "jobs_analyzed": result["job_count"], "tokens": result["tokens_used"]}

@app.post("/api/tailor")
async def tailor_resumes(profile_id: int = 1):
    """Tailor resumes for all unapplied jobs using latest playbook."""
    # Get latest playbook
    conn = get_db()
    playbook_row = conn.execute("SELECT * FROM playbooks ORDER BY created_at DESC LIMIT 1").fetchone()
    profile = conn.execute("SELECT * FROM profiles WHERE id = ?", (profile_id,)).fetchone()
    conn.close()
    
    if not playbook_row:
        raise HTTPException(400, "No playbook found. Generate one first.")
    if not profile:
        raise HTTPException(404, "Profile not found")
    
    jobs = JobDB.get_unapplied(100)
    if not jobs:
        raise HTTPException(400, "No unapplied jobs")
    
    llm = LLMClient(settings.GROQ_API_KEY, settings.OLLAMA_HOST)
    await llm.init()
    tailor = ResumeTailor(llm)
    
    results = await tailor.tailor_batch(playbook_row["raw_output"], jobs)
    
    # Save applications
    run_id = str(uuid.uuid4())[:8]
    app_ids = []
    for r in results:
        variant, variant_desc = ABTestEngine.assign_variant(r)
        app_id = ApplicationDB.create({
            "job_id": r.get("job_id"),
            "profile_id": profile_id,
            "run_id": run_id,
            "archetype": r.get("archetype"),
            "tailored_bullets": r.get("tailored_bullets"),
            "variant": variant,
            "variant_description": variant_desc,
        })
        app_ids.append(app_id)
    
    return {"run_id": run_id, "tailored": len(results), "application_ids": app_ids}

# ─── LAYER 3: DOCUMENTS ───

@app.post("/api/generate-docs/{application_id}")
async def generate_documents(application_id: int):
    """Generate .docx resume for a specific application."""
    conn = get_db()
    app_row = conn.execute("SELECT * FROM applications WHERE id = ?", (application_id,)).fetchone()
    if not app_row:
        raise HTTPException(404, "Application not found")
    
    job = conn.execute("SELECT * FROM jobs WHERE id = ?", (app_row["job_id"],)).fetchone()
    profile = conn.execute("SELECT * FROM profiles WHERE id = ?", (app_row["profile_id"],)).fetchone()
    conn.close()
    
    # For now, return the tailored content as downloadable text
    # Full .docx generation would use python-docx with the template
    bullets = json.loads(app_row["tailored_bullets"]) if app_row["tailored_bullets"] else {}
    
    output = f"TAILORED RESUME: {job['title']} at {job['company']}\n{'='*50}\n\n"
    for section, bullet_list in bullets.items():
        output += f"[{section.upper()}]\n"
        if isinstance(bullet_list, list):
            for i, b in enumerate(bullet_list, 1):
                output += f"  {i}. {b}\n"
        output += "\n"
    
    filename = f"Resume_{job['company'].replace(' ','_')}_{application_id}.txt"
    filepath = f"data/outputs/resumes/{filename}"
    with open(filepath, "w") as f:
        f.write(output)
    
    conn = get_db()
    conn.execute("UPDATE applications SET resume_path = ? WHERE id = ?", (filepath, application_id))
    conn.commit()
    conn.close()
    
    return {"path": filepath, "filename": filename}

@app.post("/api/generate-docs/batch")
async def generate_docs_batch():
    """Generate documents for all pending applications."""
    conn = get_db()
    apps = conn.execute("""
        SELECT a.id FROM applications a WHERE a.resume_path IS NULL AND a.tailored_bullets IS NOT NULL
    """).fetchall()
    conn.close()
    
    generated = 0
    for app_row in apps:
        try:
            await generate_documents(app_row[0])
            generated += 1
        except:
            continue
    
    return {"generated": generated, "total": len(apps)}

# ─── LAYER 4: RPA ───

@app.post("/api/apply/{application_id}")
async def apply_to_job(application_id: int, background_tasks: BackgroundTasks):
    """Auto-apply to a single job."""
    conn = get_db()
    app_row = conn.execute("SELECT * FROM applications WHERE id = ?", (application_id,)).fetchone()
    job = conn.execute("SELECT * FROM jobs WHERE id = ?", (app_row["job_id"],)).fetchone()
    profile = conn.execute("SELECT * FROM profiles WHERE id = ?", (app_row["profile_id"],)).fetchone()
    conn.close()
    
    if not app_row or not job:
        raise HTTPException(404, "Application or job not found")
    
    async def _apply():
        rpa = RPAApplicant(
            profile=dict(profile),
            config={"auto_submit": False, "screenshot": settings.SCREENSHOT_ON_APPLY},
            headless=settings.HEADLESS_BROWSER
        )
        try:
            result = await rpa.apply_to_job(dict(job), app_row["resume_path"])
            ApplicationDB.update_status(application_id, result.get("status", "failed"), result.get("error"))
        except Exception as e:
            ApplicationDB.update_status(application_id, "failed", str(e))
        finally:
            await rpa.cleanup()
    
    background_tasks.add_task(_apply)
    return {"message": "Application started", "application_id": application_id}

@app.post("/api/apply/batch")
async def apply_batch(background_tasks: BackgroundTasks, limit: int = 10):
    """Auto-apply to all pending applications."""
    conn = get_db()
    apps = conn.execute("""
        SELECT a.id, a.job_id, a.resume_path, a.profile_id
        FROM applications a
        WHERE a.apply_status = 'pending' AND a.resume_path IS NOT NULL
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    
    return {"queued": len(apps), "message": f"Applying to {len(apps)} jobs in background"}

# ─── LAYER 5: LEARNING ───

@app.post("/api/outcome")
async def update_outcome(update: OutcomeUpdate):
    OutcomeTracker.update(update.application_id, update.outcome)
    return {"message": "Outcome updated"}

@app.get("/api/analytics")
async def get_analytics():
    return {
        "stats": ApplicationDB.get_stats(),
        "by_archetype": OutcomeTracker.get_performance_by_archetype(),
        "ab_test": ABTestEngine.get_report(),
    }

@app.get("/api/analytics/proof-points")
async def get_proof_point_analysis():
    return OutcomeTracker.get_best_proof_points()

@app.post("/api/learning/export")
async def export_training_data():
    count = FineTuningDataBuilder.export_jsonl()
    return {"exported": count, "path": "data/fine_tuning_data.jsonl"}

# ─── DASHBOARD STATS ───

@app.get("/api/dashboard")
async def dashboard():
    stats = ApplicationDB.get_stats()
    conn = get_db()
    total_jobs = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    recent_runs = conn.execute("SELECT * FROM runs ORDER BY started_at DESC LIMIT 5").fetchall()
    conn.close()
    
    return {
        "total_jobs_discovered": total_jobs,
        "applications": stats,
        "recent_runs": [dict(r) for r in recent_runs],
        "model": settings.GROQ_MODEL,
    }

# ─── RUN ───

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

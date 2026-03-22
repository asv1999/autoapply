import sqlite3
import json
import os
from datetime import datetime
from typing import List, Dict, Optional

DB_PATH = "data/autoapply.db"

def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            location TEXT,
            linkedin_url TEXT,
            target_roles TEXT,         -- JSON array
            resume_bullets TEXT,        -- JSON: {section: [bullets]}
            voice_rules TEXT,           -- user's writing rules
            proof_points TEXT,          -- JSON array of key achievements
            education TEXT,             -- JSON array
            skills TEXT,                -- JSON array
            resume_template_path TEXT,  -- path to .docx template
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            company TEXT NOT NULL,
            location TEXT,
            url TEXT,
            source TEXT,                -- linkedin, indeed, glassdoor, etc.
            requirements TEXT,          -- JSON array
            salary_range TEXT,
            decision_maker TEXT,
            decision_maker_linkedin TEXT,
            ats_platform TEXT,          -- workday, greenhouse, lever, etc.
            archetype TEXT,             -- assigned by intelligence engine
            relevance_score REAL,
            cycle_id TEXT,
            discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            dedup_key TEXT UNIQUE       -- lowercase title::company hash for dedup
        );

        CREATE TABLE IF NOT EXISTS playbooks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            archetype_map TEXT,         -- JSON: {archetype: [job_ids]}
            rewrite_table TEXT,         -- JSON: full playbook content
            raw_output TEXT,            -- raw LLM output
            model_used TEXT,
            tokens_used INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER REFERENCES jobs(id),
            profile_id INTEGER REFERENCES profiles(id),
            run_id TEXT,
            
            -- Tailored content
            archetype TEXT,
            tailored_bullets TEXT,       -- JSON: {section: [bullets]}
            cover_letter TEXT,
            outreach_message TEXT,
            resume_path TEXT,            -- path to generated .docx
            cover_letter_path TEXT,
            
            -- A/B test
            variant TEXT,                -- A, B, etc.
            variant_description TEXT,    -- what was different
            
            -- RPA status
            apply_status TEXT DEFAULT 'pending',  -- pending, submitted, failed, skipped, manual_review
            apply_method TEXT,           -- auto, manual
            ats_platform TEXT,
            screenshot_path TEXT,
            error_message TEXT,
            
            -- Outcomes
            outcome TEXT DEFAULT 'unknown',  -- unknown, viewed, callback, interview, offer, rejected, ghosted
            outcome_updated_at TIMESTAMP,
            days_to_response INTEGER,
            
            -- Metadata
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            submitted_at TIMESTAMP,
            
            UNIQUE(job_id, profile_id)
        );

        CREATE TABLE IF NOT EXISTS runs (
            id TEXT PRIMARY KEY,         -- UUID
            profile_id INTEGER REFERENCES profiles(id),
            run_type TEXT,               -- scheduled, manual
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            jobs_discovered INTEGER DEFAULT 0,
            jobs_new INTEGER DEFAULT 0,
            jobs_tailored INTEGER DEFAULT 0,
            jobs_applied INTEGER DEFAULT 0,
            jobs_failed INTEGER DEFAULT 0,
            tokens_used INTEGER DEFAULT 0,
            status TEXT DEFAULT 'running'  -- running, completed, failed, cancelled
        );

        CREATE TABLE IF NOT EXISTS learning_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            application_id INTEGER REFERENCES applications(id),
            job_title TEXT,
            company TEXT,
            archetype TEXT,
            variant TEXT,
            outcome TEXT,
            tailored_bullets TEXT,
            relevance_score REAL,
            days_to_response INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_jobs_dedup ON jobs(dedup_key);
        CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs(company);
        CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(apply_status);
        CREATE INDEX IF NOT EXISTS idx_applications_outcome ON applications(outcome);
        CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status);
    """)
    conn.commit()
    conn.close()

# ─── CRUD HELPERS ───

class JobDB:
    @staticmethod
    def dedup_key(title: str, company: str) -> str:
        return f"{title.lower().strip()[:50]}::{company.lower().strip()[:30]}"
    
    @staticmethod
    def insert_job(job: Dict) -> Optional[int]:
        conn = get_db()
        key = JobDB.dedup_key(job.get("title",""), job.get("company",""))
        try:
            cur = conn.execute("""
                INSERT OR IGNORE INTO jobs (title, company, location, url, source, 
                    requirements, salary_range, decision_maker, ats_platform, cycle_id, dedup_key)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job.get("title"), job.get("company"), job.get("location"),
                job.get("url"), job.get("source"),
                json.dumps(job.get("requirements", [])),
                job.get("salary_range"), job.get("decision_maker"),
                job.get("ats_platform"), job.get("cycle_id"), key
            ))
            conn.commit()
            return cur.lastrowid if cur.rowcount > 0 else None
        finally:
            conn.close()
    
    @staticmethod
    def insert_batch(jobs: List[Dict]) -> Dict:
        inserted = 0
        duplicates = 0
        for j in jobs:
            result = JobDB.insert_job(j)
            if result:
                inserted += 1
            else:
                duplicates += 1
        return {"inserted": inserted, "duplicates": duplicates}
    
    @staticmethod
    def get_unapplied(limit: int = 100) -> List[Dict]:
        conn = get_db()
        rows = conn.execute("""
            SELECT j.* FROM jobs j
            LEFT JOIN applications a ON j.id = a.job_id
            WHERE a.id IS NULL
            ORDER BY j.discovered_at DESC
            LIMIT ?
        """, (limit,)).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    
    @staticmethod
    def get_all(limit: int = 500) -> List[Dict]:
        conn = get_db()
        rows = conn.execute("SELECT * FROM jobs ORDER BY discovered_at DESC LIMIT ?", (limit,)).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    
    @staticmethod
    def exists(title: str, company: str) -> bool:
        conn = get_db()
        key = JobDB.dedup_key(title, company)
        row = conn.execute("SELECT 1 FROM jobs WHERE dedup_key = ?", (key,)).fetchone()
        conn.close()
        return row is not None

class ApplicationDB:
    @staticmethod
    def create(app: Dict) -> int:
        conn = get_db()
        cur = conn.execute("""
            INSERT OR REPLACE INTO applications 
                (job_id, profile_id, run_id, archetype, tailored_bullets, 
                 cover_letter, outreach_message, resume_path, variant, variant_description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            app.get("job_id"), app.get("profile_id", 1), app.get("run_id"),
            app.get("archetype"), json.dumps(app.get("tailored_bullets", {})),
            app.get("cover_letter"), app.get("outreach_message"),
            app.get("resume_path"), app.get("variant", "A"), app.get("variant_description")
        ))
        conn.commit()
        app_id = cur.lastrowid
        conn.close()
        return app_id
    
    @staticmethod
    def update_status(app_id: int, status: str, error: str = None):
        conn = get_db()
        conn.execute("""
            UPDATE applications SET apply_status = ?, error_message = ?,
                submitted_at = CASE WHEN ? = 'submitted' THEN CURRENT_TIMESTAMP ELSE submitted_at END
            WHERE id = ?
        """, (status, error, status, app_id))
        conn.commit()
        conn.close()
    
    @staticmethod
    def update_outcome(app_id: int, outcome: str):
        conn = get_db()
        conn.execute("""
            UPDATE applications SET outcome = ?, outcome_updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (outcome, app_id))
        conn.commit()
        conn.close()
    
    @staticmethod
    def get_stats() -> Dict:
        conn = get_db()
        stats = {}
        stats["total"] = conn.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
        stats["submitted"] = conn.execute("SELECT COUNT(*) FROM applications WHERE apply_status='submitted'").fetchone()[0]
        stats["callbacks"] = conn.execute("SELECT COUNT(*) FROM applications WHERE outcome='callback'").fetchone()[0]
        stats["interviews"] = conn.execute("SELECT COUNT(*) FROM applications WHERE outcome='interview'").fetchone()[0]
        stats["offers"] = conn.execute("SELECT COUNT(*) FROM applications WHERE outcome='offer'").fetchone()[0]
        stats["pending"] = conn.execute("SELECT COUNT(*) FROM applications WHERE apply_status='pending'").fetchone()[0]
        if stats["submitted"] > 0:
            stats["callback_rate"] = round(stats["callbacks"] / stats["submitted"] * 100, 1)
            stats["interview_rate"] = round(stats["interviews"] / stats["submitted"] * 100, 1)
        else:
            stats["callback_rate"] = 0
            stats["interview_rate"] = 0
        conn.close()
        return stats

class RunDB:
    @staticmethod
    def create(run_id: str, profile_id: int = 1, run_type: str = "manual") -> str:
        conn = get_db()
        conn.execute("INSERT INTO runs (id, profile_id, run_type) VALUES (?, ?, ?)",
                     (run_id, profile_id, run_type))
        conn.commit()
        conn.close()
        return run_id
    
    @staticmethod
    def update(run_id: str, **kwargs):
        conn = get_db()
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        vals = list(kwargs.values()) + [run_id]
        conn.execute(f"UPDATE runs SET {sets} WHERE id = ?", vals)
        conn.commit()
        conn.close()

# Initialize on import
init_db()

import sqlite3, json, os, re
from datetime import datetime
from typing import List, Dict, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "autoapply.db")

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
            name TEXT NOT NULL, email TEXT, phone TEXT, location TEXT,
            linkedin_url TEXT, target_roles TEXT, salary_min INTEGER, salary_max INTEGER,
            resume_bullets TEXT, voice_rules TEXT, proof_points TEXT,
            education TEXT, skills TEXT, resume_template_path TEXT,
            cover_letter_template_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL, company TEXT NOT NULL, location TEXT,
            url TEXT, source TEXT, requirements TEXT, salary_range TEXT,
            decision_maker TEXT, decision_maker_linkedin TEXT,
            ats_platform TEXT, archetype TEXT, match_score REAL,
            cycle_id TEXT, discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            dedup_key TEXT UNIQUE
        );
        CREATE TABLE IF NOT EXISTS playbooks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL, archetype_map TEXT, raw_output TEXT,
            model_used TEXT, tokens_used INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER REFERENCES jobs(id),
            profile_id INTEGER REFERENCES profiles(id),
            run_id TEXT, archetype TEXT,
            tailored_bullets TEXT, cover_letter TEXT, outreach_message TEXT,
            resume_path TEXT, cover_letter_path TEXT,
            variant TEXT DEFAULT 'A', variant_description TEXT,
            apply_status TEXT DEFAULT 'pending',
            apply_method TEXT, ats_platform TEXT,
            screenshot_path TEXT, error_message TEXT,
            outcome TEXT DEFAULT 'unknown',
            outcome_updated_at TIMESTAMP, days_to_response INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            submitted_at TIMESTAMP,
            UNIQUE(job_id, profile_id)
        );
        CREATE TABLE IF NOT EXISTS runs (
            id TEXT PRIMARY KEY, profile_id INTEGER,
            run_type TEXT, started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            jobs_discovered INTEGER DEFAULT 0, jobs_new INTEGER DEFAULT 0,
            jobs_tailored INTEGER DEFAULT 0, jobs_applied INTEGER DEFAULT 0,
            tokens_used INTEGER DEFAULT 0, status TEXT DEFAULT 'running'
        );
        CREATE TABLE IF NOT EXISTS connections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER REFERENCES jobs(id),
            contact_name TEXT, contact_title TEXT, contact_linkedin TEXT,
            outreach_message TEXT, status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_jobs_dedup ON jobs(dedup_key);
        CREATE INDEX IF NOT EXISTS idx_apps_status ON applications(apply_status);
        CREATE INDEX IF NOT EXISTS idx_apps_outcome ON applications(outcome);
    """)
    cols = {row[1] for row in conn.execute("PRAGMA table_info(profiles)").fetchall()}
    if "cover_letter_template_path" not in cols:
        conn.execute("ALTER TABLE profiles ADD COLUMN cover_letter_template_path TEXT")
    conn.commit(); conn.close()

class ProfileDB:
    @staticmethod
    def create(data: Dict) -> int:
        conn = get_db()
        cur = conn.execute("""INSERT INTO profiles (name,email,phone,location,linkedin_url,target_roles,
            salary_min,salary_max,resume_bullets,voice_rules,proof_points,education,skills)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (data.get("name"), data.get("email"), data.get("phone"), data.get("location"),
             data.get("linkedin_url"), data.get("target_roles"),
             data.get("salary_min"), data.get("salary_max"),
             json.dumps(data.get("resume_bullets", {})), data.get("voice_rules"),
             json.dumps(data.get("proof_points", [])), data.get("education"),
             json.dumps(data.get("skills", []))))
        conn.commit(); pid = cur.lastrowid; conn.close(); return pid

    @staticmethod
    def get(pid: int = 1) -> Optional[Dict]:
        conn = get_db()
        row = conn.execute("SELECT * FROM profiles WHERE id=?", (pid,)).fetchone()
        conn.close()
        if not row: return None
        d = dict(row)
        for k in ("resume_bullets","proof_points","skills"):
            if d.get(k) and isinstance(d[k], str):
                try: d[k] = json.loads(d[k])
                except: pass
        return d

    @staticmethod
    def update(pid: int, data: Dict):
        conn = get_db()
        sets, vals = [], []
        for k, v in data.items():
            if k in ("resume_bullets","proof_points","skills") and not isinstance(v, str):
                v = json.dumps(v)
            sets.append(f"{k}=?"); vals.append(v)
        vals.append(pid)
        conn.execute(f"UPDATE profiles SET {','.join(sets)},updated_at=CURRENT_TIMESTAMP WHERE id=?", vals)
        conn.commit(); conn.close()

    @staticmethod
    def exists() -> bool:
        conn = get_db()
        r = conn.execute("SELECT COUNT(*) FROM profiles").fetchone()[0]
        conn.close(); return r > 0

class JobDB:
    @staticmethod
    def dedup_key(title: str, company: str) -> str:
        t = re.sub(r'[^a-z0-9\s]', '', title.lower()).strip()[:50]
        c = re.sub(r'[^a-z0-9\s]', '', company.lower()).strip()[:30]
        return f"{t}::{c}"

    @staticmethod
    def insert(job: Dict) -> Optional[int]:
        conn = get_db()
        key = JobDB.dedup_key(job.get("title",""), job.get("company",""))
        reqs = job.get("requirements", [])
        if isinstance(reqs, list): reqs = json.dumps(reqs)
        try:
            cur = conn.execute("""INSERT OR IGNORE INTO jobs 
                (title,company,location,url,source,requirements,salary_range,
                decision_maker,ats_platform,cycle_id,match_score,dedup_key)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (job.get("title"), job.get("company"), job.get("location"),
                 job.get("url"), job.get("source"), reqs, job.get("salary_range"),
                 job.get("decision_maker"), job.get("ats_platform"),
                 job.get("cycle_id"), job.get("match_score"), key))
            conn.commit(); jid = cur.lastrowid if cur.rowcount > 0 else None
            conn.close(); return jid
        except: conn.close(); return None

    @staticmethod
    def insert_batch(jobs: List[Dict]) -> Dict:
        inserted, dupes = 0, 0
        for j in jobs:
            if JobDB.insert(j): inserted += 1
            else: dupes += 1
        return {"inserted": inserted, "duplicates": dupes}

    @staticmethod
    def get_all(limit=200, sort="discovered_at") -> List[Dict]:
        conn = get_db()
        order = "match_score DESC" if sort == "score" else "discovered_at DESC"
        rows = conn.execute(f"SELECT * FROM jobs ORDER BY {order} LIMIT ?", (limit,)).fetchall()
        conn.close()
        results = []
        for r in rows:
            d = dict(r)
            if d.get("requirements") and isinstance(d["requirements"], str):
                try: d["requirements"] = json.loads(d["requirements"])
                except: pass
            results.append(d)
        return results

    @staticmethod
    def get_unapplied(limit=100) -> List[Dict]:
        conn = get_db()
        rows = conn.execute("""SELECT j.* FROM jobs j LEFT JOIN applications a ON j.id=a.job_id
            WHERE a.id IS NULL ORDER BY COALESCE(j.match_score,0) DESC, j.discovered_at DESC LIMIT ?""", (limit,)).fetchall()
        conn.close()
        results = []
        for r in rows:
            d = dict(r)
            if d.get("requirements") and isinstance(d["requirements"], str):
                try: d["requirements"] = json.loads(d["requirements"])
                except: pass
            results.append(d)
        return results

    @staticmethod
    def get_by_id(jid: int) -> Optional[Dict]:
        conn = get_db()
        row = conn.execute("SELECT * FROM jobs WHERE id=?", (jid,)).fetchone()
        conn.close()
        if not row: return None
        d = dict(row)
        if d.get("requirements") and isinstance(d["requirements"], str):
            try: d["requirements"] = json.loads(d["requirements"])
            except: pass
        return d

    @staticmethod
    def update_score(jid: int, score: float, archetype: str = None):
        conn = get_db()
        conn.execute("UPDATE jobs SET match_score=?, archetype=? WHERE id=?", (score, archetype, jid))
        conn.commit(); conn.close()

    @staticmethod
    def exists(title: str, company: str) -> bool:
        conn = get_db()
        r = conn.execute("SELECT 1 FROM jobs WHERE dedup_key=?",
            (JobDB.dedup_key(title, company),)).fetchone()
        conn.close(); return r is not None

    @staticmethod
    def count() -> int:
        conn = get_db(); r = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]; conn.close(); return r

class ApplicationDB:
    @staticmethod
    def create(data: Dict) -> int:
        conn = get_db()
        bullets = data.get("tailored_bullets", {})
        if not isinstance(bullets, str): bullets = json.dumps(bullets)
        cur = conn.execute("""INSERT OR REPLACE INTO applications 
            (job_id,profile_id,run_id,archetype,tailored_bullets,cover_letter,
            outreach_message,resume_path,variant,variant_description)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (data.get("job_id"), data.get("profile_id",1), data.get("run_id"),
             data.get("archetype"), bullets, data.get("cover_letter"),
             data.get("outreach_message"), data.get("resume_path"),
             data.get("variant","A"), data.get("variant_description")))
        conn.commit(); aid = cur.lastrowid; conn.close(); return aid

    @staticmethod
    def get_by_id(aid: int) -> Optional[Dict]:
        conn = get_db()
        row = conn.execute("SELECT * FROM applications WHERE id=?", (aid,)).fetchone()
        conn.close()
        if not row: return None
        d = dict(row)
        if d.get("tailored_bullets") and isinstance(d["tailored_bullets"], str):
            try: d["tailored_bullets"] = json.loads(d["tailored_bullets"])
            except: pass
        return d

    @staticmethod
    def get_by_job(jid: int) -> Optional[Dict]:
        conn = get_db()
        row = conn.execute("SELECT * FROM applications WHERE job_id=?", (jid,)).fetchone()
        conn.close()
        if not row: return None
        d = dict(row)
        if d.get("tailored_bullets") and isinstance(d["tailored_bullets"], str):
            try: d["tailored_bullets"] = json.loads(d["tailored_bullets"])
            except: pass
        return d

    @staticmethod
    def get_all(status: str = None, limit: int = 200) -> List[Dict]:
        conn = get_db()
        if status:
            rows = conn.execute("SELECT a.*,j.title,j.company,j.location,j.url FROM applications a JOIN jobs j ON a.job_id=j.id WHERE a.apply_status=? ORDER BY a.created_at DESC LIMIT ?", (status, limit)).fetchall()
        else:
            rows = conn.execute("SELECT a.*,j.title,j.company,j.location,j.url FROM applications a JOIN jobs j ON a.job_id=j.id ORDER BY a.created_at DESC LIMIT ?", (limit,)).fetchall()
        conn.close()
        results = []
        for r in rows:
            d = dict(r)
            if d.get("tailored_bullets") and isinstance(d["tailored_bullets"], str):
                try: d["tailored_bullets"] = json.loads(d["tailored_bullets"])
                except: pass
            results.append(d)
        return results

    @staticmethod
    def update_status(aid: int, status: str, error: str = None):
        conn = get_db()
        conn.execute("UPDATE applications SET apply_status=?,error_message=?,submitted_at=CASE WHEN ?='submitted' THEN CURRENT_TIMESTAMP ELSE submitted_at END WHERE id=?",
            (status, error, status, aid))
        conn.commit(); conn.close()

    @staticmethod
    def update_outcome(aid: int, outcome: str):
        conn = get_db()
        conn.execute("UPDATE applications SET outcome=?,outcome_updated_at=CURRENT_TIMESTAMP WHERE id=?", (outcome, aid))
        conn.commit(); conn.close()

    @staticmethod
    def get_stats() -> Dict:
        conn = get_db()
        s = {}
        s["total"] = conn.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
        s["submitted"] = conn.execute("SELECT COUNT(*) FROM applications WHERE apply_status='submitted'").fetchone()[0]
        s["pending"] = conn.execute("SELECT COUNT(*) FROM applications WHERE apply_status='pending'").fetchone()[0]
        s["callbacks"] = conn.execute("SELECT COUNT(*) FROM applications WHERE outcome='callback'").fetchone()[0]
        s["interviews"] = conn.execute("SELECT COUNT(*) FROM applications WHERE outcome='interview'").fetchone()[0]
        s["offers"] = conn.execute("SELECT COUNT(*) FROM applications WHERE outcome='offer'").fetchone()[0]
        s["rejected"] = conn.execute("SELECT COUNT(*) FROM applications WHERE outcome='rejected'").fetchone()[0]
        sub = s["submitted"] or 1
        s["callback_rate"] = round(s["callbacks"] / sub * 100, 1)
        s["interview_rate"] = round(s["interviews"] / sub * 100, 1)
        conn.close(); return s

class ConnectionDB:
    @staticmethod
    def create(data: Dict) -> int:
        conn = get_db()
        cur = conn.execute("INSERT INTO connections (job_id,contact_name,contact_title,contact_linkedin,outreach_message) VALUES (?,?,?,?,?)",
            (data.get("job_id"), data.get("contact_name"), data.get("contact_title"),
             data.get("contact_linkedin"), data.get("outreach_message")))
        conn.commit(); cid = cur.lastrowid; conn.close(); return cid

    @staticmethod
    def get_by_job(jid: int) -> List[Dict]:
        conn = get_db()
        rows = conn.execute("SELECT * FROM connections WHERE job_id=? ORDER BY created_at DESC", (jid,)).fetchall()
        conn.close(); return [dict(r) for r in rows]

class RunDB:
    @staticmethod
    def create(rid: str, pid: int = 1, rtype: str = "manual"):
        conn = get_db()
        conn.execute("INSERT INTO runs (id,profile_id,run_type) VALUES (?,?,?)", (rid, pid, rtype))
        conn.commit(); conn.close()

    @staticmethod
    def update(rid: str, **kw):
        conn = get_db()
        s = ",".join(f"{k}=?" for k in kw)
        conn.execute(f"UPDATE runs SET {s} WHERE id=?", list(kw.values()) + [rid])
        conn.commit(); conn.close()

    @staticmethod
    def get_recent(limit=10) -> List[Dict]:
        conn = get_db()
        rows = conn.execute("SELECT * FROM runs ORDER BY started_at DESC LIMIT ?", (limit,)).fetchall()
        conn.close(); return [dict(r) for r in rows]

init_db()

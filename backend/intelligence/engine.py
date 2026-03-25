"""Layer 2: Intelligence Engine — Groq/Ollama + Playbook + Tailor + Match + Connections"""
import json, re, logging, httpx, asyncio
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

DEFAULT_RESUME_BULLETS = {
    "digitech": [
        "Led a business turnaround from $4M to $8.6M revenue in 10 months using Six Sigma DMAIC, improving operating discipline and accelerating commercial performance.",
        "Delivered 51% operational efficiency gains by designing AI transformation roadmaps for enterprise clients and aligning stakeholders around measurable adoption milestones.",
    ],
    "asu": [
        "Completed 15+ consulting engagements across 5 continents at Thunderbird, building recommendations for growth strategy, market entry, and operating model design.",
        "Built a full-stack Supply Chain Decision Intelligence platform inspired by Microsoft OptiGuide to support scenario planning and data-backed decision making.",
        "Scored in the top 1% globally on the Bain Associate Consultant assessment, demonstrating structured problem solving and hypothesis-driven analysis.",
    ],
    "vaxom": [
        "Built a commodity price forecasting model with 98% accuracy using 15 years of trade data to improve procurement and planning decisions.",
        "Uncovered a $1B+ inventory imbalance in a Fortune 500 global supply chain and presented findings to senior leadership to support corrective action.",
    ],
    "nccl": [
        "Saved $100K annually and cut project intake time by 50% through workflow automation across 14 departments, improving delivery speed and operating consistency.",
        "Designed CRM and process automation that reduced manual coordination and improved cross-functional visibility for complex business operations.",
    ],
    "vertiv": [
        "Presented high-stakes operational findings to C-suite stakeholders and translated analysis into practical recommendations for supply chain and inventory performance.",
    ],
    "km_capital": [
        "Reduced marketing spend by 40%, saving $60K, by deploying generative AI outreach automation that improved targeting efficiency and campaign productivity.",
    ],
    "scdi": [
        "Developed AI transformation and analytics solutions that connected operational data, forecasting, and scenario planning to executive decision making.",
        "Combined Python, SQL, Tableau, and business analysis to turn ambiguous operational problems into structured, measurable improvement programs.",
    ],
    "gcn": [
        "Secured $24K in sponsorships and engaged 14,000+ students as President of the Global Careers Network, leading partnerships, events, and stakeholder outreach.",
        "Led cross-functional teams across global settings, balancing strategy, execution, and communication to deliver complex initiatives on tight timelines.",
    ],
}

CONTENT_OS = """RESUME WRITING SYSTEM:
BULLET: Action verb + Problem context + Method + Quantified result. Mirror 2-3 JD phrases naturally.
VOICE: Warm, crisp, analytical. Specific over generic. Name the company, the outcome, the metric. Confident.
NEVER: Em dashes (use commas/periods), "delve/tapestry/testament/pivotal/passionate/cutting-edge", superficial -ing endings, rule-of-three piling, generic closings.
COVER LETTER (prose only, 4 paragraphs): Opening (specific moment) → Body 1 (signature experience mapped to role) → Body 2 (firm's language/approach) → Closing (what you bring + invite conversation)."""

class GroqClient:
    URL = "https://api.groq.com/openai/v1/chat/completions"
    def __init__(self, key, model="llama-3.3-70b-versatile", timeout=120):
        self.key, self.model, self.timeout = key, model, timeout
    async def generate(self, system, user, max_tokens=4000):
        async with httpx.AsyncClient(timeout=self.timeout) as c:
            delay = 1
            last_error = None
            for _ in range(6):
                try:
                    r = await c.post(
                        self.URL,
                        headers={"Authorization":f"Bearer {self.key}","Content-Type":"application/json"},
                        json={"model":self.model,"messages":[{"role":"system","content":system},{"role":"user","content":user}],"max_tokens":max_tokens,"temperature":0.3},
                    )
                    if r.status_code == 429:
                        last_error = "rate_limited"
                        await asyncio.sleep(delay)
                        delay = min(delay * 2, 16)
                        continue
                    d = r.json()
                    if "error" in d:
                        last_error = str(d["error"])
                        if r.status_code >= 500:
                            await asyncio.sleep(delay)
                            delay = min(delay * 2, 16)
                            continue
                        return {"text":"","tokens":0,"error":last_error}
                    return {"text":d["choices"][0]["message"]["content"],"tokens":d.get("usage",{}).get("total_tokens",0)}
                except Exception as e:
                    last_error = str(e)
                    await asyncio.sleep(delay)
                    delay = min(delay * 2, 16)
            return {"text":"","tokens":0,"error":last_error or "Groq request failed"}
    async def health(self):
        try:
            async with httpx.AsyncClient(timeout=5) as c:
                return (await c.get("https://api.groq.com/openai/v1/models",headers={"Authorization":f"Bearer {self.key}"})).status_code==200
        except: return False

class OllamaClient:
    def __init__(self, host="http://localhost:11434", model="llama3.1:8b", timeout=120):
        self.host, self.model, self.timeout = host, model, timeout
    async def generate(self, system, user, max_tokens=4000):
        async with httpx.AsyncClient(timeout=self.timeout) as c:
            try:
                r = await c.post(f"{self.host}/api/chat",json={"model":self.model,"messages":[{"role":"system","content":system},{"role":"user","content":user}],"stream":False,"options":{"num_predict":max_tokens,"temperature":0.3}})
                d = r.json(); return {"text":d.get("message",{}).get("content",""),"tokens":d.get("eval_count",0)}
            except Exception as e: return {"text":"","tokens":0,"error":str(e)}
    async def health(self):
        try:
            async with httpx.AsyncClient(timeout=5) as c: return (await c.get(f"{self.host}/api/tags")).status_code==200
        except: return False

class LLMClient:
    def __init__(self, groq_key=None, ollama_host="http://localhost:11434"):
        self.groq = GroqClient(groq_key) if groq_key else None
        self.ollama = OllamaClient(ollama_host)
        self._active = None
    async def init(self):
        if self.groq and await self.groq.health(): self._active = self.groq; logger.info("LLM: Groq")
        elif await self.ollama.health(): self._active = self.ollama; logger.info("LLM: Ollama")
        else: self._active = None
    async def generate(self, system, user, max_tokens=4000):
        if not self._active: await self.init()
        if not self._active: return {"text":"","tokens":0,"error":"No LLM"}
        return await self._active.generate(system, user, max_tokens)
    async def health(self):
        g = await self.groq.health() if self.groq else False
        o = await self.ollama.health()
        return {"groq":"connected" if g else "off","ollama":"connected" if o else "off","active":type(self._active).__name__ if self._active else "none"}

def _load_resume_bullets(profile):
    bullets = profile.get("resume_bullets", {})
    if isinstance(bullets, str):
        try:
            bullets = json.loads(bullets)
        except:
            bullets = {}
    if isinstance(bullets, dict) and any(isinstance(v, list) and v for v in bullets.values()):
        return bullets
    return DEFAULT_RESUME_BULLETS


def _fmt_profile(p):
    bullets = _load_resume_bullets(p)
    secs = []
    for s, bl in bullets.items():
        if isinstance(bl, list):
            secs.append(f"[{s}]\n"+"\n".join(f"  {i+1}. {b}" for i,b in enumerate(bl)))
    return f"""{p.get('name','')} | {p.get('location','')}
Target: {p.get('target_roles','')}
Education: {p.get('education','')}
Skills: {', '.join(p.get('skills',[])) if isinstance(p.get('skills'), list) else p.get('skills','')}
Proof points: {', '.join(p.get('proof_points',[])) if isinstance(p.get('proof_points'), list) else p.get('proof_points','')}

RESUME BULLETS:
{chr(10).join(secs)}"""

class MatchScorer:
    def __init__(self, llm): self.llm = llm
    async def score_batch(self, profile, jobs):
        ptext = _fmt_profile(profile)
        jlist = "\n".join([f"{j['id']}. {j.get('title','')} @ {j.get('company','')} | Reqs: {', '.join(j.get('requirements',[])) if isinstance(j.get('requirements'),list) else j.get('requirements','')}" for j in jobs])
        r = await self.llm.generate(
            "You are a job-candidate match scorer. Score each job 0-100 for fit. Also classify archetype.",
            f"CANDIDATE:\n{ptext}\n\nJOBS:\n{jlist}\n\nFor each job return one line: JOB_ID|SCORE|ARCHETYPE\nExample: 42|85|Strategy & Ops\n\nScore ALL jobs.", 2000)
        scores = {}
        for line in r["text"].split("\n"):
            m = re.match(r'(\d+)\|(\d+)\|(.+)', line.strip())
            if m: scores[int(m.group(1))] = {"score":int(m.group(2)),"archetype":m.group(3).strip()}
        return scores, r.get("tokens",0)

class PlaybookGenerator:
    def __init__(self, llm): self.llm = llm
    async def generate(self, profile, jobs):
        ptext = _fmt_profile(profile)
        jlist = "\n".join([f"{i+1}. {j.get('title','')} @ {j.get('company','')} ({j.get('location','')})\n   Reqs: {', '.join(j.get('requirements',[])) if isinstance(j.get('requirements'),list) else j.get('requirements','')}" for i,j in enumerate(jobs)])
        r = await self.llm.generate(f"Elite career strategist. {CONTENT_OS}",
            f"CANDIDATE:\n{ptext}\n\n{len(jobs)} JOBS:\n{jlist}\n\nProduce MASTER REWRITE PLAYBOOK:\n1. ARCHETYPE MAP: Group into 4-6 archetypes, list job numbers\n2. PER-ARCHETYPE REWRITE TABLE: Key JD phrases + rewritten bullets for [digitech,asu,vaxom,nccl,vertiv,km_capital,scdi,gcn]. Keep all metrics. Reframe language only.\n3. UNIVERSAL RULES\n\nWrite every bullet in full.", 8000)
        return {"playbook_text":r["text"],"tokens":r.get("tokens",0),"job_count":len(jobs)}

class ResumeTailor:
    """Tailors one job at a time for more reliable structured output."""

    def __init__(self, llm):
        self.llm = llm

    async def tailor_one(self, profile, job, playbook_text=""):
        ptext = _fmt_profile(profile)
        reqs = job.get("requirements", [])
        if isinstance(reqs, list):
            reqs = ", ".join(reqs)

        pb_context = ""
        if playbook_text:
            pb_context = f"\nPLAYBOOK CONTEXT:\n{playbook_text[:3000]}\n"

        prompt = (
            f"CANDIDATE PROFILE:\n{ptext}\n"
            f"{pb_context}\n"
            f"TARGET JOB: {job.get('title', '')} at {job.get('company', '')}\n"
            f"Location: {job.get('location', '')}\n"
            f"Requirements: {reqs}\n\n"
            "Rewrite the candidate's resume bullets tailored to this specific job. "
            "Keep all metrics and facts identical. Reframe language to mirror the JD.\n\n"
            "You MUST use this EXACT output format:\n\n"
            "ARCHETYPE: [classify this job in 2-4 words]\n\n"
            "[digitech]\n"
            "1. [full rewritten bullet with metrics]\n"
            "2. [full rewritten bullet with metrics]\n\n"
            "[asu]\n"
            "1. [full rewritten bullet]\n"
            "2. [full rewritten bullet]\n"
            "3. [full rewritten bullet]\n\n"
            "[vaxom]\n"
            "1. [full rewritten bullet]\n"
            "2. [full rewritten bullet]\n\n"
            "[nccl]\n"
            "1. [full rewritten bullet]\n"
            "2. [full rewritten bullet]\n\n"
            "[vertiv]\n"
            "1. [full rewritten bullet]\n\n"
            "[km_capital]\n"
            "1. [full rewritten bullet]\n\n"
            "[scdi]\n"
            "1. [full rewritten bullet]\n"
            "2. [full rewritten bullet]\n\n"
            "[gcn]\n"
            "1. [full rewritten bullet]\n"
            "2. [full rewritten bullet]\n\n"
            f"COVER LETTER FOR {job.get('company', '').upper()}:\n"
            f"[Write a 4-paragraph cover letter specifically for {job.get('company', '')} "
            f"and the {job.get('title', '')} role. "
            "Opening: specific connection to THIS company. "
            "Body 1: signature achievement mapped to THEIR need. "
            "Body 2: their language and approach. "
            "Closing: what you bring and invitation to talk.]\n"
        )

        r = await self.llm.generate(f"Expert resume tailor. {CONTENT_OS}", prompt, 4000)
        return self._parse_response(r["text"], job)

    def _parse_response(self, text, job):
        bullets = {}
        cover_letter = ""
        archetype = "General"

        am = re.search(r"ARCHETYPE:\s*(.+?)(?:\n|$)", text, re.IGNORECASE)
        if am:
            archetype = am.group(1).strip().strip("[]")

        cl_patterns = [
            r"COVER\s+LETTER[^:]*:",
            r"COVER\s+LETTER\s+FOR\s+[^:]+:",
            r"---\s*COVER\s+LETTER",
        ]
        cl_split_pos = len(text)
        for pattern in cl_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match and match.start() < cl_split_pos:
                cl_split_pos = match.start()
                cover_letter = text[match.end():].strip()

        bullet_text = text[:cl_split_pos]
        sections = ["digitech", "asu", "vaxom", "nccl", "vertiv", "km_capital", "scdi", "gcn"]

        for i, sec in enumerate(sections):
            sec_pattern = rf"\[{sec}\]|#{{1,3}}\s*{sec}|\*\*{sec}\*\*|{sec}\s*:"
            match = re.search(sec_pattern, bullet_text, re.IGNORECASE)
            if not match:
                bullets[sec] = []
                continue

            start = match.end()
            end = len(bullet_text)
            for next_sec in sections[i + 1:]:
                next_pattern = rf"\[{next_sec}\]|#{{1,3}}\s*{next_sec}|\*\*{next_sec}\*\*|{next_sec}\s*:"
                next_match = re.search(next_pattern, bullet_text[start:], re.IGNORECASE)
                if next_match:
                    end = start + next_match.start()
                    break

            chunk = bullet_text[start:end]
            found = []
            for line in chunk.split("\n"):
                line = line.strip()
                bullet_match = re.match(r"^\d+[.)]\s+(.+)", line) or re.match(r"^[-*]\s+(.+)", line)
                if bullet_match:
                    bullet_text_value = bullet_match.group(1).strip()
                    if len(bullet_text_value) > 30:
                        found.append(bullet_text_value)
            bullets[sec] = found

        return {
            "job_id": job.get("id"),
            "title": job.get("title", ""),
            "company": job.get("company", ""),
            "archetype": archetype,
            "tailored_bullets": bullets,
            "cover_letter": cover_letter,
        }

    async def tailor_batch(self, profile, jobs, playbook_text=""):
        results = []
        for idx, job in enumerate(jobs):
            try:
                results.append(await self.tailor_one(profile, job, playbook_text))
            except Exception as e:
                logger.error(f"Tailor failed for {job.get('title', '')}: {e}")
                results.append({
                    "job_id": job.get("id"),
                    "title": job.get("title", ""),
                    "company": job.get("company", ""),
                    "archetype": "Unknown",
                    "tailored_bullets": {},
                    "cover_letter": "",
                })
            if idx < len(jobs) - 1:
                await asyncio.sleep(1.5)
        return results

class ConnectionFinder:
    def __init__(self, llm): self.llm = llm
    async def find(self, profile, job):
        reqs = job.get("requirements", [])
        if isinstance(reqs, list):
            reqs = ", ".join(reqs)

        r = await self.llm.generate(
            "You are a networking strategist. Be specific and direct.",
            f"CANDIDATE: {profile.get('name', '')} based in {profile.get('location', '')}\n"
            f"Target: {profile.get('target_roles', '')}\n"
            "Key achievement: Led business turnaround from $4M to $8.6M revenue in 10 months\n\n"
            f"JOB: {job.get('title', '')} at {job.get('company', '')} ({job.get('location', '')})\n"
            f"Requirements: {reqs}\n\n"
            "Provide exactly this format:\n\n"
            "TITLE: [Most likely hiring manager title, e.g. VP of Strategy]\n\n"
            "MESSAGE: [Write a 4-6 sentence personalized LinkedIn connection message. "
            "Be direct, warm, specific. Reference a concrete thing about the company. "
            "Include a small clear ask. No flattery or generic language.]\n\n"
            "SEARCH: [LinkedIn search query to find this person]",
            1500,
        )

        text = r.get("text", "")
        title_m = re.search(r"TITLE:\s*(.+?)(?:\n|$)", text)
        msg_m = re.search(r"MESSAGE:\s*([\s\S]+?)(?:SEARCH:|$)", text)
        message = msg_m.group(1).strip() if msg_m else ""
        message = re.sub(r"\n+\s*\d+\.\s*$", "", message).strip()
        if not message and len(text) > 100:
            lines = [line.strip() for line in text.split("\n") if len(line.strip()) > 30]
            message = "\n".join(lines[-3:]) if lines else text[:500]

        return {
            "contact_title": title_m.group(1).strip() if title_m else "Hiring Manager",
            "outreach_message": message,
            "raw": text, "tokens": r.get("tokens",0)
        }

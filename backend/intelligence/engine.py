"""Layer 2: Intelligence Engine — Groq/Ollama + Playbook + Tailor + Match + Connections"""
import json, re, logging, httpx, asyncio
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

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
            try:
                r = await c.post(self.URL, headers={"Authorization":f"Bearer {self.key}","Content-Type":"application/json"},
                    json={"model":self.model,"messages":[{"role":"system","content":system},{"role":"user","content":user}],"max_tokens":max_tokens,"temperature":0.3})
                d = r.json()
                if "error" in d: return {"text":"","tokens":0,"error":str(d["error"])}
                return {"text":d["choices"][0]["message"]["content"],"tokens":d.get("usage",{}).get("total_tokens",0)}
            except Exception as e: return {"text":"","tokens":0,"error":str(e)}
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

def _fmt_profile(p):
    bullets = p.get("resume_bullets",{})
    if isinstance(bullets,str):
        try: bullets = json.loads(bullets)
        except: bullets = {}
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
    def __init__(self, llm): self.llm = llm
    async def tailor_batch(self, playbook, jobs, batch_size=10):
        results = []
        for i in range(0, len(jobs), batch_size):
            results.extend(await self._batch(playbook, jobs[i:i+batch_size], i))
        return results
    async def _batch(self, playbook, jobs, si):
        jl = "\n\n".join([f"JOB {si+i+1} (id={j.get('id','?')}): {j.get('title','')} @ {j.get('company','')}\nReqs: {', '.join(j.get('requirements',[])) if isinstance(j.get('requirements'),list) else j.get('requirements','')}" for i,j in enumerate(jobs)])
        r = await self.llm.generate(f"Resume tailor. {CONTENT_OS}",
            f"PLAYBOOK:\n{playbook[:6000]}\n\nJOBS ({len(jobs)}):\n{jl}\n\nFor EACH job output:\n---JOB id=[ID]---\nArchetype: ...\n[digitech] 1. ... 2. ...\n[asu] 1. ... 2. ... 3. ...\n[vaxom] 1. ... 2. ...\n[nccl] 1. ... 2. ...\n[vertiv] 1. ...\n[km_capital] 1. ...\n[scdi] 1. ... 2. ...\n[gcn] 1. ... 2. ...\n\nCOVER LETTER:\n[4 paragraphs prose]\n\nOutput ALL {len(jobs)} jobs.", 8000)
        return self._parse(r["text"], jobs, si)
    def _parse(self, text, jobs, si):
        blocks = re.split(r'---JOB\s+(?:id=)?[\d?]+---', text)
        blocks = [b.strip() for b in blocks if b.strip()]
        results = []
        for i, job in enumerate(jobs):
            block = blocks[i] if i < len(blocks) else ""
            bullets, cur = {}, None
            cl_text = ""
            in_cl = False
            for line in block.split("\n"):
                l = line.strip()
                if "COVER LETTER" in l.upper(): in_cl = True; continue
                if in_cl:
                    if l.startswith("[") and not l.startswith("[digitech"): continue
                    cl_text += l + "\n"; continue
                sm = re.match(r'^\[(\w+)\]', l)
                if sm: cur = sm.group(1); bullets[cur] = []; in_cl = False
                elif cur and re.match(r'^\d+\.', l):
                    bt = re.sub(r'^\d+\.\s*', '', l).strip()
                    if bt: bullets[cur].append(bt)
            am = re.search(r'Archetype:\s*(.+)', block)
            results.append({"job_id":job.get("id"),"title":job.get("title",""),"company":job.get("company",""),
                "archetype":am.group(1).strip() if am else "Unknown",
                "tailored_bullets":bullets,"cover_letter":cl_text.strip()})
        return results

class ConnectionFinder:
    def __init__(self, llm): self.llm = llm
    async def find(self, profile, job):
        r = await self.llm.generate(
            "You are a networking strategist. Identify the likely decision maker for this role and craft a personalized outreach message.",
            f"CANDIDATE: {profile.get('name','')} | {profile.get('location','')}\nTarget: {profile.get('target_roles','')}\nKey achievement: Led business turnaround from $4M to $8.6M revenue in 10 months\n\nJOB: {job.get('title','')} at {job.get('company','')} ({job.get('location','')})\nRequirements: {json.dumps(job.get('requirements',[]))}\n\nProvide:\n1. DECISION_MAKER_TITLE: Most likely hiring manager title\n2. OUTREACH_MESSAGE: A 4-6 sentence personalized connection message. Direct, warm, specific. Small clear ask. No flattery.\n3. SEARCH_QUERY: LinkedIn search query to find this person", 1500)
        title_m = re.search(r'DECISION_MAKER_TITLE:\s*(.+)', r["text"])
        msg_m = re.search(r'OUTREACH_MESSAGE:\s*([\s\S]*?)(?:SEARCH_QUERY|$)', r["text"])
        return {
            "contact_title": title_m.group(1).strip() if title_m else "Hiring Manager",
            "outreach_message": msg_m.group(1).strip() if msg_m else "",
            "raw": r["text"], "tokens": r.get("tokens",0)
        }

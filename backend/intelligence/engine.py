"""
Layer 2: Intelligence Engine
Groq API for Llama3-70B (free, fast) with Ollama fallback (offline).
"""
import json, logging, re, httpx, asyncio
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class GroqClient:
    API_URL = "https://api.groq.com/openai/v1/chat/completions"
    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile", timeout: int = 120):
        self.api_key, self.model, self.timeout = api_key, model, timeout
    async def generate(self, system: str, user: str, max_tokens: int = 4000) -> Dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                r = await client.post(self.API_URL, headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    json={"model": self.model, "messages": [{"role":"system","content":system},{"role":"user","content":user}], "max_tokens": max_tokens, "temperature": 0.3})
                d = r.json()
                if "error" in d: return {"text":"","tokens":0,"model":self.model,"error":d["error"]}
                return {"text": d["choices"][0]["message"]["content"], "tokens": d.get("usage",{}).get("total_tokens",0), "model": self.model}
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    await asyncio.sleep(2); return await self.generate(system, user, max_tokens)
                return {"text":"","tokens":0,"model":self.model,"error":str(e)}
            except Exception as e: return {"text":"","tokens":0,"model":self.model,"error":str(e)}
    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5) as c:
                return (await c.get("https://api.groq.com/openai/v1/models", headers={"Authorization": f"Bearer {self.api_key}"})).status_code == 200
        except: return False

class OllamaClient:
    def __init__(self, host: str = "http://localhost:11434", model: str = "llama3.1:8b", timeout: int = 120):
        self.host, self.model, self.timeout = host, model, timeout
    async def generate(self, system: str, user: str, max_tokens: int = 4000) -> Dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                r = await client.post(f"{self.host}/api/chat", json={"model":self.model,"messages":[{"role":"system","content":system},{"role":"user","content":user}],"stream":False,"options":{"num_predict":max_tokens,"temperature":0.3}})
                d = r.json(); return {"text": d.get("message",{}).get("content",""), "tokens": d.get("eval_count",0), "model": self.model}
            except Exception as e: return {"text":"","tokens":0,"model":self.model,"error":str(e)}
    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5) as c: return (await c.get(f"{self.host}/api/tags")).status_code == 200
        except: return False

class LLMClient:
    def __init__(self, groq_key: str = None, ollama_host: str = "http://localhost:11434"):
        self.groq = GroqClient(groq_key) if groq_key else None
        self.ollama = OllamaClient(ollama_host)
        self._active = None
    async def init(self):
        if self.groq and await self.groq.health_check(): self._active = self.groq; logger.info(f"LLM: Groq ({self.groq.model})")
        elif await self.ollama.health_check(): self._active = self.ollama; logger.info(f"LLM: Ollama ({self.ollama.model})")
        else: logger.error("No LLM backend available!"); self._active = None
    async def generate(self, system: str, user: str, max_tokens: int = 4000) -> Dict:
        if not self._active: await self.init()
        if not self._active: return {"text":"","tokens":0,"error":"No LLM backend"}
        return await self._active.generate(system, user, max_tokens)
    async def health_check(self) -> Dict:
        return {"groq": "connected" if self.groq and await self.groq.health_check() else "off", "ollama": "connected" if await self.ollama.health_check() else "off", "active": self._active.__class__.__name__ if self._active else "none"}

CONTENT_OS = """RESUME WRITING SYSTEM:
BULLET: Action verb + Problem context + Method + Quantified result. Mirror 2-3 JD phrases.
VOICE: Warm, crisp, analytical. Specific over generic. Confident.
NEVER: Em dashes, "delve/tapestry/testament/pivotal/passionate/cutting-edge", -ing endings, rule-of-three.
COVER LETTER (prose, no bullets): Opening (specific moment) → Body 1 (signature experience) → Body 2 (firm's language) → Closing (what you bring)."""

class PlaybookGenerator:
    def __init__(self, llm: LLMClient): self.llm = llm
    async def generate(self, profile: Dict, jobs: List[Dict]) -> Dict:
        profile_text = self._fmt(profile)
        job_list = "\n".join([f"{i+1}. {j.get('title','')} @ {j.get('company','')} ({j.get('location','')})\n   Reqs: {', '.join(j.get('requirements',[])) if isinstance(j.get('requirements'),list) else j.get('requirements','')}" for i,j in enumerate(jobs)])
        r = await self.llm.generate(f"Elite career strategist. {CONTENT_OS}",
            f"CANDIDATE:\n{profile_text}\n\n{len(jobs)} JOBS:\n{job_list}\n\nProduce MASTER REWRITE PLAYBOOK:\n1. ARCHETYPE MAP: Group into 4-6 archetypes, list job numbers.\n2. PER-ARCHETYPE REWRITE TABLE: Key phrases + rewritten bullets per section [digitech,asu,vaxom,nccl,vertiv,km_capital,scdi,gcn]. Keep metrics, reframe language.\n3. UNIVERSAL RULES.\nWrite every bullet for every section for every archetype in full.", 8000)
        return {"playbook_text": r["text"], "tokens_used": r.get("tokens",0), "model": r.get("model",""), "job_count": len(jobs)}
    def _fmt(self, p: Dict) -> str:
        bullets = p.get("resume_bullets",{})
        if isinstance(bullets,str):
            try: bullets = json.loads(bullets)
            except: bullets = {}
        secs = [f"[{s}]\n" + "\n".join(f"  {i+1}. {b}" for i,b in enumerate(bl)) for s,bl in bullets.items() if isinstance(bl,list)]
        return f"{p.get('name','')} | {p.get('location','')}\nTarget: {p.get('target_roles','')}\n\n{chr(10).join(secs)}"

class ResumeTailor:
    def __init__(self, llm: LLMClient): self.llm = llm
    async def tailor_batch(self, playbook: str, jobs: List[Dict], batch_size: int = 10) -> List[Dict]:
        results = []
        for i in range(0, len(jobs), batch_size):
            results.extend(await self._batch(playbook, jobs[i:i+batch_size], i))
        return results
    async def _batch(self, playbook: str, jobs: List[Dict], si: int) -> List[Dict]:
        jl = "\n\n".join([f"JOB {si+i+1}: {j.get('title','')} @ {j.get('company','')}\nReqs: {', '.join(j.get('requirements',[])) if isinstance(j.get('requirements'),list) else j.get('requirements','')}" for i,j in enumerate(jobs)])
        r = await self.llm.generate(f"Resume tailor. Match jobs to playbook archetypes. {CONTENT_OS}",
            f"PLAYBOOK:\n{playbook[:6000]}\n\nJOBS ({len(jobs)}):\n{jl}\n\nFor EACH job:\n---JOB [N]---\nTitle/Company/Archetype\n[digitech] 1. 2.\n[asu] 1. 2. 3.\n[vaxom] 1. 2.\n[nccl] 1. 2.\n[vertiv] 1.\n[km_capital] 1.\n[scdi] 1. 2.\n[gcn] 1. 2.\n\nOutput ALL {len(jobs)} jobs.", 8000)
        return self._parse(r["text"], jobs, si)
    def _parse(self, text: str, jobs: List[Dict], si: int) -> List[Dict]:
        blocks = [b.strip() for b in re.split(r'---JOB\s+\d+---', text) if b.strip()]
        results = []
        for i, job in enumerate(jobs):
            block = blocks[i] if i < len(blocks) else ""
            bullets, cur = {}, None
            for line in block.split("\n"):
                line = line.strip()
                sm = re.match(r'^\[(\w+)\]', line)
                if sm: cur = sm.group(1); bullets[cur] = []
                elif cur and re.match(r'^\d+\.', line):
                    bt = re.sub(r'^\d+\.\s*', '', line).strip()
                    if bt: bullets[cur].append(bt)
            am = re.search(r'Archetype:\s*(.+)', block)
            results.append({"job_index":si+i,"job_id":job.get("id"),"title":job.get("title",""),"company":job.get("company",""),"archetype":am.group(1).strip() if am else "Unknown","tailored_bullets":bullets,"raw_output":block})
        return results

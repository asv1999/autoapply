"""A-F Job Evaluation Engine — Career-Ops style deep evaluation for each job."""
import json, re, logging, asyncio
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# 6 archetypes from career-ops
ARCHETYPES = {
    "AI Platform / LLMOps": ["observability", "evals", "pipelines", "monitoring", "reliability", "mlops", "ml platform"],
    "Agentic / Automation": ["agent", "hitl", "orchestration", "workflow", "multi-agent", "automation", "rpa"],
    "Technical AI PM": ["prd", "roadmap", "discovery", "stakeholder", "product manager", "product management"],
    "AI Solutions Architect": ["architecture", "enterprise", "integration", "design", "systems", "solutions architect"],
    "AI Forward Deployed": ["client-facing", "deploy", "prototype", "fast delivery", "field engineer", "implementation"],
    "AI Transformation": ["change management", "adoption", "enablement", "transformation", "digital transformation"],
}

# 10-dimension scoring system
SCORING_DIMENSIONS = [
    "cv_match",           # Skills, experience, proof points alignment
    "north_star",         # Fit with target archetypes
    "compensation",       # Salary vs market
    "cultural_signals",   # Company culture, growth, remote policy
    "red_flags",          # Blockers, warnings
    "seniority_fit",      # Level alignment
    "growth_potential",   # Career trajectory value
    "location_fit",       # Remote/hybrid/onsite match
    "industry_relevance", # Domain alignment
    "urgency",            # Time sensitivity, demand signals
]

EVAL_SYSTEM_PROMPT = """You are an elite career strategist performing deep A-F job evaluations.

SCORING: Rate each dimension 1-5. Global score = weighted average.
- 4.5+ = Strong match, apply immediately
- 4.0-4.4 = Good match, worth applying
- 3.5-3.9 = Decent but not ideal
- Below 3.5 = Recommend against

ARCHETYPE DETECTION: Classify into one of these (or hybrid of 2):
- AI Platform / LLMOps
- Agentic / Automation
- Technical AI PM
- AI Solutions Architect
- AI Forward Deployed
- AI Transformation
- Strategy & Operations
- Business Transformation
- Management Consulting
- Data Analytics

WRITING RULES:
- Be direct and actionable, no fluff
- Native tech English, short sentences, action verbs
- Cite exact proof points from the candidate profile
- Name specific tools, projects, metrics
- Never invent experience or metrics"""


def detect_archetype(job: Dict) -> str:
    """Quick archetype detection from job title and requirements."""
    text = f"{job.get('title', '')} {job.get('company', '')} {' '.join(job.get('requirements', []) if isinstance(job.get('requirements'), list) else [str(job.get('requirements', ''))])}".lower()

    scores = {}
    for arch, signals in ARCHETYPES.items():
        score = sum(1 for s in signals if s in text)
        if score > 0:
            scores[arch] = score

    if scores:
        top = sorted(scores.items(), key=lambda x: -x[1])
        if len(top) >= 2 and top[1][1] >= top[0][1] * 0.7:
            return f"{top[0][0]} / {top[1][0]}"
        return top[0][0]

    # Fallback heuristics
    title_lower = job.get("title", "").lower()
    if any(w in title_lower for w in ["strategy", "operations", "ops"]):
        return "Strategy & Operations"
    if any(w in title_lower for w in ["consulting", "consultant"]):
        return "Management Consulting"
    if any(w in title_lower for w in ["transformation", "change"]):
        return "Business Transformation"
    if any(w in title_lower for w in ["data", "analytics", "analyst"]):
        return "Data Analytics"
    if any(w in title_lower for w in ["product", "pm"]):
        return "Technical AI PM"

    return "General"


def extract_keywords(text: str, n: int = 15) -> List[str]:
    """Extract top keywords from JD text for ATS optimization."""
    # Remove common words
    stop = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of",
            "with", "by", "from", "is", "are", "was", "were", "be", "been", "being",
            "have", "has", "had", "do", "does", "did", "will", "would", "could", "should",
            "may", "might", "can", "shall", "this", "that", "these", "those", "we", "you",
            "they", "it", "as", "if", "not", "no", "so", "up", "out", "about", "into",
            "our", "your", "their", "its", "all", "each", "every", "both", "few", "more",
            "most", "other", "some", "such", "than", "too", "very", "just", "also", "well"}

    words = re.findall(r'\b[a-zA-Z][a-zA-Z+#.-]{2,}\b', text.lower())
    freq = {}
    for w in words:
        if w not in stop:
            freq[w] = freq.get(w, 0) + 1

    # Also extract multi-word phrases (bigrams)
    for i in range(len(words) - 1):
        if words[i] not in stop and words[i+1] not in stop:
            phrase = f"{words[i]} {words[i+1]}"
            freq[phrase] = freq.get(phrase, 0) + 1

    sorted_kw = sorted(freq.items(), key=lambda x: -x[1])
    return [kw for kw, _ in sorted_kw[:n]]


class JobEvaluator:
    """Full A-F evaluation engine inspired by career-ops oferta mode."""

    def __init__(self, llm):
        self.llm = llm

    async def evaluate(self, profile: Dict, job: Dict, jd_text: str = "") -> Dict:
        """Run full A-F evaluation on a single job."""
        from intelligence.engine import _fmt_profile

        ptext = _fmt_profile(profile)
        archetype = detect_archetype(job)

        reqs = job.get("requirements", [])
        if isinstance(reqs, list):
            reqs_text = ", ".join(reqs)
        else:
            reqs_text = str(reqs)

        jd_context = jd_text if jd_text else reqs_text

        # Extract keywords for later PDF generation
        keywords = extract_keywords(jd_context)

        prompt = self._build_eval_prompt(ptext, job, archetype, jd_context, keywords)

        r = await self.llm.generate(EVAL_SYSTEM_PROMPT, prompt, 6000)
        text = r.get("text", "")

        parsed = self._parse_evaluation(text, job, archetype, keywords)
        parsed["tokens"] = r.get("tokens", 0)
        return parsed

    def _build_eval_prompt(self, ptext: str, job: Dict, archetype: str, jd_context: str, keywords: List[str]) -> str:
        return f"""CANDIDATE PROFILE:
{ptext}

JOB TO EVALUATE:
Title: {job.get('title', '')}
Company: {job.get('company', '')}
Location: {job.get('location', '')}
Detected Archetype: {archetype}
Requirements/JD: {jd_context}

Top Keywords: {', '.join(keywords[:10])}

Produce a COMPLETE A-F evaluation in this EXACT format:

ARCHETYPE: {archetype}

SCORES:
cv_match: [1-5]
north_star: [1-5]
compensation: [1-5]
cultural_signals: [1-5]
red_flags: [1-5]
seniority_fit: [1-5]
growth_potential: [1-5]
location_fit: [1-5]
industry_relevance: [1-5]
urgency: [1-5]
GLOBAL: [1-5, weighted average]

=== BLOCK A: ROLE SUMMARY ===
Archetype: [detected]
Domain: [platform/agentic/LLMOps/ML/enterprise/consulting/analytics]
Function: [build/consult/manage/deploy/analyze]
Seniority: [junior/mid/senior/lead/director]
Remote: [full/hybrid/onsite]
TL;DR: [1 sentence summary]

=== BLOCK B: CV MATCH ===
For each key JD requirement, map to a specific line from the candidate's CV.
Format each as: REQUIREMENT -> CV MATCH (exact proof point)

GAPS:
For each gap, classify as hard-blocker or nice-to-have, and provide mitigation strategy.

=== BLOCK C: LEVEL STRATEGY ===
1. Detected level in JD vs candidate's natural level
2. "Sell senior without lying" plan: specific phrases, achievements to highlight
3. "If downleveled" plan: fair comp conditions, 6-month review criteria

=== BLOCK D: COMP AND DEMAND ===
Estimated salary range for this role and market.
Company reputation for compensation.
Demand trend for this role type.
(Base this on your knowledge of market rates)

=== BLOCK E: PERSONALIZATION PLAN ===
Top 5 CV changes (specific rewrites):
1. Section: [section] | Current: [current text] | Change to: [new text] | Why: [reason]
2. ...

Top 5 LinkedIn changes:
1. [specific change]
2. ...

=== BLOCK F: INTERVIEW PREP ===
6-8 STAR+Reflection stories mapped to JD requirements:
| # | JD Requirement | Story Title | S | T | A | R | Reflection |

Recommended case study to present and how to frame it.
Red-flag questions and how to handle them.
"""

    def _parse_evaluation(self, text: str, job: Dict, default_archetype: str, keywords: List[str]) -> Dict:
        result = {
            "job_id": job.get("id"),
            "title": job.get("title", ""),
            "company": job.get("company", ""),
            "archetype": default_archetype,
            "global_score": 0.0,
            "scores": {},
            "blocks": {},
            "keywords": keywords,
            "raw_evaluation": text,
        }

        # Parse archetype
        am = re.search(r"ARCHETYPE:\s*(.+?)(?:\n|$)", text, re.IGNORECASE)
        if am:
            result["archetype"] = am.group(1).strip()

        # Parse scores
        score_section = re.search(r"SCORES:(.*?)(?:===|BLOCK\s*A)", text, re.DOTALL | re.IGNORECASE)
        if score_section:
            for dim in SCORING_DIMENSIONS:
                m = re.search(rf"{dim}:\s*([\d.]+)", score_section.group(1), re.IGNORECASE)
                if m:
                    try:
                        result["scores"][dim] = float(m.group(1))
                    except ValueError:
                        pass

        # Parse global score
        gm = re.search(r"GLOBAL:\s*([\d.]+)", text, re.IGNORECASE)
        if gm:
            try:
                result["global_score"] = float(gm.group(1))
            except ValueError:
                pass

        # If no global score parsed, compute from dimensions
        if result["global_score"] == 0 and result["scores"]:
            vals = list(result["scores"].values())
            result["global_score"] = round(sum(vals) / len(vals), 1)

        # Parse blocks A-F
        block_patterns = [
            ("A", r"===\s*BLOCK\s*A[^=]*===\s*(.*?)(?:===\s*BLOCK\s*B|$)"),
            ("B", r"===\s*BLOCK\s*B[^=]*===\s*(.*?)(?:===\s*BLOCK\s*C|$)"),
            ("C", r"===\s*BLOCK\s*C[^=]*===\s*(.*?)(?:===\s*BLOCK\s*D|$)"),
            ("D", r"===\s*BLOCK\s*D[^=]*===\s*(.*?)(?:===\s*BLOCK\s*E|$)"),
            ("E", r"===\s*BLOCK\s*E[^=]*===\s*(.*?)(?:===\s*BLOCK\s*F|$)"),
            ("F", r"===\s*BLOCK\s*F[^=]*===\s*(.*)"),
        ]
        for block_id, pattern in block_patterns:
            m = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if m:
                result["blocks"][block_id] = m.group(1).strip()

        return result

    async def evaluate_batch(self, profile: Dict, jobs: List[Dict], jd_texts: Dict[int, str] = None) -> List[Dict]:
        """Evaluate multiple jobs sequentially (respecting rate limits)."""
        jd_texts = jd_texts or {}
        results = []
        for idx, job in enumerate(jobs):
            try:
                jd = jd_texts.get(job.get("id", 0), "")
                result = await self.evaluate(profile, job, jd)
                results.append(result)
                logger.info(f"Evaluated {idx+1}/{len(jobs)}: {job.get('title', '')} @ {job.get('company', '')} -> {result['global_score']}")
            except Exception as e:
                logger.error(f"Evaluation failed for {job.get('title', '')}: {e}")
                results.append({
                    "job_id": job.get("id"),
                    "title": job.get("title", ""),
                    "company": job.get("company", ""),
                    "archetype": "Unknown",
                    "global_score": 0.0,
                    "scores": {},
                    "blocks": {},
                    "keywords": [],
                    "raw_evaluation": f"Error: {e}",
                })
            if idx < len(jobs) - 1:
                await asyncio.sleep(2)
        return results

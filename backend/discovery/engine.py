"""
Layer 1: Discovery Engine
Scrapes job boards, deduplicates, and queues new jobs.
"""
import re
import time
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# ─── BASE SCRAPER ───

class BaseScraper(ABC):
    """Base class for all job board scrapers."""
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser = None
        self.page = None
    
    async def init_browser(self):
        from playwright.async_api import async_playwright
        self.pw = await async_playwright().start()
        self.browser = await self.pw.chromium.launch(headless=self.headless)
        self.page = await self.browser.new_page()
        await self.page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        })
    
    async def close(self):
        if self.browser:
            await self.browser.close()
        if self.pw:
            await self.pw.stop()
    
    @abstractmethod
    async def search(self, query: str, location: str, max_results: int = 10) -> List[Dict]:
        """Search for jobs. Returns list of job dicts."""
        pass
    
    def clean_text(self, text: str) -> str:
        if not text:
            return ""
        return re.sub(r'\s+', ' ', text).strip()


# ─── INDEED SCRAPER ───

class IndeedScraper(BaseScraper):
    """Scrapes Indeed job listings."""
    
    BASE_URL = "https://www.indeed.com"
    
    async def search(self, query: str, location: str = "", max_results: int = 10) -> List[Dict]:
        if not self.browser:
            await self.init_browser()
        
        jobs = []
        encoded_q = query.replace(" ", "+")
        encoded_l = location.replace(" ", "+")
        url = f"{self.BASE_URL}/jobs?q={encoded_q}&l={encoded_l}&sort=date&fromage=3"
        
        try:
            await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await self.page.wait_for_timeout(2000)
            
            # Extract job cards
            cards = await self.page.query_selector_all('div.job_seen_beacon, div.jobsearch-ResultsList > div')
            
            for card in cards[:max_results]:
                try:
                    title_el = await card.query_selector('h2.jobTitle a, h2 a')
                    company_el = await card.query_selector('[data-testid="company-name"], .companyName')
                    location_el = await card.query_selector('[data-testid="text-location"], .companyLocation')
                    
                    title = await title_el.inner_text() if title_el else ""
                    company = await company_el.inner_text() if company_el else ""
                    loc = await location_el.inner_text() if location_el else ""
                    
                    href = await title_el.get_attribute("href") if title_el else ""
                    job_url = f"{self.BASE_URL}{href}" if href and not href.startswith("http") else href
                    
                    if title and company:
                        jobs.append({
                            "title": self.clean_text(title),
                            "company": self.clean_text(company),
                            "location": self.clean_text(loc),
                            "url": job_url,
                            "source": "indeed",
                            "requirements": [],
                            "decision_maker": "",
                            "discovered_at": datetime.now().isoformat(),
                        })
                except Exception as e:
                    logger.warning(f"Error parsing Indeed card: {e}")
                    continue
            
            # Extract requirements from job descriptions (click into first few)
            for i, job in enumerate(jobs[:5]):
                try:
                    if job["url"]:
                        await self.page.goto(job["url"], wait_until="domcontentloaded", timeout=15000)
                        await self.page.wait_for_timeout(1000)
                        desc_el = await self.page.query_selector('#jobDescriptionText, .jobsearch-jobDescriptionText')
                        if desc_el:
                            desc = await desc_el.inner_text()
                            jobs[i]["requirements"] = self._extract_requirements(desc)
                except Exception:
                    continue
            
        except Exception as e:
            logger.error(f"Indeed search error: {e}")
        
        return jobs
    
    def _extract_requirements(self, description: str) -> List[str]:
        """Extract key requirements from job description text."""
        reqs = []
        lines = description.split("\n")
        capture = False
        for line in lines:
            line = line.strip()
            if any(kw in line.lower() for kw in ["requirement", "qualification", "what you", "you will", "responsibilities"]):
                capture = True
                continue
            if capture and line.startswith(("•", "-", "·", "●", "○")):
                clean = re.sub(r'^[•\-·●○]\s*', '', line).strip()
                if len(clean) > 10 and len(clean) < 200:
                    reqs.append(clean)
            if capture and len(reqs) >= 5:
                break
        return reqs[:5]


# ─── LINKEDIN SCRAPER ───

class LinkedInScraper(BaseScraper):
    """Scrapes LinkedIn public job listings (no login required)."""
    
    BASE_URL = "https://www.linkedin.com/jobs/search"
    
    async def search(self, query: str, location: str = "", max_results: int = 10) -> List[Dict]:
        if not self.browser:
            await self.init_browser()
        
        jobs = []
        params = f"?keywords={query.replace(' ', '%20')}&location={location.replace(' ', '%20')}&sortBy=DD&f_TPR=r86400"
        url = f"{self.BASE_URL}{params}"
        
        try:
            await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await self.page.wait_for_timeout(3000)
            
            # Scroll to load more results
            for _ in range(3):
                await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await self.page.wait_for_timeout(1000)
            
            cards = await self.page.query_selector_all('.base-card, .job-search-card')
            
            for card in cards[:max_results]:
                try:
                    title_el = await card.query_selector('.base-search-card__title, h3')
                    company_el = await card.query_selector('.base-search-card__subtitle, h4')
                    location_el = await card.query_selector('.job-search-card__location')
                    link_el = await card.query_selector('a.base-card__full-link, a')
                    
                    title = await title_el.inner_text() if title_el else ""
                    company = await company_el.inner_text() if company_el else ""
                    loc = await location_el.inner_text() if location_el else ""
                    href = await link_el.get_attribute("href") if link_el else ""
                    
                    if title and company:
                        jobs.append({
                            "title": self.clean_text(title),
                            "company": self.clean_text(company),
                            "location": self.clean_text(loc),
                            "url": href,
                            "source": "linkedin",
                            "requirements": [],
                            "decision_maker": "",
                        })
                except Exception as e:
                    logger.warning(f"Error parsing LinkedIn card: {e}")
            
        except Exception as e:
            logger.error(f"LinkedIn search error: {e}")
        
        return jobs


# ─── GLASSDOOR SCRAPER ───

class GlassdoorScraper(BaseScraper):
    """Scrapes Glassdoor job listings."""
    
    async def search(self, query: str, location: str = "", max_results: int = 10) -> List[Dict]:
        if not self.browser:
            await self.init_browser()
        
        jobs = []
        url = f"https://www.glassdoor.com/Job/jobs.htm?sc.keyword={query.replace(' ', '+')}&locT=N&locId=1&fromAge=3"
        
        try:
            await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await self.page.wait_for_timeout(2000)
            
            cards = await self.page.query_selector_all('li.JobsList_jobListItem__wjTHv, [data-test="jobListing"]')
            
            for card in cards[:max_results]:
                try:
                    title_el = await card.query_selector('a.JobCard_jobTitle__GLyJ1, a[data-test="job-title"]')
                    company_el = await card.query_selector('.EmployerProfile_compactEmployerName__LE242, [data-test="emp-name"]')
                    location_el = await card.query_selector('.JobCard_location__N_iYE, [data-test="emp-location"]')
                    
                    title = await title_el.inner_text() if title_el else ""
                    company = await company_el.inner_text() if company_el else ""
                    loc = await location_el.inner_text() if location_el else ""
                    href = await title_el.get_attribute("href") if title_el else ""
                    
                    if title and company:
                        job_url = f"https://www.glassdoor.com{href}" if href and not href.startswith("http") else href
                        jobs.append({
                            "title": self.clean_text(title),
                            "company": self.clean_text(company),
                            "location": self.clean_text(loc),
                            "url": job_url,
                            "source": "glassdoor",
                            "requirements": [],
                            "decision_maker": "",
                        })
                except Exception:
                    continue
        except Exception as e:
            logger.error(f"Glassdoor search error: {e}")
        
        return jobs


# ─── DEDUPLICATION ENGINE ───

class DeduplicationEngine:
    """Deduplicates jobs against the full application history."""
    
    @staticmethod
    def dedup_key(title: str, company: str) -> str:
        title_clean = re.sub(r'[^a-z0-9\s]', '', title.lower()).strip()[:50]
        company_clean = re.sub(r'[^a-z0-9\s]', '', company.lower()).strip()[:30]
        return f"{title_clean}::{company_clean}"
    
    @staticmethod
    def is_duplicate(title: str, company: str) -> bool:
        from database import JobDB
        return JobDB.exists(title, company)
    
    @staticmethod
    def filter_new(jobs: List[Dict]) -> tuple:
        """Returns (new_jobs, duplicate_count)."""
        from database import JobDB
        new = []
        dupes = 0
        seen_keys = set()
        
        for job in jobs:
            key = DeduplicationEngine.dedup_key(
                job.get("title", ""), job.get("company", "")
            )
            # Check both in-batch and historical duplicates
            if key in seen_keys or JobDB.exists(job.get("title",""), job.get("company","")):
                dupes += 1
            else:
                seen_keys.add(key)
                new.append(job)
        
        return new, dupes


# ─── DISCOVERY ORCHESTRATOR ───

class DiscoveryEngine:
    """Orchestrates job discovery across all scrapers."""
    
    def __init__(self, config):
        self.config = config
        self.scrapers = {
            "indeed": IndeedScraper(headless=config.HEADLESS_BROWSER),
            "linkedin": LinkedInScraper(headless=config.HEADLESS_BROWSER),
            "glassdoor": GlassdoorScraper(headless=config.HEADLESS_BROWSER),
        }
        self.dedup = DeduplicationEngine()
    
    async def run_cycle(self, query: str, location: str, cycle_id: str) -> Dict:
        """Run one discovery cycle across all scrapers."""
        all_jobs = []
        
        for name, scraper in self.scrapers.items():
            try:
                logger.info(f"Searching {name}: '{query}' in '{location}'")
                jobs = await scraper.search(
                    query, location, 
                    max_results=self.config.MAX_JOBS_PER_CYCLE
                )
                for j in jobs:
                    j["cycle_id"] = cycle_id
                all_jobs.extend(jobs)
                logger.info(f"  {name}: found {len(jobs)} jobs")
            except Exception as e:
                logger.error(f"  {name}: error - {e}")
        
        # Dedup
        new_jobs, dupe_count = self.dedup.filter_new(all_jobs)
        
        # Insert into database
        from database import JobDB
        result = JobDB.insert_batch(new_jobs)
        
        return {
            "total_found": len(all_jobs),
            "duplicates_removed": dupe_count,
            "new_jobs_added": result["inserted"],
            "db_duplicates": result["duplicates"],
        }
    
    async def run_full(self, run_id: str) -> Dict:
        """Run all configured search cycles."""
        total_stats = {"cycles": 0, "total_found": 0, "new_added": 0, "duplicates": 0}
        
        for qi, query in enumerate(self.config.search_query_list):
            for li, location in enumerate(self.config.location_list):
                cycle_id = f"{run_id}_c{qi}_{li}"
                stats = await self.run_cycle(query, location, cycle_id)
                total_stats["cycles"] += 1
                total_stats["total_found"] += stats["total_found"]
                total_stats["new_added"] += stats["new_jobs_added"]
                total_stats["duplicates"] += stats["duplicates_removed"]
                
                if total_stats["cycles"] >= self.config.CYCLES_PER_RUN:
                    break
            if total_stats["cycles"] >= self.config.CYCLES_PER_RUN:
                break
        
        return total_stats
    
    async def cleanup(self):
        for scraper in self.scrapers.values():
            await scraper.close()

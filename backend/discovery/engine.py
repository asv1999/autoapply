"""Layer 1: Discovery Engine — Scraping + Dedup"""
import re, logging
from abc import ABC, abstractmethod
from typing import List, Dict
from datetime import datetime

logger = logging.getLogger(__name__)

class BaseScraper(ABC):
    def __init__(self, headless=True): self.headless = headless; self.browser = None; self.page = None; self.pw = None
    async def init_browser(self):
        from playwright.async_api import async_playwright
        self.pw = await async_playwright().start()
        self.browser = await self.pw.chromium.launch(headless=self.headless)
        self.page = await self.browser.new_page()
        await self.page.set_extra_http_headers({"User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"})
    async def close(self):
        if self.browser: await self.browser.close()
        if self.pw: await self.pw.stop()
    @abstractmethod
    async def search(self, query, location, max_results=10) -> List[Dict]: pass
    def clean(self, t): return re.sub(r'\s+', ' ', t).strip() if t else ""

class IndeedScraper(BaseScraper):
    async def search(self, query, location="", max_results=10):
        if not self.browser: await self.init_browser()
        jobs = []
        url = f"https://www.indeed.com/jobs?q={query.replace(' ','+')}&l={location.replace(' ','+')}&sort=date&fromage=3"
        try:
            await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await self.page.wait_for_timeout(2000)
            cards = await self.page.query_selector_all('div.job_seen_beacon, div.jobsearch-ResultsList > div')
            for card in cards[:max_results]:
                try:
                    te = await card.query_selector('h2.jobTitle a, h2 a')
                    ce = await card.query_selector('[data-testid="company-name"], .companyName')
                    le = await card.query_selector('[data-testid="text-location"], .companyLocation')
                    title = await te.inner_text() if te else ""
                    company = await ce.inner_text() if ce else ""
                    loc = await le.inner_text() if le else ""
                    href = await te.get_attribute("href") if te else ""
                    if title and company:
                        jobs.append({"title":self.clean(title),"company":self.clean(company),"location":self.clean(loc),
                            "url":f"https://www.indeed.com{href}" if href and not href.startswith("http") else href,
                            "source":"indeed","requirements":[],"decision_maker":""})
                except: continue
        except Exception as e: logger.error(f"Indeed: {e}")
        return jobs

class LinkedInScraper(BaseScraper):
    async def search(self, query, location="", max_results=10):
        if not self.browser: await self.init_browser()
        jobs = []
        url = f"https://www.linkedin.com/jobs/search?keywords={query.replace(' ','%20')}&location={location.replace(' ','%20')}&sortBy=DD&f_TPR=r86400"
        try:
            await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await self.page.wait_for_timeout(3000)
            for _ in range(3):
                await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await self.page.wait_for_timeout(1000)
            cards = await self.page.query_selector_all('.base-card, .job-search-card')
            for card in cards[:max_results]:
                try:
                    te = await card.query_selector('.base-search-card__title, h3')
                    ce = await card.query_selector('.base-search-card__subtitle, h4')
                    le = await card.query_selector('.job-search-card__location')
                    ae = await card.query_selector('a.base-card__full-link, a')
                    title = await te.inner_text() if te else ""
                    company = await ce.inner_text() if ce else ""
                    loc = await le.inner_text() if le else ""
                    href = await ae.get_attribute("href") if ae else ""
                    if title and company:
                        jobs.append({"title":self.clean(title),"company":self.clean(company),"location":self.clean(loc),
                            "url":href,"source":"linkedin","requirements":[],"decision_maker":""})
                except: continue
        except Exception as e: logger.error(f"LinkedIn: {e}")
        return jobs

class GlassdoorScraper(BaseScraper):
    async def search(self, query, location="", max_results=10):
        if not self.browser: await self.init_browser()
        jobs = []
        url = f"https://www.glassdoor.com/Job/jobs.htm?sc.keyword={query.replace(' ','+')}&locT=N&locId=1&fromAge=3"
        try:
            await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await self.page.wait_for_timeout(2000)
            cards = await self.page.query_selector_all('[data-test="jobListing"], li[data-test]')
            for card in cards[:max_results]:
                try:
                    te = await card.query_selector('a[data-test="job-title"], a.JobCard_jobTitle')
                    ce = await card.query_selector('[data-test="emp-name"], .EmployerProfile_compactEmployerName')
                    le = await card.query_selector('[data-test="emp-location"], .JobCard_location')
                    title = await te.inner_text() if te else ""
                    company = await ce.inner_text() if ce else ""
                    loc = await le.inner_text() if le else ""
                    href = await te.get_attribute("href") if te else ""
                    if title and company:
                        jobs.append({"title":self.clean(title),"company":self.clean(company),"location":self.clean(loc),
                            "url":f"https://www.glassdoor.com{href}" if href and not href.startswith("http") else href,
                            "source":"glassdoor","requirements":[],"decision_maker":""})
                except: continue
        except Exception as e: logger.error(f"Glassdoor: {e}")
        return jobs

class DeduplicationEngine:
    @staticmethod
    def filter_new(jobs):
        from database import JobDB
        new, dupes, seen = [], 0, set()
        for j in jobs:
            key = JobDB.dedup_key(j.get("title",""), j.get("company",""))
            if key in seen or JobDB.exists(j.get("title",""), j.get("company","")): dupes += 1
            else: seen.add(key); new.append(j)
        return new, dupes

class DiscoveryEngine:
    def __init__(self, config):
        self.config = config
        self.scrapers = {"indeed": IndeedScraper(config.HEADLESS_BROWSER),
            "linkedin": LinkedInScraper(config.HEADLESS_BROWSER),
            "glassdoor": GlassdoorScraper(config.HEADLESS_BROWSER)}
    async def run_cycle(self, query, location, cycle_id):
        all_jobs = []
        for name, scraper in self.scrapers.items():
            try:
                logger.info(f"Searching {name}: '{query}' in '{location}'")
                jobs = await scraper.search(query, location, self.config.MAX_JOBS_PER_CYCLE)
                for j in jobs: j["cycle_id"] = cycle_id
                all_jobs.extend(jobs)
                logger.info(f"  {name}: {len(jobs)} jobs")
            except Exception as e: logger.error(f"  {name}: {e}")
        new, dupes = DeduplicationEngine.filter_new(all_jobs)
        from database import JobDB
        result = JobDB.insert_batch(new)
        return {"total_found":len(all_jobs),"duplicates":dupes,"new_added":result["inserted"]}
    async def run_full(self, run_id):
        stats = {"cycles":0,"total_found":0,"new_added":0,"duplicates":0}
        for qi, query in enumerate(self.config.search_query_list):
            for li, loc in enumerate(self.config.location_list):
                cid = f"{run_id}_c{qi}_{li}"
                r = await self.run_cycle(query, loc, cid)
                stats["cycles"] += 1; stats["total_found"] += r["total_found"]
                stats["new_added"] += r["new_added"]; stats["duplicates"] += r["duplicates"]
                if stats["cycles"] >= self.config.CYCLES_PER_RUN: break
            if stats["cycles"] >= self.config.CYCLES_PER_RUN: break
        return stats
    async def cleanup(self):
        for s in self.scrapers.values(): await s.close()

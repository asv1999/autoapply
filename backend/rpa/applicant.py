"""Layer 4: RPA — Auto-apply via Playwright with 5 ATS adapters"""
import os, logging, asyncio, re
from typing import Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)

class ATSDetector:
    SIGS = {"workday":["myworkdayjobs","workday"],"greenhouse":["greenhouse.io","boards.greenhouse","grnh.se"],
        "lever":["lever.co","jobs.lever"],"icims":["icims.com","careers-"],"taleo":["taleo.net","oraclecloud.com/hcm"]}
    @staticmethod
    async def detect(page):
        url = page.url.lower()
        for ats, sigs in ATSDetector.SIGS.items():
            if any(s in url for s in sigs): return ats
        try:
            c = (await page.content()).lower()
            for ats, sigs in ATSDetector.SIGS.items():
                if any(s in c for s in sigs): return ats
        except: pass
        return "unknown"

class BaseAdapter:
    def __init__(self, page, profile, config): self.page, self.profile, self.config = page, profile, config
    async def safe_fill(self, sel, val, t=3000):
        try:
            el = await self.page.wait_for_selector(sel, timeout=t)
            if el: await el.click(); await el.fill(val); return True
        except: return False
    async def safe_click(self, sel, t=3000):
        try:
            el = await self.page.wait_for_selector(sel, timeout=t)
            if el: await el.click(); return True
        except: return False
    async def safe_upload(self, sel, path, t=5000):
        try:
            el = await self.page.wait_for_selector(sel, timeout=t)
            if el: await el.set_input_files(path); return True
        except: return False
    async def screenshot(self, name):
        p = f"data/outputs/screenshots/{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        os.makedirs(os.path.dirname(p), exist_ok=True)
        await self.page.screenshot(path=p, full_page=True); return p

class WorkdayAdapter(BaseAdapter):
    async def fill(self, resume_path, cl_path=None):
        r = {"ats":"workday","status":"pending","filled":0}
        try:
            await self.page.wait_for_timeout(2000)
            if await self.safe_click('a[data-automation-id="jobPostingApplyButton"], button:has-text("Apply")'):
                await self.page.wait_for_timeout(3000)
            if await self.safe_upload('input[type="file"]', resume_path): r["filled"] += 1
            for sel, val in {
                'input[data-automation-id="legalNameSection_firstName"]': self.profile.get("first_name",""),
                'input[data-automation-id="legalNameSection_lastName"]': self.profile.get("last_name",""),
                'input[data-automation-id="email"]': self.profile.get("email",""),
                'input[data-automation-id="phone-number"]': self.profile.get("phone",""),
            }.items():
                if val and await self.safe_fill(sel, val): r["filled"] += 1
            r["screenshot"] = await self.screenshot(f"workday_{self.profile.get('last_name','')}")
            r["status"] = "ready_to_submit"
        except Exception as e: r["status"] = "failed"; r["error"] = str(e)
        return r

class GreenhouseAdapter(BaseAdapter):
    async def fill(self, resume_path, cl_path=None):
        r = {"ats":"greenhouse","status":"pending","filled":0}
        try:
            for sel, val in {
                '#first_name, input[name="job_application[first_name]"]': self.profile.get("first_name",""),
                '#last_name, input[name="job_application[last_name]"]': self.profile.get("last_name",""),
                '#email, input[name="job_application[email]"]': self.profile.get("email",""),
                '#phone, input[name="job_application[phone]"]': self.profile.get("phone",""),
            }.items():
                if val and await self.safe_fill(sel, val): r["filled"] += 1
            if await self.safe_upload('#resume_file, input[type="file"]', resume_path): r["filled"] += 1
            r["screenshot"] = await self.screenshot(f"greenhouse_{self.profile.get('last_name','')}")
            r["status"] = "ready_to_submit"
        except Exception as e: r["status"] = "failed"; r["error"] = str(e)
        return r

class LeverAdapter(BaseAdapter):
    async def fill(self, resume_path, cl_path=None):
        r = {"ats":"lever","status":"pending","filled":0}
        try:
            await self.safe_click('a.postings-btn, a:has-text("Apply")')
            await self.page.wait_for_timeout(2000)
            fn = f"{self.profile.get('first_name','')} {self.profile.get('last_name','')}"
            for sel, val in {'input[name="name"]':fn,'input[name="email"]':self.profile.get("email",""),
                'input[name="phone"]':self.profile.get("phone","")}.items():
                if val and await self.safe_fill(sel, val): r["filled"] += 1
            if await self.safe_upload('input[name="resume"], input[type="file"]', resume_path): r["filled"] += 1
            r["screenshot"] = await self.screenshot(f"lever_{self.profile.get('last_name','')}")
            r["status"] = "ready_to_submit"
        except Exception as e: r["status"] = "failed"; r["error"] = str(e)
        return r

class ICIMSAdapter(BaseAdapter):
    async def fill(self, resume_path, cl_path=None):
        r = {"ats":"icims","status":"pending","filled":0}
        try:
            await self.safe_click('a:has-text("Apply"), button:has-text("Apply")')
            await self.page.wait_for_timeout(3000)
            if await self.safe_upload('input[type="file"]', resume_path): r["filled"] += 1
            for sel, val in {'input[id*="firstName"]':self.profile.get("first_name",""),
                'input[id*="lastName"]':self.profile.get("last_name",""),
                'input[id*="email"]':self.profile.get("email","")}.items():
                if val and await self.safe_fill(sel, val): r["filled"] += 1
            r["screenshot"] = await self.screenshot(f"icims_{self.profile.get('last_name','')}")
            r["status"] = "ready_to_submit"
        except Exception as e: r["status"] = "failed"; r["error"] = str(e)
        return r

class TaleoAdapter(BaseAdapter):
    async def fill(self, resume_path, cl_path=None):
        r = {"ats":"taleo","status":"pending","filled":0}
        try:
            await self.safe_click('a:has-text("Apply"), button:has-text("Apply Online")')
            await self.page.wait_for_timeout(3000)
            if await self.safe_upload('input[type="file"]', resume_path): r["filled"] += 1
            for sel, val in {'input[id*="FirstName"]':self.profile.get("first_name",""),
                'input[id*="LastName"]':self.profile.get("last_name",""),
                'input[id*="Email"]':self.profile.get("email","")}.items():
                if val and await self.safe_fill(sel, val): r["filled"] += 1
            r["screenshot"] = await self.screenshot(f"taleo_{self.profile.get('last_name','')}")
            r["status"] = "ready_to_submit"
        except Exception as e: r["status"] = "failed"; r["error"] = str(e)
        return r

ADAPTERS = {"workday":WorkdayAdapter,"greenhouse":GreenhouseAdapter,"lever":LeverAdapter,"icims":ICIMSAdapter,"taleo":TaleoAdapter}

class RPAApplicant:
    def __init__(self, profile, config, headless=True):
        self.profile, self.config, self.headless = profile, config, headless
        self.browser = self.pw = None
    async def init(self):
        from playwright.async_api import async_playwright
        self.pw = await async_playwright().start()
        self.browser = await self.pw.chromium.launch(headless=self.headless)
    async def apply_one(self, job, resume_path, cl_path=None):
        if not self.browser: await self.init()
        page = await self.browser.new_page()
        result = {"job_id":job.get("id"),"company":job.get("company"),"title":job.get("title")}
        try:
            url = job.get("url","")
            if not url: result["status"] = "skipped"; result["error"] = "No URL"; return result
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2000)
            ats = await ATSDetector.detect(page); result["ats"] = ats
            adapter_cls = ADAPTERS.get(ats)
            if not adapter_cls: result["status"] = "manual_review"; result["error"] = f"Unknown ATS: {ats}"; return result
            adapter = adapter_cls(page, self.profile, self.config)
            r = await adapter.fill(resume_path, cl_path)
            result.update(r)
        except Exception as e: result["status"] = "failed"; result["error"] = str(e)
        finally: await page.close()
        return result
    async def cleanup(self):
        if self.browser: await self.browser.close()
        if self.pw: await self.pw.stop()

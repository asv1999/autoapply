"""
Layer 4: RPA Applicant
Browser automation for auto-applying to career pages.
Supports: Workday, Greenhouse, Lever, iCIMS, Taleo
"""
import re
import os
import logging
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

# ─── ATS DETECTOR ───

class ATSDetector:
    """Detects which ATS platform a career page uses."""
    
    SIGNATURES = {
        "workday": [
            "myworkdayjobs.com", "wd5.myworkdaysite.com", "workday.com/en-US/careers",
            "myworkdayjobs", "workday"
        ],
        "greenhouse": [
            "greenhouse.io", "boards.greenhouse.io", "grnh.se",
            "job_application[", "greenhouse"
        ],
        "lever": [
            "lever.co", "jobs.lever.co", "hire.lever.co"
        ],
        "icims": [
            "icims.com", "careers-", ".icims.com",
            "hcm-", "icims"
        ],
        "taleo": [
            "taleo.net", "oraclecloud.com/hcmUI", "taleo",
            "recruitingsite"
        ],
    }
    
    @staticmethod
    async def detect(page) -> Optional[str]:
        """Detect ATS from current page URL and content."""
        url = page.url.lower()
        
        for ats, signatures in ATSDetector.SIGNATURES.items():
            for sig in signatures:
                if sig in url:
                    return ats
        
        # Check page source for signatures
        try:
            content = await page.content()
            content_lower = content.lower()
            for ats, signatures in ATSDetector.SIGNATURES.items():
                for sig in signatures:
                    if sig in content_lower:
                        return ats
        except:
            pass
        
        return "unknown"


# ─── BASE ATS ADAPTER ───

class BaseATSAdapter(ABC):
    """Base class for ATS-specific form fillers."""
    
    def __init__(self, page, profile: Dict, config: Dict):
        self.page = page
        self.profile = profile
        self.config = config
    
    @abstractmethod
    async def fill_application(self, resume_path: str, cover_letter_path: str = None) -> Dict:
        """Fill out the application form. Returns status dict."""
        pass
    
    async def safe_fill(self, selector: str, value: str, timeout: int = 3000) -> bool:
        """Safely fill a form field, returns True if successful."""
        try:
            el = await self.page.wait_for_selector(selector, timeout=timeout)
            if el:
                await el.click()
                await el.fill(value)
                return True
        except:
            return False
    
    async def safe_click(self, selector: str, timeout: int = 3000) -> bool:
        """Safely click an element."""
        try:
            el = await self.page.wait_for_selector(selector, timeout=timeout)
            if el:
                await el.click()
                return True
        except:
            return False
    
    async def safe_upload(self, selector: str, file_path: str, timeout: int = 5000) -> bool:
        """Safely upload a file."""
        try:
            el = await self.page.wait_for_selector(selector, timeout=timeout)
            if el:
                await el.set_input_files(file_path)
                return True
        except:
            return False
    
    async def safe_select(self, selector: str, value: str, timeout: int = 3000) -> bool:
        """Safely select a dropdown option."""
        try:
            el = await self.page.wait_for_selector(selector, timeout=timeout)
            if el:
                await el.select_option(value=value)
                return True
        except:
            try:
                await el.select_option(label=value)
                return True
            except:
                return False
    
    async def take_screenshot(self, name: str) -> str:
        """Take a screenshot for verification."""
        path = f"data/outputs/screenshots/{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        os.makedirs(os.path.dirname(path), exist_ok=True)
        await self.page.screenshot(path=path, full_page=True)
        return path


# ─── WORKDAY ADAPTER ───

class WorkdayAdapter(BaseATSAdapter):
    
    async def fill_application(self, resume_path: str, cover_letter_path: str = None) -> Dict:
        result = {"ats": "workday", "status": "pending", "fields_filled": 0, "fields_skipped": 0}
        
        try:
            await self.page.wait_for_timeout(2000)
            
            # Click Apply button
            apply_clicked = await self.safe_click('a[data-automation-id="jobPostingApplyButton"], button:has-text("Apply")')
            if not apply_clicked:
                result["status"] = "failed"
                result["error"] = "Could not find Apply button"
                return result
            
            await self.page.wait_for_timeout(3000)
            
            # Upload resume
            uploaded = await self.safe_upload('input[type="file"][data-automation-id="file-upload-input-ref"]', resume_path)
            if not uploaded:
                uploaded = await self.safe_upload('input[type="file"]', resume_path)
            if uploaded:
                result["fields_filled"] += 1
                await self.page.wait_for_timeout(2000)
            
            # Fill standard fields
            fields = {
                'input[data-automation-id="legalNameSection_firstName"]': self.profile.get("first_name", ""),
                'input[data-automation-id="legalNameSection_lastName"]': self.profile.get("last_name", ""),
                'input[data-automation-id="email"]': self.profile.get("email", ""),
                'input[data-automation-id="phone-number"]': self.profile.get("phone", ""),
                'input[data-automation-id="addressSection_city"]': self.profile.get("city", ""),
            }
            
            for selector, value in fields.items():
                if value and await self.safe_fill(selector, value):
                    result["fields_filled"] += 1
                else:
                    result["fields_skipped"] += 1
            
            # Upload cover letter if available
            if cover_letter_path:
                cl_uploaded = await self.safe_upload('input[type="file"][data-automation-id="coverLetterUpload"]', cover_letter_path)
                if cl_uploaded:
                    result["fields_filled"] += 1
            
            # Take screenshot before submit
            result["screenshot"] = await self.take_screenshot(f"workday_{self.profile.get('last_name','app')}")
            
            # Submit (only if configured to auto-submit)
            if self.config.get("auto_submit", False):
                submitted = await self.safe_click('button[data-automation-id="bottom-navigation-next-button"]')
                result["status"] = "submitted" if submitted else "manual_review"
            else:
                result["status"] = "ready_to_submit"
            
        except Exception as e:
            result["status"] = "failed"
            result["error"] = str(e)
        
        return result


# ─── GREENHOUSE ADAPTER ───

class GreenhouseAdapter(BaseATSAdapter):
    
    async def fill_application(self, resume_path: str, cover_letter_path: str = None) -> Dict:
        result = {"ats": "greenhouse", "status": "pending", "fields_filled": 0, "fields_skipped": 0}
        
        try:
            await self.page.wait_for_timeout(2000)
            
            # Greenhouse forms are usually on the same page
            fields = {
                '#first_name, input[name="job_application[first_name]"]': self.profile.get("first_name", ""),
                '#last_name, input[name="job_application[last_name]"]': self.profile.get("last_name", ""),
                '#email, input[name="job_application[email]"]': self.profile.get("email", ""),
                '#phone, input[name="job_application[phone]"]': self.profile.get("phone", ""),
                'input[name="job_application[location]"]': self.profile.get("location", ""),
            }
            
            for selector, value in fields.items():
                if value and await self.safe_fill(selector, value):
                    result["fields_filled"] += 1
                else:
                    result["fields_skipped"] += 1
            
            # Resume upload
            uploaded = await self.safe_upload('#resume_file, input[name="job_application[resume]"]', resume_path)
            if not uploaded:
                uploaded = await self.safe_upload('input[type="file"]', resume_path)
            if uploaded:
                result["fields_filled"] += 1
            
            # Cover letter
            if cover_letter_path:
                await self.safe_upload('#cover_letter_file, input[name="job_application[cover_letter]"]', cover_letter_path)
            
            # LinkedIn URL
            if self.profile.get("linkedin_url"):
                await self.safe_fill('input[name*="linkedin"], input[placeholder*="LinkedIn"]', self.profile["linkedin_url"])
            
            result["screenshot"] = await self.take_screenshot(f"greenhouse_{self.profile.get('last_name','app')}")
            
            if self.config.get("auto_submit", False):
                submitted = await self.safe_click('#submit_app, button[type="submit"]')
                result["status"] = "submitted" if submitted else "manual_review"
            else:
                result["status"] = "ready_to_submit"
                
        except Exception as e:
            result["status"] = "failed"
            result["error"] = str(e)
        
        return result


# ─── LEVER ADAPTER ───

class LeverAdapter(BaseATSAdapter):
    
    async def fill_application(self, resume_path: str, cover_letter_path: str = None) -> Dict:
        result = {"ats": "lever", "status": "pending", "fields_filled": 0, "fields_skipped": 0}
        
        try:
            # Click Apply
            await self.safe_click('a.postings-btn, a:has-text("Apply for this job")')
            await self.page.wait_for_timeout(2000)
            
            fields = {
                'input[name="name"]': f"{self.profile.get('first_name','')} {self.profile.get('last_name','')}",
                'input[name="email"]': self.profile.get("email", ""),
                'input[name="phone"]': self.profile.get("phone", ""),
                'input[name="org"], input[name="company"]': self.profile.get("current_company", ""),
                'input[name*="linkedin"], input[placeholder*="LinkedIn"]': self.profile.get("linkedin_url", ""),
            }
            
            for selector, value in fields.items():
                if value and await self.safe_fill(selector, value):
                    result["fields_filled"] += 1
                else:
                    result["fields_skipped"] += 1
            
            uploaded = await self.safe_upload('input[name="resume"]', resume_path)
            if not uploaded:
                uploaded = await self.safe_upload('input[type="file"]', resume_path)
            if uploaded:
                result["fields_filled"] += 1
            
            result["screenshot"] = await self.take_screenshot(f"lever_{self.profile.get('last_name','app')}")
            
            if self.config.get("auto_submit", False):
                submitted = await self.safe_click('button[type="submit"], button:has-text("Submit")')
                result["status"] = "submitted" if submitted else "manual_review"
            else:
                result["status"] = "ready_to_submit"
                
        except Exception as e:
            result["status"] = "failed"
            result["error"] = str(e)
        
        return result


# ─── ICIMS ADAPTER ───

class ICIMSAdapter(BaseATSAdapter):
    
    async def fill_application(self, resume_path: str, cover_letter_path: str = None) -> Dict:
        result = {"ats": "icims", "status": "pending", "fields_filled": 0, "fields_skipped": 0}
        
        try:
            await self.safe_click('a.iCIMS_PrimaryButton, a:has-text("Apply"), button:has-text("Apply")')
            await self.page.wait_for_timeout(3000)
            
            uploaded = await self.safe_upload('input[type="file"]', resume_path)
            if uploaded:
                result["fields_filled"] += 1
                await self.page.wait_for_timeout(2000)
            
            fields = {
                'input[id*="firstName"], input[name*="firstName"]': self.profile.get("first_name", ""),
                'input[id*="lastName"], input[name*="lastName"]': self.profile.get("last_name", ""),
                'input[id*="email"], input[name*="email"]': self.profile.get("email", ""),
                'input[id*="phone"], input[name*="phone"]': self.profile.get("phone", ""),
            }
            
            for selector, value in fields.items():
                if value and await self.safe_fill(selector, value):
                    result["fields_filled"] += 1
                else:
                    result["fields_skipped"] += 1
            
            result["screenshot"] = await self.take_screenshot(f"icims_{self.profile.get('last_name','app')}")
            result["status"] = "ready_to_submit"
            
        except Exception as e:
            result["status"] = "failed"
            result["error"] = str(e)
        
        return result


# ─── TALEO ADAPTER ───

class TaleoAdapter(BaseATSAdapter):
    
    async def fill_application(self, resume_path: str, cover_letter_path: str = None) -> Dict:
        result = {"ats": "taleo", "status": "pending", "fields_filled": 0, "fields_skipped": 0}
        
        try:
            await self.safe_click('a:has-text("Apply"), button:has-text("Apply Online")')
            await self.page.wait_for_timeout(3000)
            
            uploaded = await self.safe_upload('input[type="file"]', resume_path)
            if uploaded:
                result["fields_filled"] += 1
            
            fields = {
                'input[id*="FirstName"]': self.profile.get("first_name", ""),
                'input[id*="LastName"]': self.profile.get("last_name", ""),
                'input[id*="Email"]': self.profile.get("email", ""),
                'input[id*="Phone"]': self.profile.get("phone", ""),
            }
            
            for selector, value in fields.items():
                if value and await self.safe_fill(selector, value):
                    result["fields_filled"] += 1
                else:
                    result["fields_skipped"] += 1
            
            result["screenshot"] = await self.take_screenshot(f"taleo_{self.profile.get('last_name','app')}")
            result["status"] = "ready_to_submit"
            
        except Exception as e:
            result["status"] = "failed"
            result["error"] = str(e)
        
        return result


# ─── RPA ORCHESTRATOR ───

class RPAApplicant:
    """Orchestrates the auto-apply process across all ATS platforms."""
    
    ADAPTERS = {
        "workday": WorkdayAdapter,
        "greenhouse": GreenhouseAdapter,
        "lever": LeverAdapter,
        "icims": ICIMSAdapter,
        "taleo": TaleoAdapter,
    }
    
    def __init__(self, profile: Dict, config: Dict, headless: bool = True):
        self.profile = profile
        self.config = config
        self.headless = headless
        self.browser = None
        self.pw = None
    
    async def init_browser(self):
        from playwright.async_api import async_playwright
        self.pw = await async_playwright().start()
        self.browser = await self.pw.chromium.launch(headless=self.headless)
    
    async def apply_to_job(self, job: Dict, resume_path: str, cover_letter_path: str = None) -> Dict:
        """Apply to a single job. Detects ATS and uses appropriate adapter."""
        if not self.browser:
            await self.init_browser()
        
        page = await self.browser.new_page()
        result = {"job_id": job.get("id"), "company": job.get("company"), "title": job.get("title")}
        
        try:
            # Navigate to career page
            url = job.get("url", "")
            if not url:
                result["status"] = "skipped"
                result["error"] = "No URL"
                return result
            
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2000)
            
            # Detect ATS
            ats = await ATSDetector.detect(page)
            result["ats"] = ats
            logger.info(f"Detected ATS: {ats} for {job.get('company')}")
            
            # Get appropriate adapter
            adapter_class = self.ADAPTERS.get(ats)
            if not adapter_class:
                result["status"] = "manual_review"
                result["error"] = f"No adapter for ATS: {ats}"
                result["screenshot"] = await page.screenshot(
                    path=f"data/outputs/screenshots/unknown_{job.get('company','')}.png"
                )
                return result
            
            # Run adapter
            adapter = adapter_class(page, self.profile, self.config)
            apply_result = await adapter.fill_application(resume_path, cover_letter_path)
            result.update(apply_result)
            
        except Exception as e:
            result["status"] = "failed"
            result["error"] = str(e)
        finally:
            await page.close()
        
        return result
    
    async def apply_batch(self, jobs: List[Dict], resume_paths: Dict, delay: int = 5) -> List[Dict]:
        """Apply to a batch of jobs with delay between applications."""
        results = []
        
        for i, job in enumerate(jobs):
            job_id = job.get("id", i)
            resume_path = resume_paths.get(job_id, resume_paths.get("default", ""))
            
            logger.info(f"Applying {i+1}/{len(jobs)}: {job.get('title')} @ {job.get('company')}")
            result = await self.apply_to_job(job, resume_path)
            results.append(result)
            
            # Delay between applications
            if i < len(jobs) - 1:
                await asyncio.sleep(delay)
        
        return results
    
    async def cleanup(self):
        if self.browser:
            await self.browser.close()
        if self.pw:
            await self.pw.stop()

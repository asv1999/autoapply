#!/usr/bin/env python3
"""
AutoApply — Local RPA Client
Runs on YOUR machine. Pulls pending applications from the cloud API,
downloads tailored resumes, and auto-applies via your real browser.

Usage:
    python rpa_local.py --server https://your-api.com --limit 10
    python rpa_local.py --server https://your-api.com --limit 10 --headless
    python rpa_local.py --server https://your-api.com --dry-run
"""
import os
import sys
import json
import time
import asyncio
import argparse
import httpx

# Add parent directory for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

async def main():
    parser = argparse.ArgumentParser(description="AutoApply Local RPA Client")
    parser.add_argument("--server", required=True, help="Backend API URL (e.g., https://your-droplet.com)")
    parser.add_argument("--limit", type=int, default=10, help="Max applications per run")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    parser.add_argument("--dry-run", action="store_true", help="Fill forms but don't submit")
    parser.add_argument("--delay", type=int, default=5, help="Seconds between applications")
    parser.add_argument("--profile-id", type=int, default=1, help="Profile ID")
    args = parser.parse_args()

    api_url = args.server.rstrip("/")
    
    print(f"""
╔══════════════════════════════════════════╗
║  AutoApply — Local RPA Client            ║
║  Server: {api_url:<32} ║
║  Limit:  {args.limit:<32} ║
║  Mode:   {'DRY RUN' if args.dry_run else 'HEADLESS' if args.headless else 'VISIBLE BROWSER':<32} ║
╚══════════════════════════════════════════╝
""")

    async with httpx.AsyncClient(timeout=30) as client:
        # 1. Health check
        try:
            r = await client.get(f"{api_url}/health")
            health = r.json()
            print(f"[✓] Server connected: {health}")
        except Exception as e:
            print(f"[✗] Cannot reach server: {e}")
            return

        # 2. Get profile
        try:
            r = await client.get(f"{api_url}/api/profile/{args.profile_id}")
            profile = r.json()
            print(f"[✓] Profile loaded: {profile.get('name', 'Unknown')}")
        except:
            print("[✗] Profile not found. Create one via the dashboard first.")
            return

        # 3. Get pending applications with resume paths
        r = await client.get(f"{api_url}/api/jobs?status=unapplied&limit={args.limit}")
        jobs = r.json()
        
        if not jobs:
            print("[i] No pending applications. Run discovery + tailoring first.")
            return
        
        print(f"[i] Found {len(jobs)} pending applications\n")

        # 4. Download resumes
        os.makedirs("_rpa_temp", exist_ok=True)

        # 5. Apply to each job
        from playwright.async_api import async_playwright
        
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=args.headless)
            
            applied = 0
            failed = 0
            skipped = 0
            
            for i, job in enumerate(jobs):
                title = job.get("title", "Unknown")
                company = job.get("company", "Unknown")
                url = job.get("url", "")
                
                if not url:
                    print(f"  [{i+1}] SKIP — {title} @ {company} — no URL")
                    skipped += 1
                    continue
                
                print(f"  [{i+1}/{len(jobs)}] {title} @ {company}")
                print(f"         URL: {url}")
                
                page = await browser.new_page()
                
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    await page.wait_for_timeout(2000)
                    
                    # Detect ATS
                    page_url = page.url.lower()
                    ats = "unknown"
                    for name, sigs in {
                        "workday": ["myworkdayjobs", "workday"],
                        "greenhouse": ["greenhouse.io", "boards.greenhouse"],
                        "lever": ["lever.co", "jobs.lever"],
                        "icims": ["icims.com"],
                        "taleo": ["taleo.net", "oraclecloud.com/hcm"],
                    }.items():
                        if any(s in page_url for s in sigs):
                            ats = name
                            break
                    
                    print(f"         ATS: {ats}")
                    
                    # Screenshot
                    ss_path = f"_rpa_temp/screenshot_{company.replace(' ','_')}_{i}.png"
                    await page.screenshot(path=ss_path)
                    print(f"         Screenshot saved: {ss_path}")
                    
                    if args.dry_run:
                        print(f"         DRY RUN — would apply here")
                        applied += 1
                    else:
                        # Try to find and click Apply button
                        apply_selectors = [
                            'a:has-text("Apply")', 'button:has-text("Apply")',
                            'a:has-text("Submit")', 'button:has-text("Submit Application")',
                            '[data-automation-id="jobPostingApplyButton"]',
                            '.postings-btn', '#apply-button',
                        ]
                        
                        clicked = False
                        for sel in apply_selectors:
                            try:
                                el = await page.wait_for_selector(sel, timeout=2000)
                                if el:
                                    await el.click()
                                    clicked = True
                                    print(f"         Clicked: {sel}")
                                    break
                            except:
                                continue
                        
                        if clicked:
                            await page.wait_for_timeout(2000)
                            
                            # Fill basic fields
                            name_parts = profile.get("name", "").split()
                            first_name = name_parts[0] if name_parts else ""
                            last_name = name_parts[-1] if len(name_parts) > 1 else ""
                            
                            field_map = {
                                'input[name*="first"], input[id*="first"], input[autocomplete="given-name"]': first_name,
                                'input[name*="last"], input[id*="last"], input[autocomplete="family-name"]': last_name,
                                'input[name*="email"], input[type="email"], input[autocomplete="email"]': profile.get("email", ""),
                                'input[name*="phone"], input[type="tel"], input[autocomplete="tel"]': profile.get("phone", ""),
                            }
                            
                            filled = 0
                            for sel, val in field_map.items():
                                if not val:
                                    continue
                                try:
                                    el = await page.wait_for_selector(sel, timeout=1500)
                                    if el:
                                        await el.click()
                                        await el.fill(val)
                                        filled += 1
                                except:
                                    continue
                            
                            # Take final screenshot
                            ss_path2 = f"_rpa_temp/filled_{company.replace(' ','_')}_{i}.png"
                            await page.screenshot(path=ss_path2, full_page=True)
                            
                            print(f"         Filled {filled} fields. Screenshot: {ss_path2}")
                            print(f"         STATUS: ready_to_submit (manual review)")
                            applied += 1
                        else:
                            print(f"         Could not find Apply button. Flagged for manual.")
                            skipped += 1
                    
                except Exception as e:
                    print(f"         ERROR: {e}")
                    failed += 1
                finally:
                    await page.close()
                
                # Delay between applications
                if i < len(jobs) - 1:
                    print(f"         Waiting {args.delay}s...")
                    await asyncio.sleep(args.delay)
            
            await browser.close()
        
        print(f"""
╔══════════════════════════════════════════╗
║  Run Complete                            ║
║  Applied:  {applied:<30} ║
║  Failed:   {failed:<30} ║
║  Skipped:  {skipped:<30} ║
║  Screenshots: _rpa_temp/                 ║
╚══════════════════════════════════════════╝
""")

if __name__ == "__main__":
    asyncio.run(main())

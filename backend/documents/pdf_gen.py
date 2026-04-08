"""ATS-Optimized PDF Resume Generator — HTML template + WeasyPrint rendering."""
import json, logging, os, re
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "data", "outputs", "resumes")
TEMPLATE_DIR = os.path.dirname(__file__)

# Work experience metadata
WORK_SECTIONS = {
    "digitech": {
        "role": "Business Insights & Process Analytics Analyst",
        "org": "Digitech Services Limited",
        "location": "Phoenix, AZ",
        "dates": "Aug 2025 - Dec 2025",
    },
    "asu": {
        "role": "Analytics & Reporting Intern, Strategic Projects",
        "org": "Arizona State University",
        "location": "Tempe, AZ",
        "dates": "Aug 2024 - May 2025",
    },
    "vaxom": {
        "role": "Data Insights & Commercial Analytics Analyst",
        "org": "Vaxom Packaging",
        "location": "Mumbai, India",
        "dates": "Aug 2022 - Aug 2023",
    },
    "nccl": {
        "role": "Data Analytics & Reporting Analyst",
        "org": "National Commodities Clearing Limited",
        "location": "Mumbai, India",
        "dates": "Feb 2021 - Aug 2022",
    },
}

CONSULTING_SECTIONS = {
    "vertiv": {
        "role": "Performance Analytics & Benchmarking",
        "org": "Vertiv, Global Data Center Infrastructure",
        "location": "Thunderbird Capstone",
        "dates": "Sep 2024 - Dec 2024",
    },
    "km_capital": {
        "role": "Market Sizing & Data Analysis",
        "org": "KM Capital Partners, Healthcare Strategy",
        "location": "Thunderbird Corporate Partners",
        "dates": "Jan 2025 - May 2025",
    },
    "scdi": {
        "role": "Founder",
        "org": "Supply Chain Decision Intelligence Platform",
        "location": "Independent Project",
        "dates": "Jan 2026 - Present",
    },
}

# ATS-safe HTML template with Space Grotesk + DM Sans (via Google Fonts CDN)
CV_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{NAME}} - CV</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=DM+Sans:wght@400;500;600;700&display=swap');

  * { margin: 0; padding: 0; box-sizing: border-box; }
  html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }

  body {
    font-family: 'DM Sans', 'Calibri', sans-serif;
    font-size: 11px;
    line-height: 1.5;
    color: #1a1a2e;
    background: #ffffff;
    padding: 0;
    margin: 0;
  }

  .page {
    width: 100%;
    max-width: 8.5in;
    margin: 0 auto;
    padding: 0.55in 0.6in;
  }

  .header { margin-bottom: 14px; }
  .header h1 {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 24px;
    font-weight: 700;
    color: #1a1a2e;
    letter-spacing: -0.02em;
    margin-bottom: 4px;
  }
  .header-gradient {
    height: 2px;
    background: linear-gradient(to right, hsl(187, 74%, 32%), hsl(270, 70%, 45%));
    border-radius: 1px;
    margin-bottom: 8px;
  }
  .contact-row {
    display: flex;
    flex-wrap: wrap;
    gap: 6px 14px;
    font-size: 10px;
    color: #555;
  }
  .contact-row a { color: #555; text-decoration: none; }
  .separator { color: #ccc; }

  .section { margin-bottom: 12px; }
  .section-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 13px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: hsl(187, 74%, 32%);
    border-bottom: 1px solid #e5e5e5;
    padding-bottom: 3px;
    margin-bottom: 8px;
  }

  .summary-text { font-size: 11px; line-height: 1.6; color: #333; }

  .competencies-grid { display: flex; flex-wrap: wrap; gap: 6px; }
  .competency-tag {
    font-size: 10px;
    font-weight: 500;
    color: hsl(187, 74%, 28%);
    background: hsl(187, 40%, 95%);
    padding: 3px 10px;
    border-radius: 3px;
    border: 1px solid hsl(187, 40%, 88%);
  }

  .job { margin-bottom: 10px; }
  .job-header { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 2px; }
  .job-company {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 12px;
    font-weight: 600;
    color: hsl(270, 70%, 45%);
  }
  .job-period { font-size: 10px; color: #777; white-space: nowrap; }
  .job-role { font-size: 11px; font-weight: 500; color: #444; margin-bottom: 3px; }

  .job ul { padding-left: 16px; margin-top: 3px; }
  .job li { font-size: 10.5px; line-height: 1.5; color: #333; margin-bottom: 2px; }

  .project { margin-bottom: 8px; }
  .project-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 11px;
    font-weight: 600;
    color: hsl(270, 70%, 45%);
  }
  .project-desc { font-size: 10.5px; color: #444; margin-top: 2px; }

  .edu-item { margin-bottom: 5px; }
  .edu-header { display: flex; justify-content: space-between; align-items: baseline; }
  .edu-title { font-weight: 600; font-size: 11px; color: #333; }
  .edu-org { color: hsl(270, 70%, 45%); font-weight: 500; }
  .edu-year { font-size: 10px; color: #777; }
  .edu-desc { font-size: 10px; color: #666; }

  .skills-grid { display: flex; flex-wrap: wrap; gap: 4px 12px; }
  .skill-category { font-weight: 600; color: #333; font-size: 10.5px; }
  .skill-item { font-size: 10.5px; color: #444; }

  a { white-space: nowrap; }
  .avoid-break { break-inside: avoid; }

  @media print {
    body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    .page { padding: 0.55in 0.6in; }
  }
</style>
</head>
<body>
<div class="page">
  <div class="header">
    <h1>{{NAME}}</h1>
    <div class="header-gradient"></div>
    <div class="contact-row">
      <span>{{EMAIL}}</span>
      <span class="separator">|</span>
      <a href="{{LINKEDIN_URL}}">{{LINKEDIN_DISPLAY}}</a>
      <span class="separator">|</span>
      <span>{{LOCATION}}</span>
    </div>
  </div>

  <div class="section">
    <div class="section-title">Professional Summary</div>
    <div class="summary-text">{{SUMMARY_TEXT}}</div>
  </div>

  <div class="section">
    <div class="section-title">Core Competencies</div>
    <div class="competencies-grid">{{COMPETENCIES}}</div>
  </div>

  <div class="section">
    <div class="section-title">Work Experience</div>
    {{EXPERIENCE}}
  </div>

  <div class="section">
    <div class="section-title">Consulting & Projects</div>
    {{PROJECTS}}
  </div>

  <div class="section avoid-break">
    <div class="section-title">Education</div>
    {{EDUCATION}}
  </div>

  <div class="section avoid-break">
    <div class="section-title">Skills</div>
    {{SKILLS}}
  </div>

  <div class="section avoid-break">
    <div class="section-title">Leadership</div>
    {{LEADERSHIP}}
  </div>
</div>
</body>
</html>"""

# ATS normalization: replace smart quotes, em-dashes with ASCII
def _ats_normalize(text: str) -> str:
    replacements = {
        "\u2018": "'", "\u2019": "'",  # smart single quotes
        "\u201c": '"', "\u201d": '"',  # smart double quotes
        "\u2013": "-", "\u2014": "-",  # en-dash, em-dash
        "\u2026": "...",               # ellipsis
        "\u200b": "",                  # zero-width space
        "\ufeff": "",                  # BOM
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def _parse_jsonish(value, default):
    if value is None:
        return default
    if isinstance(value, str):
        try:
            return json.loads(value)
        except:
            return default
    return value


def _normalize_bullets(application):
    bullets = _parse_jsonish(application.get("tailored_bullets"), {})
    return bullets if isinstance(bullets, dict) else {}


def _get_bullets(section: str, tailored: Dict, base: Dict) -> List[str]:
    for source in (tailored, base):
        vals = source.get(section, [])
        if isinstance(vals, list):
            cleaned = [str(b).strip() for b in vals if len(str(b).strip()) > 20]
            if cleaned:
                return cleaned
    return []


def _html_escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _build_job_html(org: str, role: str, location: str, dates: str, bullets: List[str]) -> str:
    bullet_html = "\n".join(f"    <li>{_html_escape(_ats_normalize(b))}</li>" for b in bullets)
    return f"""<div class="job avoid-break">
  <div class="job-header">
    <span class="job-company">{_html_escape(org)}</span>
    <span class="job-period">{_html_escape(dates)}</span>
  </div>
  <div class="job-role">{_html_escape(role)} | {_html_escape(location)}</div>
  <ul>
{bullet_html}
  </ul>
</div>"""


def _build_summary(profile: Dict, job: Dict, keywords: List[str] = None) -> str:
    """Build keyword-injected professional summary."""
    name = profile.get("name", "Candidate")
    title = job.get("title", "strategy and operations role")
    company = job.get("company", "the team")

    kw_inject = ""
    if keywords:
        top_kw = [k for k in keywords[:6] if len(k) > 3]
        if top_kw:
            kw_inject = f" with expertise in {', '.join(top_kw[:4])}"

    summary = (
        f"Results-driven strategy and operations professional with 4+ years driving analytics, "
        f"process improvement, and business transformation across consulting, manufacturing, and technology. "
        f"Track record includes a 115% revenue turnaround ($4M to $8.6M), 51% operational efficiency gains "
        f"through AI transformation, and $100K+ in annual savings from workflow redesign{kw_inject}. "
        f"Multi-market experience across 5 continents, bringing structured problem-solving and "
        f"cross-cultural execution to {_html_escape(company)}."
    )
    return _ats_normalize(summary)


def _build_competency_tags(keywords: List[str], profile: Dict) -> str:
    """Build competency grid from JD keywords."""
    if not keywords:
        # Fallback to profile skills
        skills = _parse_jsonish(profile.get("skills"), [])
        if isinstance(skills, list) and skills:
            keywords = skills[:8]
        else:
            keywords = ["Strategy & Operations", "Business Analytics", "Process Improvement",
                       "AI Transformation", "Stakeholder Management", "Data Visualization"]

    tags = keywords[:8]
    return "\n".join(f'      <span class="competency-tag">{_html_escape(_ats_normalize(t))}</span>' for t in tags)


def generate_pdf_resume(
    profile: Dict,
    application: Dict,
    job: Dict,
    keywords: List[str] = None,
    output_dir: str = None,
) -> Tuple[Optional[str], Optional[str]]:
    """Generate ATS-optimized PDF resume from HTML template."""
    output_dir = output_dir or OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)

    tailored = _normalize_bullets(application)
    base = _parse_jsonish(profile.get("resume_bullets"), {})
    if not isinstance(base, dict):
        base = {}

    # Profile info
    name = profile.get("name", "Atharva Vaidya")
    email = profile.get("email", "")
    linkedin = profile.get("linkedin_url", "")
    linkedin_display = linkedin.replace("https://", "").replace("http://", "").rstrip("/") if linkedin else ""
    location = profile.get("location", "Phoenix, AZ")

    # Build sections
    summary = _build_summary(profile, job, keywords)
    competencies = _build_competency_tags(keywords or [], profile)

    # Work experience
    experience_html = ""
    for sec_name in ("digitech", "asu", "vaxom", "nccl"):
        info = WORK_SECTIONS[sec_name]
        bullets = _get_bullets(sec_name, tailored, base)
        if bullets:
            experience_html += _build_job_html(info["org"], info["role"], info["location"], info["dates"], bullets) + "\n"

    # Consulting & Projects
    projects_html = ""
    for sec_name in ("vertiv", "km_capital", "scdi"):
        info = CONSULTING_SECTIONS[sec_name]
        bullets = _get_bullets(sec_name, tailored, base)
        if bullets:
            projects_html += _build_job_html(info["org"], info["role"], info["location"], info["dates"], bullets) + "\n"

    # Education
    education_html = """<div class="edu-item">
  <div class="edu-header">
    <span class="edu-title">Master of Global Management - <span class="edu-org">Thunderbird School of Global Management, ASU</span></span>
    <span class="edu-year">May 2025</span>
  </div>
  <div class="edu-desc">Thunderbird Alumni Scholarship (60% tuition) | GPA: 3.49/4.0</div>
</div>
<div class="edu-item">
  <div class="edu-header">
    <span class="edu-title">B.Tech, Electronics & Telecommunications - <span class="edu-org">VIT Pune</span> | Research Scholar, <span class="edu-org">KIST Seoul</span></span>
    <span class="edu-year">Jun 2021</span>
  </div>
</div>"""

    # Skills
    skills = _parse_jsonish(profile.get("skills"), [])
    if isinstance(skills, list) and skills:
        skills_text = ", ".join(str(s) for s in skills)
    else:
        skills_text = "SQL, Python, Excel, Tableau, Alteryx, Power BI, Salesforce, SAP EWM, Oracle ERP, VBA, Generative AI"

    skills_html = f"""<div class="skills-grid">
  <span><span class="skill-category">Analytics & Reporting:</span> <span class="skill-item">SQL, Python, Tableau, Excel, Power BI, Alteryx</span></span>
  <span><span class="skill-category">Strategy & Ops:</span> <span class="skill-item">Six Sigma DMAIC, Process Improvement, Stakeholder Management</span></span>
  <span><span class="skill-category">Technology:</span> <span class="skill-item">Salesforce CRM, SAP EWM, Oracle ERP, Generative AI</span></span>
</div>"""

    # Leadership
    gcn_bullets = _get_bullets("gcn", tailored, base)
    if gcn_bullets:
        leadership_html = "<ul>" + "\n".join(f"  <li>{_html_escape(_ats_normalize(b))}</li>" for b in gcn_bullets) + "\n</ul>"
    else:
        leadership_html = """<ul>
  <li>President, Global Careers Network ASU (2024-25): Drove 12% YoY internship growth across 14,000+ students by connecting them with Fortune 500 partners including JP Morgan Chase, Bain & Company, and McKinsey.</li>
</ul>"""

    # Fill template
    html = CV_TEMPLATE
    replacements = {
        "{{NAME}}": _html_escape(name),
        "{{EMAIL}}": _html_escape(email),
        "{{LINKEDIN_URL}}": _html_escape(linkedin),
        "{{LINKEDIN_DISPLAY}}": _html_escape(linkedin_display),
        "{{LOCATION}}": _html_escape(location),
        "{{SUMMARY_TEXT}}": summary,
        "{{COMPETENCIES}}": competencies,
        "{{EXPERIENCE}}": experience_html,
        "{{PROJECTS}}": projects_html,
        "{{EDUCATION}}": education_html,
        "{{SKILLS}}": skills_html,
        "{{LEADERSHIP}}": leadership_html,
    }
    for placeholder, value in replacements.items():
        html = html.replace(placeholder, value)

    # Write HTML
    company_slug = re.sub(r"[^a-zA-Z0-9]+", "_", job.get("company", "Unknown")).strip("_")
    name_slug = re.sub(r"[^a-zA-Z0-9]+", "_", name).strip("_")

    html_filename = f"cv_{name_slug}_{company_slug}.html"
    html_path = os.path.join(output_dir, html_filename)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    # Generate PDF using WeasyPrint
    pdf_filename = f"Resume_{name_slug}_{company_slug}.pdf"
    pdf_path = os.path.join(output_dir, pdf_filename)

    try:
        from weasyprint import HTML
        HTML(string=html).write_pdf(pdf_path)
        logger.info(f"Generated PDF resume: {pdf_path}")
        return pdf_path, pdf_filename
    except ImportError:
        logger.warning("WeasyPrint not installed. Falling back to HTML-only output.")
        return html_path, html_filename
    except Exception as e:
        logger.error(f"PDF generation failed: {e}. Returning HTML.")
        return html_path, html_filename


def generate_pdf_cover_letter(
    profile: Dict,
    application: Dict,
    job: Dict,
    output_dir: str = None,
) -> Tuple[Optional[str], Optional[str]]:
    """Generate ATS-optimized PDF cover letter."""
    output_dir = output_dir or OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)

    cover_letter = str(application.get("cover_letter") or "").strip()
    if len(cover_letter) < 50:
        return None, None

    name = profile.get("name", "Atharva Vaidya")
    email = profile.get("email", "")
    linkedin = profile.get("linkedin_url", "")
    linkedin_display = linkedin.replace("https://", "").replace("http://", "").rstrip("/") if linkedin else ""
    location = profile.get("location", "Phoenix, AZ")

    # Build paragraphs
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n+", cover_letter) if len(p.strip()) > 20]
    para_html = "\n".join(f"    <p style='margin: 0 0 14px; font-size: 11px; line-height: 1.7; color: #333;'>{_html_escape(_ats_normalize(p))}</p>" for p in paragraphs)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=DM+Sans:wght@400;500;600;700&display=swap');
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: 'DM Sans', sans-serif; font-size: 11px; line-height: 1.5; color: #1a1a2e; background: #fff; }}
  .page {{ max-width: 8.5in; margin: 0 auto; padding: 0.8in 1in; }}
  .header h1 {{ font-family: 'Space Grotesk', sans-serif; font-size: 24px; font-weight: 700; margin-bottom: 4px; }}
  .header-gradient {{ height: 2px; background: linear-gradient(to right, hsl(187, 74%, 32%), hsl(270, 70%, 45%)); margin-bottom: 8px; }}
  .contact-row {{ font-size: 10px; color: #555; margin-bottom: 20px; }}
  .contact-row a {{ color: #555; text-decoration: none; }}
</style>
</head>
<body>
<div class="page">
  <div class="header">
    <h1>{_html_escape(name)}</h1>
    <div class="header-gradient"></div>
    <div class="contact-row">
      {_html_escape(email)} | <a href="{_html_escape(linkedin)}">{_html_escape(linkedin_display)}</a> | {_html_escape(location)}
    </div>
  </div>
  <div style="margin-top: 20px;">
{para_html}
  </div>
</div>
</body>
</html>"""

    company_slug = re.sub(r"[^a-zA-Z0-9]+", "_", job.get("company", "Unknown")).strip("_")
    name_slug = re.sub(r"[^a-zA-Z0-9]+", "_", name).strip("_")

    pdf_filename = f"CoverLetter_{name_slug}_{company_slug}.pdf"
    pdf_path = os.path.join(output_dir, pdf_filename)

    try:
        from weasyprint import HTML
        HTML(string=html).write_pdf(pdf_path)
        logger.info(f"Generated PDF cover letter: {pdf_path}")
        return pdf_path, pdf_filename
    except ImportError:
        html_filename = f"cl_{name_slug}_{company_slug}.html"
        html_path = os.path.join(output_dir, html_filename)
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
        return html_path, html_filename
    except Exception as e:
        logger.error(f"PDF cover letter generation failed: {e}")
        html_filename = f"cl_{name_slug}_{company_slug}.html"
        html_path = os.path.join(output_dir, html_filename)
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
        return html_path, html_filename

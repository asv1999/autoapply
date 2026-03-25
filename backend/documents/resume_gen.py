"""Document generator for tailored resumes and cover letters."""
import json
import logging
import os
import re

from docx import Document
from docx.shared import Inches, Pt, RGBColor

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
TEMPLATE_DIR = os.path.join(BASE_DIR, "data", "profiles")
OUTPUT_DIR = os.path.join(BASE_DIR, "data", "outputs", "resumes")
TEMPLATE_NAME = "resume_template.docx"

# These paragraph indices map to the user's existing resume template structure.
BULLET_MAP = {
    "digitech": [3, 4],
    "asu": [7, 8, 9],
    "vaxom": [12, 13],
    "nccl": [16, 17],
    "vertiv": [21],
    "km_capital": [24],
    "scdi": [27, 28],
    "gcn": [32, 33],
}


def _get_template_path():
    path = os.path.join(TEMPLATE_DIR, TEMPLATE_NAME)
    if os.path.exists(path):
        return path
    for alt in (
        os.path.join(BASE_DIR, "resume_template.docx"),
        os.path.join(TEMPLATE_DIR, "Atharva_Vaidya_Resume.docx"),
    ):
        if os.path.exists(alt):
            return alt
    return None


def _replace_bullet_text(paragraph, new_text):
    if not paragraph.runs:
        paragraph.add_run(new_text)
        return
    first_run = paragraph.runs[0]
    for run in paragraph.runs[1:]:
        run.text = ""
    first_run.text = new_text


def _normalize_bullets(application):
    bullets = application.get("tailored_bullets", {})
    if isinstance(bullets, str):
        try:
            bullets = json.loads(bullets)
        except Exception:
            bullets = {}
    return bullets


def _has_content(bullets):
    return any(
        isinstance(values, list) and values and any(len(str(item)) > 20 for item in values)
        for values in bullets.values()
    )


def _company_slug(job):
    return re.sub(r"[^a-zA-Z0-9]", "_", job.get("company", "Unknown"))


def _name_slug(profile):
    return profile.get("name", "").replace(" ", "_") or "Candidate"


def generate_resume(profile, application, job, output_dir=None):
    output_dir = output_dir or OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)

    bullets = _normalize_bullets(application)
    template_path = _get_template_path()
    if template_path and _has_content(bullets):
        doc = Document(template_path)
        paragraphs = doc.paragraphs
        for section_name, paragraph_indexes in BULLET_MAP.items():
            section_bullets = bullets.get(section_name, [])
            if not isinstance(section_bullets, list):
                continue
            for bullet_idx, paragraph_idx in enumerate(paragraph_indexes):
                if paragraph_idx >= len(paragraphs) or bullet_idx >= len(section_bullets):
                    continue
                bullet = section_bullets[bullet_idx]
                if bullet and len(str(bullet)) > 20:
                    _replace_bullet_text(paragraphs[paragraph_idx], str(bullet))
        filename = f"Resume_{_name_slug(profile)}_{_company_slug(job)}.docx"
        filepath = os.path.join(output_dir, filename)
        doc.save(filepath)
        return filepath, filename

    logger.warning("Using fallback resume generation for application %s", application.get("id"))
    return _generate_fallback(profile, application, job, output_dir)


def _generate_fallback(profile, application, job, output_dir):
    doc = Document()
    for section in doc.sections:
        section.top_margin = Inches(0.6)
        section.bottom_margin = Inches(0.6)
        section.left_margin = Inches(0.6)
        section.right_margin = Inches(0.6)

    header = doc.add_paragraph()
    header.alignment = 1
    run = header.add_run(profile.get("name", ""))
    run.font.size = Pt(14)
    run.font.bold = True
    run.font.name = "Garamond"
    run.font.color.rgb = RGBColor(0x1A, 0x1A, 0x2E)

    parts = [value for value in (profile.get("location"), profile.get("email"), profile.get("phone")) if value]
    contact = doc.add_paragraph()
    contact.alignment = 1
    run = contact.add_run(" | ".join(parts))
    run.font.size = Pt(8)
    run.font.name = "Garamond"
    run.font.color.rgb = RGBColor(0x49, 0x50, 0x57)

    doc.add_paragraph()
    note = doc.add_paragraph()
    run = note.add_run(f"Tailored for: {job.get('title', '')} at {job.get('company', '')}")
    run.font.size = Pt(10)
    run.font.italic = True
    run.font.name = "Garamond"

    bullets = _normalize_bullets(application)
    for section_name, values in bullets.items():
        if not isinstance(values, list) or not values:
            continue
        title = doc.add_paragraph()
        run = title.add_run(section_name.replace("_", " ").title())
        run.font.bold = True
        run.font.size = Pt(11)
        run.font.name = "Garamond"
        for value in values:
            doc.add_paragraph(str(value), style="List Bullet")

    filename = f"Resume_{_name_slug(profile)}_{_company_slug(job)}.docx"
    filepath = os.path.join(output_dir, filename)
    doc.save(filepath)
    return filepath, filename


def generate_cover_letter(profile, application, job, output_dir=None):
    output_dir = output_dir or OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)

    cover_letter = application.get("cover_letter", "")
    if not cover_letter or len(cover_letter.strip()) < 50:
        return None, None

    doc = Document()
    for section in doc.sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)

    name = doc.add_paragraph()
    run = name.add_run(profile.get("name", ""))
    run.font.size = Pt(14)
    run.font.bold = True
    run.font.name = "Garamond"
    run.font.color.rgb = RGBColor(0x1A, 0x1A, 0x2E)

    parts = [value for value in (profile.get("location"), profile.get("email"), profile.get("phone")) if value]
    contact = doc.add_paragraph()
    run = contact.add_run(" | ".join(parts))
    run.font.size = Pt(9)
    run.font.name = "Garamond"
    run.font.color.rgb = RGBColor(0x49, 0x50, 0x57)

    doc.add_paragraph()
    for paragraph in re.split(r"\n\n+", cover_letter):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        body = doc.add_paragraph()
        body.paragraph_format.space_after = Pt(8)
        run = body.add_run(paragraph)
        run.font.size = Pt(11)
        run.font.name = "Garamond"

    filename = f"CoverLetter_{_name_slug(profile)}_{_company_slug(job)}.docx"
    filepath = os.path.join(output_dir, filename)
    doc.save(filepath)
    return filepath, filename

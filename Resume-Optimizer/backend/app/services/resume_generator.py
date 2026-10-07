"""Shared structured-resume content with distinct Professional/Corporate rendering themes."""
from pathlib import Path
import re
from xml.sax.saxutils import escape, quoteattr

from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import HRFlowable, KeepTogether, ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer

TEMPLATES = {
    "professional": {"name": "Professional", "accent": "#0d766e", "docx_accent": RGBColor(13, 118, 110), "font": "Arial", "pdf_font": "Helvetica", "pdf_bold": "Helvetica-Bold", "name_align": "center", "font_size": 9.5, "space": 7, "heading_case": "title"},
    "corporate": {"name": "Corporate", "accent": "#253d55", "docx_accent": RGBColor(37, 61, 85), "font": "Times New Roman", "pdf_font": "Times-Roman", "pdf_bold": "Times-Bold", "name_align": "left", "font_size": 10, "space": 4, "heading_case": "upper"},
    "finance": {"name": "Finance", "accent": "#17365d", "docx_accent": RGBColor(23, 54, 93), "font": "Calibri", "pdf_font": "Helvetica", "pdf_bold": "Helvetica-Bold", "name_align": "left", "font_size": 9.5, "space": 8, "heading_case": "upper"},
    "fresher": {"name": "Fresher", "accent": "#6b4c7a", "docx_accent": RGBColor(107, 76, 122), "font": "Arial", "pdf_font": "Helvetica", "pdf_bold": "Helvetica-Bold", "name_align": "center", "font_size": 10, "space": 9, "heading_case": "title"},
}

SECTION_ORDER = [
    ("summary", "Professional Summary"), ("objective", "Objective"), ("experience", "Experience"), ("internships", "Internships"),
    ("projects", "Projects"), ("education", "Education"), ("skills", "Skills"),
    ("certifications", "Certifications"), ("achievements", "Achievements"),
    ("leadership", "Leadership"), ("awards", "Awards"), ("extracurricular", "Extracurricular Activities"),
    ("languages", "Languages"), ("publications", "Publications"), ("interests", "Interests"), ("other", "Additional Information"),
]
SKILL_LABELS = {"technical": "Technical", "tools": "Tools", "soft_skills": "Soft Skills", "domain": "Domain", "other": "Other Skills"}
_INTERNAL_SKILL_GROUPS = set(SKILL_LABELS)


def _as_list(value):
    if value is None: return []
    return value if isinstance(value, list) else [value]


def _safe(value):
    text = str(value).strip() if value is not None else ""
    text = re.sub(r"(?m)^\s*#{1,6}\s*", "", text)
    text = re.sub(r"\*\*(.+?)\*\*|__(.+?)__", lambda m: m.group(1) or m.group(2), text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"\1", text)
    text = re.sub(r"(?<!\\)\\([@._+-])", r"\1", text)
    text = re.sub(r"(?m)^\s*[-*]\s+", "", text)
    return text


def _skill_group_label(group: str) -> str:
    if group in SKILL_LABELS:
        return SKILL_LABELS[group]
    if group in _INTERNAL_SKILL_GROUPS:
        return group.replace("_", " ").title()
    return group


def _structured_resume(resume: dict) -> dict:
    """Normalize legacy and parser data to the renderer's supported schema."""
    data = dict(resume)
    for key in ("experience", "internships", "education", "projects"):
        values = _as_list(data.get(key))
        structured = []
        for value in values:
            if isinstance(value, dict):
                structured.append(dict(value))
            elif value:
                if key == "education": structured.append({"institution": str(value), "degree": "", "field": "", "start_date": "", "end_date": "", "grade": "", "other": []})
                elif key == "projects": structured.append({"name": str(value), "description": "", "technologies": [], "bullets": []})
                else: structured.append({"company": "", "role": str(value), "location": "", "start_date": "", "end_date": "", "bullets": [str(value)]})
        if key == "education":
            for item in structured:
                for internal in ("raw_text", "other", "metadata"):
                    item.pop(internal, None)
        data[key] = structured
    skills = data.get("skills", {})
    if isinstance(skills, list): data["skills"] = {"technical": skills}
    elif isinstance(skills, dict):
        normalized = {}
        for group, values in skills.items():
            label = re.sub(r"[_-]+", " ", str(group)).strip()
            clean_values = [clean for value in _as_list(values) if (clean := _safe(value)) and clean.casefold() not in {"tools:", "raw text:"}]
            if clean_values: normalized.setdefault(label, []).extend(clean_values)
        data["skills"] = normalized
    allowed = {key for key, _ in SECTION_ORDER} | {"personal_info", "headline", "section_order", "section_heading_labels", "source_lines", "format_signals", "sections_detected", "normalized_skills", "skill_category_labels", "legacy_skills", "contact_details"}
    for key in list(data):
        if key not in allowed: data.pop(key, None)
    data["_section_order"] = resume.get("section_order", [])
    return data


def _ordered_sections(data: dict, template_id: str = "professional"):
    by_key = {key: label for key, label in SECTION_ORDER}
    preferred = list(SECTION_ORDER)
    if template_id == "finance":
        priority = ["summary", "experience", "education", "skills", "projects"]
        preferred = sorted(SECTION_ORDER, key=lambda pair: priority.index(pair[0]) if pair[0] in priority else 50)
    elif template_id == "fresher":
        priority = ["objective", "education", "projects", "internships", "experience", "skills"]
        preferred = sorted(SECTION_ORDER, key=lambda pair: priority.index(pair[0]) if pair[0] in priority else 50)
    source_labels = data.get("section_heading_labels", {})
    def label_for(key):
        headings = source_labels.get(key, []) if isinstance(source_labels, dict) else []
        return headings[0] if headings else by_key[key]
    ordered = []
    for key in data.get("_section_order", []):
        if key in by_key and key not in [item[0] for item in ordered]:
            ordered.append((key, label_for(key)))
    ordered_keys = {key for key, _ in ordered}
    ordered.extend((key, label_for(key)) for key, _ in preferred if key not in ordered_keys)
    used = {key for key, _ in ordered}
    ignored = {"personal_info", "contact_details", "source_lines", "format_signals", "sections_detected", "section_heading_labels", "normalized_skills", "skill_category_labels", "legacy_skills", "_section_order", "section_order"}
    return ordered


def _entry_parts(item: dict, section: str) -> tuple[str, str, str, str, list[str], list[str]]:
    if section == "education":
        title = _safe(item.get("institution")); subtitle = _safe(item.get("degree") or item.get("field"))
        dates = _safe(item.get("dates")) or " – ".join(filter(None, [_safe(item.get("start_date")), _safe(item.get("end_date"))]))
        grade = item.get("gpa") or item.get("grade")
        extra = [_safe(grade)] if grade else []
        return title, subtitle, _safe(item.get("location")), dates, extra, []
    if section == "projects":
        title = _safe(item.get("name")); subtitle = ", ".join(_as_list(item.get("technologies")))
        description = _safe(item.get("description"))
        bullets = _as_list(item.get("bullets"))
        extra = [description] if description else []
        extra.extend(_safe(value) for value in _as_list(item.get("other")) if _safe(value))
        url = _safe(item.get("url") or item.get("link"))
        if url: extra.append("Link: " + url)
        return title, subtitle, "", "", extra, bullets
    role = _safe(item.get("job_title") or item.get("role") or item.get("title"))
    company = _safe(item.get("company") or item.get("employer") or item.get("organization"))
    title = role or company; subtitle = company if role else ""; location = _safe(item.get("location"))
    dates = _safe(item.get("dates")) or " – ".join(filter(None, [_safe(item.get("start_date")), _safe(item.get("end_date"))]))
    extra = []
    bullets = [_safe(value) for value in _as_list(item.get("bullets"))]
    for field in ("description", "responsibilities", "achievements"):
        bullets.extend(_safe(value) for value in _as_list(item.get(field)) if _safe(value))
    extra.extend(_safe(value) for value in _as_list(item.get("other")) if _safe(value))
    for field in ("technologies", "technology", "tech_stack"):
        tech = [_safe(value) for value in _as_list(item.get(field)) if _safe(value)]
        if tech: extra.append("Technologies: " + ", ".join(tech))
    return title, subtitle, location, dates, extra, bullets


def _generic_values(value):
    if isinstance(value, dict):
        return [f"{_safe(k).replace('_', ' ').title()}: {_safe(v)}" for k, v in value.items() if v not in (None, "", [], {})]
    if isinstance(value, list):
        lines = []
        for item in value:
            lines.extend(_generic_values(item) if isinstance(item, (dict, list)) else ([_safe(item)] if _safe(item) else []))
        return lines
    return [_safe(value)] if _safe(value) else []


def _contact_line(info: dict) -> str:
    links = info.get("links", [])
    linkedin = _safe(info.get("linkedin")) or next((url for url in links if "linkedin.com" in url.lower()), "")
    github = _safe(info.get("github")) or next((url for url in links if "github.com" in url.lower()), "")
    values = [_safe(info.get("email")), _safe(info.get("phone")), _safe(info.get("location")), linkedin, github]
    return " | ".join(dict.fromkeys(value for value in values if value))


def _contact_markup(info: dict) -> str:
    values = [(_safe(info.get("email")), ""), (_safe(info.get("phone")), ""),
              (_safe(info.get("location")), ""), (_safe(info.get("linkedin")), "https://"),
              (_safe(info.get("github")), "https://")]
    rendered = []
    for value, scheme in values:
        if not value:
            continue
        if scheme:
            href = value if value.lower().startswith(("http://", "https://")) else scheme + value
            rendered.append(f"<link href={quoteattr(href)} color='#53636a'>{escape(value)}</link>")
        else:
            rendered.append(escape(value))
    return " | ".join(dict.fromkeys(rendered))


def _visible_section_value(key: str, value, info: dict):
    """Drop contact facts already rendered in the header from catch-all content."""
    if key != "other":
        return value
    contacts = {item.casefold() for item in _contact_line(info).split(" | ") if item}
    contacts.add(_safe(info.get("location")).casefold())
    values = _generic_values(value)
    return [item for item in values if item.casefold() not in contacts
            and not re.search(r"(?:e-?mail|phone|linkedin|github)\s*[:|]|(?:linkedin\.com|github\.com)", item, re.I)]


def _has_section_content(value) -> bool:
    if isinstance(value, dict):
        return any(_has_section_content(item) for item in value.values())
    if isinstance(value, list):
        return any(_has_section_content(item) for item in value)
    return bool(_safe(value))


def render_docx(resume: dict, path: Path, template_id: str = "professional") -> None:
    if template_id not in TEMPLATES: raise ValueError("Unknown resume template.")
    theme = TEMPLATES[template_id]
    data = _structured_resume(resume)
    doc = Document()
    page = doc.sections[0]
    page.top_margin = Inches(.62 if template_id == "professional" else .55)
    page.bottom_margin = Inches(.62 if template_id == "professional" else .55)
    page.left_margin = Inches(.75); page.right_margin = Inches(.75)
    normal = doc.styles["Normal"]
    normal.font.name = theme["font"]; normal.font.size = Pt(theme["font_size"])
    normal.paragraph_format.space_after = Pt(3 if template_id == "professional" else 2)
    normal.paragraph_format.line_spacing = 1.05 if template_id == "corporate" else 1.1
    heading = doc.styles["Heading 1"]
    heading.font.name = theme["font"]; heading.font.size = Pt(10 if template_id == "professional" else 10.5)
    heading.font.bold = True; heading.font.color.rgb = theme["docx_accent"]
    heading.paragraph_format.space_before = Pt(theme["space"]); heading.paragraph_format.space_after = Pt(3)
    if "Resume Entry" not in doc.styles:
        entry_style = doc.styles.add_style("Resume Entry", WD_STYLE_TYPE.PARAGRAPH)
    else: entry_style = doc.styles["Resume Entry"]
    entry_style.base_style = normal
    entry_style.paragraph_format.space_after = Pt(1)

    info = data.get("personal_info", {})
    name = doc.add_paragraph(); name.alignment = WD_ALIGN_PARAGRAPH.CENTER if theme["name_align"] == "center" else WD_ALIGN_PARAGRAPH.LEFT
    name.paragraph_format.space_after = Pt(3)
    run = name.add_run(_safe(info.get("name")) or "Candidate"); run.bold = True; run.font.name = theme["font"]
    run.font.size = Pt(19 if template_id == "professional" else 17); run.font.color.rgb = theme["docx_accent"]
    contact = _contact_line(info)
    if contact:
        paragraph = doc.add_paragraph(contact); paragraph.alignment = name.alignment
        paragraph.paragraph_format.space_after = Pt(7)
    if template_id == "corporate":
        rule = doc.add_paragraph(); rule.paragraph_format.space_after = Pt(2)
        border = rule._element.get_or_add_pPr()
        from docx.oxml import OxmlElement
        p_borders = OxmlElement("w:pBdr"); bottom = OxmlElement("w:bottom")
        bottom.set(qn("w:val"), "single"); bottom.set(qn("w:sz"), "8"); bottom.set(qn("w:space"), "1"); bottom.set(qn("w:color"), "253D55")
        p_borders.append(bottom); border.append(p_borders)

    for key, label in _ordered_sections(data, template_id):
        value = _visible_section_value(key, data.get(key), info)
        if not _has_section_content(value): continue
        title = label.upper() if theme["heading_case"] == "upper" else label.title()
        doc.add_heading(title, level=1)
        if key == "summary":
            for paragraph_text in _as_list(value):
                if _safe(paragraph_text): doc.add_paragraph(_safe(paragraph_text))
        elif key == "skills":
            skills = value if isinstance(value, dict) else {"technical": _as_list(value)}
            for group, values in skills.items():
                values = _as_list(values)
                if not values: continue
                paragraph = doc.add_paragraph()
                label_run = paragraph.add_run(_skill_group_label(group) + ": "); label_run.bold = True
                paragraph.add_run(", ".join(_safe(skill) for skill in values))
        elif key in {"experience", "internships", "projects", "education"}:
            for item in _as_list(value):
                if not isinstance(item, dict): continue
                title_text, subtitle, location, dates, extra, bullets = _entry_parts(item, key)
                if not any((title_text, subtitle, location, dates, extra, bullets)): continue
                company_p = doc.add_paragraph(style="Resume Entry")
                company_p.paragraph_format.keep_with_next = bool(subtitle or dates)
                if title_text:
                    company_run = company_p.add_run(title_text); company_run.bold = True
                if dates:
                    company_p.paragraph_format.tab_stops.add_tab_stop(Inches(7), WD_TAB_ALIGNMENT.RIGHT)
                    date_run = company_p.add_run("\t" + dates); date_run.italic = template_id == "professional"
                if subtitle:
                    role_p = doc.add_paragraph(style="Resume Entry"); role_run = role_p.add_run(subtitle); role_run.bold = True
                    role_p.paragraph_format.keep_with_next = bool(bullets or extra)
                if location:
                    loc = doc.add_paragraph(location, style="Resume Entry")
                for line in extra:
                    if line: doc.add_paragraph(line, style="Resume Entry")
                for bullet in bullets:
                    if bullet: doc.add_paragraph(_safe(bullet), style="List Bullet")
        else:
            values = _generic_values(value)
            for item in values:
                if not item: continue
                doc.add_paragraph(_safe(item), style="List Bullet")
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(path)


def render_pdf(resume: dict, path: Path, template_id: str = "professional") -> None:
    if template_id not in TEMPLATES: raise ValueError("Unknown resume template.")
    theme = TEMPLATES[template_id]
    data = _structured_resume(resume)
    styles = getSampleStyleSheet()
    accent = colors.HexColor(theme["accent"])
    name_align = TA_CENTER if theme["name_align"] == "center" else TA_LEFT
    font = theme["pdf_font"]
    styles.add(ParagraphStyle(name="ResumeName", parent=styles["Title"], fontName=theme["pdf_bold"], fontSize=18 if template_id == "professional" else 16, leading=21, alignment=name_align, textColor=accent, spaceAfter=3))
    styles.add(ParagraphStyle(name="ResumeContact", parent=styles["Normal"], fontName=font, fontSize=8, leading=10, alignment=name_align, textColor=colors.HexColor("#53636a"), spaceAfter=7))
    styles.add(ParagraphStyle(name="ResumeHeading", parent=styles["Heading2"], fontName=theme["pdf_bold"], fontSize=10 if template_id == "professional" else 10.5, leading=12, textColor=accent, spaceBefore=theme["space"], spaceAfter=3, borderPadding=2))
    styles.add(ParagraphStyle(name="ResumeEntry", parent=styles["BodyText"], fontName=font, fontSize=9 if template_id == "professional" else 9.5, leading=11, spaceAfter=1))
    styles.add(ParagraphStyle(name="ResumeRole", parent=styles["ResumeEntry"], fontName=theme["pdf_bold"], spaceAfter=1))
    styles.add(ParagraphStyle(name="ResumeSmall", parent=styles["ResumeEntry"], fontSize=8, textColor=colors.HexColor("#65757a")))
    story = []
    info = data.get("personal_info", {})
    story.append(Paragraph(escape(_safe(info.get("name")) or "Candidate"), styles["ResumeName"]))
    contact = _contact_line(info)
    if contact: story.append(Paragraph(_contact_markup(info), styles["ResumeContact"]))
    if template_id == "corporate": story.append(HRFlowable(width="100%", thickness=1.2, color=accent, spaceAfter=3))

    for key, label in _ordered_sections(data, template_id):
        value = _visible_section_value(key, data.get(key), info)
        if not _has_section_content(value): continue
        title = label.upper() if theme["heading_case"] == "upper" else label.title()
        story.append(Paragraph(escape(title), styles["ResumeHeading"]))
        if key == "summary":
            story.extend(Paragraph(escape(_safe(paragraph)), styles["ResumeEntry"]) for paragraph in _as_list(value) if _safe(paragraph))
        elif key == "skills":
            skills = value if isinstance(value, dict) else {"technical": _as_list(value)}
            for group, values in skills.items():
                values = _as_list(values)
                if values:
                    label_text = _skill_group_label(group)
                    story.append(Paragraph(f"<b>{escape(label_text)}:</b> {escape(', '.join(map(_safe, values)))}", styles["ResumeEntry"]))
        elif key in {"experience", "internships", "projects", "education"}:
            for item in _as_list(value):
                if not isinstance(item, dict): continue
                title_text, subtitle, location, dates, extra, bullets = _entry_parts(item, key)
                chunks = []
                title_date = escape(title_text)
                if dates: title_date += f" <font color='{theme['accent']}' size='8'>· {escape(dates)}</font>"
                if title_date: chunks.append(Paragraph(f"<b>{title_date}</b>", styles["ResumeEntry"]))
                if subtitle: chunks.append(Paragraph(f"<b>{escape(subtitle)}</b>", styles["ResumeRole"]))
                if location: chunks.append(Paragraph(escape(location), styles["ResumeSmall"]))
                for line in extra:
                    if not line: continue
                    if line.startswith("Link: "):
                        url = line[6:].strip()
                        href = url if url.lower().startswith(("http://", "https://")) else "https://" + url
                        chunks.append(Paragraph(f"Link: <link href={quoteattr(href)} color='{theme['accent']}'>{escape(url)}</link>", styles["ResumeEntry"]))
                    else:
                        chunks.append(Paragraph(escape(line), styles["ResumeEntry"]))
                if bullets:
                    bullet_items = [ListItem(Paragraph(escape(_safe(bullet)), styles["ResumeEntry"]), leftIndent=10) for bullet in bullets if _safe(bullet)]
                    if bullet_items: chunks.append(ListFlowable(bullet_items, bulletType="bullet", leftIndent=15, bulletFontName=font, bulletFontSize=6))
                if chunks: story.append(KeepTogether(chunks)); story.append(Spacer(1, 2 if template_id == "professional" else 1))
        else:
            bullet_items = [ListItem(Paragraph(escape(_safe(item)), styles["ResumeEntry"]), leftIndent=10) for item in _generic_values(value) if _safe(item)]
            if bullet_items: story.append(ListFlowable(bullet_items, bulletType="bullet", leftIndent=15, bulletFontName=font, bulletFontSize=6))
    path.parent.mkdir(parents=True, exist_ok=True)
    SimpleDocTemplate(str(path), pagesize=LETTER, rightMargin=.68*inch, leftMargin=.68*inch,
                      topMargin=.55*inch if template_id == "corporate" else .62*inch,
                      bottomMargin=.55*inch if template_id == "corporate" else .62*inch).build(story)


def preview_text(resume: dict) -> dict:
    """Public structured preview mirrors exactly the sections consumed by both renderers."""
    internal = {"source_lines", "legacy_skills", "normalized_skills", "skill_category_labels", "format_signals", "section_heading_labels", "section_order", "_section_order"}
    return {key: value for key, value in _structured_resume(resume).items() if key not in internal}

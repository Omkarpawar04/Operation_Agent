"""Text extraction and conservative, layout-independent resume structure detection."""
import re
from pathlib import Path

import pymupdf
from docx import Document

from .keyword_extractor import normalize

SECTION_ALIASES = {
    "contact": {"contact", "contact information", "personal information", "personal details"},
    "summary": {"summary", "professional summary", "profile"},
    "objective": {"objective", "career objective"},
    "education": {"education", "academic background", "academic qualifications", "educational background"},
    "experience": {"experience", "work experience", "professional experience", "employment", "employment history"},
    "internships": {"internship", "internships", "internship experience", "internship experiences"},
    "projects": {"projects", "academic projects", "personal projects", "project experience"},
    "skills": {"skills", "technical skills", "technical & finance skills", "core competencies", "areas of expertise", "key skills"},
    "tools": {"tools", "tools & technologies", "technologies", "software"},
    "certifications": {"certifications", "licenses & certifications", "certificates", "licenses"},
    "achievements": {"achievements", "accomplishments"},
    "leadership": {"leadership", "achievements & leadership", "leadership & achievements"},
    "awards": {"awards", "honors"},
    "extracurricular": {"extracurricular", "extracurricular activities", "activities"},
    "languages": {"languages", "language skills"},
    "publications": {"publications", "papers"},
    "interests": {"interests", "hobbies"},
}
_HEADING_LOOKUP = {re.sub(r"[^a-z0-9]+", " ", alias).strip(): section for section, aliases in SECTION_ALIASES.items() for alias in aliases}
_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE = re.compile(r"(?:\+?\d[\d ().-]{7,}\d)")
_MONTH = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
_DATE = re.compile(rf"\b(?:{_MONTH}\s+)?(?:19|20)\d{{2}}\s*(?:[-–—]|to)\s*(?:{_MONTH}\s+)?(?:19|20)\d{{2}}|\b(?:{_MONTH}\s+)?(?:19|20)\d{{2}}\s*(?:[-–—]|to)\s*(?:present|current|now)\b", re.I)
_BULLET = re.compile(r"^\s*(?:[•●▪◦‣*-]|\d+[.)])\s*")
_DEGREE = re.compile(r"\b(?:M\.?CA|B\.?CA|M\.?Tech|B\.?Tech|B\.?[AS]|M\.?[AS]|MBA|Ph\.?D|Bachelor|Master|Diploma|BCom|BBA|BSc|BA|MCom|Associate|Doctor)\b", re.I)

TOOL_TERMS = {"excel", "ms excel", "microsoft excel", "power bi", "tableau", "sap", "bloomberg", "quickbooks", "google sheets", "capital iq", "factset"}
TECH_TERMS = {"sql", "python", "r", "java", "c++", "data analysis", "data analytics", "dashboard development", "statistics", "machine learning"}
SOFT_TERMS = {"communication", "leadership", "teamwork", "collaboration", "problem solving", "problem-solving", "attention to detail", "time management", "stakeholder management"}
DOMAIN_TERMS = {"financial analysis", "financial modeling", "financial modelling", "financial reporting", "forecasting", "budgeting", "variance analysis", "valuation", "cash flow", "risk assessment", "financial planning", "accounting", "business partnering", "equity research", "fp&a", "investment banking"}


def extract_text(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        with pymupdf.open(path) as pdf:
            text = "\n".join(page.get_text() for page in pdf)
    elif path.suffix.lower() == ".docx":
        doc = Document(path)
        def paragraph_text(paragraph):
            value = paragraph.text
            properties = paragraph._p.pPr
            is_list = bool(properties is not None and properties.numPr is not None)
            is_list = is_list or "list bullet" in (paragraph.style.name or "").casefold()
            return f"- {value}" if value.strip() and is_list else value
        text = "\n".join([paragraph_text(p) for p in doc.paragraphs] + [c.text for t in doc.tables for row in t.rows for c in row.cells])
    else:
        raise ValueError("Please upload a PDF or DOCX resume.")
    if not text.strip():
        raise ValueError("No readable text found. Please use a text-based PDF or DOCX file.")
    return text


def _clean_line(line: str) -> str:
    return re.sub(r"\s+", " ", line).strip()


def _heading(line: str) -> str | None:
    candidate = re.sub(r"^[\s#•*-]+|[\s:|]+$", "", line).lower()
    candidate = re.sub(r"[^a-z0-9]+", " ", candidate).strip()
    return _HEADING_LOOKUP.get(candidate)


def _structured_items(lines: list[str], section: str) -> tuple[list[dict], list[str]]:
    """Group entry headers and bullet text without relying on source formatting."""
    records: list[dict] = []
    unclassified: list[str] = []
    headers: list[str] = []
    current: dict | None = None

    def start_record(header_lines: list[str], date: str = "") -> dict:
        cleaned = []
        for value in header_lines:
            value = _DATE.sub("", value).strip(" |,–—-")
            if value:
                cleaned.append(value)
        if section != "education" and cleaned and re.search(r"\s+[^\w\s]+\s+", cleaned[0]):
            split_header = [part.strip() for part in re.split(r"\s+[^\w\s]+\s+", cleaned[0], maxsplit=1) if part.strip()]
            if len(split_header) == 2:
                cleaned = [*split_header, *cleaned[1:]]
        record = {"company": "", "role": "", "location": "", "start_date": "", "end_date": "", "bullets": [], "other": []}
        if cleaned:
            record["company"] = cleaned[0]
        if len(cleaned) > 1:
            record["role"] = cleaned[1]
            if section != "education" and re.search(r"\b(intern|analyst|manager|engineer|developer|assistant|associate|director|consultant|lead)\b", cleaned[0], re.I):
                record["role"], record["company"] = cleaned[0], cleaned[1]
        if len(cleaned) > 2:
            record["location"] = cleaned[2]
        if len(cleaned) > 3:
            record["other"].extend(cleaned[3:])
        if date:
            halves = re.split(r"\s*(?:-|–|—|to)\s*", date, maxsplit=1, flags=re.I)
            record["start_date"] = halves[0].strip()
            record["end_date"] = halves[1].strip() if len(halves) > 1 else ""
        return record

    def flush():
        nonlocal current
        if current:
            records.append(current)
        current = None

    for raw in lines:
        line = _clean_line(raw)
        bullet_match = _BULLET.match(line)
        content = _BULLET.sub("", line).strip()
        date_match = _DATE.search(content)
        if section == "education" and not date_match:
            date_match = re.search(r"\b(?:19|20)\d{2}\b", content)
        date_value = date_match.group(0) if date_match else ""
        without_date = _DATE.sub("", content).strip(" |,–—-") if date_match else content

        if section == "education":
            if not current:
                current = {"institution": "", "degree": "", "field": "", "start_date": "", "end_date": "", "dates": "", "grade": "", "gpa": "", "raw_text": "", "other": []}
            education_content = _DATE.sub("", content).strip(" |,–—-") if date_value else content
            degree_line = _DEGREE.search(education_content)
            if current["degree"] and degree_line:
                flush()
                current = {"institution": "", "degree": "", "field": "", "start_date": "", "end_date": "", "dates": "", "grade": "", "gpa": "", "raw_text": "", "other": []}
            current["raw_text"] = "\n".join(filter(None, [current.get("raw_text", ""), content]))
            if date_value:
                halves = re.split(r"\s*(?:-|–|—|to)\s*", date_value, maxsplit=1, flags=re.I)
                current["start_date"] = halves[0].strip(); current["end_date"] = halves[1].strip() if len(halves) > 1 else ""
                current["dates"] = date_value
            grade_match = re.search(r"\b(?:GPA|CGPA|grade|percentage|score)\s*[:=-]?\s*[0-9]+(?:\.[0-9]+)?(?:\s*/\s*[0-9]+(?:\.[0-9]+)?)?\s*%?", education_content, re.I)
            if grade_match:
                current["grade"] = grade_match.group(0).strip()
                current["gpa"] = current["grade"]
                education_content = (education_content[:grade_match.start()] + education_content[grade_match.end():]).strip(" |,–—-")
            if not education_content:
                continue
            if current["degree"] and current["institution"] and re.search(r"\b(university|college|institute|school)\b", education_content, re.I):
                flush()
                current = {"institution": education_content, "degree": "", "field": "", "start_date": "", "end_date": "", "dates": "", "grade": "", "gpa": "", "raw_text": "", "other": []}
                continue
            if _DEGREE.search(education_content):
                current["degree"] = education_content
                if date_value:
                    current["start_date"] = halves[0].strip(); current["end_date"] = halves[1].strip() if len(halves) > 1 else ""
                    current["dates"] = date_value
                field_match = re.search(r"\b(?:in|of)\s+(.+)$", education_content, re.I)
                if field_match:
                    current["field"] = field_match.group(1).strip()
                continue
            if not current["institution"]:
                if re.search(r"\b(university|college|school|institute|academy)\b", education_content, re.I):
                    current["institution"] = education_content
                else:
                    current["other"].append(education_content)
            elif not current["degree"] and not current["institution"].lower() == education_content.lower():
                # Plain-text degrees vary; retain the second line as a degree only when it resembles one.
                if re.search(r"\b(degree|commerce|economics|finance|computer|engineering|science|arts|business|management)\b", education_content, re.I):
                    current["degree"] = education_content
                else:
                    current["other"].append(education_content)
            else:
                current["other"].append(education_content)
            continue

        if bullet_match:
            if current is None:
                current = start_record(headers)
                headers = []
            current["bullets"].append(content)
            continue

        if date_match:
            if current and (current["bullets"] or current["company"] or current["role"]):
                flush()
            if without_date:
                headers.extend(value.strip() for value in re.split(r"\s*[|]\s*", without_date) if value.strip())
            current = start_record(headers, date_value)
            headers = []
            continue

        # A non-bullet line following bullets usually begins the next entry.
        if current and current["bullets"]:
            flush()
        headers.append(content)

    if headers:
        if current is None:
            current = start_record(headers)
        else:
            current["other"].extend(headers)
    flush()
    # Remove empty records; preserve their source lines as unclassified content.
    nonempty = []
    for record in records:
        if any(value for key, value in record.items() if key != "other") or record["other"]:
            nonempty.append(record)
    return nonempty, unclassified


def _classify_skill(skill: str) -> str:
    normalized = normalize(skill)
    if normalized in TOOL_TERMS:
        return "tools"
    if normalized in SOFT_TERMS:
        return "soft_skills"
    if normalized in DOMAIN_TERMS:
        return "domain"
    if normalized in TECH_TERMS:
        return "technical"
    return "other"


def _parse_skill_groups(lines: list[str]) -> dict[str, list[str]]:
    """Retain user-authored skill category labels and keep values separate."""
    explicit: dict[str, list[str]] = {}
    ungrouped: list[str] = []
    active_group = None
    has_explicit_groups = False

    def add_values(target: list[str], value: str):
        target.extend(item.strip() for item in re.split(r"[,|;•·]", value) if item.strip())

    for raw_line in lines:
        line = _BULLET.sub("", _clean_line(raw_line)).strip()
        plain_category = re.fullmatch(r"(?:financial skills|tools?\s*(?:&|and)\s*technologies|soft skills|technical skills)", line, re.I)
        if plain_category:
            has_explicit_groups = True
            active_group = line
            explicit.setdefault(line, [])
            continue
        category = re.match(r"^([^:]{2,80}):\s*(.*)$", line)
        if category:
            label = category.group(1).strip()
            if label:
                has_explicit_groups = True
                active_group = label
                group = explicit.setdefault(label, [])
                add_values(group, category.group(2))
                continue
        if active_group:
            add_values(explicit[active_group], line)
        else:
            add_values(ungrouped, line)

    if not has_explicit_groups:
        explicit = {}
        for skill in ungrouped:
            explicit.setdefault(_classify_skill(skill), []).append(skill)
    elif ungrouped:
        for skill in ungrouped:
            explicit.setdefault(_classify_skill(skill), []).append(skill)
    return explicit


def _project_items(lines: list[str]) -> list[dict]:
    projects = []
    pending: list[str] = []
    pending_tech: list[str] = []
    current = None

    def flush():
        nonlocal current
        if current and (current["name"] or current["description"] or current["bullets"]):
            projects.append(current)
        current = None

    for raw in lines:
        line = _clean_line(raw)
        bullet = bool(_BULLET.match(line))
        value = _BULLET.sub("", line).strip()
        if re.match(r"^(?:https?://|www\.)\S+", value, re.I):
            if current:
                current["url"] = value
            elif pending:
                current = {"name": pending[0], "description": " ".join(pending[1:]), "technologies": pending_tech, "bullets": [], "other": [], "url": value}
                pending = []
                pending_tech = []
            else:
                pending.append(value)
            continue
        if bullet:
            if current is None:
                current = {"name": pending[0] if pending else "", "description": " ".join(pending[1:]), "technologies": pending_tech, "bullets": [], "other": []}
                pending = []
                pending_tech = []
            current["bullets"].append(value)
        elif re.match(r"^(technologies|tools|stack)\s*:", value, re.I) and current:
            tech = re.sub(r"^(?:technologies|tools|stack)\s*:", "", value, flags=re.I)
            current["technologies"].extend(x.strip() for x in re.split(r"[,|;]", tech) if x.strip())
        elif re.match(r"^(technologies|tools|stack)\s*:", value, re.I):
            tech = re.sub(r"^(?:technologies|tools|stack)\s*:", "", value, flags=re.I)
            pending_tech.extend(x.strip() for x in re.split(r"[,|;]", tech) if x.strip())
        elif current and not current["bullets"]:
            current["description"] = (current["description"] + " " + value).strip()
        else:
            if current:
                flush()
            if pending:
                projects.append({"name": pending[0], "description": " ".join(pending[1:]), "technologies": pending_tech, "bullets": [], "other": []})
                pending = []
                pending_tech = []
            pending.append(value)
    if current:
        flush()
    elif pending:
        projects.append({"name": pending[0], "description": " ".join(pending[1:]), "technologies": pending_tech, "bullets": [], "other": []})
    return projects


def parse_resume(text: str) -> dict:
    raw_lines = text.replace("\r", "\n").splitlines()
    blank_line_count = sum(not line.strip() for line in raw_lines)
    lines = [_clean_line(line) for line in raw_lines]
    lines = [line for line in lines if line]
    buckets: dict[str, list[str]] = {key: [] for key in SECTION_ALIASES}
    other: list[str] = []
    detected: list[str] = []
    section_order: list[str] = []
    heading_labels: dict[str, list[str]] = {}
    custom_sections: dict[str, list[str]] = {}
    current = None
    preamble: list[str] = []
    for line in lines:
        # A colon-terminated label inside Skills is a user category, including
        # "Tools:", which otherwise aliases a top-level section heading.
        skill_category_line = current == "skills" and bool(
            re.match(r"^[^:]{2,80}:\s*", line)
            or re.fullmatch(r"(?:financial skills|tools?\s*(?:&|and)\s*technologies|soft skills|technical skills)", line, re.I)
        )
        key = None if skill_category_line else _heading(line)
        if not key and current and len(line.split()) <= 5 and len(line) <= 64 and re.fullmatch(r"[A-Z][A-Z &/-]*", line):
            is_heading = True
            if is_heading:
                slug = re.sub(r"[^a-z0-9]+", "_", line.lower()).strip("_") or "custom_section"
                if slug not in buckets and slug not in custom_sections:
                    custom_sections[slug] = []
                    heading_labels[slug] = [line.strip(" #:-")]
                    section_order.append(slug)
                    current = slug
                    continue
        if key:
            current = key
            heading_labels.setdefault(key, []).append(line.strip(" #:-"))
            if key not in detected:
                detected.append(key)
                section_order.append(key)
            continue
        if current:
            if current in buckets:
                buckets[current].append(line)
            else:
                custom_sections.setdefault(current, []).append(line)
        else:
            preamble.append(line)

    emails = _EMAIL.findall(text)
    phones = [phone for phone in _PHONE.findall(text) if len(re.sub(r"\D", "", phone)) >= 9]
    links = re.findall(r"(?:https?://)?(?:www\.)?(?:linkedin\.com/in/|github\.com/)[^\s,;]+", text, re.I)
    linkedin = next((url for url in links if "linkedin.com" in url.lower()), "")
    github = next((url for url in links if "github.com" in url.lower()), "")
    name_lines = preamble + buckets["contact"]
    name = next((candidate for line in name_lines[:10]
                 if (candidate := re.sub(r"^(?:name|candidate)\s*[:|-]\s*", "", line, flags=re.I))
                 and "@" not in candidate and not re.search(r"\d{4,}", candidate)
                 and 1 < len(candidate.split()) <= 5
                 and not re.search(r"linkedin|github|resume|curriculum vitae|contact information|personal details", candidate, re.I)), "")
    location = ""
    for line in name_lines:
        candidate = _EMAIL.sub("", line)
        candidate = _PHONE.sub("", candidate)
        candidate = re.sub(r"(?:https?://)?(?:www\.)?(?:linkedin\.com/in/|github\.com/)[^\s,;]+", "", candidate, flags=re.I)
        candidate = candidate.strip(" |,;·")
        if candidate != name and re.search(r"\b(city|street|road|india|usa|uk|california|mumbai|delhi|pune|maharashtra|london|new york)\b", candidate, re.I):
            location = candidate
            break

    skills = _parse_skill_groups(buckets["skills"] + buckets["tools"])
    raw_skills = [skill for values in skills.values() for skill in values]
    normalized_skills = list(dict.fromkeys(normalize(skill) for skill in raw_skills if normalize(skill)))
    skill_category_labels = list(dict.fromkeys(
        match.group(1).strip()
        for line in buckets["skills"] + buckets["tools"]
        if (match := re.match(r"^([^:]{2,80}):\s*", _BULLET.sub("", line).strip()))
    ))

    experience, exp_other = _structured_items(buckets["experience"], "experience")
    internships, intern_other = _structured_items(buckets["internships"], "internships")
    education, _ = _structured_items(buckets["education"], "education")
    projects = _project_items(buckets["projects"])
    for source_lines in (exp_other, intern_other):
        other.extend(source_lines)
    # Preserve sections whose content has not yet been semantically modeled.
    other.extend(f"{section}: {line}" for section in ("publications", "interests") for line in buckets[section])
    for line in preamble:
        residual = _EMAIL.sub("", line)
        residual = _PHONE.sub("", residual)
        residual = re.sub(r"(?:https?://)?(?:www\.)?(?:linkedin\.com/in/|github\.com/)[^\s,;]+", "", residual, flags=re.I)
        residual = residual.strip(" |,;·")
        if (residual and residual != name and residual != location and line not in links
                and not re.search(r"linkedin\.com|github\.com", line, re.I)
                and not _EMAIL.search(line) and not _PHONE.search(line)):
            other.append(residual)
    structured = {
        "personal_info": {"name": name, "email": emails[0] if emails else "", "phone": phones[0].strip() if phones else "", "location": location, "linkedin": linkedin, "github": github, "links": links},
        "contact_details": buckets["contact"],
        "summary": " ".join(buckets["summary"]), "objective": " ".join(buckets["objective"]),
        "experience": experience, "internships": internships, "education": education,
        "projects": projects,
        "skills": skills,
        "normalized_skills": normalized_skills,
        "skill_category_labels": skill_category_labels,
        "certifications": [_BULLET.sub("", line).strip() for line in buckets["certifications"] if _BULLET.sub("", line).strip()], "achievements": [_BULLET.sub("", line).strip() for line in buckets["achievements"] if _BULLET.sub("", line).strip()],
        "leadership": buckets["leadership"], "awards": buckets["awards"],
        "extracurricular": buckets["extracurricular"],
        "languages": [_BULLET.sub("", line).strip() for line in buckets["languages"] if _BULLET.sub("", line).strip()], "publications": buckets["publications"], "interests": buckets["interests"],
        "other": other, "sections_detected": detected, "section_order": section_order, "section_heading_labels": heading_labels,
        "format_signals": {"blank_line_count": blank_line_count, "nonempty_line_count": len(lines),
                           "bullet_styles": list(dict.fromkeys(match.group(0).strip() for line in lines if (match := _BULLET.match(line))))},
        "source_lines": lines,
        # Compatibility fields are retained for existing API consumers.
        "legacy_skills": raw_skills,
    }
    structured.update(custom_sections)
    return structured

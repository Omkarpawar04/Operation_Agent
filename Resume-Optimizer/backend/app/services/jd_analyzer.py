"""Convert a job description into transparent, typed requirement records."""
import re
from typing import Any

from .keyword_extractor import (
    classify_importance,
    classify_requirement,
    extract_candidate_phrases,
    extract_proficiency,
    extract_terms,
    normalize,
)

_SECTION_ALIASES = {
    "required": {
        "requirements", "required qualifications", "qualifications",
        "minimum qualifications", "what you need", "what you'll need",
        "key requirements", "basic qualifications",
    },
    "preferred": {
        "preferred qualifications", "preferred skills", "nice to have",
        "bonus qualifications", "desired qualifications", "bonus skills",
    },
    "optional": {
        "optional", "optional qualifications",
    },
    "responsibilities": {
        "responsibilities", "what you ll do", "what you will do",
        "duties", "key responsibilities", "role responsibilities",
    },
    "certifications": {
        "certifications", "licenses", "licenses and certifications",
    },
}

_DISPLAY_NAMES = {
    "excel": "Excel",
    "power bi": "Power BI",
    "sql": "SQL",
    "python": "Python",
    "tableau": "Tableau",
    "r": "R",
    "sap": "SAP",
    "bloomberg": "Bloomberg",
    "quickbooks": "QuickBooks",
    "git": "Git",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "aws": "AWS",
    "azure": "Azure",
    "jira": "Jira",
    "mysql": "MySQL",
    "postgresql": "PostgreSQL",
    "rest apis": "REST APIs",
    "fp&a": "FP&A",
    "cfa": "CFA",
    "cpa": "CPA",
    "pmp": "PMP",
    "financial modeling": "Financial Modeling",
    "financial analysis": "Financial Analysis",
    "financial reporting": "Financial Reporting",
    "financial planning": "Financial Planning",
    "forecasting": "Forecasting",
    "budgeting": "Budgeting",
    "variance analysis": "Variance Analysis",
    "data analysis": "Data Analysis",
    "accounting": "Accounting",
    "valuation": "Valuation",
    "cash flow analysis": "Cash Flow Analysis",
    "business partnering": "Business Partnering",
    "business analysis": "Business Analysis",
}


def _section_for(line: str) -> str | None:
    clean = re.sub(r"[^a-z0-9 ]", " ", line.lower()).strip()
    clean = re.sub(r"\s+", " ", clean)
    for section, aliases in _SECTION_ALIASES.items():
        if clean in {re.sub(r"[^a-z0-9 ]", " ", alias.lower()).strip() for alias in aliases}:
            return section
    return None


def _canonical_name(raw_name: str, norm_key: str) -> str:
    """Format display name cleanly using known display map or title casing."""
    if norm_key in _DISPLAY_NAMES:
        return _DISPLAY_NAMES[norm_key]
    # Clean up prefixes like 'advanced' if already stripped in normalization
    cleaned = re.sub(r"^(?:advanced|intermediate|basic|expert)\s+", "", raw_name, flags=re.I).strip()
    cleaned = re.sub(r"\s+(?:fundamentals|basics)$", "", cleaned, flags=re.I).strip()
    if normalize(cleaned) in _DISPLAY_NAMES:
        return _DISPLAY_NAMES[normalize(cleaned)]
    return raw_name.title() if raw_name.islower() or raw_name.isupper() else raw_name


def _build_requirement(
    name: str,
    evidence: str,
    source: str,
    importance: str,
    kind: str | None = None,
    proficiency: str | None = None,
) -> dict[str, Any]:
    norm = normalize(name)
    req_type = kind or classify_requirement(name, evidence)
    canonical = _canonical_name(name, norm)
    prof = proficiency or extract_proficiency(evidence) or extract_proficiency(name)

    rec: dict[str, Any] = {
        "name": canonical,
        "normalized_name": norm,
        "type": req_type,
        "importance": importance,
        "source": source,
        "evidence": evidence.strip(),
    }
    if prof:
        rec["proficiency"] = prof
    return rec


def analyze_job(job: dict[str, Any]) -> dict[str, Any]:
    """Parse and normalize all JD fields into structured, typed requirements.
    
    Processes:
      - description
      - required_skills
      - preferred_skills
      - responsibilities
      - education
    """
    if not isinstance(job, dict):
        raise ValueError("Job must be a dictionary.")

    title = str(job.get("title") or "").strip()
    company = str(job.get("company") or "").strip()
    job_id = str(job.get("job_id") or "").strip()
    text = str(job.get("description") or "").strip()

    raw_required_skills = [str(s).strip() for s in job.get("required_skills", []) if str(s).strip()]
    raw_preferred_skills = [str(s).strip() for s in job.get("preferred_skills", []) if str(s).strip()]
    raw_responsibilities = [str(r).strip() for r in job.get("responsibilities", []) if str(r).strip()]
    education_data = job.get("education") or {}

    if not text and not raw_required_skills and not raw_responsibilities:
        raise ValueError("This job description is empty.")

    requirements: list[dict[str, Any]] = []
    seen_normalized: set[str] = set()

    # 1. Process structured required_skills
    for skill_text in raw_required_skills:
        norm = normalize(skill_text)
        if norm and norm not in seen_normalized:
            req = _build_requirement(
                name=skill_text,
                evidence=skill_text,
                source="required_skills",
                importance="required",
            )
            requirements.append(req)
            seen_normalized.add(norm)

    # 2. Process structured preferred_skills
    for skill_text in raw_preferred_skills:
        norm = normalize(skill_text)
        if norm and norm not in seen_normalized:
            req = _build_requirement(
                name=skill_text,
                evidence=skill_text,
                source="preferred_skills",
                importance="preferred",
            )
            requirements.append(req)
            seen_normalized.add(norm)

    # 3. Process structured responsibilities
    responsibilities_list: list[str] = []
    for resp_line in raw_responsibilities:
        responsibilities_list.append(resp_line)
        requirements.append(_build_requirement(
            name=resp_line,
            evidence=resp_line,
            source="responsibilities",
            importance="required",
            kind="responsibility",
        ))

    # 4. Process structured education
    qualifications_list: list[str] = []
    if isinstance(education_data, dict):
        min_degree = str(education_data.get("minimum_degree") or "").strip()
        if min_degree:
            qualifications_list.append(min_degree)
            requirements.append(_build_requirement(
                name=min_degree,
                evidence=min_degree,
                source="education",
                importance="required",
                kind="education",
            ))
        for field in education_data.get("fields", []):
            field_str = str(field).strip()
            if field_str:
                qualifications_list.append(field_str)
                requirements.append(_build_requirement(
                    name=field_str,
                    evidence=f"Education field: {field_str}",
                    source="education",
                    importance="required",
                    kind="education",
                ))
    elif isinstance(education_data, str) and education_data.strip():
        qualifications_list.append(education_data.strip())
        requirements.append(_build_requirement(
            name=education_data.strip(),
            evidence=education_data.strip(),
            source="education",
            importance="required",
            kind="education",
        ))

    # 5. Parse description text for sections and additional terms
    lines = [line.strip(" •-\t") for line in text.splitlines() if line.strip()]
    active_section = "unknown"
    context_by_line: list[tuple[str, str]] = []
    certifications: list[str] = []

    for line in lines:
        detected_section = _section_for(line)
        if detected_section:
            active_section = detected_section
            continue
        context_by_line.append((line, active_section))

        if not raw_responsibilities and active_section == "responsibilities":
            responsibilities_list.append(line)
            requirements.append(_build_requirement(
                name=line,
                evidence=line,
                source="description",
                importance="required",
                kind="responsibility",
            ))
        elif not qualifications_list and active_section in {"required", "preferred", "optional"} and (
            line.startswith(("•", "-")) or len(line.split()) > 4
        ):
            qualifications_list.append(line)
        elif active_section == "certifications":
            certifications.append(line)
            requirements.append(_build_requirement(
                name=line,
                evidence=line,
                source="description",
                importance=classify_importance(line, active_section),
                kind="certification",
            ))

    # Controlled vocabulary terms from text
    for line, section in context_by_line:
        for term in extract_terms(line):
            key = normalize(term)
            if key not in seen_normalized:
                importance = "preferred" if section == "preferred" else classify_importance(line, section)
                requirements.append(_build_requirement(
                    name=term,
                    evidence=line,
                    source="description",
                    importance=importance,
                ))
                seen_normalized.add(key)

    # Cue-based candidate phrases from description
    for candidate in extract_candidate_phrases(text):
        key = candidate["normalized_name"]
        if key not in seen_normalized:
            source_line = next(
                (line for line, _ in context_by_line if candidate["evidence"].lower() in line.lower()),
                candidate["evidence"],
            )
            section = next((s for line, s in context_by_line if source_line == line), "unknown")
            importance = "preferred" if section == "preferred" else classify_importance(source_line, section)
            requirements.append(_build_requirement(
                name=candidate["name"],
                evidence=source_line,
                source="description",
                importance=importance,
            ))
            seen_normalized.add(key)

    skill_requirements = [
        r for r in requirements
        if r.get("type") in {"tool", "technical_skill", "domain_skill", "soft_skill"}
    ]
    other_requirements = [
        r for r in requirements
        if r.get("type") not in {"tool", "technical_skill", "domain_skill", "soft_skill"}
    ]

    required_skill_names = [r["name"] for r in skill_requirements if r.get("importance") == "required"]
    preferred_skill_names = [r["name"] for r in skill_requirements if r.get("importance") == "preferred"]

    # Infer domain / industry tag in a general way
    combined_text = f"{title} {text}".lower()
    if re.search(r"\b(finance|financial|accounting|investment|equity|banking|fp&a)\b", combined_text):
        industry = "finance"
    elif re.search(r"\b(software|developer|engineer|fullstack|backend|frontend|devops)\b", combined_text):
        industry = "technology"
    elif re.search(r"\b(marketing|seo|growth|content|branding)\b", combined_text):
        industry = "marketing"
    else:
        industry = "general"

    return {
        "title": title,
        "company": company,
        "job_id": job_id,
        "industry": industry,
        "requirements": requirements,
        "required_skills": required_skill_names,
        "required_only_skills": required_skill_names,
        "preferred_skills": preferred_skill_names,
        "technical_skills": [r["name"] for r in skill_requirements if r.get("type") == "technical_skill"],
        "domain_skills": [r["name"] for r in skill_requirements if r.get("type") == "domain_skill"],
        "soft_skills": [r["name"] for r in skill_requirements if r.get("type") == "soft_skill"],
        "tools": [r["name"] for r in skill_requirements if r.get("type") == "tool"],
        "qualifications": qualifications_list,
        "responsibilities": responsibilities_list,
        "certifications": certifications,
        "education": education_data,
        "industry_requirements": [r for r in skill_requirements if industry in ("finance", "technology")],
        "education_requirements": [r for r in other_requirements if r.get("type") == "education"],
        "experience_requirements": [r for r in other_requirements if r.get("type") == "experience"],
        "preferred_requirements": [r for r in requirements if r.get("importance") == "preferred"],
        "keywords": [r["name"] for r in skill_requirements],
    }

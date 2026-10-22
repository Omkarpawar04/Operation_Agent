"""Transparent exact/alias/known-related matching with source-line evidence."""
import re
from typing import Any

from .keyword_extractor import ALIASES, normalize

RELATED: dict[str, set[str]] = {
    "financial analysis": {
        "sales and expense analysis", "financial statements", "variance analysis",
        "data analysis", "financial performance",
    },
    "financial modeling": {
        "financial analysis", "valuation", "excel models", "projections",
    },
    "financial reporting": {
        "financial statements", "management reporting", "recurring reports",
        "operating expenses", "revenue and expenses", "management reports",
    },
    "forecasting": {
        "budgeting", "financial analysis", "financial planning", "projections", "forecasts",
    },
    "budgeting": {
        "forecasting", "financial planning", "planned expenses", "expense planning",
    },
    "data analysis": {
        "financial analysis", "variance analysis", "data insights", "analytics",
    },
    "variance analysis": {
        "planned vs actual", "planned and actual", "actual vs budget",
        "actual expenses with planned expenses", "budgeted results", "variances",
    },
    "financial planning": {
        "budgeting", "forecasting", "strategic planning",
    },
    "accounting": {
        "basic accounting", "financial statements", "bookkeeping", "general ledger",
        "introduction to accounting", "accounting fundamentals",
    },
    "valuation": {
        "financial modeling", "dcf", "comparables", "equity research",
    },
    "cash flow analysis": {
        "cash flow", "liquidity", "working capital",
    },
    "business partnering": {
        "stakeholder management", "cross functional collaboration", "team collaboration",
    },
    "business analysis": {
        "requirements analysis", "business insights", "data analysis",
    },
    "rest apis": {
        "web services", "api endpoints", "backend services", "fastapi", "flask",
    },
    "git": {
        "github", "gitlab", "version control",
    },
    "docker": {
        "containers", "containerization", "dockerfile",
    },
    "cloud": {
        "aws", "azure", "gcp",
    },
}

SKILL_TYPES = {"tool", "technical_skill", "domain_skill", "soft_skill"}


def _resume_lines(resume: dict[str, Any]) -> list[str]:
    """Extract candidate-facing text lines from resume."""
    lines: list[str] = []

    # Source lines or raw text
    raw_lines = resume.get("source_lines") or []
    if not raw_lines and resume.get("raw_text"):
        raw_lines = resume["raw_text"].splitlines()
    category_headers = {normalize(str(label)) for label in resume.get("skill_category_labels", [])}

    for line in raw_lines:
        s = str(line).strip(" •●▪◦‣*-\t\r\n")
        if s.rstrip(":").strip() and normalize(s.rstrip(":").strip()) in category_headers:
            continue
        if s and s not in lines:
            lines.append(s)

    # Experience & internship bullets
    for section_name in ("experience", "internships", "projects", "education"):
        for item in resume.get(section_name, []):
            if isinstance(item, dict):
                for bullet in item.get("bullets", []):
                    b = str(bullet).strip()
                    if b and b not in lines:
                        lines.append(b)
                desc = str(item.get("description") or "").strip()
                if desc and desc not in lines:
                    lines.append(desc)
                role = str(item.get("role") or "").strip()
                if role and role not in lines:
                    lines.append(role)
                company = str(item.get("company") or "").strip()
                if company and company not in lines:
                    lines.append(company)

    # Summary
    summary = str(resume.get("summary") or "").strip()
    if summary and summary not in lines:
        lines.append(summary)

    # Skills explicitly listed
    skills = resume.get("skills") or {}
    if isinstance(skills, dict):
        for group in skills.values():
            if isinstance(group, list):
                for sk in group:
                    s_str = str(sk).strip()
                    if s_str and s_str not in lines:
                        lines.append(s_str)
    elif isinstance(skills, list):
        for sk in skills:
            s_str = str(sk).strip()
            if s_str and s_str not in lines:
                lines.append(s_str)

    return lines


def _phrase_in_line(phrase: str, line: str) -> bool:
    """Case-insensitive exact word boundary search of phrase in line."""
    norm_p = normalize(phrase)
    norm_l = normalize(line)
    if not norm_p or not norm_l:
        return False
    pattern = r"(?<!\w)" + re.escape(norm_p) + r"(?!\w)"
    return bool(re.search(pattern, norm_l))


def _literal_phrase_in_line(phrase: str, line: str) -> bool:
    clean_p = re.sub(r"[^a-z0-9+# ]", " ", phrase.lower()).strip()
    clean_l = re.sub(r"[^a-z0-9+# ]", " ", line.lower())
    clean_l = re.sub(r"\s+", " ", clean_l)
    if not clean_p:
        return False
    pattern = r"(?<!\w)" + re.escape(clean_p) + r"(?!\w)"
    return bool(re.search(pattern, clean_l))


def _evidence_for(phrase: str, lines: list[str]) -> list[str]:
    """Find all unique lines in resume that evidence the target phrase or its aliases."""
    norm = normalize(phrase)
    variants = {phrase.lower(), norm}
    for alias, canonical in ALIASES.items():
        if normalize(canonical) == norm:
            variants.add(alias.lower())
            variants.add(normalize(alias))

    matches: list[str] = []
    for line in lines:
        if any(_phrase_in_line(v, line) or _literal_phrase_in_line(v, line) for v in variants):
            if line not in matches:
                matches.append(line)
    return matches


def _requirement_objects(job_analysis: dict[str, Any]) -> list[dict[str, Any]]:
    requirements = job_analysis.get("requirements")
    if requirements:
        return [item for item in requirements if item.get("type") in SKILL_TYPES]
    return [
        {
            "name": name,
            "normalized_name": normalize(name),
            "type": "domain_skill",
            "importance": "unknown",
        }
        for name in job_analysis.get("required_skills", [])
    ]


def match_resume(resume: dict[str, Any], job_analysis: dict[str, Any]) -> dict[str, Any]:
    """Deterministically match resume content against JD requirements.
    
    Produces transparent categories:
      MATCHED: Exact or alias match found with verifiable resume evidence.
      RELATED: Supporting context or related concept found with resume evidence.
      NOT DETECTED: No evidence found. Never hallucinated or assumed.
    """
    lines = _resume_lines(resume)
    matched: list[str] = []
    related: list[str] = []
    missing: list[str] = []
    items: list[dict[str, Any]] = []

    for req in _requirement_objects(job_analysis):
        name = req["name"]
        norm = req.get("normalized_name") or normalize(name)

        exact_evidence = _evidence_for(name, lines)
        if exact_evidence:
            aliases = {a for a, c in ALIASES.items() if normalize(c) == norm}
            alias_match = any(
                a != norm and _literal_phrase_in_line(a, line)
                for a in aliases
                for line in exact_evidence
            )
            status = "matched"
            match_type: str | None = "alias" if alias_match else "exact"
            evidence = exact_evidence
            matched.append(name)
        else:
            # Check related concepts
            related_terms = RELATED.get(norm, set())
            rel_evidence: list[str] = []
            for rel_term in related_terms:
                found_lines = _evidence_for(rel_term, lines)
                if found_lines:
                    for fl in found_lines:
                        if fl not in rel_evidence:
                            rel_evidence.append(fl)

            if rel_evidence:
                status = "related"
                match_type = "related"
                evidence = rel_evidence
                related.append(name)
            else:
                status = "not_detected"
                match_type = None
                evidence = []
                missing.append(name)

        items.append({
            "requirement": name,
            "normalized_name": norm,
            "type": req.get("type", "other"),
            "importance": req.get("importance", "unknown"),
            "status": status,
            "match_type": match_type,
            "evidence": evidence,
        })

    counts = {
        "matched": len(matched),
        "related": len(related),
        "missing": len(missing),
    }

    return {
        "matched": matched,
        "related": related,
        "missing": missing,
        "items": items,
        "resume_skills_detected": _all_skills(resume),
        "counts": counts,
    }


def _all_skills(resume: dict[str, Any]) -> list[str]:
    normalized = resume.get("normalized_skills")
    if isinstance(normalized, list):
        return normalized
    skills = resume.get("skills", [])
    if isinstance(skills, list):
        return skills
    if isinstance(skills, dict):
        return [skill for group in skills.values() if isinstance(group, list) for skill in group]
    return []

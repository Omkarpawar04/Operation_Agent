"""Post-optimization checks that prevent section loss or factual drift."""
from copy import deepcopy
from collections import Counter

from .keyword_extractor import normalize


CRITICAL_SECTIONS = (
    "education", "certifications", "achievements", "leadership", "awards",
    "projects", "experience", "internships", "publications", "interests",
    "languages", "extracurricular",
)


class ResumeValidationError(ValueError):
    pass


def validate_optimized_resume(original: dict, optimized: dict) -> dict:
    """Verify source facts before restoring critical fields as an immutable baseline."""
    safe = deepcopy(optimized)
    errors = []
    source_education = original.get("education", []) or []
    optimized_education = safe.get("education", []) or []
    for index, source in enumerate(source_education):
        candidate = optimized_education[index] if index < len(optimized_education) else {}
        def value(entry, key):
            return str(entry.get(key) or "").strip() if isinstance(entry, dict) else ""
        def canonical(text):
            return " ".join(text.lower().replace("–", "-").replace("—", "-").split())
        source_dates = value(source, "dates") or " - ".join(filter(None, [value(source, "start_date"), value(source, "end_date")]))
        candidate_dates = value(candidate, "dates") or " - ".join(filter(None, [value(candidate, "start_date"), value(candidate, "end_date")]))
        for label, source_value, candidate_value in (
            ("degree", value(source, "degree") or value(source, "field"), value(candidate, "degree") or value(candidate, "field")),
            ("institution", value(source, "institution"), value(candidate, "institution")),
            ("dates", source_dates, candidate_dates),
            ("GPA/CGPA", value(source, "gpa") or value(source, "grade"), value(candidate, "gpa") or value(candidate, "grade")),
        ):
            if source_value and canonical(source_value) != canonical(candidate_value):
                errors.append(f"education entry {index + 1} {label} missing or changed")
    if len(source_education) != len(optimized_education):
        errors.append("education entry count changed")
    source_skills = original.get("skills", {})
    candidate_skills = safe.get("skills", {})
    if isinstance(source_skills, dict):
        if not isinstance(candidate_skills, dict):
            errors.append("skills categories changed")
        else:
            for category, values in source_skills.items():
                if category not in candidate_skills:
                    errors.append(f"skills category '{category}' disappeared")
                    continue
                if not isinstance(values, list) or not isinstance(candidate_skills[category], list):
                    errors.append(f"skills category '{category}' has invalid structure")
                    continue
                source_counts = Counter(normalize(str(value)) for value in values)
                candidate_counts = Counter(normalize(str(value)) for value in candidate_skills[category])
                if source_counts != candidate_counts:
                    errors.append(f"skills in category '{category}' were changed, lost, or invented")
            for category in candidate_skills:
                if category not in source_skills:
                    errors.append(f"unsupported skills category '{category}' was added")
    for section in CRITICAL_SECTIONS:
        source = original.get(section, [])
        candidate = safe.get(section, [])
        # Preserve source section contents verbatim; rewriting can be applied to
        # prose sections, but these identity-bearing entries are never changed.
        if source and not candidate:
            errors.append(f"{section} section disappeared")
        if source:
            safe[section] = deepcopy(source)
    metadata = {
        "personal_info", "contact_details", "source_lines", "format_signals",
        "sections_detected", "section_heading_labels", "section_order",
        "normalized_skills", "skill_category_labels", "legacy_skills",
    }
    known_fields = set(CRITICAL_SECTIONS) | {
        "summary", "objective", "skills", "other",
    } | metadata
    for section, source in original.items():
        if section not in known_fields and source not in (None, "", [], {}):
            # Keep custom sections exactly as authored; AI may not know their schema.
            safe[section] = deepcopy(source)
    if original.get("personal_info") and safe.get("personal_info") != original.get("personal_info"):
        errors.append("personal information changed")
    if errors:
        raise ResumeValidationError("; ".join(dict.fromkeys(errors)))
    safe["section_order"] = list(original.get("section_order", []))
    if isinstance(source_skills, dict):
        safe["skills"] = deepcopy(source_skills)
        safe["normalized_skills"] = deepcopy(original.get("normalized_skills", []))
    return safe

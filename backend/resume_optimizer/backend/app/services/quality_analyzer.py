"""Rule-based, explainable resume quality checks; never reduces to an opaque score."""
import re


def analyze_resume_quality(resume: dict, matching: dict | None = None) -> dict:
    info = resume.get("personal_info", {})
    issues = []

    def issue(code: str, severity: str, message: str):
        issues.append({"code": code, "severity": severity, "message": message})

    if not info.get("name"):
        issue("missing_name", "high", "Add your name near the top of the resume.")
    if not info.get("email") and not info.get("phone"):
        issue("missing_contact", "high", "No email address or phone number was detected.")
    if not resume.get("summary"):
        issue("missing_summary", "medium", "Consider adding a concise professional summary or objective.")
    if not resume.get("education"):
        issue("missing_education", "medium", "No education section was detected.")
    if not resume.get("experience") and not resume.get("internships"):
        issue("missing_experience", "low", "No experience or internship entry was detected.")
    if not resume.get("projects"):
        issue("missing_projects", "low", "No project section was detected.")

    entries = [("experience", x) for x in resume.get("experience", [])] + [("internship", x) for x in resume.get("internships", [])]
    missing_role_company = 0
    missing_bullets = 0
    for kind, entry in entries:
        if not entry.get("company") or not entry.get("role"):
            missing_role_company += 1
        if not entry.get("bullets"):
            missing_bullets += 1
    if missing_role_company:
        issue("incomplete_experience_heading", "medium", f"{missing_role_company} experience/internship entry(ies) lack a clearly detected company or role.")
    if missing_bullets:
        issue("missing_experience_bullets", "medium", f"{missing_bullets} experience/internship entry(ies) have no detected bullet points.")
    if any(not project.get("bullets") and not project.get("description") for project in resume.get("projects", [])):
        issue("missing_project_description", "low", "At least one project has no detected description or bullet points.")

    lines = resume.get("source_lines", [])
    long_lines = [line for line in lines if len(line.split()) > 55]
    if long_lines:
        issue("long_paragraph", "low", f"{len(long_lines)} unusually long text line(s) may be harder to scan.")
    date_shapes = {"range" if re.search(r"[-–—]|\bto\b", line, re.I) else "single" for line in lines if re.search(r"\b(?:19|20)\d{2}\b", line)}
    if len(date_shapes) > 1:
        issue("inconsistent_date_format", "low", "Date ranges use more than one separator style; consider making them consistent.")
    signals = resume.get("format_signals", {})
    if signals.get("blank_line_count", 0) > max(5, signals.get("nonempty_line_count", 0) // 2):
        issue("excessive_whitespace", "low", "The source contains many blank lines relative to its content; check spacing in the final version.")
    if len(signals.get("bullet_styles", [])) > 1:
        issue("inconsistent_bullets", "low", "The source uses several bullet styles; use one consistent style in the final resume.")
    repeated_headings = [section for section, labels in resume.get("section_heading_labels", {}).items() if len(labels) > 1]
    if repeated_headings:
        issue("repeated_section_headings", "low", "Repeated section headings were found for: " + ", ".join(repeated_headings) + ".")
    if resume.get("other"):
        issue("unclassified_content", "low", f"{len(resume['other'])} line(s) were preserved under Other because they could not be confidently classified.")

    match_counts = (matching or {}).get("counts", {"matched": 0, "related": 0, "missing": 0})
    return {
        "issues": issues,
        "structure": {"name": bool(info.get("name")), "contact": bool(info.get("email") or info.get("phone")),
                      "summary": bool(resume.get("summary")), "education": bool(resume.get("education")),
                      "experience_or_internship": bool(entries), "projects": bool(resume.get("projects")),
                      "skills": bool(any(resume.get("skills", {}).values()) if isinstance(resume.get("skills"), dict) else resume.get("skills"))},
        "completeness": {"experience_entries": len(resume.get("experience", [])), "internship_entries": len(resume.get("internships", [])),
                         "project_entries": len(resume.get("projects", [])), "unclassified_lines": len(resume.get("other", []))},
        "jd_alignment": {"matched": match_counts["matched"], "related": match_counts["related"], "not_detected": match_counts["missing"]},
        "method": "Transparent rule-based checks; not an ATS score.",
    }

"""
Gemini-powered resume optimization service.

Responsibilities:
- Optimize existing resume content against a job description.
- Never invent candidate facts.
- Never add missing skills simply because they appear in the JD.
- Preserve the structured resume schema.
- Preserve protected factual information.
- Validate Gemini output before accepting it.
- Automatically fall back to deterministic optimization when:
    * Gemini is unavailable
    * Gemini returns invalid JSON
    * Gemini changes protected information
    * Gemini removes required resume content
    * Gemini introduces suspicious factual claims

Environment variables:

    AI_PROVIDER=gemini
    AI_API_KEY=<your Gemini API key>
    AI_API_URL=https://generativelanguage.googleapis.com/v1beta/openai/
    AI_MODEL=gemini-3.8-flash
"""

from __future__ import annotations

import json
import logging
import os
import re
from collections import Counter
from copy import deepcopy
from typing import Any

from dotenv import load_dotenv

from .keyword_extractor import normalize

load_dotenv()

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_AI_PROVIDER = "gemini"

DEFAULT_AI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/openai/"
)

DEFAULT_AI_MODEL = "gemini-3.8-flash"


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def optimize_resume(
    resume: dict,
    job: dict,
    requirements: dict,
    match: dict,
    quality: dict | None = None,
) -> tuple[dict, str]:
    """
    Optimize a structured resume using Gemini.

    Gemini output is NEVER trusted directly.

    Pipeline:

        Original Resume
             ↓
        Gemini Optimization
             ↓
        Validation
             ↓
        PASS → optimized resume
        FAIL → deterministic fallback

    Returns:
        tuple[dict, str]:
            optimized/fallback structured resume
            optimization mode
    """

    source_resume = deepcopy(resume)

    # ---------------------------------------------------------------
    # AI configuration check
    # ---------------------------------------------------------------

    if not _ai_is_configured():
        logger.info(
            "Gemini is not configured; using deterministic fallback."
        )

        fallback = _deterministic_optimize(
            source_resume,
            job,
            requirements,
            match,
        )

        return (
            fallback,
            "Deterministic optimization (Gemini not configured; AI not integrated)",
        )

    # ---------------------------------------------------------------
    # Gemini optimization
    # ---------------------------------------------------------------

    try:
        optimized = _optimize_with_gemini(
            resume=source_resume,
            job=job,
            requirements=requirements,
            match=match,
            quality=quality or {},
        )

    except Exception as exc:
        logger.exception(
            "Gemini optimization failed: %s",
            exc,
        )

        fallback = _deterministic_optimize(
            source_resume,
            job,
            requirements,
            match,
        )

        return (
            fallback,
            f"Deterministic fallback (Gemini error: {type(exc).__name__})",
        )

    # ---------------------------------------------------------------
    # Validation
    # ---------------------------------------------------------------

    validated, validation_errors = _validate_gemini_result(
        original=source_resume,
        optimized=optimized,
    )

    if validation_errors:
        logger.warning(
            "Gemini output rejected during validation: %s",
            validation_errors,
        )

        fallback = _deterministic_optimize(
            source_resume,
            job,
            requirements,
            match,
        )

        return (
            fallback,
            "Deterministic fallback (Gemini validation failed)",
        )

    # ---------------------------------------------------------------
    # Gemini output accepted
    # ---------------------------------------------------------------

    return (
        validated,
        "Gemini AI optimization",
    )


# ---------------------------------------------------------------------------
# Configuration helpers
# ---------------------------------------------------------------------------

def _ai_is_configured() -> bool:
    """
    Return True only when Gemini configuration is available.
    """

    provider = os.getenv(
        "AI_PROVIDER",
        DEFAULT_AI_PROVIDER,
    ).strip().lower()

    api_key = os.getenv(
        "AI_API_KEY",
        "",
    ).strip()

    return provider == "gemini" and bool(api_key)


def _get_ai_config() -> tuple[str, str, str]:
    """
    Read Gemini configuration from environment variables.
    """

    api_key = os.getenv(
        "AI_API_KEY",
        "",
    ).strip()

    api_url = (
        os.getenv(
            "AI_API_URL",
            DEFAULT_AI_API_URL,
        ).strip()
        or DEFAULT_AI_API_URL
    )

    model = (
        os.getenv(
            "AI_MODEL",
            DEFAULT_AI_MODEL,
        ).strip()
        or DEFAULT_AI_MODEL
    )

    if not api_key:
        raise RuntimeError(
            "AI_API_KEY is not configured."
        )

    return api_key, api_url, model


# ---------------------------------------------------------------------------
# Gemini integration
# ---------------------------------------------------------------------------

def _optimize_with_gemini(
    resume: dict,
    job: dict,
    requirements: dict,
    match: dict,
    quality: dict,
) -> dict:
    """
    Send structured resume information to Gemini.

    Gemini is responsible only for wording/content optimization.

    Formatting remains the responsibility of the renderer.
    """

    try:
        from openai import OpenAI

    except ImportError as exc:
        raise RuntimeError(
            "The 'openai' package is required for Gemini integration. "
            "Install it with: pip install openai"
        ) from exc

    api_key, api_url, model = _get_ai_config()

    client = OpenAI(
        api_key=api_key,
        base_url=api_url,
        timeout=30.0,
        max_retries=1,
    )

    system_prompt = _build_system_prompt()

    user_prompt = _build_user_prompt(
        resume=resume,
        job=job,
        requirements=requirements,
        match=match,
        quality=quality,
    )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
        temperature=0.15,
    )

    content = _extract_response_content(response)

    if not content:
        raise RuntimeError(
            "Gemini returned an empty response."
        )

    return _parse_json_response(content)


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

def _build_system_prompt() -> str:
    """
    Build the strict Gemini optimization prompt.
    """

    return """
You are FINXL Resume Optimization AI.

Your task is to improve a candidate's existing resume for a target job
description while preserving factual accuracy.

The candidate resume is the ONLY source of truth about the candidate.

The job description is NOT evidence that the candidate possesses a skill,
technology, qualification, responsibility, achievement, or experience.

==================================================
ABSOLUTE FACTUAL RULES
==================================================

1. NEVER invent candidate information.

Never invent:
- skills
- technologies
- programming languages
- tools
- certifications
- degrees
- employers
- job titles
- internships
- projects
- responsibilities
- achievements
- metrics
- percentages
- dates
- locations
- clients
- awards
- qualifications
- experience

2. NEVER add a missing JD requirement to the resume.

If the JD says:
"Power BI required"

and Power BI is not in the candidate resume,
DO NOT add Power BI.
 
3. NEVER invent metrics.

Do not create:
- percentages
- revenue
- user counts
- performance improvements
- response-time improvements
- accuracy values
- rankings
- scale
- business impact

unless explicitly present in the source resume.

4. NEVER upgrade the candidate's level of responsibility.

Do not transform:

"worked on" → "led"

"assisted" → "managed"

"participated in" → "directed"

"used" → "expert in"

"familiar with" → "proficient in"

unless the source resume explicitly supports the stronger claim.

5. NEVER claim production deployment, leadership, ownership, management,
client interaction, financial impact, or business impact unless explicitly
supported by the candidate resume.

==================================================
ALLOWED OPTIMIZATION
==================================================

You MAY:

- improve grammar
- improve clarity
- improve professional wording
- make bullets concise
- remove unnecessary repetition
- improve action-oriented wording
- emphasize existing relevant skills
- align wording with the JD when the underlying fact already exists
- improve existing project descriptions
- improve existing experience descriptions
- improve the professional summary using existing facts
- reorder existing skills if the schema permits it

You MAY NOT create new facts while doing so.

Example:

Source:
"Worked on sales data using Excel."

Allowed:
"Analyzed sales data using Excel."

Not allowed:
"Built advanced Excel financial models."

unless financial modeling is explicitly supported by the source resume.

==================================================
FINANCE DOMAIN OPTIMIZATION
==================================================

FINXL is primarily designed to optimize resumes for finance-related roles.

Finance-related roles may include:

- Financial Analysis
- Financial Modeling
- FP&A
- Equity Research
- Investment Banking
- Corporate Finance
- Valuation
- Financial Reporting
- Management Reporting
- Budgeting
- Forecasting
- Variance Analysis
- Accounting
- Cash Flow Analysis
- Financial Statements
- Ratio Analysis
- Investment Analysis
- Business Analysis
- Excel
- Power BI
- Tableau
- SQL
- Python for Finance
- Data Analysis
- Quantitative Analysis

When optimizing a finance-related resume, prioritize relevant existing
finance-related evidence and terminology.

However, finance terminology in the JD is NOT evidence that the candidate
has that experience.

For example:

If the candidate has:
"Python"

Do NOT change it to:
"Python for Financial Modeling"

unless the original resume provides evidence of financial modeling.

If the candidate has:
"Data Analysis"

Do NOT automatically change it to:
"Financial Analysis"

unless the original resume provides evidence of financial analysis.

If the candidate has:
"SQL"

Do NOT change it to:
"Financial Data Analysis"

unless supported by the original resume.

If the candidate has:
"Excel"

Do NOT change it to:
"Advanced Financial Modeling"

unless explicitly supported.

Never invent or imply:

- financial modeling
- DCF
- LBO
- valuation
- equity research
- investment banking
- FP&A
- forecasting
- budgeting
- accounting
- financial reporting
- financial statement analysis
- portfolio management
- trading
- investment returns
- financial KPIs
- revenue
- profit
- financial metrics
- client/investor interaction

unless supported by the candidate's original resume.

Finance relevance must come from the candidate's existing evidence,
not from the job description.

==================================================
STRUCTURE RULES
==================================================

Preserve the original resume schema.

Do NOT:
- remove sections
- create unsupported sections
- rename sections
- merge sections
- flatten structured skills
- move achievements into certifications
- move leadership into certifications
- move projects into experience
- move education into certifications
- move certifications into achievements

Preserve:
- project names
- project technologies
- education entries
- education institutions
- degree names
- dates
- GPA/CGPA
- certification names
- achievements
- leadership information
- skill categories
- skill values

==================================================
PERSONAL INFORMATION
==================================================

Never change:
- name
- email
- phone
- LinkedIn
- GitHub
- location

==================================================
SKILLS
==================================================

The candidate_resume.skills object is authoritative.

Preserve every existing skill category.

Preserve every existing skill.

Do NOT:
- add JD skills that are missing
- remove skills
- merge categories
- rename categories
- flatten categories
- create new categories

A skill appearing in multiple source categories must remain in each
original category.

==================================================
PROJECTS
==================================================

Preserve every original project.

Preserve:
- project name
- technologies
- project identity

You may rewrite project bullets only when the rewritten statement remains
supported by the original project information.

Do not invent:
- deployment
- users
- clients
- performance
- business impact
- leadership
- ownership
- metrics

==================================================
EDUCATION
==================================================

Preserve every education entry exactly in terms of factual identity.

Never change:
- degree
- institution
- dates
- GPA/CGPA
- field of study
- original raw text

Do not return an incomplete Education entry; preserve all source education facts.
Education institutions and GPA/CGPA values are immutable source facts.

==================================================
CERTIFICATIONS
==================================================

Do not add certifications.

Do not remove certifications.

Do not move achievements or leadership into certifications.

==================================================
ACHIEVEMENTS & LEADERSHIP
==================================================

Preserve achievements and leadership information.

Do not rewrite them into stronger claims.

Do not move them into certifications.

==================================================
OUTPUT
==================================================

Return ONLY a JSON object.

Do not return:
- Markdown
- code fences
- explanations
- comments
- headings outside JSON

Return the same structured schema expected by the application.

The final result must remain a truthful representation of the candidate.
"""


def _build_user_prompt(
    resume: dict,
    job: dict,
    requirements: dict,
    match: dict,
    quality: dict,
) -> str:
    """
    Build structured Gemini input.
    """

    payload = {
        "task": (
            "Optimize the candidate resume for the target job "
            "using only supported candidate facts."
        ),
        "candidate_resume": resume,
        "job": job,
        "requirements": requirements,
        "matching_analysis": match,
        "resume_quality": quality,
        "instructions": {
            "preserve_schema": True,
            "preserve_personal_information": True,
            "preserve_dates": True,
            "preserve_employers": True,
            "preserve_existing_facts": True,
            "preserve_education": True,
            "preserve_project_identity": True,
            "preserve_project_technologies": True,
            "preserve_certifications": True,
            "preserve_achievements": True,
            "preserve_leadership": True,
            "preserve_skill_categories": True,
            "preserve_skill_category_names": True,
            "preserve_all_existing_skills": True,
            "do_not_add_missing_jd_requirements": True,
            "do_not_invent_metrics": True,
            "do_not_invent_experience": True,
            "do_not_invent_skills": True,
            "do_not_invent_responsibilities": True,
            "do_not_invent_business_impact": True,
            "do_not_invent_leadership": True,
            "do_not_upgrade_responsibility": True,
            "do_not_flatten_skills": True,
            "rewrite_supported_content_only": True,
            "return_json_only": True,
        },
    }

    return (
        "Optimize the candidate resume using the following structured data.\n\n"
        "IMPORTANT:\n"
        "candidate_resume is factual source material.\n"
        "The job description is NOT evidence that the candidate possesses "
        "any missing requirement.\n\n"
        + json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        )
    )


# ---------------------------------------------------------------------------
# Response handling
# ---------------------------------------------------------------------------

def _extract_response_content(response: Any) -> str:
    """
    Extract text from OpenAI-compatible Gemini response.
    """

    try:
        message = response.choices[0].message
        content = message.content

    except (AttributeError, IndexError, TypeError) as exc:
        raise RuntimeError(
            "Unexpected Gemini response format."
        ) from exc

    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        parts: list[str] = []

        for item in content:
            if isinstance(item, dict):
                text = item.get("text")

                if isinstance(text, str):
                    parts.append(text)

            else:
                text = getattr(item, "text", None)

                if isinstance(text, str):
                    parts.append(text)

        return "\n".join(parts).strip()

    return str(content).strip()


def _parse_json_response(content: str) -> dict:
    """
    Parse Gemini JSON response.

    Handles occasional Markdown code fences defensively.
    """

    cleaned = content.strip()

    # Remove ```json
    if cleaned.startswith("```json"):
        cleaned = cleaned[len("```json"):].strip()

    # Remove generic ```
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:].strip()

    # Remove closing fence
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3].strip()

    try:
        result = json.loads(cleaned)

    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "Gemini returned invalid JSON."
        ) from exc

    if not isinstance(result, dict):
        raise RuntimeError(
            "Gemini output must be a JSON object."
        )

    return result


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _validate_gemini_result(
    original: dict,
    optimized: dict,
) -> tuple[dict, list[str]]:
    """
    Validate Gemini output.

    Returns:

        validated_resume
        validation_errors

    Any validation error causes the caller to use deterministic fallback.
    """

    errors: list[str] = []

    if not isinstance(optimized, dict):
        return deepcopy(original), [
            "Gemini output is not a JSON object."
        ]

    # ---------------------------------------------------------------
    # Top-level schema
    # ---------------------------------------------------------------

    original_keys = set(original.keys())
    optimized_keys = set(optimized.keys())

    missing_keys = original_keys - optimized_keys

    if missing_keys:
        errors.append(
            f"Missing original sections/fields: {sorted(missing_keys)}"
        )

    # ---------------------------------------------------------------
    # Personal information
    # ---------------------------------------------------------------

    _validate_personal_information(
        original,
        optimized,
        errors,
    )

    # ---------------------------------------------------------------
    # Skills
    # ---------------------------------------------------------------

    if "skills" in original:
        _validate_skills_strict(
            original.get("skills"),
            optimized.get("skills"),
            errors,
        )

    # ---------------------------------------------------------------
    # Education
    # ---------------------------------------------------------------

    if "education" in original:
        _validate_structured_identity_section(
            original.get("education"),
            optimized.get("education"),
            section_name="education",
            identity_fields=(
                "degree",
                "institution",
                "dates",
                "date",
                "gpa",
                "grade",
            ),
            errors=errors,
        )

    # ---------------------------------------------------------------
    # Projects
    # ---------------------------------------------------------------

    if "projects" in original:
        _validate_projects(
            original.get("projects"),
            optimized.get("projects"),
            errors,
        )

    # ---------------------------------------------------------------
    # Experience
    # ---------------------------------------------------------------

    for section_name in (
        "experience",
        "internships",
    ):
        if section_name in original:
            _validate_structured_identity_section(
                original.get(section_name),
                optimized.get(section_name),
                section_name=section_name,
                identity_fields=(
                    "company",
                    "employer",
                    "organization",
                    "role",
                    "title",
                    "job_title",
                    "location",
                    "start_date",
                    "end_date",
                    "date",
                    "dates",
                ),
                errors=errors,
            )

    # ---------------------------------------------------------------
    # Certifications
    # ---------------------------------------------------------------

    if "certifications" in original:
        _validate_string_list_strict(
            original.get("certifications"),
            optimized.get("certifications"),
            section_name="certifications",
            errors=errors,
        )

    # ---------------------------------------------------------------
    # Achievements
    # ---------------------------------------------------------------

    if "achievements" in original:
        _validate_string_list_strict(
            original.get("achievements"),
            optimized.get("achievements"),
            section_name="achievements",
            errors=errors,
        )

    # ---------------------------------------------------------------
    # Leadership
    # ---------------------------------------------------------------

    if "leadership" in original:
        _validate_string_list_strict(
            original.get("leadership"),
            optimized.get("leadership"),
            section_name="leadership",
            errors=errors,
        )

    # ---------------------------------------------------------------
    # Build sanitized result
    # ---------------------------------------------------------------

    sanitized = _sanitize_validated_resume(
        original,
        optimized,
    )

    return sanitized, errors


# ---------------------------------------------------------------------------
# Personal information validation
# ---------------------------------------------------------------------------

def _validate_personal_information(
    original: dict,
    optimized: dict,
    errors: list[str],
) -> None:
    """
    Personal information must never change.
    """

    original_info = original.get("personal_info")

    if not isinstance(original_info, dict):
        return

    optimized_info = optimized.get("personal_info")

    if not isinstance(optimized_info, dict):
        errors.append(
            "personal_info is missing or invalid."
        )
        return

    for key, original_value in original_info.items():

        optimized_value = optimized_info.get(key)

        if _normalize_value(original_value) != _normalize_value(
            optimized_value
        ):
            errors.append(
                f"Personal information changed: {key}"
            )


# ---------------------------------------------------------------------------
# Skills validation
# ---------------------------------------------------------------------------

def _validate_skills_strict(
    original: Any,
    optimized: Any,
    errors: list[str],
) -> None:
    """
    Strictly validate skill categories and values.
    """

    if not isinstance(original, dict):
        return

    if not isinstance(optimized, dict):
        errors.append(
            "Skills section is missing or invalid."
        )
        return

    original_groups = set(original.keys())
    optimized_groups = set(optimized.keys())

    missing_groups = original_groups - optimized_groups

    if missing_groups:
        errors.append(
            f"Missing skill categories: {sorted(missing_groups)}"
        )

    extra_groups = optimized_groups - original_groups

    if extra_groups:
        errors.append(
            f"Unexpected skill categories: {sorted(extra_groups)}"
        )

    for group, original_values in original.items():

        model_values = optimized.get(group)

        if not isinstance(original_values, list):
            continue

        if not isinstance(model_values, list):
            errors.append(
                f"Skill category is invalid: {group}"
            )
            continue

        original_counts = Counter(
            normalize(str(value))
            for value in original_values
            if isinstance(value, str)
        )

        model_counts = Counter(
            normalize(str(value))
            for value in model_values
            if isinstance(value, str)
        )

        # Every original skill must exist.
        for skill, count in original_counts.items():

            if model_counts[skill] < count:
                errors.append(
                    f"Skill removed from '{group}': {skill}"
                )

        # No new skills.
        for skill in model_counts:

            if skill not in original_counts:
                errors.append(
                    f"New unsupported skill in '{group}': {skill}"
                )

            elif model_counts[skill] > original_counts[skill]:
                errors.append(
                    f"Duplicate skill introduced in '{group}': {skill}"
                )


# ---------------------------------------------------------------------------
# Structured section validation
# ---------------------------------------------------------------------------

def _validate_structured_identity_section(
    original: Any,
    optimized: Any,
    section_name: str,
    identity_fields: tuple[str, ...],
    errors: list[str],
) -> None:
    """
    Validate structured sections such as education and experience.

    Entry identity must remain unchanged.
    """

    if not isinstance(original, list):
        return

    if not isinstance(optimized, list):
        errors.append(
            f"{section_name} section is missing or invalid."
        )
        return

    if len(original) != len(optimized):
        errors.append(
            f"{section_name} entry count changed."
        )
        return

    original_identity = [
        _identity_signature(item, identity_fields)
        for item in original
    ]

    optimized_identity = [
        _identity_signature(item, identity_fields)
        for item in optimized
    ]

    if sorted(original_identity) != sorted(optimized_identity):
        errors.append(
            f"{section_name} factual identity changed."
        )


def _validate_projects(
    original: Any,
    optimized: Any,
    errors: list[str],
) -> None:
    """
    Validate project names and technologies.
    """

    if not isinstance(original, list):
        return

    if not isinstance(optimized, list):
        errors.append(
            "Projects section is missing or invalid."
        )
        return

    if len(original) != len(optimized):
        errors.append(
            "Project count changed."
        )
        return

    original_map = {}

    for item in original:

        if not isinstance(item, dict):
            continue

        identity = _project_identity(item)

        if identity:
            original_map[identity] = item

    optimized_map = {}

    for item in optimized:

        if not isinstance(item, dict):
            continue

        identity = _project_identity(item)

        if identity:
            optimized_map[identity] = item

    if set(original_map.keys()) != set(optimized_map.keys()):
        errors.append(
            "Project names/identities changed."
        )
        return

    # Validate technologies for every project.
    for identity, original_project in original_map.items():

        optimized_project = optimized_map[identity]

        original_technologies = _extract_project_technologies(
            original_project
        )

        optimized_technologies = _extract_project_technologies(
            optimized_project
        )

        original_normalized = {
            normalize(str(value))
            for value in original_technologies
        }

        optimized_normalized = {
            normalize(str(value))
            for value in optimized_technologies
        }

        missing = original_normalized - optimized_normalized

        if missing:
            errors.append(
                f"Project technologies removed from '{identity}': "
                f"{sorted(missing)}"
            )


# ---------------------------------------------------------------------------
# String-list validation
# ---------------------------------------------------------------------------

def _validate_string_list_strict(
    original: Any,
    optimized: Any,
    section_name: str,
    errors: list[str],
) -> None:
    """
    Ensure list-based factual sections are not changed.

    Formatting differences such as em-dash vs hyphen are tolerated.
    """

    if not isinstance(original, list):
        return

    if not isinstance(optimized, list):
        errors.append(
            f"{section_name} section is missing or invalid."
        )
        return

    original_normalized = Counter(
        normalize(str(item))
        for item in original
        if isinstance(item, str)
    )

    optimized_normalized = Counter(
        normalize(str(item))
        for item in optimized
        if isinstance(item, str)
    )

    for value, count in original_normalized.items():

        if optimized_normalized[value] < count:
            errors.append(
                f"{section_name} item removed: {value}"
            )

    for value, count in optimized_normalized.items():

        if value not in original_normalized:
            errors.append(
                f"Unsupported item added to {section_name}: {value}"
            )


# ---------------------------------------------------------------------------
# Sanitization
# ---------------------------------------------------------------------------

def _sanitize_validated_resume(
    original: dict,
    optimized: dict,
) -> dict:
    """
    Build final resume using the original resume as the factual base.

    Only safe wording fields are accepted from Gemini.
    """

    result = deepcopy(original)

    # ---------------------------------------------------------------
    # Summary
    # ---------------------------------------------------------------

    if "summary" in original:

        model_summary = optimized.get("summary")

        if isinstance(model_summary, str):

            result["summary"] = _safe_rewrite(
                original.get("summary", ""),
                model_summary,
            )

    # ---------------------------------------------------------------
    # Experience / internships
    # ---------------------------------------------------------------

    for section_name in (
        "experience",
        "internships",
    ):

        if section_name in original:

            result[section_name] = _sanitize_structured_section(
                original.get(section_name),
                optimized.get(section_name),
            )

    # ---------------------------------------------------------------
    # Projects
    # ---------------------------------------------------------------

    if "projects" in original:

        result["projects"] = _sanitize_projects(
            original.get("projects"),
            optimized.get("projects"),
        )

    # ---------------------------------------------------------------
    # Education
    # ---------------------------------------------------------------

    if "education" in original:

        result["education"] = _sanitize_structured_section(
            original.get("education"),
            optimized.get("education"),
        )

    # ---------------------------------------------------------------
    # Skills
    # ---------------------------------------------------------------

    if "skills" in original:

        result["skills"] = _sanitize_skills(
            original.get("skills"),
            optimized.get("skills"),
        )

    # ---------------------------------------------------------------
    # Factual list sections
    # ---------------------------------------------------------------

    for section_name in (
        "certifications",
        "achievements",
        "leadership",
        "languages",
    ):

        if section_name in original:
            result[section_name] = deepcopy(
                original.get(section_name)
            )

    return result


def _sanitize_structured_section(
    original: Any,
    optimized: Any,
) -> list:
    """
    Preserve original structured fields.

    Only descriptions/bullets are eligible for rewriting.
    """

    if not isinstance(original, list):
        return deepcopy(original)

    if not isinstance(optimized, list):
        return deepcopy(original)

    result = []

    for index, original_item in enumerate(original):

        if not isinstance(original_item, dict):
            result.append(
                deepcopy(original_item)
            )
            continue

        if index >= len(optimized):
            result.append(
                deepcopy(original_item)
            )
            continue

        model_item = optimized[index]

        if not isinstance(model_item, dict):
            result.append(
                deepcopy(original_item)
            )
            continue

        safe_item = deepcopy(original_item)

        # Description
        if "description" in original_item:

            candidate = model_item.get("description")

            if isinstance(candidate, str):

                safe_item["description"] = _safe_rewrite(
                    original_item["description"],
                    candidate,
                )

        # Summary
        if "summary" in original_item:

            candidate = model_item.get("summary")

            if isinstance(candidate, str):

                safe_item["summary"] = _safe_rewrite(
                    original_item["summary"],
                    candidate,
                )

        # Bullets
        if "bullets" in original_item:

            safe_item["bullets"] = _sanitize_bullets(
                original_item.get("bullets"),
                model_item.get("bullets"),
            )

        result.append(safe_item)

    return result


def _sanitize_projects(
    original: Any,
    optimized: Any,
) -> list:
    """
    Sanitize projects while preserving project identity and technologies.
    """

    if not isinstance(original, list):
        return deepcopy(original)

    if not isinstance(optimized, list):
        return deepcopy(original)

    optimized_map = {}

    for item in optimized:

        if isinstance(item, dict):

            identity = _project_identity(item)

            if identity:
                optimized_map[identity] = item

    result = []

    for original_project in original:

        if not isinstance(original_project, dict):
            result.append(
                deepcopy(original_project)
            )
            continue

        identity = _project_identity(
            original_project
        )

        model_project = optimized_map.get(
            identity
        )

        if not isinstance(model_project, dict):
            result.append(
                deepcopy(original_project)
            )
            continue

        safe_project = deepcopy(
            original_project
        )

        if "description" in original_project:

            candidate = model_project.get(
                "description"
            )

            if isinstance(candidate, str):

                safe_project["description"] = _safe_rewrite(
                    original_project["description"],
                    candidate,
                )

        if "summary" in original_project:

            candidate = model_project.get(
                "summary"
            )

            if isinstance(candidate, str):

                safe_project["summary"] = _safe_rewrite(
                    original_project["summary"],
                    candidate,
                )

        if "bullets" in original_project:

            safe_project["bullets"] = _sanitize_bullets(
                original_project.get("bullets"),
                model_project.get("bullets"),
            )

        result.append(
            safe_project
        )

    return result


def _sanitize_bullets(
    original: Any,
    optimized: Any,
) -> list[str]:
    """
    Sanitize bullet points.

    Gemini cannot increase the number of bullets.
    """

    if not isinstance(original, list):
        return deepcopy(original)

    if not isinstance(optimized, list):
        return deepcopy(original)

    result = []

    for index, original_bullet in enumerate(original):

        if not isinstance(original_bullet, str):
            result.append(
                deepcopy(original_bullet)
            )
            continue

        if index >= len(optimized):
            result.append(original_bullet)
            continue

        model_bullet = optimized[index]

        if not isinstance(model_bullet, str):
            result.append(original_bullet)
            continue

        result.append(
            _safe_rewrite(
                original_bullet,
                model_bullet,
            )
        )

    return result


def _sanitize_skills(
    original: Any,
    optimized: Any,
) -> dict:
    """
    Preserve original skills and categories.

    Gemini may reorder existing skills but cannot add/remove them.
    """

    if not isinstance(original, dict):
        return deepcopy(original)

    if not isinstance(optimized, dict):
        return deepcopy(original)

    result = {}

    for group, original_values in original.items():

        if not isinstance(original_values, list):
            result[group] = deepcopy(
                original_values
            )
            continue

        model_values = optimized.get(group)

        if not isinstance(model_values, list):
            result[group] = deepcopy(
                original_values
            )
            continue

        original_map = {
            normalize(str(value)): value
            for value in original_values
            if isinstance(value, str)
        }

        original_counts = Counter(
            normalize(str(value))
            for value in original_values
            if isinstance(value, str)
        )

        used_counts = Counter()

        reordered = []

        for value in model_values:

            if not isinstance(value, str):
                continue

            normalized = normalize(value)

            if (
                normalized in original_map
                and used_counts[normalized]
                < original_counts[normalized]
            ):

                reordered.append(
                    original_map[normalized]
                )

                used_counts[normalized] += 1

        # Restore anything Gemini omitted.
        for original_value in original_values:

            normalized = normalize(
                str(original_value)
            )

            if (
                used_counts[normalized]
                < original_counts[normalized]
            ):

                reordered.append(
                    original_value
                )

                used_counts[normalized] += 1

        result[group] = reordered

    return result


# ---------------------------------------------------------------------------
# Safe rewriting
# ---------------------------------------------------------------------------

def _safe_rewrite(
    original_text: str,
    model_text: str,
) -> str:
    """
    Conservative rewrite validation.

    If the rewrite introduces suspicious factual information,
    the original text is retained.
    """

    if not isinstance(original_text, str):
        return original_text

    if not isinstance(model_text, str):
        return original_text

    original_text = original_text.strip()
    model_text = model_text.strip()

    if not original_text:
        return model_text

    if not model_text:
        return original_text

    # ---------------------------------------------------------------
    # Numeric claims
    # ---------------------------------------------------------------

    original_numbers = _extract_numbers(
        original_text
    )

    model_numbers = _extract_numbers(
        model_text
    )

    if not model_numbers.issubset(
        original_numbers
    ):

        logger.warning(
            "Rejected AI rewrite because it introduced "
            "new numeric values."
        )

        return original_text

    # ---------------------------------------------------------------
    # Dates
    # ---------------------------------------------------------------

    original_dates = _extract_dates(
        original_text
    )

    model_dates = _extract_dates(
        model_text
    )

    if not model_dates.issubset(
        original_dates
    ):

        logger.warning(
            "Rejected AI rewrite because it introduced "
            "new dates."
        )

        return original_text

    # ---------------------------------------------------------------
    # Excessive expansion
    # ---------------------------------------------------------------

    if len(model_text) > max(
        len(original_text) * 3,
        len(original_text) + 250,
    ):

        logger.warning(
            "Rejected AI rewrite because it expanded "
            "the text excessively."
        )

        return original_text

    # ---------------------------------------------------------------
    # Suspicious responsibility upgrades
    # ---------------------------------------------------------------

    suspicious_patterns = [
        r"\bled\b",
        r"\bmanaged\b",
        r"\bdirected\b",
        r"\bsupervised\b",
        r"\bowned\b",
        r"\barchitected\b",
        r"\bdeployed\b",
        r"\bproduction\b",
        r"\bexpert\b",
        r"\bproficient\b",
        r"\benterprise\b",
    ]

    original_lower = original_text.lower()
    model_lower = model_text.lower()

    for pattern in suspicious_patterns:

        if re.search(pattern, model_lower) and not re.search(
            pattern,
            original_lower,
        ):

            logger.warning(
                "Rejected AI rewrite because it may have "
                "introduced an unsupported responsibility/claim."
            )

            return original_text

    return model_text


# ---------------------------------------------------------------------------
# Identity helpers
# ---------------------------------------------------------------------------

def _identity_signature(
    item: Any,
    fields: tuple[str, ...],
) -> str:
    """
    Generate a normalized identity signature.
    """

    if not isinstance(item, dict):
        return ""

    values = []

    for field in fields:

        value = item.get(field)

        if isinstance(value, str) and value.strip():
            values.append(
                normalize(value)
            )

    return " | ".join(values)


def _project_identity(
    item: dict,
) -> str:
    """
    Get project identity from common schema fields.
    """

    for field in (
        "name",
        "project_name",
        "title",
    ):

        value = item.get(field)

        if isinstance(value, str) and value.strip():
            return normalize(value)

    return ""


def _extract_project_technologies(
    project: dict,
) -> list[str]:
    """
    Extract technologies from common project schemas.
    """

    for field in (
        "technologies",
        "technology",
        "tech_stack",
        "tech",
    ):

        value = project.get(field)

        if isinstance(value, list):
            return [
                str(item)
                for item in value
                if item is not None
            ]

        if isinstance(value, str):
            return [
                item.strip()
                for item in re.split(
                    r"[,|;]",
                    value,
                )
                if item.strip()
            ]

    return []


def _normalize_value(
    value: Any,
) -> str:
    """
    Normalize values for factual comparison.
    """

    if value is None:
        return ""

    return normalize(
        str(value)
    ).strip()


# ---------------------------------------------------------------------------
# Numeric/date extraction
# ---------------------------------------------------------------------------

def _extract_numbers(
    text: str,
) -> set[str]:
    """
    Extract numbers and percentages.
    """

    return set(
        re.findall(
            r"\b\d+(?:\.\d+)?%?\b",
            text,
        )
    )


def _extract_dates(
    text: str,
) -> set[str]:
    """
    Extract four-digit years.
    """

    return set(
        re.findall(
            r"\b(?:19|20)\d{2}\b",
            text,
        )
    )


# ---------------------------------------------------------------------------
# Deterministic fallback
# ---------------------------------------------------------------------------

def _deterministic_optimize(
    resume: dict,
    job: dict,
    requirements: dict,
    match: dict,
) -> dict:
    """
    Safe non-AI optimization.

    Does not rewrite candidate content.

    It only reorders existing skills so matched/related
    skills appear first.
    """

    optimized = deepcopy(resume)

    matched = {
        normalize(str(name))
        for name in match.get(
            "matched",
            [],
        )
        if name
    }

    related = {
        normalize(str(name))
        for name in match.get(
            "related",
            [],
        )
        if name
    }

    skills = optimized.get("skills")

    if not isinstance(skills, dict):
        return optimized

    for group, values in skills.items():

        if not isinstance(values, list):
            continue

        def sort_key(value: Any):

            normalized = normalize(
                str(value)
            )

            if normalized in matched:
                priority = 0

            elif normalized in related:
                priority = 1

            else:
                priority = 2

            return (
                priority,
                str(value).lower(),
            )

        values.sort(
            key=sort_key
        )

    return optimized

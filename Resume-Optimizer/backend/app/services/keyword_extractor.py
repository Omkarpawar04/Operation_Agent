"""Layered deterministic keywords plus lightweight, dependency-free phrase candidates."""
import re
from typing import Any

# Standard vocabulary covering finance, tech, data, and business domains
TERMS = [
    # Tools
    "excel", "ms excel", "microsoft excel", "advanced microsoft excel", "advanced excel",
    "power bi", "tableau", "bloomberg", "sap", "quickbooks", "google sheets",
    "capital iq", "factset", "git", "docker", "kubernetes", "aws", "azure", "jira",
    "salesforce", "figma", "mysql", "postgresql", "powerpoint",
    # Technical skills
    "sql", "python", "r", "java", "c++", "c#", "javascript", "typescript",
    "data analysis", "data analytics", "variance analysis", "statistics",
    "machine learning", "dashboard development", "rest apis", "web development",
    # Domain skills
    "financial analysis", "financial modeling", "financial modelling", "financial reporting",
    "financial planning", "forecasting", "budgeting", "valuation", "cash flow analysis",
    "cash flow", "business partnering", "business analysis", "risk assessment",
    "risk management", "accounting", "accounting fundamentals", "basic accounting",
    "investment banking", "equity research", "fp&a", "financial statement analysis",
    "financial statements", "sales and expense analysis", "portfolio management",
    "market research", "project management", "product management",
    # Soft skills
    "communication", "attention to detail", "problem solving", "problem-solving",
    "leadership", "collaboration", "teamwork", "stakeholder management",
    "critical thinking", "time management", "adaptability",
]

ALIASES: dict[str, str] = {
    "ms excel": "excel",
    "microsoft excel": "excel",
    "advanced microsoft excel": "excel",
    "advanced excel": "excel",
    "financial modelling": "financial modeling",
    "data analytics": "data analysis",
    "accounting fundamentals": "accounting",
    "basic accounting": "accounting",
    "introduction to accounting": "accounting",
    "problem-solving": "problem solving",
    "cash flow": "cash flow analysis",
    "financial statements": "financial reporting",
    "financial statement analysis": "financial reporting",
    "fp&a": "financial planning",
}

TYPE_GROUPS: dict[str, set[str]] = {
    "tool": {
        "excel", "power bi", "tableau", "bloomberg", "sap", "quickbooks",
        "google sheets", "capital iq", "factset", "git", "docker", "kubernetes",
        "aws", "azure", "jira", "salesforce", "figma", "mysql", "postgresql", "powerpoint",
    },
    "technical_skill": {
        "sql", "python", "r", "java", "c++", "c#", "javascript", "typescript",
        "statistics", "data analysis", "dashboard development", "machine learning",
        "rest apis", "web development",
    },
    "soft_skill": {
        "communication", "attention to detail", "problem solving", "leadership",
        "collaboration", "teamwork", "stakeholder management", "time management",
        "critical thinking", "adaptability",
    },
    "domain_skill": {
        "financial analysis", "financial modeling", "financial reporting",
        "financial planning", "forecasting", "budgeting", "variance analysis",
        "valuation", "cash flow analysis", "business partnering", "business analysis",
        "risk assessment", "risk management", "accounting", "investment banking",
        "equity research", "portfolio management", "market research",
        "project management", "product management", "sales and expense analysis",
    },
    "qualification": {
        "bachelor", "master", "phd", "bba", "bcom", "bsc", "ba", "mcom", "mca", "bca", "mba",
        "degree", "diploma",
    },
    "education": {
        "finance", "accounting", "business", "computer science", "economics",
        "software engineering", "mathematics", "information technology", "related field",
    },
}

_CUE = re.compile(
    r"\b(?:experience\s+(?:in|with)|proficiency\s+(?:in|with)|knowledge\s+(?:of|in)|"
    r"skills?\s+(?:in|with)|expertise\s+(?:in|with)|familiarity\s+(?:with|in)|"
    r"ability\s+to|competence\s+in|support\b|assist\s+with|responsible\s+for|"
    r"perform\b|conduct\b|lead\b|manage\b|participate\s+in)\s+([^.;\n]+)",
    re.I,
)

_PREFERENCE_CUE = re.compile(
    r"\b(?:nice\s+to\s+have|preferred|bonus|a\s+plus|desirable|advantageous)\b\s*:?\s*([^.;\n]+)",
    re.I,
)

_SPLIT = re.compile(r"\s*(?:,|;|\band\b|\bor\b|\bas\s+well\s+as\b|/)\s*", re.I)


def extract_proficiency(term: str) -> str | None:
    """Extract proficiency level such as advanced, intermediate, or basic."""
    low = term.lower()
    for level in ("advanced", "intermediate", "basic", "expert", "senior", "lead"):
        if re.search(r"\b" + level + r"\b", low):
            return level
    return None


def normalize(term: str) -> str:
    """Normalize requirement terms consistently while mapping synonyms/aliases.
    
    Examples:
        'Microsoft Excel' -> 'excel'
        'MS Excel' -> 'excel'
        'Advanced Microsoft Excel' -> 'excel'
        'Financial modelling' -> 'financial modeling'
        'Accounting fundamentals' -> 'accounting'
        'Data analytics' -> 'data analysis'
    """
    if not term:
        return ""
    value = re.sub(r"[^a-z0-9+#& ]", " ", term.lower())
    value = re.sub(r"\s+", " ", value).strip()
    if not value:
        return ""

    if value in ALIASES:
        return ALIASES[value]

    # Strip proficiency prefixes if present
    for prefix in ("advanced ", "intermediate ", "basic ", "expert ", "senior "):
        if value.startswith(prefix):
            sub = value[len(prefix):].strip()
            if sub in ALIASES:
                return ALIASES[sub]
            if any(sub in group for group in TYPE_GROUPS.values()):
                return sub

    # Strip suffixes like 'fundamentals', 'basics'
    for suffix in (" fundamentals", " basics", " fundamental", " basic"):
        if value.endswith(suffix):
            sub = value[:-len(suffix)].strip()
            if sub in ALIASES:
                return ALIASES[sub]
            if any(sub in group for group in TYPE_GROUPS.values()):
                return sub

    return ALIASES.get(value, value)


def extract_terms(text: str) -> list[str]:
    """Return normalized controlled-vocabulary matches from text."""
    normalized_text = " " + re.sub(r"[^a-z0-9+#& ]", " ", text.lower()) + " "
    found = []
    # Match longer terms first to prevent partial shadowing
    for term in sorted(TERMS, key=len, reverse=True):
        pattern = r"(?<!\w)" + re.escape(term.lower()) + r"(?!\w)"
        if re.search(pattern, normalized_text):
            canonical = normalize(term)
            if canonical and canonical not in found:
                found.append(canonical)
    return found


def extract_candidate_phrases(text: str) -> list[dict[str, str]]:
    """Extract candidate phrases listed after skill and responsibility cues.
    
    Guarantees clean boundary handling so coordinated phrases like
    'financial planning, reporting, forecasting, and business analysis'
    are separated cleanly and never concatenated into 'Financial PlanningForecasting'.
    """
    found: dict[str, dict[str, str]] = {}
    matches = list(_CUE.finditer(text)) + list(_PREFERENCE_CUE.finditer(text))

    for match in matches:
        clause = match.group(1).strip()
        parts = [p.strip() for p in _SPLIT.split(clause) if p.strip()]

        last_modifier = ""
        for raw in parts:
            phrase = re.sub(
                r"\b(?:required|preferred|desired|strong|excellent|proven|solid|minimum)\b",
                "",
                raw,
                flags=re.I,
            ).strip(" .:-")

            # Strip trailing noise words like 'activities', 'tasks', 'duties'
            phrase = re.sub(
                r"\s+\b(?:activities|tasks|duties|initiatives|responsibilities|workflows)\b$",
                "",
                phrase,
                flags=re.I,
            ).strip()

            if not phrase:
                continue

            # Check if this phrase is coordinated after a domain qualifier (e.g. 'financial planning, reporting')
            words = phrase.split()
            if len(words) == 1 and last_modifier and f"{last_modifier} {phrase}".lower() in TERMS:
                phrase = f"{last_modifier.title()} {phrase.title()}"
            elif len(words) >= 2 and words[0].lower() in {"financial", "data", "business", "cloud", "software"}:
                last_modifier = words[0].lower()

            words = phrase.split()
            if not 1 <= len(words) <= 5 or len(phrase) < 3:
                continue

            key = normalize(phrase)
            if key and key not in found:
                found[key] = {
                    "name": phrase.title() if phrase.islower() else phrase,
                    "normalized_name": key,
                    "evidence": match.group(0).strip(),
                }

    return list(found.values())


def classify_requirement(name: str, context: str = "") -> str:
    """Classify a requirement into standard types:
    tool, technical_skill, domain_skill, soft_skill, qualification,
    education, certification, experience, responsibility, other.
    """
    norm = normalize(name)
    low_name = name.lower()
    low_ctx = (context or "").lower()

    # Check controlled type groups
    for kind, values in TYPE_GROUPS.items():
        if norm in values or any(normalize(v) == norm for v in values):
            return kind

    # Context / heuristic classifications
    if re.search(r"\b(certification|certificate|licensed|license|cfa|cpa|pmp|frm|cma)\b", low_ctx) or re.search(r"\b(certification|certificate|licensed|license|cfa|cpa|pmp|frm|cma)\b", low_name):
        return "certification"
    if re.search(r"\b(degree|bachelor|master|phd|mba|education|graduate|bcom|bba|bsc|ba|mcom|mca|bca)\b", low_ctx) or re.search(r"\b(degree|bachelor|master|phd|mba|graduate|bcom|bba|bsc|ba|mcom|mca|bca)\b", low_name):
        return "education"
    if re.search(r"\b(years?\s+of\s+experience|experience\s+in|experience\s+with)\b", low_ctx):
        return "experience"
    if re.search(r"\b(responsible\s+for|responsibilities|will\s+support|will\s+lead|duties\s+include|assist\s+with)\b", low_ctx):
        return "responsibility"

    # Default fallback for unlisted skill-like phrases
    if any(w in norm for w in ("tool", "software", "platform", "system")):
        return "tool"
    if any(w in norm for w in ("code", "programming", "database", "api", "query")):
        return "technical_skill"
    if any(w in norm for w in ("leadership", "communication", "collaborat", "problem solve")):
        return "soft_skill"

    return "domain_skill"


def classify_importance(context: str, section: str = "") -> str:
    """Determine requirement importance: required, preferred, or unknown."""
    sec = (section or "").lower()
    low = (context or "").lower()

    if sec in {"preferred", "preferred_skills", "bonus"} or re.search(
        r"\b(preferred|preferably|nice\s+to\s+have|bonus|a\s+plus|desirable|advantageous)\b",
        low,
    ):
        return "preferred"

    if sec in {"required", "required_skills", "requirements", "minimum qualifications"} or re.search(
        r"\b(required|must\s+have|mandatory|minimum|must\s+possess|essential|necessary)\b",
        low,
    ):
        return "required"

    return "unknown"

"""Job source abstraction: local JSON storage with seamless FINXL API readiness."""
import json
import logging
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


class JobNotFoundError(KeyError):
    """Raised when the requested job_id does not exist in any configured data source."""

    def __init__(self, job_id: str):
        self.job_id = job_id
        super().__init__(f"Job not found: {job_id}")


def normalize_job_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Ensure consistent internal job structure regardless of source."""
    if not isinstance(data, dict):
        raise ValueError("Job data must be a dictionary.")

    job_id = str(data.get("job_id") or "").strip()
    title = str(data.get("title") or "").strip()
    company = str(data.get("company") or "").strip()
    description = str(data.get("description") or "").strip()

    required_skills = [
        str(s).strip() for s in data.get("required_skills", []) if str(s).strip()
    ]
    preferred_skills = [
        str(s).strip() for s in data.get("preferred_skills", []) if str(s).strip()
    ]
    responsibilities = [
        str(r).strip() for r in data.get("responsibilities", []) if str(r).strip()
    ]

    education_raw = data.get("education")
    if isinstance(education_raw, dict):
        education = {
            "minimum_degree": str(education_raw.get("minimum_degree") or "").strip(),
            "fields": [str(f).strip() for f in education_raw.get("fields", []) if str(f).strip()],
        }
    elif isinstance(education_raw, str) and education_raw.strip():
        education = {
            "minimum_degree": education_raw.strip(),
            "fields": [],
        }
    else:
        education = {
            "minimum_degree": "",
            "fields": [],
        }

    normalized: dict[str, Any] = {
        "job_id": job_id,
        "title": title,
        "company": company,
        "description": description,
        "required_skills": required_skills,
        "preferred_skills": preferred_skills,
        "responsibilities": responsibilities,
        "education": education,
    }

    # Retain any extra keys (e.g. aliases, department, etc.)
    for k, v in data.items():
        if k not in normalized:
            normalized[k] = v

    return normalized


def _fetch_from_finxl_api(job_id: str) -> dict[str, Any] | None:
    """Attempt to retrieve JD from FINXL Main System API if configured."""
    api_url = os.getenv("FINXL_API_URL", "").strip().rstrip("/")
    if not api_url:
        return None

    api_key = os.getenv("FINXL_API_KEY", "").strip()
    endpoint = f"{api_url}/jobs/{job_id}"
    req = urllib.request.Request(endpoint)
    req.add_header("Accept", "application/json")
    if api_key:
        req.add_header("Authorization", f"Bearer {api_key}")

    try:
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            if resp.status == 200:
                payload = json.loads(resp.read().decode("utf-8"))
                return normalize_job_dict(payload)
            if resp.status == 404:
                raise JobNotFoundError(job_id)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise JobNotFoundError(job_id) from exc
        logger.warning("FINXL API error for job %s: %s", job_id, exc)
    except Exception as exc:
        logger.warning("Failed to connect to FINXL API at %s: %s", endpoint, exc)

    return None


def _load_local_jobs() -> list[dict[str, Any]]:
    """Scan local data directory for all valid job JSON files."""
    jobs: list[dict[str, Any]] = []
    if not DATA_DIR.is_dir():
        return jobs

    for json_path in DATA_DIR.glob("*.json"):
        try:
            content = json.loads(json_path.read_text(encoding="utf-8"))
            if isinstance(content, dict):
                content.setdefault("_file_stem", json_path.stem)
                jobs.append(content)
            elif isinstance(content, list):
                for item in content:
                    if isinstance(item, dict):
                        item.setdefault("_file_stem", json_path.stem)
                        jobs.append(item)
        except Exception as exc:
            logger.warning("Could not read local job file %s: %s", json_path, exc)

    return jobs


def get_job_description(job_id: str) -> dict[str, Any]:
    """Single job retrieval service abstraction for the entire pipeline.
    
    Reads from remote FINXL API if configured; otherwise reads from local JSON.
    Never hardcodes a specific job ID.
    Raises JobNotFoundError (subclass of KeyError) if the job does not exist.
    """
    if not job_id or not str(job_id).strip():
        raise JobNotFoundError(job_id)

    normalized_id = str(job_id).strip()

    # 1. Try remote FINXL API if configured
    remote_job = _fetch_from_finxl_api(normalized_id)
    if remote_job is not None:
        return remote_job

    # 2. Search local data
    for raw in _load_local_jobs():
        raw_id = str(raw.get("job_id") or "").strip()
        aliases = [str(a).strip() for a in raw.get("aliases", []) if str(a).strip()]
        file_stem = str(raw.get("_file_stem") or "").strip()

        if normalized_id in (raw_id, *aliases, file_stem):
            return normalize_job_dict(raw)

    raise JobNotFoundError(normalized_id)


def list_jobs() -> list[dict[str, Any]]:
    """List all available jobs with basic summary information."""
    seen_ids = set()
    summaries: list[dict[str, Any]] = []

    for raw in _load_local_jobs():
        job_id = str(raw.get("job_id") or "").strip()
        if not job_id or job_id in seen_ids:
            continue
        seen_ids.add(job_id)
        summaries.append({
            "job_id": job_id,
            "title": str(raw.get("title") or "Untitled Job"),
            "company": str(raw.get("company") or ""),
            "description": str(raw.get("description") or ""),
        })

    return summaries

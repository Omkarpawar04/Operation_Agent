import hashlib
import json
from datetime import date, datetime
from pathlib import Path


def _student_key(student_id):
    key = str(student_id).strip().casefold()
    if not key:
        raise ValueError("student_id must not be empty.")
    return key


def _account_key(account_id):
    account = str(account_id).strip().casefold()
    if not account:
        raise ValueError("IIMJobs account email must not be empty.")
    digest = hashlib.sha256(account.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _load_store(path):
    path = Path(path)
    if not path.exists():
        return {"schema_version": 1, "students": {}}

    with path.open("r", encoding="utf-8") as file:
        store = json.load(file)

    if not isinstance(store, dict) or not isinstance(
        store.get("students"),
        dict,
    ):
        raise ValueError(f"Invalid IIMJobs tracker format: {path}")

    return store


def empty_application_log():
    return {"jobs": {}, "daily_submissions": {}}


def load_application_log(path, student_id, account_id):
    store = _load_store(path)
    student = store["students"].get(_student_key(student_id), {})
    account = student.get("accounts", {}).get(_account_key(account_id), {})
    log = {
        "jobs": account.get("jobs", {}),
        "daily_submissions": account.get("daily_submissions", {}),
    }
    if not isinstance(log["jobs"], dict):
        raise ValueError("Invalid jobs map in IIMJobs tracker.")
    if not isinstance(log["daily_submissions"], dict):
        raise ValueError("Invalid daily_submissions map in IIMJobs tracker.")

    return log


def save_application_log(path, student_id, account_id, log):
    if not isinstance(log, dict):
        raise TypeError("IIMJobs application log must be a dictionary.")
    jobs = log.get("jobs", {})
    daily_submissions = log.get("daily_submissions", {})
    if not isinstance(jobs, dict) or not isinstance(daily_submissions, dict):
        raise ValueError("Invalid IIMJobs application log structure.")

    path = Path(path)
    store = _load_store(path)
    student = store["students"].setdefault(
        _student_key(student_id),
        {"accounts": {}},
    )
    if not isinstance(student, dict):
        raise ValueError("Invalid student entry in IIMJobs tracker.")
    accounts = student.setdefault("accounts", {})
    if not isinstance(accounts, dict):
        raise ValueError("Invalid accounts map in IIMJobs tracker.")

    accounts[_account_key(account_id)] = {
        "jobs": jobs,
        "daily_submissions": daily_submissions,
    }
    store["schema_version"] = 1
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    with temporary_path.open("w", encoding="utf-8") as file:
        json.dump(store, file, indent=2, ensure_ascii=False)
    temporary_path.replace(path)


def job_key(job):
    url = str(job.get("url", "")).strip()
    if not url:
        return None
    return url


def has_been_submitted(log, job):
    key = job_key(job)
    if not key:
        return False

    record = log.get("jobs", {}).get(key)
    return isinstance(record, dict) and record.get("status") == "submitted"


def get_today_submitted_count(log, today=None):
    today = today or date.today().isoformat()
    jobs = log.get("jobs", {})
    submission_ids = log.get("daily_submissions", {}).get(today, [])
    if not isinstance(jobs, dict) or not isinstance(submission_ids, list):
        return 0

    return sum(
        1
        for key in submission_ids
        if isinstance(jobs.get(key), dict)
        and jobs[key].get("status") == "submitted"
    )


def record_application(log, job, submitted, now=None):
    key = job_key(job)
    if not key:
        raise ValueError("IIMJobs job must have a URL to be tracked.")

    now = now or datetime.now()
    timestamp = now.isoformat()
    status = "submitted" if submitted else "failed"
    log.setdefault("jobs", {})[key] = {
        "title": job.get("title", ""),
        "url": key,
        "status": status,
        "updated_at": timestamp,
    }

    if submitted:
        day = now.date().isoformat()
        daily_submissions = log.setdefault("daily_submissions", {})
        day_ids = daily_submissions.setdefault(day, [])
        if key not in day_ids:
            day_ids.append(key)

    return log

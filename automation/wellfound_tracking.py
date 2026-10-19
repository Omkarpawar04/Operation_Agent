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
    normalized_account = str(account_id).strip().casefold()
    if not normalized_account:
        raise ValueError("Wellfound account email must not be empty.")
    digest = hashlib.sha256(
        normalized_account.encode("utf-8")
    ).hexdigest()
    return f"sha256:{digest}"


def _load_store(path):
    path = Path(path)
    if not path.exists():
        return {"schema_version": 1, "students": {}}

    with path.open("r", encoding="utf-8") as file:
        store = json.load(file)

    if (
        not isinstance(store, dict)
        or not isinstance(store.get("students"), dict)
    ):
        raise ValueError(f"Invalid Wellfound tracker format: {path}")

    return store


def empty_application_log():
    return {"jobs": {}, "daily_submissions": {}, "daily_attempts": {}}


def load_application_log(path, student_id, account_id):
    store = _load_store(path)
    student = store["students"].get(_student_key(student_id), {})
    account = student.get("accounts", {}).get(
        _account_key(account_id),
        {},
    )
    log = {
        "jobs": account.get("jobs", {}),
        "daily_submissions": account.get("daily_submissions", {}),
        "daily_attempts": account.get("daily_attempts", {}),
    }

    if not isinstance(log["jobs"], dict):
        raise ValueError("Invalid jobs map in Wellfound tracker.")
    if not isinstance(log["daily_submissions"], dict):
        raise ValueError("Invalid daily_submissions map in Wellfound tracker.")

    return log


def save_application_log(path, student_id, account_id, log):
    if not isinstance(log, dict):
        raise TypeError("Wellfound application log must be a dictionary.")
    jobs = log.get("jobs", {})
    daily_submissions = log.get("daily_submissions", {})
    daily_attempts = log.get("daily_attempts", {})
    if (
        not isinstance(jobs, dict)
        or not isinstance(daily_submissions, dict)
        or not isinstance(daily_attempts, dict)
    ):
        raise ValueError("Invalid Wellfound application log structure.")

    path = Path(path)
    store = _load_store(path)
    student_key = _student_key(student_id)
    account_key = _account_key(account_id)
    student = store["students"].setdefault(
        student_key,
        {"accounts": {}},
    )
    if not isinstance(student, dict):
        raise ValueError("Invalid student entry in Wellfound tracker.")

    accounts = student.setdefault("accounts", {})
    if not isinstance(accounts, dict):
        raise ValueError("Invalid accounts map in Wellfound tracker.")

    accounts[account_key] = {
        "jobs": jobs,
        "daily_submissions": daily_submissions,
        "daily_attempts": daily_attempts,
    }
    store["schema_version"] = 1
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    with temporary_path.open("w", encoding="utf-8") as file:
        json.dump(store, file, indent=4, ensure_ascii=False)
    temporary_path.replace(path)


def has_been_processed(log, job_key, terminal_statuses):
    record = log.get("jobs", {}).get(job_key)
    return (
        isinstance(record, dict)
        and record.get("status") in terminal_statuses
    )


def get_today_submission_ids(log, today=None):
    today = today or date.today().isoformat()
    records = log.get("daily_submissions", {}).get(today, [])
    return records if isinstance(records, list) else []


def get_today_submitted_count(log, today=None):
    jobs = log.get("jobs", {})
    if not isinstance(jobs, dict):
        return 0

    count = 0
    for job_key in get_today_submission_ids(log, today):
        record = jobs.get(job_key)
        if isinstance(record, dict) and record.get("status") == "submitted":
            count += 1

    return count



def get_today_attempt_count(log, today=None):
    today = today or date.today().isoformat()
    attempts_by_day = log.get("daily_attempts", {})
    if not isinstance(attempts_by_day, dict):
        return 0
    records = attempts_by_day.get(today, [])
    return len(records) if isinstance(records, list) else 0


def record_application_attempt(log, job_key, today=None):
    if not isinstance(log, dict):
        raise TypeError("Wellfound application log must be a dictionary.")
    if not str(job_key).strip():
        raise ValueError("job_key must not be empty.")

    today = today or date.today().isoformat()
    attempts_by_day = log.setdefault("daily_attempts", {})
    if not isinstance(attempts_by_day, dict):
        raise ValueError("Invalid daily_attempts map in Wellfound tracker.")

    records = attempts_by_day.setdefault(today, [])
    if not isinstance(records, list):
        raise ValueError("Invalid daily attempt list in Wellfound tracker.")

    records.append({
        "job_key": str(job_key),
        "attempted_at": datetime.now().isoformat(timespec="seconds"),
    })

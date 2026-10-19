import hashlib
import json
from datetime import date
from pathlib import Path


_SUBMISSION_CONFIRMATION_PHRASES = (
    "application submitted",
    "application has been submitted",
    "application was submitted",
    "application sent successfully",
    "application submitted successfully",
    "successfully applied",
    "successfully applied for",
    "thank you for applying",
    "thank you for your application",
    "your application was received",
    "application received successfully",
    "application received",
    "your application has been received",
)


def submission_confirmation_detected(body):
    normalized_body = str(body or "").strip().casefold()
    return any(
        phrase in normalized_body
        for phrase in _SUBMISSION_CONFIRMATION_PHRASES
    )


def _student_key(student_id):
    normalized_id = str(student_id).strip().casefold()

    if not normalized_id:
        raise ValueError("student_id must not be empty.")

    return normalized_id


def _account_key(account_id):
    normalized_account = str(account_id).strip().casefold()

    if not normalized_account:
        raise ValueError("JobGrin account ID must not be empty.")

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
        raise ValueError(
            f"Invalid JobGrin student tracker format: {path}"
        )

    return store


def load_student_history(path, student_id, account_id):
    store = _load_store(path)
    student = store["students"].get(_student_key(student_id), {})
    account = student.get("accounts", {}).get(
        _account_key(account_id),
        {},
    )
    jobs = account.get("jobs", {})

    if not isinstance(jobs, dict):
        raise ValueError("Invalid jobs map in JobGrin student tracker.")

    return jobs


def save_student_history(path, student_id, account_id, jobs):
    if not isinstance(jobs, dict):
        raise TypeError("JobGrin history must be a dictionary.")

    path = Path(path)
    store = _load_store(path)
    student_key = _student_key(student_id)
    account_key = _account_key(account_id)
    student = store["students"].setdefault(
        student_key,
        {"accounts": {}},
    )

    if not isinstance(student, dict):
        raise ValueError("Invalid student entry in JobGrin tracker.")

    accounts = student.setdefault("accounts", {})

    if not isinstance(accounts, dict):
        raise ValueError("Invalid accounts map in JobGrin tracker.")

    accounts[account_key] = {"jobs": jobs}
    store["schema_version"] = 1
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")

    with temporary_path.open("w", encoding="utf-8") as file:
        json.dump(store, file, indent=2, ensure_ascii=False)

    temporary_path.replace(path)


def has_processed_job(job_key, processed):
    value = processed.get(job_key)

    if not isinstance(value, dict):
        return False

    raw_status = value.get("status", "")
    status = str(raw_status).strip().upper() if raw_status is not None else ""
    return status in {"APPLIED", "ALREADY_APPLIED", "EXTERNAL"}


def applications_today(processed, today=None):
    today = today or date.today().isoformat()
    count = 0

    for value in processed.values():
        if not isinstance(value, dict):
            continue

        raw_status = value.get("status", "")
        status = str(raw_status).strip().upper() if raw_status is not None else ""
        if status != "APPLIED" or value.get("reason") == "ALREADY_APPLIED":
            continue

        timestamp = str(value.get("timestamp", ""))
        if timestamp.startswith(today):
            count += 1

    return count

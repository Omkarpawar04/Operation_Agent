from datetime import date, datetime

if __package__:
    from .jobgrin_tracking import (
        load_student_history,
        save_student_history,
    )
else:
    from jobgrin_tracking import (
        load_student_history,
        save_student_history,
    )


def load_application_history(path, student_id, account_id):
    return load_student_history(path, student_id, account_id)


def save_application_history(path, student_id, account_id, history):
    save_student_history(path, student_id, account_id, history)


def has_application_record(job_url, history):
    return job_url in history


def has_submission_confirmation(message):
    normalized_message = str(message or "").casefold()
    confirmation_phrases = (
        "application submitted",
        "application has been submitted",
        "application was submitted",
        "application sent successfully",
        "application has been sent",
        "application received",
        "thank you for applying",
        "successfully applied",
    )
    return any(
        phrase in normalized_message
        for phrase in confirmation_phrases
    )


def get_today_application_count(history, today=None):
    today = today or date.today()
    count = 0

    for data in history.values():
        try:
            if data.get("status") != "submitted":
                continue

            timestamp = data.get("timestamp", "")
            if not timestamp:
                continue

            if datetime.fromisoformat(timestamp).date() == today:
                count += 1
        except (AttributeError, TypeError, ValueError):
            continue

    return count

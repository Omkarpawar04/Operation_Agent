import pandas as pd
from pathlib import Path
import os


# Excel file location
EXCEL_FILE = Path(__file__).resolve().parent.parent / "data" / "users.xlsx"


def load_users():
    """
    Load applicant/user details from Excel.
    """

    if not EXCEL_FILE.exists():
        raise FileNotFoundError(
            f"Excel file not found: {EXCEL_FILE}"
        )

    df = pd.read_excel(EXCEL_FILE)

    # Replace empty Excel cells with empty strings
    df = df.fillna("")

    # Convert Excel rows into Python dictionaries
    users = df.to_dict(orient="records")

    if not users:
        raise ValueError("No users found in users.xlsx")

    return users


def get_user(index=0):
    """
    Get one user from Excel.

    index=0 means first row after the headers.
    """

    users = load_users()

    selected_student_id = os.environ.get(
        "JOB_AUTOMATION_STUDENT_ID",
        "",
    ).strip()
    if selected_student_id:
        return select_student(users, selected_student_id)

    if index >= len(users):
        raise IndexError(
            f"User index {index} does not exist. "
            f"Only {len(users)} user(s) found."
        )

    return users[index]


def get_student_id(user):
    """Return a required, stable ID from an Excel user record."""
    raw_student_id = user.get("student_id", "")
    student_id = (
        str(raw_student_id).strip()
        if raw_student_id is not None
        else ""
    )

    if not student_id:
        raise ValueError(
            "Each student row in users.xlsx must have a non-empty "
            "'student_id' value."
        )

    return student_id


def select_valid_students(users):
    """Return rows with unique, non-empty student IDs, preserving workbook order."""
    valid_users = []
    seen_ids = set()

    for row_number, user in enumerate(users, start=2):
        if not any(value not in ("", None) for value in user.values()):
            continue

        try:
            student_id = get_student_id(user)
        except ValueError:
            continue

        normalized_id = student_id.casefold()
        if normalized_id in seen_ids:
            raise ValueError(
                f"Duplicate student_id in users.xlsx near row {row_number}."
            )
        seen_ids.add(normalized_id)
        valid_users.append(user)

    if not valid_users:
        raise ValueError("No valid students with student_id were found.")

    return valid_users


def select_student(users, student_id):
    """Select exactly one row by its stable, case-insensitive student ID."""
    normalized_id = str(student_id).strip().casefold()
    if not normalized_id:
        raise ValueError("Selected student_id must not be empty.")

    matches = [
        user
        for user in users
        if str(user.get("student_id", "")).strip().casefold()
        == normalized_id
    ]
    if len(matches) != 1:
        raise ValueError(
            "Selected student_id must match exactly one row in users.xlsx."
        )

    return matches[0]
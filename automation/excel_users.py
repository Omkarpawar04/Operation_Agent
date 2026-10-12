import pandas as pd
from pathlib import Path


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

    if index >= len(users):
        raise IndexError(
            f"User index {index} does not exist. "
            f"Only {len(users)} user(s) found."
        )

    return users[index]
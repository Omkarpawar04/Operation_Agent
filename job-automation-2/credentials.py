"""Read portal login credentials from the shared users.xlsx workbook."""

from pathlib import Path

from openpyxl import load_workbook


WORKBOOK_PATH = Path(__file__).resolve().with_name("users.xlsx")


def load_portal_credentials(portal):
    portal_key = portal.strip().upper().replace(" ", "_")
    if not WORKBOOK_PATH.is_file():
        raise FileNotFoundError(f"Credential workbook not found: {WORKBOOK_PATH}")

    workbook = load_workbook(WORKBOOK_PATH, read_only=True, data_only=True)
    try:
        worksheet = workbook.active
        header_cells = next(worksheet.iter_rows(min_row=1, max_row=1, values_only=True))
        headers = {
            str(value).strip().upper(): index
            for index, value in enumerate(header_cells)
            if value is not None
        }

        portal_prefixes = [portal_key]
        if portal_key == "FRESHERSWORLD":
            # Accept the workbook's FRESHERWORLD spelling as well.
            portal_prefixes.append("FRESHERWORLD")

        credential_pairs = []
        for prefix in portal_prefixes:
            credential_pairs.extend([
                (f"{prefix}_EMAIL", f"{prefix}_PASSWORD"),
                (f"{prefix}_USER_ID", f"{prefix}_PASSWORD"),
                (f"{prefix}_USERNAME", f"{prefix}_PASSWORD"),
            ])
        credential_pairs.extend([
            ("EMAIL", "PASSWORD"),
            ("EMAIL_ID", "PASSWORD"),
            ("USER_ID", "PASSWORD"),
            ("USERNAME", "PASSWORD"),
        ])
        if portal_key == "FRESHERSWORLD":
            # Fall back to the shared Instahyre credentials only if the workbook
            # has no complete Freshersworld-specific pair.
            credential_pairs.append(("INSTAHYRE_EMAIL", "INSTAHYRE_PASSWORD"))

        for row in worksheet.iter_rows(min_row=2, values_only=True):
            for email_header, password_header in credential_pairs:
                email_index = headers.get(email_header)
                password_index = headers.get(password_header)
                if email_index is None or password_index is None:
                    continue
                if email_index >= len(row) or password_index >= len(row):
                    continue

                email = row[email_index]
                password = row[password_index]
                if email and password:
                    return str(email).strip(), str(password).strip()
    finally:
        workbook.close()

    raise ValueError(
        f"No complete {portal_key} email/password pair was found in "
        f"{WORKBOOK_PATH.name}."
    )

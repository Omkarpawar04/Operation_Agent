import re
import time
import os
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import pandas as pd
from excel_users import get_student_id, get_user
from placementindia_tracking import (
    get_today_application_count,
    has_submission_confirmation,
    has_application_record,
    load_application_history as load_scoped_application_history,
    save_application_history as save_scoped_application_history,
)
from application_limits import (
    DAILY_APPLICATION_LIMIT,
    has_reached_daily_limit,
)

from selenium import webdriver
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# ============================================================
# SETTINGS
# ============================================================

BASE_URL = "https://www.placementindia.com"

MAX_APPLICATIONS_PER_DAY = DAILY_APPLICATION_LIMIT

# Excel file
DATA_FILE = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "users.xlsx"
)

# Legacy application history; retained unchanged and never loaded for attribution.
LEGACY_APPLICATION_LOG_FILE = (
    Path(__file__).resolve().parent
    / "placementindia_applications.json"
)

# Student- and account-scoped application history.
APPLICATION_LOG_FILE = (
    Path(__file__).resolve().parent
    / "placementindia_student_applications.json"
)

# ============================================================
# GLOBAL USER SETTINGS
# ============================================================

EMAIL = ""
PASSWORD = ""
STUDENT_ID = ""

SEARCH_KEYWORD = ""
SEARCH_CITY = ""
JOB_POSTED = ""

# Optional settings
MAX_EXPERIENCE = ""


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def clean_excel_value(value, default=""):
    """
    Convert Excel values into clean strings.
    """
    if pd.isna(value):
        return default

    value = str(value).strip()

    if value.lower() in ["nan", "none", "null"]:
        return default

    return value


def normalize_text(text):
    """
    Normalize text for comparison.
    """
    if not text:
        return ""

    return re.sub(r"\s+", " ", text).strip().lower()


# ============================================================
# LOAD SETTINGS FROM EXCEL
# ============================================================

def load_user_settings():
    """
    Load PlacementIndia credentials and job-search settings
    from data/users.xlsx.

    Column names are handled case-insensitively.
    """

    global EMAIL
    global PASSWORD
    global STUDENT_ID
    global SEARCH_KEYWORD
    global SEARCH_CITY
    global JOB_POSTED
    global MAX_EXPERIENCE

    print("\n" + "=" * 70)
    print("LOADING USER SETTINGS FROM EXCEL")
    print("=" * 70)

    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"\nExcel file not found:\n{DATA_FILE}\n\n"
            "Expected structure:\n"
            "project/\n"
            "  automation/\n"
            "  data/\n"
            "    users.xlsx"
        )

    try:
        df = pd.read_excel(DATA_FILE)

    except Exception as e:
        raise Exception(
            f"Unable to read Excel file.\nError: {e}"
        )

    if df.empty:
        raise Exception(
            "users.xlsx is empty. Add at least one user row."
        )

    print(f"Excel file loaded: {DATA_FILE}")
    print(f"Rows found: {len(df)}")

    print("\nExcel columns:")

    for column in df.columns:
        print(f"  - {column}")

    # ========================================================
    # NORMALIZE COLUMN NAMES
    # ========================================================
    #
    # Example:
    #
    # PLACEMENTINDIA_EMAIL
    # PlacementIndia_Email
    # placementindia_email
    #
    # All become:
    #
    # placementindia_email
    #
    # ========================================================

    normalized_columns = {}

    for column in df.columns:

        normalized_name = str(
            column
        ).strip().lower()

        normalized_columns[
            normalized_name
        ] = column

    # ========================================================
    # FIRST USER
    # ========================================================

    user = pd.Series(get_user())

    student_id_column = normalized_columns.get("student_id")

    if not student_id_column:
        raise ValueError(
            "A 'student_id' column is required in users.xlsx."
        )

    STUDENT_ID = get_student_id(user.to_dict())

    if not STUDENT_ID:
        raise ValueError(
            "The selected student row must have a non-empty student_id."
        )

    # ========================================================
    # PLACEMENTINDIA EMAIL
    # ========================================================

    email_column = None

    if "placementindia_email" in normalized_columns:

        email_column = normalized_columns[
            "placementindia_email"
        ]

    elif "email" in normalized_columns:

        email_column = normalized_columns[
            "email"
        ]

    # ========================================================
    # PLACEMENTINDIA PASSWORD
    # ========================================================

    password_column = None

    if "placementindia_password" in normalized_columns:

        password_column = normalized_columns[
            "placementindia_password"
        ]

    elif "password" in normalized_columns:

        password_column = normalized_columns[
            "password"
        ]

    # ========================================================
    # VALIDATE CREDENTIAL COLUMNS
    # ========================================================

    if not email_column:

        raise Exception(
            "\nPlacementIndia email column not found.\n\n"
            "Add one of these columns to users.xlsx:\n"
            "  PLACEMENTINDIA_EMAIL\n"
            "or\n"
            "  placementindia_email\n"
            "or\n"
            "  email"
        )

    if not password_column:

        raise Exception(
            "\nPlacementIndia password column not found.\n\n"
            "Add one of these columns to users.xlsx:\n"
            "  PLACEMENTINDIA_PASSWORD\n"
            "or\n"
            "  placementindia_password\n"
            "or\n"
            "  password"
        )

    # ========================================================
    # LOAD CREDENTIALS
    # ========================================================

    EMAIL = clean_excel_value(
        user[email_column]
    )

    if not EMAIL:
        raise ValueError(
            "The selected student row must have a non-empty "
            "PlacementIndia account email."
        )

    PASSWORD = clean_excel_value(
        user[password_column]
    )

    # ========================================================
    # JOB KEYWORD
    # ========================================================

    if "job_keyword" in normalized_columns:

        keyword_column = normalized_columns[
            "job_keyword"
        ]

        SEARCH_KEYWORD = clean_excel_value(
            user[keyword_column],
            "Financial Analyst"
        )

    elif "keyword" in normalized_columns:

        keyword_column = normalized_columns[
            "keyword"
        ]

        SEARCH_KEYWORD = clean_excel_value(
            user[keyword_column],
            "Financial Analyst"
        )

    else:

        SEARCH_KEYWORD = "Financial Analyst"

    # ========================================================
    # CITY
    # ========================================================

    if "city" in normalized_columns:

        city_column = normalized_columns[
            "city"
        ]

        SEARCH_CITY = clean_excel_value(
            user[city_column]
        )

    elif "location" in normalized_columns:

        location_column = normalized_columns[
            "location"
        ]

        SEARCH_CITY = clean_excel_value(
            user[location_column]
        )

    else:

        SEARCH_CITY = ""

    # ========================================================
    # JOB POSTED FILTER
    # ========================================================

    if "job_posted" in normalized_columns:

        posted_column = normalized_columns[
            "job_posted"
        ]

        JOB_POSTED = clean_excel_value(
            user[posted_column],
            "All"
        )

    elif "posted" in normalized_columns:

        posted_column = normalized_columns[
            "posted"
        ]

        JOB_POSTED = clean_excel_value(
            user[posted_column],
            "All"
        )

    else:

        JOB_POSTED = "All"

    # ========================================================
    # EXPERIENCE
    # ========================================================

    if "experience" in normalized_columns:

        experience_column = normalized_columns[
            "experience"
        ]

        MAX_EXPERIENCE = clean_excel_value(
            user[experience_column]
        )

    else:

        MAX_EXPERIENCE = ""

    # ========================================================
    # VALIDATION
    # ========================================================

    if not EMAIL:

        raise Exception(
            "PlacementIndia email is empty in users.xlsx."
        )

    if not PASSWORD:

        raise Exception(
            "PlacementIndia password is empty in users.xlsx."
        )

    if not SEARCH_KEYWORD:

        SEARCH_KEYWORD = "Financial Analyst"

    if not JOB_POSTED:

        JOB_POSTED = "All"

    # ========================================================
    # DISPLAY SETTINGS
    # ========================================================

    print("\nLoaded settings:")

    print(
        f"Email       : {EMAIL}"
    )

    print(
        f"Password    : {'*' * 8}"
    )

    print(
        f"Keyword     : {SEARCH_KEYWORD}"
    )

    print(
        f"City        : "
        f"{SEARCH_CITY or 'All Cities'}"
    )

    print(
        f"Posted      : {JOB_POSTED}"
    )

    print(
        f"Experience  : "
        f"{MAX_EXPERIENCE if MAX_EXPERIENCE else 'Not set'}"
    )

    print("=" * 70)


# ============================================================
# BROWSER
# ============================================================

def start_browser():
    print("\n" + "=" * 70)
    print("STARTING CHROME")
    print("=" * 70)

    options = Options()

    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")

    profile_dir = os.environ.get("JOB_AUTOMATION_PROFILE_DIR")
    if profile_dir:
        options.add_argument(f"--user-data-dir={profile_dir}")

    driver = webdriver.Chrome(options=options)

    driver.set_page_load_timeout(60)

    print("Chrome started.")

    return driver


# ============================================================
# OPEN PLACEMENTINDIA
# ============================================================

def open_placementindia(driver):
    print("\nOpening PlacementIndia...")

    driver.get(BASE_URL)

    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located(
            (By.TAG_NAME, "body")
        )
    )

    time.sleep(3)

    print("PlacementIndia opened.")
    print("URL:", driver.current_url)
    print("Title:", driver.title)


# ============================================================
# LOGIN
# ============================================================

def click_login(driver):
    print("\nClicking Login...")

    selectors = (
        (
            By.XPATH,
            "//a[contains(translate(normalize-space(.), "
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', "
            "'abcdefghijklmnopqrstuvwxyz'), 'login')]"
        ),
        (
            By.XPATH,
            "//button[contains(translate(normalize-space(.), "
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', "
            "'abcdefghijklmnopqrstuvwxyz'), 'login')]"
        ),
        (
            By.LINK_TEXT,
            "Login"
        ),
    )

    def find_visible_login_control(current_driver):
        for by, selector in selectors:
            for element in current_driver.find_elements(by, selector):
                try:
                    if element.is_displayed() and element.is_enabled():
                        return element
                except StaleElementReferenceException:
                    continue

        return False

    try:
        element = WebDriverWait(driver, 10).until(
            find_visible_login_control
        )
    except TimeoutException:
        log_login_page_diagnostic(driver)
        print(
            "Login control not found: no visible, enabled anchor or "
            "button matched the existing Login selectors."
        )
        return False

    driver.execute_script(
        "arguments[0].click();",
        element
    )

    time.sleep(2)

    print("Login clicked.")

    return True


def log_login_page_diagnostic(driver):
    try:
        parsed_url = urlsplit(driver.current_url)
        hostname = parsed_url.hostname or "<unknown-host>"
        if parsed_url.port:
            hostname = f"{hostname}:{parsed_url.port}"
        safe_url = urlunsplit(
            (
                parsed_url.scheme,
                hostname,
                _safe_diagnostic_value(parsed_url.path),
                "",
                "",
            )
        )
    except WebDriverException:
        safe_url = "<unavailable>"

    try:
        page_title = driver.title
    except WebDriverException:
        page_title = "<unavailable>"

    visible_fields = []
    try:
        for element in driver.find_elements(
            By.CSS_SELECTOR,
            "input, textarea, select",
        ):
            try:
                if not element.is_displayed():
                    continue
                visible_fields.append(
                    "type="
                    + _safe_diagnostic_value(
                        element.get_attribute("type")
                    )
                    + ", name="
                    + _safe_diagnostic_value(
                        element.get_attribute("name")
                    )
                    + ", placeholder="
                    + _safe_diagnostic_value(
                        element.get_attribute("placeholder")
                    )
                )
            except StaleElementReferenceException:
                continue
    except WebDriverException:
        visible_fields = ["<unavailable>"]

    visible_controls = []
    try:
        for element in driver.find_elements(
            By.CSS_SELECTOR,
            "button, a, [role='button']",
        ):
            try:
                if not element.is_displayed():
                    continue
                label = (
                    element.text
                    or element.get_attribute("aria-label")
                    or element.get_attribute("value")
                    or ""
                )
                visible_controls.append(
                    _safe_diagnostic_value(label)
                )
            except StaleElementReferenceException:
                continue
    except WebDriverException:
        visible_controls = ["<unavailable>"]

    try:
        iframe_count = len(
            driver.find_elements(By.TAG_NAME, "iframe")
        )
    except WebDriverException:
        iframe_count = "unavailable"

    print(
        "[PlacementIndia login diagnostic] "
        f"URL={safe_url!r}; title={page_title!r}; "
        f"visible_fields={visible_fields[:20]!r}; "
        f"visible_buttons_links={visible_controls[:30]!r}; "
        f"iframe_count={iframe_count}. "
        "Field values, cookies, and page body text were not logged."
    )


def _safe_diagnostic_value(value):
    value = re.sub(r"\s+", " ", str(value or "")).strip()
    value = re.sub(
        r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}",
        "<redacted-email>",
        value,
    )
    value = re.sub(
        r"\b[A-Za-z0-9_-]{24,}\b",
        "<redacted-token>",
        value,
    )
    return value[:120]


def enter_email(driver):
    print("Entering email...")

    email_selectors = [
        (
            By.XPATH,
            "//input[contains(@placeholder,'Email')]"
        ),
        (
            By.XPATH,
            "//input[contains(@placeholder,'email')]"
        ),
        (
            By.XPATH,
            "//input[contains(@type,'email')]"
        ),
        (
            By.XPATH,
            "//input[contains(@name,'email')]"
        ),
    ]

    for by, selector in email_selectors:

        try:

            element = WebDriverWait(
                driver,
                10
            ).until(
                EC.visibility_of_element_located(
                    (by, selector)
                )
            )

            element.clear()
            element.send_keys(EMAIL)

            print("Email entered.")

            return True

        except Exception:
            continue

    print("Email input not found.")

    return False


def click_continue(driver):
    print("Clicking Continue...")

    selectors = [
        (
            By.XPATH,
            "//button[contains(translate(normalize-space(.), "
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', "
            "'abcdefghijklmnopqrstuvwxyz'), 'continue')]"
        ),
        (
            By.XPATH,
            "//input[@value='Continue']"
        ),
        (
            By.XPATH,
            "//button[contains(translate(normalize-space(.), "
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', "
            "'abcdefghijklmnopqrstuvwxyz'), 'next')]"
        ),
    ]

    for by, selector in selectors:

        try:

            elements = driver.find_elements(
                by,
                selector
            )

            for element in elements:

                if element.is_displayed():

                    driver.execute_script(
                        "arguments[0].click();",
                        element
                    )

                    time.sleep(2)

                    print("Continue clicked.")

                    return True

        except Exception:
            continue

    print("Continue button not found.")

    return False


def enter_password(driver):
    print("Entering password...")

    password_selectors = [
        (
            By.XPATH,
            "//input[@type='password']"
        ),
        (
            By.XPATH,
            "//input[contains(@name,'password')]"
        ),
        (
            By.XPATH,
            "//input[contains(@placeholder,'Password')]"
        ),
    ]

    for by, selector in password_selectors:

        try:

            element = WebDriverWait(
                driver,
                15
            ).until(
                EC.visibility_of_element_located(
                    (by, selector)
                )
            )

            element.clear()
            element.send_keys(PASSWORD)

            print("Password entered.")

            return True

        except Exception:
            continue

    print("Password input not found.")

    return False


def click_final_login(driver):
    print("Clicking final Login...")

    selectors = [
        (
            By.XPATH,
            "//button[contains(translate(normalize-space(.), "
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', "
            "'abcdefghijklmnopqrstuvwxyz'), 'login')]"
        ),
        (
            By.XPATH,
            "//input[@value='Login']"
        ),
        (
            By.XPATH,
            "//button[@type='submit']"
        ),
    ]

    for by, selector in selectors:

        try:

            elements = driver.find_elements(
                by,
                selector
            )

            for element in elements:

                if element.is_displayed():

                    driver.execute_script(
                        "arguments[0].click();",
                        element
                    )

                    time.sleep(5)

                    print("Final Login clicked.")

                    return True

        except Exception:
            continue

    print("Final Login button not found.")

    return False


def verify_login(driver):
    print("\nVerifying login...", flush=True)

    time.sleep(3)

    try:
        page_text = normalize_text(
            driver.find_element(By.TAG_NAME, "body").text
        )
    except WebDriverException:
        page_text = ""

    # Strong indicators that an account session is authenticated.
    login_indicators = [
        "logout",
        "log out",
        "my profile",
        "dashboard",
        "my account",
    ]

    for indicator in login_indicators:
        if indicator in page_text:
            print(
                f"Login verification successful: '{indicator}' found.",
                flush=True,
            )
            return True

    # PlacementIndia's account page can show these counters without
    # displaying the words "Dashboard", "My Account", or "Logout".
    has_applied_jobs = "applied jobs" in page_text
    has_profile_views = "profile view" in page_text
    has_my_messages = "my messages" in page_text

    if has_applied_jobs and (has_profile_views or has_my_messages):
        print(
            "Login verification successful: account application "
            "and profile/message counters found.",
            flush=True,
        )
        return True

    print(
        "Could not verify an authenticated PlacementIndia session.",
        flush=True,
    )
    log_login_page_diagnostic(driver)
    return False


def login_placementindia(driver):

    print("\n" + "=" * 70)
    print("PLACEMENTINDIA LOGIN")
    print("=" * 70)

    if verify_login(driver):
        print("Existing PlacementIndia session is already authenticated.")
        return True

    if not click_login(driver):
        return False

    if not enter_email(driver):
        return False

    if not click_continue(driver):
        return False

    if not enter_password(driver):
        return False

    if not click_final_login(driver):
        return False

    return verify_login(driver)


# ============================================================
# OPEN JOB SEARCH
# ============================================================

def open_job_search(driver):

    print("\n" + "=" * 70)
    print("OPENING JOB SEARCH")
    print("=" * 70)

    search_url = (
        BASE_URL
        + "/job-search/"
    )

    driver.get(search_url)

    WebDriverWait(
        driver,
        30
    ).until(
        EC.presence_of_element_located(
            (By.TAG_NAME, "body")
        )
    )

    time.sleep(3)

    print("Job search opened.")
    print("URL:", driver.current_url)


# ============================================================
# FIND KEYWORD SEARCH BAR
# ============================================================

def find_search_bar(driver):

    selectors = [

        (
            By.XPATH,
            "//input[contains(@placeholder,"
            "'Skills')]"
        ),

        (
            By.XPATH,
            "//input[contains(@placeholder,"
            "'Designation')]"
        ),

        (
            By.XPATH,
            "//input[contains(@placeholder,"
            "'Enter Skills')]"
        ),

        (
            By.XPATH,
            "//input[contains(@name,'keyword')]"
        ),

        (
            By.XPATH,
            "//input[contains(@name,'skills')]"
        ),

        (
            By.XPATH,
            "//input[contains(@id,'keyword')]"
        ),

        (
            By.XPATH,
            "//input[contains(@id,'search')]"
        ),
    ]

    for by, selector in selectors:

        try:

            elements = driver.find_elements(
                by,
                selector
            )

            for element in elements:

                if element.is_displayed():

                    return element

        except Exception:
            continue

    return None


# ============================================================
# FIND LOCATION / CITY INPUT
# ============================================================

def find_city_input(driver):

    print("Looking for city/location field...")

    selectors = [

        # Placeholder based
        (
            By.XPATH,
            "//input[contains(translate(@placeholder,"
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
            "'abcdefghijklmnopqrstuvwxyz'),'location')]"
        ),

        (
            By.XPATH,
            "//input[contains(translate(@placeholder,"
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
            "'abcdefghijklmnopqrstuvwxyz'),'city')]"
        ),

        (
            By.XPATH,
            "//input[contains(translate(@placeholder,"
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
            "'abcdefghijklmnopqrstuvwxyz'),'place')]"
        ),

        # Name based
        (
            By.XPATH,
            "//input[contains(translate(@name,"
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
            "'abcdefghijklmnopqrstuvwxyz'),'location')]"
        ),

        (
            By.XPATH,
            "//input[contains(translate(@name,"
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
            "'abcdefghijklmnopqrstuvwxyz'),'city')]"
        ),

        # ID based
        (
            By.XPATH,
            "//input[contains(translate(@id,"
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
            "'abcdefghijklmnopqrstuvwxyz'),'location')]"
        ),

        (
            By.XPATH,
            "//input[contains(translate(@id,"
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
            "'abcdefghijklmnopqrstuvwxyz'),'city')]"
        ),

        # Generic fallback - inputs near location text
        (
            By.XPATH,
            "//label[contains(translate(normalize-space(.),"
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
            "'abcdefghijklmnopqrstuvwxyz'),'location')]"
            "/following::input[1]"
        ),

        (
            By.XPATH,
            "//*[contains(translate(normalize-space(.),"
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
            "'abcdefghijklmnopqrstuvwxyz'),'location')]"
            "/following::input[1]"
        ),
    ]

    for by, selector in selectors:

        try:

            elements = driver.find_elements(
                by,
                selector
            )

            for element in elements:

                if element.is_displayed() and element.is_enabled():

                    print(
                        "City/location input found."
                    )

                    return element

        except Exception:
            continue

    print(
        "City/location input NOT found."
    )

    return None


# ============================================================
# SELECT CITY AUTOCOMPLETE
# ============================================================

def select_city_suggestion(driver, city):

    if not city:
        return False

    print(
        f"Looking for city suggestion: {city}"
    )

    city_normalized = normalize_text(city)

    # Give autocomplete time to load
    time.sleep(2)

    # ========================================================
    # TRY COMMON AUTOCOMPLETE ELEMENTS
    # ========================================================

    selectors = [

        # li suggestions
        (
            By.XPATH,
            "//li[contains(translate(normalize-space(.),"
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
            "'abcdefghijklmnopqrstuvwxyz'),"
            f"'{city_normalized}')]"
        ),

        # div suggestions
        (
            By.XPATH,
            "//div[contains(translate(normalize-space(.),"
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
            "'abcdefghijklmnopqrstuvwxyz'),"
            f"'{city_normalized}')]"
        ),

        # span suggestions
        (
            By.XPATH,
            "//span[contains(translate(normalize-space(.),"
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
            "'abcdefghijklmnopqrstuvwxyz'),"
            f"'{city_normalized}')]"
        ),

        # option
        (
            By.XPATH,
            "//option[contains(translate(normalize-space(.),"
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
            "'abcdefghijklmnopqrstuvwxyz'),"
            f"'{city_normalized}')]"
        ),

    ]

    # ========================================================
    # FIRST TRY: EXACT CITY MATCH
    # ========================================================

    for by, selector in selectors:

        try:

            elements = driver.find_elements(
                by,
                selector
            )

            for element in elements:

                if not element.is_displayed():
                    continue

                text = normalize_text(
                    element.text
                )

                if (
                    text == city_normalized
                    or city_normalized in text
                ):

                    print(
                        f"City suggestion found: "
                        f"{element.text}"
                    )

                    driver.execute_script(
                        """
                        arguments[0].scrollIntoView({
                            block: 'center'
                        });
                        """,
                        element
                    )

                    time.sleep(0.5)

                    driver.execute_script(
                        "arguments[0].click();",
                        element
                    )

                    time.sleep(1)

                    print(
                        f"City selected successfully: {city}"
                    )

                    return True

        except Exception:
            continue

    # ========================================================
    # SECOND METHOD: PRESS ARROW DOWN + ENTER
    # ========================================================

    print(
        "City suggestion not found directly."
    )

    print(
        "Trying keyboard autocomplete..."
    )

    try:

        city_input = find_city_input(
            driver
        )

        if city_input:

            city_input.click()

            time.sleep(1)

            city_input.send_keys(
                "\ue015"
            )  # ARROW_DOWN

            time.sleep(0.5)

            city_input.send_keys(
                "\ue007"
            )  # ENTER

            time.sleep(1)

            print(
                f"City selected using keyboard: "
                f"{city}"
            )

            return True

    except Exception as e:

        print(
            "Keyboard city selection failed:",
            e
        )

    print(
        f"Could not select city: {city}"
    )

    return False


# ============================================================
# FIND SEARCH BUTTON
# ============================================================

def find_search_button(driver):

    selectors = [

        (
            By.XPATH,
            "//button[contains(translate(normalize-space(.), "
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', "
            "'abcdefghijklmnopqrstuvwxyz'), 'search')]"
        ),

        (
            By.XPATH,
            "//input[@value='Search']"
        ),

        (
            By.XPATH,
            "//input[@type='submit']"
        ),

        (
            By.XPATH,
            "//button[@type='submit']"
        ),

    ]

    for by, selector in selectors:

        try:

            elements = driver.find_elements(
                by,
                selector
            )

            for element in elements:

                if element.is_displayed():

                    return element

        except Exception:
            continue

    return None


# ============================================================
# SEARCH JOBS WITH KEYWORD + CITY
# ============================================================

def search_jobs(driver, keyword, city=""):

    print("\n" + "=" * 70)
    print("APPLYING JOB SEARCH FILTERS")
    print("=" * 70)

    print(f"Keyword : {keyword}")
    print(
        f"City    : "
        f"{city if city else 'All Cities'}"
    )

    # ========================================================
    # KEYWORD
    # ========================================================

    search_bar = find_search_bar(
        driver
    )

    if not search_bar:

        raise Exception(
            "Could not find PlacementIndia keyword search bar."
        )

    search_bar.click()

    search_bar.clear()

    search_bar.send_keys(
        keyword
    )

    print(
        f"Keyword entered: {keyword}"
    )

    # ========================================================
    # CITY
    # ========================================================

    if city:

        city_input = find_city_input(
            driver
        )

        if city_input:

            print(
                f"Entering city: {city}"
            )

            city_input.click()

            city_input.clear()

            city_input.send_keys(
                city
            )

            # IMPORTANT:
            # Wait for PlacementIndia autocomplete
            time.sleep(2)

            city_selected = (
                select_city_suggestion(
                    driver,
                    city
                )
            )

            if city_selected:

                print(
                    f"âœ“ City selected: {city}"
                )

            else:

                print(
                    f"âš  Could not confirm city "
                    f"selection: {city}"
                )

        else:

            print(
                "âš  City/location field was not found."
            )

    else:

        print(
            "No city filter configured."
        )

    # ========================================================
    # SEARCH BUTTON
    # ========================================================

    search_button = find_search_button(
        driver
    )

    if not search_button:

        raise Exception(
            "Could not find PlacementIndia Search button."
        )

    print(
        "Clicking Search..."
    )

    driver.execute_script(
        """
        arguments[0].scrollIntoView({
            block: 'center'
        });
        """,
        search_button
    )

    time.sleep(0.5)

    driver.execute_script(
        "arguments[0].click();",
        search_button
    )

    print(
        "Search clicked."
    )

    # ========================================================
    # WAIT FOR RESULTS
    # ========================================================

    time.sleep(5)

    try:

        WebDriverWait(
            driver,
            20
        ).until(
            EC.presence_of_element_located(
                (By.TAG_NAME, "body")
            )
        )

    except TimeoutException:

        pass

    print(
        "\nSearch results loaded."
    )

    print(
        "Current URL:",
        driver.current_url
    )

    print(
        "Page title:",
        driver.title
    )


# ============================================================
# SORT BY DATE / LATEST
# ============================================================

def sort_by_latest(driver):

    print("\n" + "=" * 70)
    print("SORTING JOBS BY LATEST DATE")
    print("=" * 70)

    selectors = [

        (
            By.XPATH,
            "//a[contains(translate(normalize-space(.), "
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', "
            "'abcdefghijklmnopqrstuvwxyz'), 'date')]"
        ),

        (
            By.XPATH,
            "//button[contains(translate(normalize-space(.), "
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', "
            "'abcdefghijklmnopqrstuvwxyz'), 'date')]"
        ),

        (
            By.XPATH,
            "//*[contains(translate(normalize-space(.), "
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', "
            "'abcdefghijklmnopqrstuvwxyz'), 'date')]"
        ),

    ]

    for by, selector in selectors:

        try:

            elements = driver.find_elements(
                by,
                selector
            )

            for element in elements:

                if not element.is_displayed():
                    continue

                text = normalize_text(
                    element.text
                )

                if text == "date" or "date" in text:

                    driver.execute_script(
                        "arguments[0].click();",
                        element
                    )

                    time.sleep(4)

                    print(
                        "Date sorting applied."
                    )

                    return True

        except Exception:
            continue

    print(
        "Date sorting button not found."
    )

    print(
        "The script will still perform "
        "local latest-job filtering."
    )

    return False


# ============================================================
# POSTED DATE FILTER
# ============================================================

def get_posted_days(posted_text):

    """
    Convert PlacementIndia text into number of days.

    Examples:

    Today
        -> 0

    1 days ago
        -> 1

    3 days ago
        -> 3

    15 days ago
        -> 15
    """

    if not posted_text:
        return None

    text = normalize_text(
        posted_text
    )

    if "today" in text:
        return 0

    match = re.search(
        r"(\d+)\s*day",
        text
    )

    if match:
        return int(
            match.group(1)
        )

    if "yesterday" in text:
        return 1

    return None


def get_posted_limit(job_posted):

    value = normalize_text(
        job_posted
    )

    if value in [
        "",
        "all",
        "all jobs",
        "any",
        "anytime",
    ]:
        return None

    if value == "today":
        return 0

    match = re.search(
        r"(\d+)",
        value
    )

    if match:
        return int(
            match.group(1)
        )

    return None


def job_matches_posted_filter(
    posted_text,
    job_posted
):

    limit = get_posted_limit(
        job_posted
    )

    if limit is None:
        return True

    posted_days = get_posted_days(
        posted_text
    )

    # If website did not expose the date,
    # don't reject the job.
    if posted_days is None:
        return True

    return posted_days <= limit


# ============================================================
# EXTRACT JOB CARD
# ============================================================

def find_job_card(
    driver,
    job_link
):

    try:

        # Find the closest useful container
        card = job_link.find_element(
            By.XPATH,
            "./ancestor::*[self::article or self::li or self::div]"
            "[.//a[contains(@href,'/job-detail/')]][1]"
        )

        return card

    except Exception:
        pass

    # Fallback
    try:

        return job_link.find_element(
            By.XPATH,
            "./ancestor::div[1]"
        )

    except Exception:
        return None


# ============================================================
# EXTRACT JOBS
# ============================================================

def extract_jobs(
    driver,
    city="",
    job_posted="All"
):

    print("\n" + "=" * 70)
    print("EXTRACTING JOBS")
    print("=" * 70)

    jobs = []

    seen_urls = set()

    links = driver.find_elements(
        By.XPATH,
        "//a[contains(@href,'/job-detail/')]"
    )

    print(
        f"Job links found on page: {len(links)}"
    )

    for link in links:

        try:

            href = link.get_attribute(
                "href"
            )

            title = link.text.strip()

            if not href:
                continue

            if not title:
                continue

            if href in seen_urls:
                continue

            seen_urls.add(href)

            # ------------------------------------------------
            # FIND JOB CARD
            # ------------------------------------------------

            card = find_job_card(
                driver,
                link
            )

            card_text = ""

            if card:

                try:
                    card_text = card.text.strip()

                except Exception:
                    card_text = ""

            # ------------------------------------------------
            # POSTED DATE
            # ------------------------------------------------

            posted_match = re.search(
                r"Posted\s+on\s+([^\n]+)",
                card_text,
                re.IGNORECASE
            )

            posted_text = ""

            if posted_match:

                posted_text = (
                    posted_match
                    .group(1)
                    .strip()
                )

            # ------------------------------------------------
            # POSTED DATE FILTER
            # ------------------------------------------------
            #
            # IMPORTANT:
            # City is NOT checked here.
            #
            # PlacementIndia already applied city
            # through:
            #
            # seeker_search_city
            #
            # ------------------------------------------------

            if not job_matches_posted_filter(
                posted_text,
                job_posted
            ):

                print(
                    f"[DATE SKIP] {title} | "
                    f"Posted: {posted_text}"
                )

                continue

            # ------------------------------------------------
            # SAVE JOB
            # ------------------------------------------------

            job = {
                "title": title,
                "url": href,
                "posted": posted_text,
                "city": city,
                "card_text": card_text,
            }

            jobs.append(job)

        except (
            StaleElementReferenceException,
            NoSuchElementException,
        ):
            continue

        except Exception:
            continue

    print(
        f"\nJobs remaining after filters: "
        f"{len(jobs)}"
    )

    return jobs


# ============================================================
# DISPLAY JOBS
# ============================================================

def display_jobs(jobs):

    print("\n" + "=" * 70)
    print("FILTERED JOBS")
    print("=" * 70)

    if not jobs:

        print(
            "No jobs matched the selected filters."
        )

        return

    for index, job in enumerate(
        jobs,
        start=1
    ):

        print(
            f"\n{index}. {job['title']}"
        )

        print(
            f"   Posted : "
            f"{job['posted'] or 'Unknown'}"
        )

        print(
            f"   City   : "
            f"{job['city'] or 'All'}"
        )

        print(
            f"   URL    : "
            f"{job['url']}"
        )


# ============================================================
# APPLICATION HISTORY
# ============================================================

def load_application_history():
    if not STUDENT_ID or not EMAIL:
        raise ValueError(
            "Load the selected student's PlacementIndia settings "
            "before loading application history."
        )

    return load_scoped_application_history(
        APPLICATION_LOG_FILE,
        STUDENT_ID,
        EMAIL,
    )


def save_application_history(history):
    if not STUDENT_ID or not EMAIL:
        raise ValueError(
            "Load the selected student's PlacementIndia settings "
            "before saving application history."
        )

    save_scoped_application_history(
        APPLICATION_LOG_FILE,
        STUDENT_ID,
        EMAIL,
        history,
    )


# ============================================================
# FIND APPLY BUTTON
# ============================================================

def find_apply_button(driver):

    selectors = [

        (
            By.XPATH,
            "//a[contains(translate(normalize-space(.), "
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', "
            "'abcdefghijklmnopqrstuvwxyz'), 'apply now')]"
        ),

        (
            By.XPATH,
            "//button[contains(translate(normalize-space(.), "
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', "
            "'abcdefghijklmnopqrstuvwxyz'), 'apply now')]"
        ),

        (
            By.XPATH,
            "//a[contains(translate(normalize-space(.), "
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', "
            "'abcdefghijklmnopqrstuvwxyz'), 'apply')]"
        ),

        (
            By.XPATH,
            "//button[contains(translate(normalize-space(.), "
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', "
            "'abcdefghijklmnopqrstuvwxyz'), 'apply')]"
        ),

        (
            By.XPATH,
            "//*[contains(@class,'apply')]"
        ),

    ]

    for by, selector in selectors:

        try:

            elements = driver.find_elements(
                by,
                selector
            )

            for element in elements:

                if element.is_displayed():

                    return element

        except Exception:
            continue

    return None


# ============================================================
# CLICK APPLY
# ============================================================

def click_apply_button(driver):

    print("Looking for Apply button...")

    button = find_apply_button(
        driver
    )

    if not button:

        print(
            "Apply button not found."
        )

        return False

    try:

        driver.execute_script(
            """
            arguments[0].scrollIntoView({
                block: 'center'
            });
            """,
            button
        )

        time.sleep(1)

        driver.execute_script(
            "arguments[0].click();",
            button
        )

        print(
            "Apply button clicked."
        )

        deadline = time.monotonic() + 15
        last_error = None
        while time.monotonic() < deadline:
            try:
                body_text = driver.find_element(
                    By.TAG_NAME,
                    "body",
                ).text
                if has_submission_confirmation(body_text):
                    print("Application submission confirmed.")
                    return True
            except Exception as error:
                last_error = error
            time.sleep(1)

        if last_error is not None:
            print(
                "Could not read submission confirmation:",
                type(last_error).__name__,
            )
        print(
            "Apply was clicked, but successful submission "
            "was not confirmed."
        )
        return False

    except (
        ElementClickInterceptedException,
        Exception,
    ) as e:

        print(
            "Could not click Apply:",
            e
        )

        return False


# ============================================================
# PROCESS JOBS
# ============================================================

def process_jobs(
    driver,
    jobs
):

    print("\n" + "=" * 70)
    print("PROCESSING JOB APPLICATIONS")
    print("=" * 70)

    history = load_application_history()

    today_count = get_today_application_count(
        history
    )

    print(
        f"Applications already sent today: "
        f"{today_count}"
    )

    remaining_today = (
        MAX_APPLICATIONS_PER_DAY
        - today_count
    )

    if remaining_today <= 0:

        print(
            "\nDaily application limit already reached."
        )

        return

    print(
        f"Applications remaining today: "
        f"{remaining_today}"
    )

    applications_sent = 0

    for index, job in enumerate(
        jobs,
        start=1
    ):

        if applications_sent >= remaining_today:
            break

        job_url = job["url"]
        job_title = job["title"]

        print("\n" + "-" * 70)
        print(
            f"JOB {index}/{len(jobs)}"
        )
        print(
            f"Title : {job_title}"
        )
        print(
            f"Posted: "
            f"{job.get('posted', 'Unknown')}"
        )
        print(
            f"URL   : {job_url}"
        )

        # ----------------------------------------------------
        # DUPLICATE CHECK
        # ----------------------------------------------------

        if has_application_record(job_url, history):

            print(
                "[SKIP] Already processed."
            )

            continue

        # ----------------------------------------------------
        # OPEN JOB
        # ----------------------------------------------------

        try:

            driver.get(
                job_url
            )

            WebDriverWait(
                driver,
                20
            ).until(
                EC.presence_of_element_located(
                    (By.TAG_NAME, "body")
                )
            )

            time.sleep(3)

        except Exception as e:

            print(
                "[ERROR] Could not open job:",
                e
            )

            history[job_url] = {
                "title": job_title,
                "status": "open_failed",
                "timestamp": datetime.now().isoformat(),
            }

            save_application_history(
                history
            )

            continue

        # ----------------------------------------------------
        # APPLY
        # ----------------------------------------------------

        success = click_apply_button(
            driver
        )

        if success:

            applications_sent += 1

            history[job_url] = {
                "title": job_title,
                "status": "submitted",
                "posted": job.get(
                    "posted",
                    ""
                ),
                "city": job.get(
                    "city",
                    ""
                ),
                "timestamp": datetime.now().isoformat(),
            }

            save_application_history(
                history
            )

            print(
                f"[SUCCESS] Application processed."
            )

            print(
                f"Applications this run: "
                f"{applications_sent}"
            )

            if has_reached_daily_limit(today_count + applications_sent):
                print(
                    "Daily confirmed application limit reached; "
                    "stopping job processing."
                )
                break

            time.sleep(3)

        else:

            history[job_url] = {
                "title": job_title,
                "status": "apply_button_not_found",
                "posted": job.get(
                    "posted",
                    ""
                ),
                "city": job.get(
                    "city",
                    ""
                ),
                "timestamp": datetime.now().isoformat(),
            }

            save_application_history(
                history
            )

            print(
                "[FAILED] Apply button not found."
            )

    # --------------------------------------------------------
    # FINAL SUMMARY
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("APPLICATION SUMMARY")
    print("=" * 70)

    print(
        f"Applications sent this run : "
        f"{applications_sent}"
    )

    print(
        f"Applications before run    : "
        f"{today_count}"
    )

    print(
        f"Applications today total   : "
        f"{today_count + applications_sent}"
    )

    print(
        f"Daily limit                 : "
        f"{MAX_APPLICATIONS_PER_DAY}"
    )

    print("=" * 70)

def debug_inputs(driver):

    print("\n" + "=" * 70)
    print("DEBUG: INPUT FIELDS")
    print("=" * 70)

    inputs = driver.find_elements(
        By.TAG_NAME,
        "input"
    )

    for index, element in enumerate(
        inputs,
        start=1
    ):

        try:

            if not element.is_displayed():
                continue

            print(
                f"\nINPUT {index}"
            )

            print(
                "  type        :",
                element.get_attribute("type")
            )

            print(
                "  name        :",
                element.get_attribute("name")
            )

            print(
                "  id          :",
                element.get_attribute("id")
            )

            print(
                "  placeholder :",
                element.get_attribute("placeholder")
            )

            print(
                "  value       :",
                element.get_attribute("value")
            )

        except Exception:
            continue

    print("=" * 70)
    

# ============================================================
# MAIN
# ============================================================

def main():

    driver = None

    try:
        # 1. LOAD EXCEL SETTINGS
        print("\n[PlacementIndia] Loading Excel settings...", flush=True)
        load_user_settings()

        today_count = get_today_application_count(
            load_application_history()
        )
        if has_reached_daily_limit(today_count):
            print(
                "[PlacementIndia] Daily confirmed application limit "
                "already reached; skipping browser startup and job search.",
                flush=True,
            )
            return

        # 2. START BROWSER
        print("[PlacementIndia] Starting browser...", flush=True)
        driver = start_browser()

        # 3. OPEN PLACEMENTINDIA
        print("[PlacementIndia] Opening website...", flush=True)
        open_placementindia(driver)

        # 4. LOGIN
        print("[PlacementIndia] Logging in...", flush=True)
        login_success = login_placementindia(driver)

        if not login_success:
            print("[PlacementIndia] Login failed.", flush=True)
            if os.environ.get("JOB_AUTOMATION_STUDENT_ID"):
                raise RuntimeError("PlacementIndia login failed.")
            return

        print("[PlacementIndia] Login successful.", flush=True)

        # 5. OPEN JOB SEARCH
        print("[PlacementIndia] Opening job search...", flush=True)
        open_job_search(driver)

        # Optional debugging of search inputs
        debug_inputs(driver)

        # 6. SEARCH ONCE: KEYWORD + CITY
        print(
            f"[PlacementIndia] Searching: "
            f"{SEARCH_KEYWORD}, {SEARCH_CITY or 'All Cities'}",
            flush=True,
        )

        search_jobs(
            driver,
            SEARCH_KEYWORD,
            SEARCH_CITY,
        )

        # 7. SORT BY LATEST
        print("[PlacementIndia] Sorting by latest...", flush=True)
        sort_by_latest(driver)

        # 8. EXTRACT AND FILTER JOBS
        print("[PlacementIndia] Extracting jobs...", flush=True)
        jobs = extract_jobs(
            driver,
            city=SEARCH_CITY,
            job_posted=JOB_POSTED,
        )

        # 9. DISPLAY JOBS
        display_jobs(jobs)

        # 10. PROCESS APPLICATIONS
        if jobs:
            print(
                f"[PlacementIndia] Processing {len(jobs)} jobs...",
                flush=True,
            )
            process_jobs(driver, jobs)
        else:
            print(
                "[PlacementIndia] No jobs found for the selected filters.",
                flush=True,
            )

        # 11. FINAL SUMMARY
        print("\n" + "=" * 70, flush=True)
        print("[PlacementIndia] AUTOMATION COMPLETED", flush=True)
        print("=" * 70, flush=True)
        print(f"Keyword : {SEARCH_KEYWORD}", flush=True)
        print(f"City    : {SEARCH_CITY or 'All Cities'}", flush=True)
        print(f"Posted  : {JOB_POSTED}", flush=True)

    except KeyboardInterrupt:
        print(
            "\n[PlacementIndia] Automation interrupted.",
            flush=True,
        )

    except Exception:
        import traceback

        print(
            "\n[PlacementIndia] AUTOMATION ERROR",
            flush=True,
        )
        traceback.print_exc()
        if os.environ.get("JOB_AUTOMATION_STUDENT_ID"):
            raise

    finally:
        if driver:
            try:
                driver.quit()
                print(
                    "[PlacementIndia] Browser closed.",
                    flush=True,
                )
            except Exception as close_error:
                print(
                    f"[PlacementIndia] Browser cleanup warning: {close_error}",
                    flush=True,
                )


if __name__ == "__main__":
    main()

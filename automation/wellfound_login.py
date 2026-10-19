import os
import time
import re
import hashlib
from datetime import datetime, date, timedelta
from urllib.parse import urlsplit, urlunsplit

from excel_users import get_student_id, get_user
from wellfound_tracking import (
    empty_application_log as empty_scoped_application_log,
    get_today_submission_ids as get_scoped_today_submission_ids,
    get_today_submitted_count as get_scoped_today_submitted_count,
    get_today_attempt_count as get_scoped_today_attempt_count,
    record_application_attempt as record_scoped_application_attempt,
    has_been_processed as has_scoped_been_processed,
    load_application_log as load_scoped_application_log,
    save_application_log as save_scoped_application_log,
)
from application_limits import (
    DAILY_APPLICATION_LIMIT,
    has_reached_daily_limit,
)

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import (
    TimeoutException,
    StaleElementReferenceException,
    WebDriverException,
)


# ============================================================
# CONFIGURATION
# ============================================================

ALLOWED_LOCATIONS = [
    "Mumbai",
    "Pune",
    "Remote",
    "Bengaluru",
    "Hyderabad",
    "Chennai",
    "Noida",
    "Gurugram",
    "Vellore",
    "Delhi",
    "Toronto",
    "Old Toronto",
]

FINANCE_KEYWORDS = [
    "finance",
    "financial",
    "accounting",
    "accountant",
    "investment",
    "investment banking",
    "equity research",
    "financial analyst",
    "finance analyst",
    "financial planning",
    "fp&a",
    "corporate finance",
    "credit analyst",
    "risk analyst",
    "treasury",
    "wealth management",
    "portfolio analyst",
    "tax",
    "audit",
    "financial controller",
]


# ============================================================
# APPLICATION TARGET
# ============================================================

# The automation stops ONLY when this many successful
# applications have been confirmed for today.
TARGET_SUCCESSFUL_APPLICATIONS = DAILY_APPLICATION_LIMIT


# ============================================================
# SEARCH SAFETY LIMITS
# ============================================================

# Maximum search-result pages to inspect.
MAX_SEARCH_PAGES = 10

# Maximum jobs inspected in one execution.
MAX_JOBS_TO_INSPECT = 20

# Only consider jobs posted within this many days.
# Set to None to disable posting-date filtering.
MAX_JOB_AGE_DAYS = 30


# ============================================================
# APPLICATION SETTINGS
# ============================================================

LEGACY_APPLICATION_LOG_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "wellfound_applications.json",
)
APPLICATION_LOG_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "wellfound_student_applications.json",
)

STUDENT_ID = ""
WELLFOUND_EMAIL = ""
WELLFOUND_PASSWORD = ""

AUTO_SUBMIT_APPLICATIONS = True

DEFAULT_APPLICATION_ANSWER = (
    "Iâ€™m interested in working on practical products, solving business problems "
    "with data, and contributing to a team where I can learn and deliver measurable value."
)


# These statuses mean the job must NEVER be attempted again.
TERMINAL_APPLICATION_STATUSES = {
    "submitted",
    "rejected",
}


# ============================================================
# BASIC HELPERS
# ============================================================

def clean_text(text):
    if not text:
        return ""

    return re.sub(r"\s+", " ", text).strip()


def normalize_job_url(url):
    """
    Remove query parameters/fragments so the same job does not
    appear as multiple different jobs.
    """

    if not url:
        return ""

    try:
        parsed = urlsplit(url)

        return urlunsplit(
            (
                parsed.scheme,
                parsed.netloc,
                parsed.path.rstrip("/"),
                "",
                "",
            )
        )

    except Exception:
        return (
            url
            .split("?")[0]
            .split("#")[0]
            .rstrip("/")
        )


def get_job_id(job_url):
    """
    Extract Wellfound numeric job ID.

    Example:
        /jobs/123456-financial-analyst

    returns:
        123456
    """

    if not job_url:
        return None

    match = re.search(
        r"/jobs/(\d+)",
        job_url,
        re.IGNORECASE,
    )

    if match:
        return match.group(1)

    return None


def get_job_key(job):
    """
    Create a stable permanent key for a job.

    Numeric Wellfound ID is preferred.
    URL SHA1 is used as fallback.
    """

    job_id = get_job_id(
        job.get("url", "")
    )

    if job_id:
        return f"wellfound:{job_id}"

    normalized_url = normalize_job_url(
        job.get("url", "")
    )

    if not normalized_url:
        return None

    return "url:" + hashlib.sha1(
        normalized_url.encode("utf-8")
    ).hexdigest()


# ============================================================
# LOCATION
# ============================================================

def normalize_location(location):

    if not location:
        return "Unknown"

    location = clean_text(location)

    value = location.lower()

    # INDIA
    if (
        value == "india"
        or "india gate" in value
        or "new delhi" in value
        or "delhi" in value
    ):
        return "Delhi"

    # MUMBAI
    if "mumbai" in value:
        return "Mumbai"

    # PUNE
    if "pune" in value:
        return "Pune"

    # BENGALURU / BANGALORE
    if "bengaluru" in value:
        return "Bengaluru"

    if "bangalore" in value:
        return "Bengaluru"

    # HYDERABAD
    if "hyderabad" in value:
        return "Hyderabad"

    # CHENNAI
    if "chennai" in value:
        return "Chennai"

    # NOIDA
    if "noida" in value:
        return "Noida"

    # GURUGRAM / GURGAON
    if "gurugram" in value:
        return "Gurugram"

    if "gurgaon" in value:
        return "Gurugram"

    # VELLORE
    if "vellore" in value:
        return "Vellore"

    # REMOTE
    if "remote" in value:
        return "Remote"

    return location


def is_allowed_location(location):
    return location in ALLOWED_LOCATIONS


def extract_job_location(driver):

    # --------------------------------------------------------
    # Exact Location labels
    # --------------------------------------------------------

    labels = driver.find_elements(
        By.XPATH,
        "//*[normalize-space()='Location']",
    )

    for label in labels:

        try:

            candidates = [
                "./following-sibling::*[1]",
                "./parent::*/*[2]",
                "./parent::*/*[2]//*",
            ]

            for xpath in candidates:

                elements = label.find_elements(
                    By.XPATH,
                    xpath,
                )

                for element in elements:

                    try:

                        value = clean_text(
                            element.text
                        )

                        if not value:
                            continue

                        if value.lower() == "location":
                            continue

                        if len(value) > 150:
                            continue

                        normalized = normalize_location(
                            value
                        )

                        if normalized != "Unknown":
                            return normalized

                    except Exception:
                        continue

        except Exception:
            continue

    # --------------------------------------------------------
    # Fallback selectors
    # --------------------------------------------------------

    candidates = [
        "//*[@aria-label='Location']",
        "//*[@data-testid='location']",
        "//*[contains(@data-testid,'location')]",
        "//*[contains(@class,'location')]",
    ]

    for xpath in candidates:

        try:

            elements = driver.find_elements(
                By.XPATH,
                xpath,
            )

            for element in elements:

                value = clean_text(
                    element.text
                )

                if not value:
                    continue

                if len(value) > 150:
                    continue

                normalized = normalize_location(
                    value
                )

                if normalized != "Unknown":
                    return normalized

        except Exception:
            continue

    return "Unknown"


# ============================================================
# REMOTE POLICY
# ============================================================

def extract_remote_policy(driver):

    labels = driver.find_elements(
        By.XPATH,
        "//*[contains("
        "translate(normalize-space(.),"
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
        "'abcdefghijklmnopqrstuvwxyz'),"
        "'remote work policy'"
        ")]",
    )

    for label in labels:

        try:

            parent = label.find_element(
                By.XPATH,
                "./..",
            )

            text = clean_text(
                parent.text
            )

            if text:
                return text

        except Exception:
            continue

    return ""


# ============================================================
# APPLICATION METHOD
# ============================================================

def detect_application_method(driver):

    try:

        body_text = clean_text(
            driver.find_element(
                By.TAG_NAME,
                "body",
            ).text
        )

    except Exception:
        return "Unknown"

    body_lower = body_text.lower()

    # --------------------------------------------------------
    # External application
    # --------------------------------------------------------

    external_messages = [
        "applications to this job are managed outside of wellfound",
        "apply on company website",
        "apply on website",
        "application managed outside",
        "apply externally",
    ]

    for message in external_messages:

        if message in body_lower:
            return "Apply on company website"

    # --------------------------------------------------------
    # Wellfound application
    # --------------------------------------------------------

    wellfound_messages = [
        "send application",
        "your application",
    ]

    for message in wellfound_messages:

        if message in body_lower:
            return "Apply on Wellfound"

    # --------------------------------------------------------
    # Button fallback
    # --------------------------------------------------------

    apply_xpaths = [

        "//button[normalize-space()='Apply']",

        "//button[contains("
        "translate(normalize-space(.),"
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
        "'abcdefghijklmnopqrstuvwxyz'),"
        "'apply'"
        ")]",

        "//a[normalize-space()='Apply']",

        "//a[contains("
        "translate(normalize-space(.),"
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
        "'abcdefghijklmnopqrstuvwxyz'),"
        "'apply'"
        ")]",
    ]

    for xpath in apply_xpaths:

        try:

            elements = driver.find_elements(
                By.XPATH,
                xpath,
            )

            for element in elements:

                if element.is_displayed():
                    return "Apply on Wellfound"

        except Exception:
            continue

    return "Unknown"


# ============================================================
# POSTING DATE
# ============================================================

def extract_posting_date(driver):
    """
    Attempt to determine the job posting date.

    Returns:
        datetime
        or None
    """

    try:

        body = clean_text(
            driver.find_element(
                By.TAG_NAME,
                "body",
            ).text
        )

    except Exception:
        return None

    text = body.lower()
    now = datetime.now()

    if "posted today" in text:
        return now

    if "posted yesterday" in text:
        return now - timedelta(days=1)

    patterns = [
        (
            r"posted\s+(\d+)\s+hour[s]?\s+ago",
            "hours",
        ),
        (
            r"posted\s+(\d+)\s+day[s]?\s+ago",
            "days",
        ),
        (
            r"posted\s+(\d+)\s+week[s]?\s+ago",
            "weeks",
        ),
        (
            r"(\d+)\s+day[s]?\s+ago",
            "days",
        ),
        (
            r"(\d+)\s+week[s]?\s+ago",
            "weeks",
        ),
    ]

    for pattern, unit in patterns:

        match = re.search(
            pattern,
            text,
        )

        if not match:
            continue

        try:

            amount = int(
                match.group(1)
            )

            if unit == "hours":
                return now - timedelta(
                    hours=amount
                )

            if unit == "days":
                return now - timedelta(
                    days=amount
                )

            if unit == "weeks":
                return now - timedelta(
                    weeks=amount
                )

        except Exception:
            continue

    return None


def is_fresh_job(posted_date):

    if MAX_JOB_AGE_DAYS is None:
        return True

    if posted_date is None:
        # If Wellfound doesn't expose the date,
        # don't reject the job.
        return True

    age = (
        datetime.now() - posted_date
    ).days

    return age <= MAX_JOB_AGE_DAYS


# ============================================================
# JOB PAGE INSPECTION
# ============================================================

def inspect_job_page(driver, wait):

    wait.until(
        EC.presence_of_element_located(
            (
                By.TAG_NAME,
                "body",
            )
        )
    )

    time.sleep(1.5)

    body_text = clean_text(
        driver.find_element(
            By.TAG_NAME,
            "body",
        ).text
    )

    location = extract_job_location(
        driver
    )

    remote_policy = extract_remote_policy(
        driver
    )

    apply_method = detect_application_method(
        driver
    )

    posted_date = extract_posting_date(
        driver
    )

    # --------------------------------------------------------
    # Remote fallback
    # --------------------------------------------------------

    if location == "Unknown":

        remote_text = (
            remote_policy
            + " "
            + body_text[:5000]
        ).lower()

        remote_keywords = [
            "remote only",
            "fully remote",
            "100% remote",
            "work from home",
            "remote work",
        ]

        if any(
            keyword in remote_text
            for keyword in remote_keywords
        ):
            location = "Remote"

    return {
        "location": location,
        "remote_policy": remote_policy,
        "apply_method": apply_method,
        "posted_date": posted_date,
        "body_text": body_text,
    }


# ============================================================
# APPLICATION LOG
# ============================================================

def empty_application_log():
    return empty_scoped_application_log()


def load_application_log():
    if not STUDENT_ID or not WELLFOUND_EMAIL:
        raise ValueError(
            "Load the selected student's Wellfound account settings "
            "before accessing application history."
        )

    return load_scoped_application_log(
        APPLICATION_LOG_FILE,
        STUDENT_ID,
        WELLFOUND_EMAIL,
    )


def save_application_log(log):
    if not STUDENT_ID or not WELLFOUND_EMAIL:
        raise ValueError(
            "Load the selected student's Wellfound account settings "
            "before saving application history."
        )

    save_scoped_application_log(
        APPLICATION_LOG_FILE,
        STUDENT_ID,
        WELLFOUND_EMAIL,
        log,
    )


def get_job_record(log, job):

    key = get_job_key(job)

    if not key:
        return None

    return log.get(
        "jobs",
        {}
    ).get(key)


def has_been_processed(log, job):

    key = get_job_key(job)
    if not key:
        return False

    return has_scoped_been_processed(
        log,
        key,
        TERMINAL_APPLICATION_STATUSES,
    )


def get_today_submission_ids(log):
    return get_scoped_today_submission_ids(log)


def get_today_submitted_count(log):
    return get_scoped_today_submitted_count(log)


def get_today_attempt_count(log):
    return get_scoped_today_attempt_count(log)


def record_application_attempt(log, job):
    job_key = get_job_key(job)
    if not job_key:
        print("WARNING: Could not record submission attempt: missing job key.")
        return False

    record_scoped_application_attempt(log, job_key)
    save_application_log(log)
    return True


def record_application_status(
    log,
    job,
    status,
    reason=None,
):

    job_key = get_job_key(
        job
    )

    if not job_key:

        print(
            "WARNING: Could not create job key."
        )

        return False

    # --------------------------------------------------------
    # NEVER overwrite terminal record
    # --------------------------------------------------------

    existing = log.setdefault(
        "jobs",
        {}
    ).get(
        job_key
    )

    if isinstance(existing, dict):

        existing_status = existing.get(
            "status"
        )

        if existing_status in TERMINAL_APPLICATION_STATUSES:

            print(
                f"LOG PROTECTION: {job_key} already has "
                f"terminal status '{existing_status}'."
            )

            return False

    now = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    record = {
        "title": job.get(
            "title",
            "Unknown Job",
        ),
        "url": normalize_job_url(
            job.get("url", "")
        ),
        "location": job.get(
            "location",
            "Unknown",
        ),
        "status": status,
        "updated_at": now,
    }

    if job.get("posted_date"):

        record["posted_date"] = (
            job["posted_date"]
        )

    if reason:

        record["reason"] = reason

    if status == "submitted":

        record["submitted_at"] = now

    log["jobs"][job_key] = record

    # --------------------------------------------------------
    # Only successful submissions count
    # --------------------------------------------------------

    if status == "submitted":

        today = date.today().isoformat()

        log.setdefault(
            "daily_submissions",
            {}
        )

        log["daily_submissions"].setdefault(
            today,
            [],
        )

        if job_key not in log[
            "daily_submissions"
        ][today]:

            log[
                "daily_submissions"
            ][today].append(
                job_key
            )

    save_application_log(
        log
    )

    return True


# ============================================================
# APPLICATION ANSWER
# ============================================================

def get_application_answer(driver, element):

    name = (
        element.get_attribute("name")
        or ""
    )

    placeholder = (
        element.get_attribute("placeholder")
        or ""
    )

    field_id = (
        element.get_attribute("id")
        or ""
    )

    # Find nearby question text
    question_text = ""

    try:

        question_text = driver.execute_script(
            """
            const el = arguments[0];

            let parent = el.parentElement;

            for (let i = 0; i < 5 && parent; i++) {

                const text = parent.innerText || "";

                if (text.length > 5) {
                    return text;
                }

                parent = parent.parentElement;
            }

            return "";
            """,
            element,
        )

    except Exception:
        pass

    question = clean_text(
        question_text
    ).lower()

    combined = (
        f"{name} "
        f"{placeholder} "
        f"{field_id} "
        f"{question}"
    ).lower()

    # --------------------------------------------------
    # COMMON OPEN-ENDED QUESTION
    # --------------------------------------------------

    if (
        "what interests you" in combined
        or "why are you interested" in combined
        or "why do you want" in combined
    ):

        return (
            "I am interested in this opportunity because "
            "it aligns with my finance and analytical interests. "
            "I am eager to contribute, learn from the team, "
            "and grow while delivering meaningful results."
        )

    # --------------------------------------------------
    # DO NOT INVENT PERSONAL INFORMATION
    # --------------------------------------------------

    if (
        "current ctc" in combined
        or "expected ctc" in combined
        or "notice period" in combined
        or "salary" in combined
        or "compensation" in combined
    ):

        return None

    if (
        "years of experience" in combined
        or "experience" in combined
    ):

        return None

    # --------------------------------------------------
    # UNKNOWN CUSTOM QUESTION
    # --------------------------------------------------

    return None


# ============================================================
# FILL APPLICATION FORM
# ============================================================

def fill_application_form(driver):

    print(
        "\nFILLING WELLFOUND APPLICATION FORM...",
        flush=True,
    )

    filled_count = 0

    # --------------------------------------------------
    # TEXT INPUTS
    # --------------------------------------------------

    try:

        inputs = driver.find_elements(
            By.XPATH,
            "//input[@type='text']"
            "|//input[not(@type)]"
            "|//textarea",
        )

        for element in inputs:

            try:

                if not element.is_displayed():
                    continue

                name = (
                    element.get_attribute("name")
                    or ""
                )

                placeholder = (
                    element.get_attribute("placeholder")
                    or ""
                )

                value = (
                    element.get_attribute("value")
                    or ""
                )

                identifier = (
                    f"{name} {placeholder}"
                ).lower()

                # Already filled
                if value.strip():
                    continue

                # Ignore unrelated fields
                if (
                    "customquestionanswers" not in identifier
                    and element.tag_name.lower() != "textarea"
                ):
                    continue

                answer = get_application_answer(
                    driver,
                    element,
                )

                if answer is None:
                    print(
                        f"SKIPPED FIELD - answer not configured: "
                        f"{name}",
                        flush=True,
                    )
                    continue

                element.clear()

                element.send_keys(
                    answer
                )

                filled_count += 1

                print(
                    f"Filled field: {name}",
                    flush=True,
                )

            except (
                StaleElementReferenceException,
                WebDriverException,
            ):
                continue

    except Exception as error:

        print(
            "Text field processing error:",
            type(error).__name__,
            flush=True,
        )

    # --------------------------------------------------
    # CHECKBOXES
    # --------------------------------------------------

    try:

        checkboxes = driver.find_elements(
            By.XPATH,
            "//input[@type='checkbox']",
        )

        for checkbox in checkboxes:

            try:

                if not checkbox.is_displayed():
                    continue

                if checkbox.is_selected():
                    continue

                name = (
                    checkbox.get_attribute("name")
                    or ""
                )

                # Wellfound privacy agreement
                if (
                    "privacy" in name.lower()
                    or "agree" in name.lower()
                    or "terms" in name.lower()
                ):

                    driver.execute_script(
                        "arguments[0].click();",
                        checkbox,
                    )

                    filled_count += 1

                    print(
                        "Checked required privacy/terms checkbox.",
                        flush=True,
                    )

            except (
                StaleElementReferenceException,
                WebDriverException,
            ):
                continue

    except Exception as error:

        print(
            "Checkbox processing error:",
            type(error).__name__,
            flush=True,
        )

    # --------------------------------------------------
    # RADIO BUTTONS
    # --------------------------------------------------

    try:

        radios = driver.find_elements(
            By.XPATH,
            "//input[@type='radio']",
        )

        print(
            f"Radio buttons detected: {len(radios)}",
            flush=True,
        )

        for radio in radios:

            try:

                if not radio.is_displayed():
                    continue

                if radio.is_selected():
                    continue

                # Don't randomly select yes/no.
                # User-specific answers must be configured.
                continue

            except (
                StaleElementReferenceException,
                WebDriverException,
            ):
                continue

    except Exception as error:

        print(
            "Radio processing error:",
            type(error).__name__,
            flush=True,
        )

    print(
        f"Fields filled: {filled_count}",
        flush=True,
    )

    return filled_count


# ============================================================
# APPLY BUTTON
# ============================================================

def find_apply_button(driver):

    xpaths = [

        "//button[normalize-space()='Apply']",

        "//button[contains("
        "translate(normalize-space(.),"
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
        "'abcdefghijklmnopqrstuvwxyz'),"
        "'apply'"
        ")]",

        "//a[normalize-space()='Apply']",

        "//a[contains("
        "translate(normalize-space(.),"
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
        "'abcdefghijklmnopqrstuvwxyz'),"
        "'apply'"
        ")]",
    ]

    for xpath in xpaths:

        try:

            elements = driver.find_elements(
                By.XPATH,
                xpath,
            )

            for element in elements:

                if (
                    element.is_displayed()
                    and element.is_enabled()
                ):

                    return element

        except Exception:
            continue

    return None


# ============================================================
# SUBMIT APPLICATION
# ============================================================

def submit_application(driver, job):

    print(
        "\nLooking for Send Application button...",
        flush=True,
    )

    submit_xpath = (
        "//button[contains("
        "translate(normalize-space(.),"
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
        "'abcdefghijklmnopqrstuvwxyz'),"
        "'send application'"
        ")]"
        "|//input[@type='submit' and contains("
        "translate(@value,"
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
        "'abcdefghijklmnopqrstuvwxyz'),"
        "'send application'"
        ")]"
    )

    # --------------------------------------------------
    # WAIT FOR BUTTON
    # --------------------------------------------------

    try:

        submit_button = WebDriverWait(
            driver,
            15,
        ).until(
            lambda d: next(
                (
                    element
                    for element in d.find_elements(
                        By.XPATH,
                        submit_xpath,
                    )
                    if (
                        element.is_displayed()
                        and element.is_enabled()
                    )
                ),
                None,
            )
        )

    except TimeoutException:

        print(
            "Send Application button not found.",
            flush=True,
        )

        return False

    # --------------------------------------------------
    # CHECK REQUIRED FIELDS
    # --------------------------------------------------

    try:

        invalid_fields = driver.find_elements(
            By.XPATH,
            """
            //input[@required and not(@type='hidden')]
            [not(@type='checkbox')]
            |//textarea[@required]
            |//select[@required]
            """,
        )

        missing_required = []

        for field in invalid_fields:

            try:

                if not field.is_displayed():
                    continue

                value = (
                    field.get_attribute("value")
                    or ""
                )

                if not value.strip():

                    missing_required.append(
                        field.get_attribute("name")
                        or field.get_attribute("id")
                        or "unknown field"
                    )

            except Exception:
                continue

        if missing_required:

            print(
                "REQUIRED FIELDS STILL EMPTY:",
                flush=True,
            )

            for field_name in missing_required:

                print(
                    f"  - {field_name}",
                    flush=True,
                )

            print(
                "Application will NOT be submitted "
                "with missing required answers.",
                flush=True,
            )

            return False

    except Exception as error:

        print(
            "Required-field validation error:",
            type(error).__name__,
            flush=True,
        )

    # --------------------------------------------------
    # RECORD ATTEMPT, THEN CLICK
    # --------------------------------------------------

    application_log = load_application_log()
    attempts_today = get_today_attempt_count(application_log)

    if has_reached_daily_limit(attempts_today):
        print("Daily submission-attempt limit already reached.", flush=True)
        return False

    if not record_application_attempt(application_log, job):
        print("Could not persist submission attempt; refusing to click.", flush=True)
        return False

    # --------------------------------------------------
    # CLICK
    # --------------------------------------------------

    try:

        driver.execute_script(
            "arguments[0].scrollIntoView({block:'center'});",
            submit_button,
        )

        time.sleep(1)

        submit_button.click()

        print(
            "Send application clicked.",
            flush=True,
        )

    except StaleElementReferenceException:

        print(
            "Send button became stale. Re-finding...",
            flush=True,
        )

        try:

            submit_button = WebDriverWait(
                driver,
                10,
            ).until(
                lambda d: next(
                    (
                        element
                        for element in d.find_elements(
                            By.XPATH,
                            submit_xpath,
                        )
                        if (
                            element.is_displayed()
                            and element.is_enabled()
                        )
                    ),
                    None,
                )
            )

            driver.execute_script(
                "arguments[0].click();",
                submit_button,
            )

            print(
                "Send application clicked after re-find.",
                flush=True,
            )

        except Exception as error:

            print(
                "Could not click Send application:",
                type(error).__name__,
                flush=True,
            )

            return False

    except Exception as error:

        print(
            "Could not click Send application:",
            type(error).__name__,
            flush=True,
        )

        return False

    # --------------------------------------------------
    # CONFIRMATION
    # --------------------------------------------------

    success_phrases = [
        "application sent",
        "your application has been sent",
        "your application was sent",
        "thanks for applying",
        "application received",
    ]

    deadline = time.time() + 20

    while time.time() < deadline:

        try:

            body = clean_text(
                driver.find_element(
                    By.TAG_NAME,
                    "body",
                ).text
            ).lower()

            if any(
                phrase in body
                for phrase in success_phrases
            ):

                print(
                    "SUCCESS: Application submission confirmed.",
                    flush=True,
                )

                return True

        except Exception:
            pass

        time.sleep(1)

    print(
        "Submission clicked, but Wellfound did not "
        "show a success confirmation.",
        flush=True,
    )

    return False


# ============================================================
# EXTRACT JOBS FROM SEARCH PAGE
# ============================================================

def extract_jobs_from_search_page(driver):

    jobs = []
    seen = set()

    try:

        links = driver.find_elements(
            By.XPATH,
            "//a[contains(@href,'/jobs/')]",
        )

    except Exception:
        return jobs

    for link in links:

        try:

            href = link.get_attribute(
                "href"
            )

            if not href:
                continue

            clean_url = normalize_job_url(
                href
            )

            job_id = get_job_id(
                clean_url
            )

            if not job_id:
                continue

            key = (
                f"wellfound:{job_id}"
            )

            if key in seen:
                continue

            seen.add(key)

            title = clean_text(
                link.text
            )

            # ------------------------------------------------
            # Fallback title from URL
            # ------------------------------------------------

            if not title:

                path = urlsplit(
                    clean_url
                ).path

                slug = path.split(
                    "/jobs/"
                )[-1]

                slug = re.sub(
                    r"^\d+-",
                    "",
                    slug,
                )

                title = slug.replace(
                    "-",
                    " ",
                ).title()

            jobs.append(
                {
                    "title": title,
                    "url": clean_url,
                }
            )

        except (
            StaleElementReferenceException,
            WebDriverException,
        ):
            continue

    return jobs


# ============================================================
# WAIT FOR JOB RESULTS TO CHANGE
# ============================================================

def wait_for_new_jobs(
    driver,
    old_ids,
    old_url,
    timeout=15,
):

    deadline = time.time() + timeout

    while time.time() < deadline:

        time.sleep(1)

        try:

            new_url = driver.current_url

            if new_url != old_url:

                print(
                    "Search URL changed."
                )

                print(
                    "New URL:",
                    new_url,
                )

                return True

        except Exception:
            pass

        try:

            new_jobs = extract_jobs_from_search_page(
                driver
            )

            new_ids = {
                get_job_key(job)
                for job in new_jobs
                if get_job_key(job)
            }

            if new_ids and new_ids != old_ids:

                print(
                    "New jobs detected."
                )

                print(
                    "New job count:",
                    len(new_ids),
                )

                return True

        except Exception:
            pass

    return False


# ============================================================
# NEXT PAGE / NEXT RESULTS
# ============================================================

def go_to_next_page(driver, current_page):
    """
    Move directly to the next Wellfound search page.

    Wellfound supports normal ?page=N pagination.
    This is more reliable than trying to click a dynamic Next button.
    """

    next_page = current_page + 1

    current_url = driver.current_url

    print(
        f"[PAGINATION] Current page: {current_page}",
        flush=True,
    )

    print(
        f"[PAGINATION] Opening page: {next_page}",
        flush=True,
    )

    # Remove existing page parameter
    base_url = re.sub(
        r"([?&])page=\d+",
        "",
        current_url,
    )

    # Clean trailing ? or &
    base_url = base_url.rstrip("?&")

    separator = "&" if "?" in base_url else "?"

    next_url = (
        f"{base_url}"
        f"{separator}"
        f"page={next_page}"
    )

    print(
        "[PAGINATION] Next URL:",
        next_url,
        flush=True,
    )

    try:

        old_url = driver.current_url

        driver.get(next_url)

        WebDriverWait(
            driver,
            15,
        ).until(
            lambda d: (
                d.current_url != old_url
                or "page=" in d.current_url
            )
        )

        time.sleep(2)

        # Make sure the page actually contains job links
        WebDriverWait(
            driver,
            15,
        ).until(
            lambda d: len(
                d.find_elements(
                    By.XPATH,
                    "//a[contains(@href, '/jobs/')]",
                )
            ) > 0
        )

        job_links = driver.find_elements(
            By.XPATH,
            "//a[contains(@href, '/jobs/')]",
        )

        print(
            f"[PAGINATION] Page {next_page} loaded.",
            flush=True,
        )

        print(
            f"[PAGINATION] Job links found: {len(job_links)}",
            flush=True,
        )

        return True

    except Exception as error:

        print(
            "[PAGINATION] Failed to open next page:",
            type(error).__name__,
            str(error),
            flush=True,
        )

        return False


# ============================================================
# LOGIN
# ============================================================

def load_selected_student_account():
    global STUDENT_ID
    global WELLFOUND_EMAIL
    global WELLFOUND_PASSWORD

    user = get_user()
    STUDENT_ID = get_student_id(user)
    normalized_user = {
        str(key).strip().casefold(): value
        for key, value in user.items()
    }
    WELLFOUND_EMAIL = str(
        normalized_user.get("wellfound_email") or ""
    ).strip()
    WELLFOUND_PASSWORD = str(
        normalized_user.get("wellfound_password") or ""
    ).strip()

    if not WELLFOUND_EMAIL or not WELLFOUND_PASSWORD:
        raise ValueError(
            "The selected Excel student row must contain non-empty "
            "'wellfound_email' and 'wellfound_password' values."
        )



def login_wellfound(driver):
    """
    Load the selected student's credentials, reuse an authenticated
    session when available, and otherwise attempt the normal login flow.
    """
    load_selected_student_account()

    email = WELLFOUND_EMAIL
    password = WELLFOUND_PASSWORD
    wait = WebDriverWait(driver, 20)

    # --------------------------------------------------------
    # OPEN WELLFOUND
    # --------------------------------------------------------

    driver.get("https://wellfound.com/join")

    print("[LOGIN] Wellfound opened.", flush=True)
    print("[LOGIN] URL:", driver.current_url, flush=True)
    print("[LOGIN] Title:", driver.title, flush=True)

    wait.until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )

    # --------------------------------------------------------
    # CHECK FOR AN EXISTING AUTHENTICATED SESSION
    # --------------------------------------------------------

    def has_authenticated_session(d):
        try:
            current_url = d.current_url.casefold()

            body_text = clean_text(
                d.find_element(By.TAG_NAME, "body").text
            ).casefold()

            # These indicators were observed on the Wellfound
            # jobs page when the account session was active.
            authenticated_markers = (
                "profile",
                "applied",
                "messages",
                "search for jobs",
            )

            is_jobs_area = (
                "/jobs" in current_url
                or "/dashboard" in current_url
            )

            return (
                is_jobs_area
                and all(
                    marker in body_text
                    for marker in authenticated_markers
                )
            )

        except (WebDriverException, StaleElementReferenceException):
            return False

    if has_authenticated_session(driver):
        print(
            "[LOGIN] Existing authenticated session detected. "
            "Skipping login form.",
            flush=True,
        )
        print("[LOGIN] Current URL:", driver.current_url, flush=True)
        return True

    # --------------------------------------------------------
    # FIND A LOGIN CONTROL
    # --------------------------------------------------------

    def find_login_button(d):
        candidates = d.find_elements(
            By.XPATH,
            "//a | //button | //*[@role='button']",
        )

        for element in candidates:
            try:
                if not element.is_displayed() or not element.is_enabled():
                    continue

                labels = [
                    element.text or "",
                    element.get_attribute("aria-label") or "",
                    element.get_attribute("title") or "",
                    element.get_attribute("href") or "",
                ]

                label = " ".join(labels).casefold()

                if any(
                    phrase in label
                    for phrase in (
                        "log in",
                        "login",
                        "sign in",
                        "sign-in",
                    )
                ):
                    return element

            except (
                StaleElementReferenceException,
                WebDriverException,
            ):
                continue

        return False

    login_button = None

    try:
        login_button = WebDriverWait(
            driver,
            8,
            ignored_exceptions=[StaleElementReferenceException],
        ).until(find_login_button)

    except TimeoutException:
        print(
            "[LOGIN] Login control not found on the initial page. "
            "Trying the direct login URL.",
            flush=True,
        )

        driver.get("https://wellfound.com/login")

        wait.until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        if has_authenticated_session(driver):
            print(
                "[LOGIN] Authenticated session detected after redirect.",
                flush=True,
            )
            return True

        try:
            login_button = WebDriverWait(
                driver,
                10,
                ignored_exceptions=[StaleElementReferenceException],
            ).until(find_login_button)

        except TimeoutException:
            print("[LOGIN] Could not find a login control.", flush=True)
            print("[LOGIN] URL:", driver.current_url, flush=True)
            print("[LOGIN] Title:", driver.title, flush=True)

            try:
                body_text = driver.find_element(
                    By.TAG_NAME, "body"
                ).text

                print(
                    "[LOGIN] Visible page text:",
                    body_text[:2000],
                    flush=True,
                )

                driver.save_screenshot("wellfound_login_failure.png")
                print(
                    "[LOGIN] Screenshot saved: wellfound_login_failure.png",
                    flush=True,
                )

            except WebDriverException as diagnostic_error:
                print(
                    "[LOGIN] Diagnostics failed:",
                    type(diagnostic_error).__name__,
                    flush=True,
                )

            raise RuntimeError(
                "Wellfound login control was not found. "
                "Check the printed URL and page text."
            )

    # --------------------------------------------------------
    # OPEN THE LOGIN FORM
    # --------------------------------------------------------

    try:
        login_button.click()

    except (
        StaleElementReferenceException,
        WebDriverException,
    ):
        login_button = WebDriverWait(
            driver,
            10,
            ignored_exceptions=[StaleElementReferenceException],
        ).until(find_login_button)

        driver.execute_script(
            "arguments[0].click();",
            login_button,
        )

    print("[LOGIN] Login control clicked.", flush=True)

    # --------------------------------------------------------
    # ENTER EMAIL
    # --------------------------------------------------------

    email_xpath = (
        "//input[@type='email']"
        "|//input[contains("
        "translate(@placeholder,"
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
        "'abcdefghijklmnopqrstuvwxyz'),"
        "'email'"
        ")]"
    )

    email_input = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, email_xpath)
        )
    )

    email_input.clear()
    email_input.send_keys(email)

    print("[LOGIN] Email entered.", flush=True)

    # --------------------------------------------------------
    # ENTER PASSWORD
    # --------------------------------------------------------

    password_input = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, "//input[@type='password']")
        )
    )

    password_input.clear()
    password_input.send_keys(password)

    print("[LOGIN] Password entered.", flush=True)

    # --------------------------------------------------------
    # SUBMIT LOGIN
    # --------------------------------------------------------

    submit_xpath = (
        "//button[contains("
        "translate(normalize-space(.),"
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
        "'abcdefghijklmnopqrstuvwxyz'),"
        "'log in'"
        ")]"
        "|//button[contains("
        "translate(normalize-space(.),"
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
        "'abcdefghijklmnopqrstuvwxyz'),"
        "'sign in'"
        ")]"
        "|//button[@type='submit']"
        "|//input[@type='submit']"
    )

    login_submitted = False

    for attempt in range(1, 4):
        try:
            submit_button = WebDriverWait(
                driver,
                10,
                ignored_exceptions=[StaleElementReferenceException],
            ).until(
                EC.element_to_be_clickable(
                    (By.XPATH, submit_xpath)
                )
            )

            driver.execute_script(
                "arguments[0].scrollIntoView({block:'center'});",
                submit_button,
            )

            time.sleep(0.5)

            # Re-find immediately before clicking in case the
            # page re-rendered the button.
            submit_button = WebDriverWait(
                driver,
                5,
                ignored_exceptions=[StaleElementReferenceException],
            ).until(
                EC.element_to_be_clickable(
                    (By.XPATH, submit_xpath)
                )
            )

            try:
                submit_button.click()

            except StaleElementReferenceException:
                submit_button = WebDriverWait(
                    driver,
                    5,
                    ignored_exceptions=[StaleElementReferenceException],
                ).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, submit_xpath)
                    )
                )

                driver.execute_script(
                    "arguments[0].click();",
                    submit_button,
                )

            login_submitted = True

            print(
                f"[LOGIN] Submit button clicked on attempt {attempt}.",
                flush=True,
            )
            break

        except (
            StaleElementReferenceException,
            TimeoutException,
            WebDriverException,
        ) as error:
            print(
                f"[LOGIN] Submit attempt {attempt}/3 failed: "
                f"{type(error).__name__}",
                flush=True,
            )

            if attempt < 3:
                time.sleep(1)

    if not login_submitted:
        raise RuntimeError(
            "Could not submit the Wellfound login form after 3 attempts."
        )

    # --------------------------------------------------------
    # VERIFY LOGIN
    # --------------------------------------------------------

    print("[LOGIN] Waiting for login to complete...", flush=True)

    try:
        WebDriverWait(driver, 25).until(
            lambda d: (
                has_authenticated_session(d)
                or any(
                    marker in d.current_url.casefold()
                    for marker in ("/jobs", "/dashboard")
                )
            )
        )

    except TimeoutException:
        pass

    current_url = driver.current_url.casefold()

    try:
        body_text = clean_text(
            driver.find_element(By.TAG_NAME, "body").text
        ).casefold()

    except WebDriverException:
        body_text = ""

    login_failed_messages = (
        "invalid email",
        "invalid password",
        "incorrect password",
        "incorrect email",
        "unable to log in",
        "couldn't log in",
        "could not log in",
        "login failed",
    )

    if any(
        message in body_text
        for message in login_failed_messages
    ):
        raise RuntimeError(
            "Wellfound rejected the login. Check the account credentials "
            "in the selected Excel student row."
        )

    if has_authenticated_session(driver):
        print("[LOGIN] Login verified successfully.", flush=True)
        print("[LOGIN] Post-login URL:", driver.current_url, flush=True)
        print("[LOGIN] Post-login title:", driver.title, flush=True)
        return True

    if "/login" in current_url or "/signin" in current_url:
        raise RuntimeError(
            "Wellfound login could not be verified. "
            f"Current URL: {driver.current_url}"
        )

    raise RuntimeError(
        "Wellfound login could not be confirmed. "
        f"Current URL: {driver.current_url}. "
        "Refusing to start job processing without verification."
    )



# ============================================================
# MAIN JOB PROCESSOR
# ============================================================

def process_wellfound_jobs(driver):

    wait = WebDriverWait(
        driver,
        20,
    )

    application_log = load_application_log()

    submitted_today = (
        get_today_submitted_count(
            application_log
        )
    )
    attempts_today = get_today_attempt_count(application_log)

    print(
        "\n======================================================"
    )

    print(
        "WELLFOUND JOB AUTOMATION"
    )

    print(
        "======================================================"
    )

    print(
        "Successful applications today:",
        submitted_today,
        "/",
        TARGET_SUCCESSFUL_APPLICATIONS,
    )

    print(
        "Fresh-job window:",
        (
            f"{MAX_JOB_AGE_DAYS} days"
            if MAX_JOB_AGE_DAYS is not None
            else "disabled"
        ),
    )

    # ========================================================
    # TARGET ALREADY REACHED
    # ========================================================

    if has_reached_daily_limit(attempts_today):

        print(
            "\n======================================================"
        )

        print(
            "TARGET ALREADY REACHED"
        )

        print(
            "======================================================"
        )

        print(
            "Successful applications today:",
            submitted_today,
        )

        print(
            "Target:",
            TARGET_SUCCESSFUL_APPLICATIONS,
        )

        return

    # ========================================================
    # OPEN JOB SEARCH
    # ========================================================

    driver.get(
        "https://wellfound.com/jobs"
    )

    print(
        "\nJobs page opened."
    )

    wait.until(
        EC.presence_of_element_located(
            (
                By.TAG_NAME,
                "body",
            )
        )
    )

    time.sleep(4)

    # ========================================================
    # GLOBAL DUPLICATE SET
    # ========================================================

    seen_job_keys = set()

    # Jobs processed during this execution.
    processed_this_run = set()

    page_number = 1

    inspected_count = 0

    applications_submitted_this_run = 0

    # ========================================================
    # SEARCH PAGE LOOP
    # ========================================================

    while page_number <= MAX_SEARCH_PAGES:

        # ----------------------------------------------------
        # ALWAYS CHECK TARGET AT START OF PAGE
        # ----------------------------------------------------

        application_log = load_application_log()

        submitted_today = (
            get_today_submitted_count(
                application_log
            )
        )
        attempts_today = get_today_attempt_count(application_log)

        if has_reached_daily_limit(attempts_today):

            print(
                "\n======================================================"
            )

            print(
                "DAILY SUBMISSION-ATTEMPT LIMIT REACHED"
            )

            print(
                "======================================================"
            )

            print(
                "Successful applications today:",
                submitted_today,
            )

            print(
                "Target:",
                TARGET_SUCCESSFUL_APPLICATIONS,
            )

            break

        print(
            "\n======================================================"
        )

        print(
            f"SEARCH PAGE {page_number}"
        )

        print(
            "======================================================"
        )

        print(
            "Successful applications today:",
            submitted_today,
            "/",
            TARGET_SUCCESSFUL_APPLICATIONS,
        )

        # ----------------------------------------------------
        # EXTRACT JOBS
        # ----------------------------------------------------

        page_jobs = extract_jobs_from_search_page(
            driver
        )

        print(
            "Jobs found on current page:",
            len(page_jobs),
        )

        # ----------------------------------------------------
        # NO JOBS
        # ----------------------------------------------------

        if not page_jobs:

            print(
                "\nNo jobs found on this page."
            )

            print(
                "Trying to load more results..."
            )

            moved = go_to_next_page(
            driver,
            page_number
            )

            if not moved:

                print(
                    "\nNo more searchable results."
                )

                break

            page_number += 1

            continue

        # ====================================================
        # PROCESS JOBS ON CURRENT PAGE
        # ====================================================

        for job in page_jobs:

            # ------------------------------------------------
            # TARGET CHECK BEFORE EVERY JOB
            # ------------------------------------------------

            application_log = load_application_log()

            submitted_today = (
                get_today_submitted_count(
                    application_log
                )
            )
            attempts_today = get_today_attempt_count(application_log)

            if has_reached_daily_limit(attempts_today):

                print(
                    "\nDAILY SUBMISSION-ATTEMPT LIMIT REACHED."
                )

                break

            # ------------------------------------------------
            # MAX INSPECTION CHECK
            # ------------------------------------------------

            if inspected_count >= MAX_JOBS_TO_INSPECT:

                print(
                    "\nMaximum job inspection limit reached."
                )

                break

            job_key = get_job_key(
                job
            )

            if not job_key:
                continue

            # ------------------------------------------------
            # DUPLICATE WITHIN THIS RUN
            # ------------------------------------------------

            if job_key in seen_job_keys:

                print(
                    "\nSKIPPED DUPLICATE:",
                    job["title"],
                )

                continue

            seen_job_keys.add(
                job_key
            )

            # ------------------------------------------------
            # DUPLICATE FROM APPLICATION LOG
            # ------------------------------------------------

            existing_record = get_job_record(
                application_log,
                job,
            )

            if has_been_processed(
                application_log,
                job,
            ):

                print(
                    "\nSKIPPED â€” ALREADY PROCESSED"
                )

                print(
                    "Title:",
                    job["title"],
                )

                print(
                    "Previous status:",
                    existing_record.get(
                        "status"
                    )
                    if existing_record
                    else "unknown",
                )

                continue

            # ------------------------------------------------
            # DUPLICATE IN CURRENT RUN
            # ------------------------------------------------

            if job_key in processed_this_run:

                continue

            processed_this_run.add(
                job_key
            )

            inspected_count += 1

            print(
                "\n------------------------------------------------------"
            )

            print(
                f"CHECKING JOB {inspected_count}"
            )

            print(
                "Title:",
                job["title"],
            )

            print(
                "URL:",
                job["url"],
            )

            # =================================================
            # OPEN JOB
            # =================================================

            try:

                driver.get(
                    job["url"]
                )

                wait.until(
                    EC.presence_of_element_located(
                        (
                            By.TAG_NAME,
                            "body",
                        )
                    )
                )

                time.sleep(1.5)

            except Exception as error:

                print(
                    "Could not open job:",
                    error,
                )

                record_application_status(
                    application_log,
                    job,
                    "failed",
                    f"Could not open job page: {error}",
                )

                continue

            # =================================================
            # INSPECT JOB
            # =================================================

            try:

                job_data = inspect_job_page(
                    driver,
                    wait,
                )

            except Exception as error:

                print(
                    "Inspection failed:",
                    error,
                )

                record_application_status(
                    application_log,
                    job,
                    "failed",
                    f"Job inspection failed: {error}",
                )

                continue

            location = job_data[
                "location"
            ]

            apply_method = job_data[
                "apply_method"
            ]

            posted_date = job_data[
                "posted_date"
            ]

            remote_policy = job_data[
                "remote_policy"
            ]

            print(
                "Location:",
                location,
            )

            print(
                "Application method:",
                apply_method,
            )

            if posted_date:

                print(
                    "Posted:",
                    posted_date.strftime(
                        "%Y-%m-%d %H:%M"
                    ),
                )

            else:

                print(
                    "Posted: Unknown"
                )

            # =================================================
            # FINANCE TITLE FILTER
            # =================================================

            title_lower = job[
                "title"
            ].lower()

            if not any(
                keyword in title_lower
                for keyword in FINANCE_KEYWORDS
            ):

                print(
                    "SKIPPED: Not a finance-related role."
                )

                continue

            # =================================================
            # FRESH JOB FILTER
            # =================================================

            if not is_fresh_job(
                posted_date
            ):

                print(
                    "SKIPPED: Job is older than",
                    MAX_JOB_AGE_DAYS,
                    "days.",
                )

                continue

            # =================================================
            # LOCATION FILTER
            # =================================================

            if not is_allowed_location(
                location
            ):

                print(
                    "SKIPPED: Location not allowed."
                )

                continue

            # =================================================
            # APPLICATION METHOD
            # =================================================

            if apply_method != "Apply on Wellfound":

                print(
                    "SKIPPED: External or unknown application."
                )

                continue

            # =================================================
            # COMPLETE JOB RECORD
            # =================================================

            qualified_job = {
                "title": job[
                    "title"
                ],
                "url": normalize_job_url(
                    job["url"]
                ),
                "location": location,
                "remote_policy": remote_policy,
                "apply_method": apply_method,
                "posted_date": (
                    posted_date.strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                    if posted_date
                    else None
                ),
            }

            print(
                "\nQUALIFIED FRESH FINANCE JOB."
            )

            # =================================================
            # FINAL DUPLICATE CHECK
            # =================================================

            application_log = load_application_log()

            if has_been_processed(
                application_log,
                qualified_job,
            ):

                print(
                    "SKIPPED: Job was already processed."
                )

                continue

            # =================================================
            # OPEN QUALIFIED JOB AGAIN
            # =================================================

            try:

                driver.get(
                    qualified_job["url"]
                )

                wait.until(
                    EC.presence_of_element_located(
                        (
                            By.TAG_NAME,
                            "body",
                        )
                    )
                )

                time.sleep(1.5)

            except Exception as error:

                print(
                    "Could not reopen job:",
                    error,
                )

                record_application_status(
                    application_log,
                    qualified_job,
                    "failed",
                    f"Could not reopen job: {error}",
                )

                continue

            # =================================================
            # VERIFY APPLICATION METHOD AGAIN
            # =================================================

            current_method = (
                detect_application_method(
                    driver
                )
            )

            if current_method != "Apply on Wellfound":

                print(
                    "SKIPPED: Application method changed."
                )

                continue

            # =================================================
            # FIND APPLY BUTTON
            # =================================================

            print(
                "Finding Apply button..."
            )

            apply_button = find_apply_button(
                driver
            )

            if not apply_button:

                print(
                    "Apply button not found."
                )

                record_application_status(
                    application_log,
                    qualified_job,
                    "failed",
                    "Apply button was not found.",
                )

                continue

            print(
                "Apply button found."
            )

            # =================================================
            # CLICK APPLY
            # =================================================

            try:

                driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center'});",
                    apply_button,
                )

                time.sleep(0.7)

                try:

                    apply_button.click()

                except Exception:

                    driver.execute_script(
                        "arguments[0].click();",
                        apply_button,
                    )
                    time.sleep(2)

                    application_body = clean_text(
                    driver.find_element(
                    By.TAG_NAME,
                    "body",
                    ).text
                    ).lower()

                    if (
                    "applications to this job are managed outside of wellfound"
                    in application_body
                    or "apply on website" in application_body
                    ):

                        print(
                        "SKIPPED: Application is managed on external website.",
                        flush=True,
                        )

                        continue

                print(
                    "Apply clicked."
                )

            except Exception as error:

                print(
                    "Could not click Apply:",
                    error,
                )

                record_application_status(
                    application_log,
                    qualified_job,
                    "failed",
                    f"Could not click Apply: {error}",
                )

                continue

            time.sleep(2)

            # =================================================
            # READ APPLICATION PAGE
            # =================================================

            try:

                body_text = clean_text(
                    driver.find_element(
                        By.TAG_NAME,
                        "body",
                    ).text
                )

                body_lower = body_text.lower()

            except Exception as error:

                record_application_status(
                    application_log,
                    qualified_job,
                    "failed",
                    f"Could not read application page: {error}",
                )

                continue

            # =================================================
            # BLOCKED / NOT ELIGIBLE
            # =================================================

            blocked_messages = [
                "you cannot apply to this job",
                "not accepting applications from your current location",
                "missing the following critical pieces of information",
                "you are not eligible to apply",
                "not eligible to apply",
            ]

            blocked_reason = None

            for message in blocked_messages:

                if message in body_lower:

                    blocked_reason = message

                    break

            if blocked_reason:

                print(
                    "\nNOT ELIGIBLE:",
                    blocked_reason,
                )

                record_application_status(
                    application_log,
                    qualified_job,
                    "rejected",
                    blocked_reason,
                )

                continue

            # =================================================
            # FORM DETECTION
            # =================================================

            form_detected = False

            if (
                "your application"
                in body_lower
                or "send application"
                in body_lower
            ):

                form_detected = True

            visible_fields = driver.find_elements(
                By.XPATH,
                "//textarea"
                "|//input[not(@type='hidden')]",
            )

            for field in visible_fields:

                try:

                    if field.is_displayed():

                        form_detected = True

                        break

                except Exception:
                    continue

            if not form_detected:

                print(
                    "\nAPPLICATION FORM NOT CONFIRMED."
                )

                record_application_status(
                    application_log,
                    qualified_job,
                    "failed",
                    "Apply clicked but application form was not detected.",
                )

                continue

            # =================================================
            # APPLICATION AVAILABLE
            # =================================================

            print(
                "\n======================================================"
            )

            print(
                "APPLICATION AVAILABLE"
            )

            print(
                "======================================================"
            )

            print(
                "Title:",
                qualified_job["title"],
            )

            print(
                "Location:",
                qualified_job["location"],
            )

            print(
                "URL:",
                qualified_job["url"],
            )

            # =================================================
            # AUTO SUBMIT CHECK
            # =================================================

            if not AUTO_SUBMIT_APPLICATIONS:

                print(
                    "\nAUTO SUBMISSION DISABLED."
                )

                continue

            # =================================================
            # FILL FORM
            # =================================================

            filled_count = (
                fill_application_form(
                    driver
                )
            )

            print(
                "Fields filled:",
                filled_count,
            )

            # =================================================
            # FINAL SUBMISSION
            # =================================================

            submitted = submit_application(
                driver,
                qualified_job,
            )

            # =================================================
            # SUCCESS
            # =================================================

            if submitted:

                # ------------------------------------------------
                # SAVE SUCCESS IMMEDIATELY
                # ------------------------------------------------

                application_log = load_application_log()

                record_application_status(
                    application_log,
                    qualified_job,
                    "submitted",
                )

                applications_submitted_this_run += 1

                # ------------------------------------------------
                # RECALCULATE FROM LOG
                # ------------------------------------------------

                application_log = load_application_log()

                submitted_today = (
                    get_today_submitted_count(
                        application_log
                    )
                )
                attempts_today = get_today_attempt_count(application_log)

                print(
                    "\n======================================================"
                )

                print(
                    "APPLICATION SUBMITTED SUCCESSFULLY"
                )

                print(
                    "======================================================"
                )

                print(
                    "Title:",
                    qualified_job["title"],
                )

                print(
                    "Applications submitted THIS RUN:",
                    applications_submitted_this_run,
                )

                print(
                    "Successful applications TODAY:",
                    submitted_today,
                    "/",
                    TARGET_SUCCESSFUL_APPLICATIONS,
                )

                # ------------------------------------------------
                # TARGET REACHED
                # ------------------------------------------------

                if (
                    has_reached_daily_limit(attempts_today)
                ):

                    print(
                        "\n======================================================"
                    )

                    print(
                        "DAILY SUBMISSION-ATTEMPT LIMIT REACHED"
                    )

                    print(
                        "======================================================"
                    )

                    print(
                        "The automation will stop now."
                    )

                    return

                # ------------------------------------------------
                # TARGET NOT REACHED
                # ------------------------------------------------

                print(
                    "\nTarget not reached yet."
                )

                print(
                    "Searching for another fresh job..."
                )

                continue

            # =================================================
            # SUBMISSION FAILED
            # =================================================

            print(
                "\nSUBMISSION NOT CONFIRMED."
            )

            # submit_application() saved the attempt separately.
            # Reload before saving failure status to avoid overwriting it.
            application_log = load_application_log()

            record_application_status(
                application_log,
                qualified_job,
                "failed",
                "Send Application was clicked but successful submission was not confirmed.",
            )

            # Stop immediately if this failed/unconfirmed submission was
            # the fifth attempt. Do not process another job on this page.
            application_log = load_application_log()
            attempts_today = get_today_attempt_count(application_log)

            if has_reached_daily_limit(attempts_today):
                print(
                    "\nDAILY SUBMISSION-ATTEMPT LIMIT REACHED. "
                    "Stopping automation.",
                    flush=True,
                )
                return

        # ========================================================
        # TARGET CHECK AFTER CURRENT PAGE
        # ========================================================

        application_log = load_application_log()

        submitted_today = (
            get_today_submitted_count(
                application_log
            )
        )
        attempts_today = get_today_attempt_count(application_log)

        print(
            "\n======================================================"
        )

        print(
            "CURRENT PAGE COMPLETED"
        )

        print(
            "======================================================"
        )

        print(
            "Successful applications today:",
            submitted_today,
            "/",
            TARGET_SUCCESSFUL_APPLICATIONS,
        )

        # --------------------------------------------------------
        # TARGET REACHED
        # --------------------------------------------------------

        if has_reached_daily_limit(attempts_today):

            print(
                "\nTARGET REACHED."
            )

            print(
                "Stopping automation."
            )

            break

        # --------------------------------------------------------
        # INSPECTION LIMIT
        # --------------------------------------------------------

        if inspected_count >= MAX_JOBS_TO_INSPECT:

            print(
                "\nMaximum inspection limit reached."
            )

            break

        # --------------------------------------------------------
        # NEXT PAGE
        # --------------------------------------------------------

        print(
            "\nCurrent page did not produce enough successful applications."
        )

        print(
            "Searching for MORE FRESH JOBS..."
        )

        moved = go_to_next_page(
        driver,
        page_number,
        )

        if not moved:

            print(
                "\n======================================================"
            )

            print(
                "NO MORE SEARCH RESULTS DETECTED"
            )

            print(
                "======================================================"
            )

            print(
                "Successful applications today:",
                submitted_today,
                "/",
                TARGET_SUCCESSFUL_APPLICATIONS,
            )

            print(
                "Automation cannot reach 5 if Wellfound has no more"
            )

            print(
                "searchable/eligible jobs available."
            )

            break

        # --------------------------------------------------------
        # IMPORTANT
        # Move to next page only here.
        # --------------------------------------------------------

        page_number += 1

        print(
            "\nMoving to SEARCH PAGE",
            page_number,
        )

        time.sleep(2)

    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    application_log = load_application_log()

    final_submitted_today = (
        get_today_submitted_count(
            application_log
        )
    )
    final_attempts_today = get_today_attempt_count(application_log)

    print(
        "\n\n======================================================"
    )

    print(
        "AUTOMATION FINISHED"
    )

    print(
        "======================================================"
    )

    print(
        "Pages inspected:",
        page_number,
    )

    print(
        "Jobs inspected:",
        inspected_count,
    )

    print(
        "Applications submitted this run:",
        applications_submitted_this_run,
    )

    print(
        "Successful applications today:",
        final_submitted_today,
        "/",
        TARGET_SUCCESSFUL_APPLICATIONS,
    )

    print(
        "Application log:",
        APPLICATION_LOG_FILE,
    )

    if has_reached_daily_limit(final_attempts_today):

        print(
            "\nSTATUS: TARGET REACHED."
        )

    else:

        print(
            "\nSTATUS: TARGET NOT REACHED."
        )

        print(
            "The automation stopped because no more searchable"
        )

        print(
            "results were detected or a safety limit was reached."
        )


# ============================================================
# BROWSER STARTER
# ============================================================

def start_browser():

    options = Options()

    options.add_argument(
        "--start-maximized"
    )

    options.add_argument(
        "--disable-notifications"
    )

    profile_dir = os.environ.get("JOB_AUTOMATION_PROFILE_DIR")
    if profile_dir:
        options.add_argument(
            f"--user-data-dir={profile_dir}"
        )

    driver = webdriver.Chrome(
        options=options
    )

    return driver


# ============================================================
# STANDALONE EXECUTION
# ============================================================
def main():

    print(
        "\n======================================================"
    )

    print(
        "WELLFOUND FINANCE JOB AUTOMATION"
    )

    print(
        "======================================================"
    )

    print(
        "Target:",
        TARGET_SUCCESSFUL_APPLICATIONS,
        "successful applications",
    )

    print(
        "Maximum search pages:",
        MAX_SEARCH_PAGES,
    )

    print(
        "Maximum jobs to inspect:",
        MAX_JOBS_TO_INSPECT,
    )

    driver = start_browser()

    try:

        # ====================================================
        # LOGIN
        # ====================================================

        login_wellfound(
            driver
        )

        # ====================================================
        # START JOB PROCESSOR
        # ====================================================

        print(
            "\n======================================================"
        )

        print(
            "STARTING WELLFOUND JOB PROCESSOR"
        )

        print(
            "======================================================"
        )

        process_wellfound_jobs(
            driver
        )

        # ====================================================
        # AUTOMATION COMPLETE
        # ====================================================

        print(
            "\n======================================================"
        )

        print(
            "WELLFOUND AUTOMATION COMPLETED"
        )

        print(
            "======================================================"
        )

        if not os.environ.get("JOB_AUTOMATION_STUDENT_ID"):
            input(
                "\nPress ENTER to close browser..."
            )

    except Exception as error:

        print(
            "\nAUTOMATION ERROR:",
            error,
        )

        import traceback

        traceback.print_exc()

        if not os.environ.get("JOB_AUTOMATION_STUDENT_ID"):
            input(
                "\nPress ENTER to close..."
            )

        if os.environ.get("JOB_AUTOMATION_STUDENT_ID"):
            raise

    finally:

        driver.quit()


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()

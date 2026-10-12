import json
import re
import time
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

from excel_users import get_user

from selenium import webdriver
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    JavascriptException,
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"
DEBUG_DIR = DATA_DIR / "jobgrin_debug"

DATA_DIR.mkdir(parents=True, exist_ok=True)
DEBUG_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# USER FROM EXCEL
# ============================================================

user = get_user(0)

if not user:
    raise RuntimeError("No user found in Excel.")


def get_user_value(key, default=""):
    target = str(key).strip().lower()

    for k, v in user.items():
        if str(k).strip().lower() == target:
            if v is None:
                return default
            return v

    return default


APPLICANT_NAME = str(
    get_user_value("name", "")
).strip()

APPLICANT_EMAIL = str(
    get_user_value("email", "")
).strip()

APPLICANT_PHONE = str(
    get_user_value("phone", "")
).strip()

APPLICANT_LOCATION = str(
    get_user_value("location", "")
).strip()

APPLICANT_RESUME = str(
    get_user_value("resume", "")
).strip()

APPLICANT_LINKEDIN = str(
    get_user_value("linkedin", "")
).strip()

APPLICANT_GITHUB = str(
    get_user_value("github", "")
).strip()

APPLICANT_EXPERIENCE = str(
    get_user_value("experience", "0")
).strip()


# ============================================================
# JOBGRIN CREDENTIALS
# ============================================================

JOBGRIN_EMAIL = str(
    get_user_value("jobgrin_email", "")
).strip()

JOBGRIN_PASSWORD = str(
    get_user_value("jobgrin_password", "")
).strip()


# ============================================================
# SEARCH SETTINGS
# ============================================================

SEARCH_KEYWORD = str(
    get_user_value(
        "job_keyword",
        "Software Developer"
    )
).strip()

SEARCH_CITY = str(
    get_user_value("city", "")
).strip()

JOB_POSTED_FILTER = str(
    get_user_value("job_posted", "")
).strip()


# ============================================================
# AUTOMATION SETTINGS
# ============================================================

MAX_APPLICATIONS_PER_DAY = 10

MAX_EXPERIENCE_YEARS = 1

PAGE_SCROLL_LIMIT = 8

WAIT_TIMEOUT = 25

AUTO_SUBMIT = True

KEEP_BROWSER_OPEN = True

MAX_PAGES = 50

SCREENSHOT_ON_FAILURE = True

SAVE_HTML_ON_FAILURE = True

# How long to wait after clicking a job card
JOB_CARD_NAVIGATION_TIMEOUT = 10

# How long to wait for application UI
APPLICATION_UI_TIMEOUT = 15


# ============================================================
# URLS
# ============================================================

LOGIN_URL = (
    "https://jobgrin.co.in/candidate/login"
)

JOBS_URL = (
    "https://jobgrin.co.in/jobs"
)

JOBGRIN_DOMAIN = "jobgrin.co.in"


# ============================================================
# JOB CARD
# ============================================================

JOB_CARD_SELECTOR = (
    "div.bg-white.rounded-xl.border.border-gray-200.p-4.cursor-pointer"
)


# ============================================================
# STORAGE
# ============================================================

APPLIED_FILE = (
    DATA_DIR / "jobgrin_applied_jobs.json"
)


# ============================================================
# TERMINAL OUTPUT
# ============================================================

def banner(title):
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


def small_banner(title):
    print()
    print("-" * 70)
    print(title)
    print("-" * 70)


# ============================================================
# NORMALIZATION
# ============================================================

def normalize_text(value):
    if value is None:
        return ""

    value = str(value)

    value = value.replace("\xa0", " ")

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value.strip()


def normalize_lower(value):
    return normalize_text(value).lower()


def clean_url(url):
    if not url:
        return ""

    url = str(url).strip()

    if url.startswith("//"):
        url = "https:" + url

    if url.startswith("/"):
        url = urljoin(
            JOBS_URL,
            url
        )

    return url


def is_jobgrin_domain(url):
    if not url:
        return False

    try:
        parsed = urlparse(url)

        hostname = (
            parsed.netloc.lower()
        )

        return (
            JOBGRIN_DOMAIN in hostname
        )

    except Exception:
        return False


def is_search_page_url(url):
    if not url:
        return False

    try:
        parsed = urlparse(url)

        path = (
            parsed.path or ""
        ).lower().rstrip("/")

        if path == "/jobs":
            return True

        if path.endswith("-jobs"):
            return True

        return False

    except Exception:
        return False


def is_job_detail_url(
    url,
    source_url=""
):
    """
    JobGrin has historically used different URL structures.

    Therefore we do NOT require:
        /jobs/

    anymore.

    We mainly check:
      - JobGrin domain
      - URL is different from source
      - URL isn't login/dashboard/search
    """

    if not url:
        return False

    url = clean_url(url)

    if not is_jobgrin_domain(url):
        return False

    if source_url:
        if normalize_text(url).rstrip("/") == normalize_text(
            source_url
        ).rstrip("/"):
            return False

    lower = url.lower()

    blocked = [
        "/candidate/login",
        "/candidate/dashboard",
        "/login",
        "/register",
        "/signup",
    ]

    if any(
        item in lower
        for item in blocked
    ):
        return False

    if is_search_page_url(url):
        return False

    return True


# ============================================================
# EXPERIENCE PARSING
# ============================================================

def parse_max_experience(text):

    text = normalize_lower(text)

    if not text:
        return None

    if "fresher" in text:
        return 0.0

    numbers = [
        float(x)
        for x in re.findall(
            r"\d+(?:\.\d+)?",
            text
        )
    ]

    if not numbers:
        return None

    if "+" in text:
        return numbers[0]

    if "-" in text and len(numbers) >= 2:
        return max(numbers[:2])

    return numbers[0]


def experience_is_eligible(
    experience_text
):

    experience_text = normalize_text(
        experience_text
    )

    if not experience_text:
        return True

    max_exp = parse_max_experience(
        experience_text
    )

    if max_exp is None:
        return True

    return (
        max_exp <= MAX_EXPERIENCE_YEARS
    )


# ============================================================
# POSTED DATE
# ============================================================

def parse_posted_age_days(text):

    text = normalize_lower(text)

    if not text:
        return None

    if "today" in text:
        return 0

    if "just now" in text:
        return 0

    if "yesterday" in text:
        return 1

    match = re.search(
        r"(\d+)\s*(day|days)\s*ago",
        text
    )

    if match:
        return int(match.group(1))

    match = re.search(
        r"(\d+)\s*(hour|hours)\s*ago",
        text
    )

    if match:
        return 0

    match = re.search(
        r"(\d+)\s*(week|weeks)\s*ago",
        text
    )

    if match:
        return (
            int(match.group(1)) * 7
        )

    match = re.search(
        r"(\d+)\s*(month|months)\s*ago",
        text
    )

    if match:
        return (
            int(match.group(1)) * 30
        )

    return None


def posted_filter_days():

    text = normalize_lower(
        JOB_POSTED_FILTER
    )

    if not text:
        return None

    if "today" in text:
        return 0

    match = re.search(
        r"(\d+)\s*day",
        text
    )

    if match:
        return int(match.group(1))

    match = re.search(
        r"(\d+)\s*week",
        text
    )

    if match:
        return (
            int(match.group(1)) * 7
        )

    return None


def posted_date_is_eligible(job):

    max_days = posted_filter_days()

    if max_days is None:
        return True

    age = parse_posted_age_days(
        job.get("posted_text", "")
    )

    # Unknown date = don't reject.
    if age is None:
        return True

    return age <= max_days


# ============================================================
# PROCESSED JOB STORAGE
# ============================================================

def load_processed_jobs():

    if not APPLIED_FILE.exists():
        return {}

    try:
        with open(
            APPLIED_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

        if isinstance(data, dict):
            return data

        return {}

    except Exception as e:

        print(
            f"[WARNING] Could not read "
            f"application file: {e}"
        )

        return {}


def save_processed_jobs(data):

    temp_file = (
        APPLIED_FILE.with_suffix(".tmp")
    )

    try:

        with open(
            temp_file,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                data,
                f,
                indent=2,
                ensure_ascii=False
            )

        temp_file.replace(
            APPLIED_FILE
        )

    except Exception as e:

        print(
            f"[WARNING] Could not save "
            f"application file: {e}"
        )


def job_key(job):

    url = normalize_text(
        job.get("url", "")
    )

    if url:
        return url

    public_id = normalize_text(
        job.get("public_id", "")
    )

    if public_id:
        return public_id

    title = normalize_lower(
        job.get("title", "")
    )

    company = normalize_lower(
        job.get("company", "")
    )

    location = normalize_lower(
        job.get("location", "")
    )

    return (
        f"{title}|"
        f"{company}|"
        f"{location}"
    )


def is_already_processed(
    job,
    processed
):
    key = job_key(job)

    value = processed.get(key)

    if not isinstance(value, dict):
        return False

    status = normalize_upper(
        value.get("status", "")
    )

    # IMPORTANT:
    # Only APPLIED and EXTERNAL block future attempts.
    #
    # FAILED jobs can be retried.
    return status in {
        "APPLIED",
        "EXTERNAL",
    }


def normalize_upper(value):
    return normalize_text(value).upper()


def record_job(
    processed,
    job,
    status,
    reason=""
):

    key = job_key(job)

    processed[key] = {
        "status": status,
        "title": job.get(
            "title",
            ""
        ),
        "company": job.get(
            "company",
            ""
        ),
        "location": job.get(
            "location",
            ""
        ),
        "url": job.get(
            "url",
            ""
        ),
        "reason": reason,
        "timestamp": datetime.now().isoformat(),
    }

    save_processed_jobs(
        processed
    )


def applications_today(
    processed
):

    today = date.today().isoformat()

    count = 0

    for value in processed.values():

        if not isinstance(value, dict):
            continue

        if (
            normalize_upper(
                value.get("status", "")
            )
            != "APPLIED"
        ):
            continue

        timestamp = str(
            value.get(
                "timestamp",
                ""
            )
        )

        if timestamp.startswith(today):
            count += 1

    return count


# ============================================================
# RESUME
# ============================================================

def resolve_resume_path():

    if not APPLICANT_RESUME:
        return None

    raw = Path(
        APPLICANT_RESUME
    )

    candidates = []

    if raw.is_absolute():

        candidates.append(raw)

    else:

        candidates.extend([
            BASE_DIR / raw,
            DATA_DIR / raw,
            BASE_DIR / "resume" / raw,
            raw,
        ])

    for path in candidates:

        try:

            if (
                path.exists()
                and path.is_file()
            ):
                return path.resolve()

        except Exception:
            pass

    return None


# ============================================================
# BROWSER
# ============================================================

def start_browser():

    banner("STARTING CHROME")

    options = Options()

    options.add_argument(
        "--start-maximized"
    )

    options.add_argument(
        "--disable-notifications"
    )

    options.add_argument(
        "--disable-popup-blocking"
    )

    options.add_argument(
        "--disable-blink-features=AutomationControlled"
    )

    options.add_experimental_option(
        "excludeSwitches",
        ["enable-automation"]
    )

    options.add_experimental_option(
        "useAutomationExtension",
        False
    )

    driver = webdriver.Chrome(
        options=options
    )

    driver.set_page_load_timeout(
        45
    )

    print("Chrome started.")

    return driver


# ============================================================
# SELENIUM HELPERS
# ============================================================

def wait_for_document_ready(
    driver,
    timeout=WAIT_TIMEOUT
):

    try:

        WebDriverWait(
            driver,
            timeout
        ).until(
            lambda d:
            d.execute_script(
                "return document.readyState"
            )
            in (
                "interactive",
                "complete",
            )
        )

    except Exception:
        pass


def visible(element):

    try:
        return element.is_displayed()

    except Exception:
        return False


def enabled(element):

    try:
        return element.is_enabled()

    except Exception:
        return False


def element_text(element):

    try:
        return normalize_text(
            element.text
        )

    except Exception:
        return ""


def safe_attribute(
    element,
    name
):

    try:

        return (
            element.get_attribute(
                name
            )
            or ""
        )

    except Exception:
        return ""


def scroll_into_view(
    driver,
    element
):

    try:

        driver.execute_script(
            """
            arguments[0].scrollIntoView({
                block: 'center',
                inline: 'center'
            });
            """,
            element
        )

        time.sleep(0.4)

    except Exception:
        pass


def safe_click(
    driver,
    element
):

    try:

        scroll_into_view(
            driver,
            element
        )

        element.click()

        return True

    except (
        ElementClickInterceptedException,
        StaleElementReferenceException,
        WebDriverException,
    ):

        pass

    try:

        driver.execute_script(
            "arguments[0].click();",
            element
        )

        return True

    except Exception:

        return False


def close_extra_tabs(
    driver,
    main_handle
):

    handles = list(
        driver.window_handles
    )

    for handle in handles:

        if handle == main_handle:
            continue

        try:

            driver.switch_to.window(
                handle
            )

            driver.close()

        except Exception:
            pass

    if (
        main_handle
        in driver.window_handles
    ):

        driver.switch_to.window(
            main_handle
        )


# ============================================================
# DEBUG
# ============================================================

def save_debug_artifacts(
    driver,
    label
):

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    safe_label = re.sub(
        r"[^a-zA-Z0-9_-]+",
        "_",
        label
    )[:80]

    base = DEBUG_DIR / (
        f"{timestamp}_{safe_label}"
    )

    if SCREENSHOT_ON_FAILURE:

        try:

            driver.save_screenshot(
                str(
                    base.with_suffix(
                        ".png"
                    )
                )
            )

        except Exception:
            pass

    if SAVE_HTML_ON_FAILURE:

        try:

            html = driver.page_source

            with open(
                base.with_suffix(".html"),
                "w",
                encoding="utf-8"
            ) as f:

                f.write(html)

        except Exception:
            pass

    print(
        f"[DEBUG] Debug files saved: {base}"
    )


# ============================================================
# LOGIN
# ============================================================

def login_jobgrin(driver):

    banner("JOBGRIN LOGIN")

    driver.get(
        LOGIN_URL
    )

    wait_for_document_ready(
        driver
    )

    time.sleep(2)

    email_input = None
    password_input = None

    email_selectors = [
        (By.NAME, "email"),
        (By.ID, "email"),
        (
            By.CSS_SELECTOR,
            "input[type='email']"
        ),
        (
            By.CSS_SELECTOR,
            "input[placeholder*='email' i]"
        ),
    ]

    password_selectors = [
        (By.NAME, "password"),
        (By.ID, "password"),
        (
            By.CSS_SELECTOR,
            "input[type='password']"
        ),
    ]

    for by, value in email_selectors:

        try:

            element = WebDriverWait(
                driver,
                5
            ).until(
                EC.presence_of_element_located(
                    (
                        by,
                        value
                    )
                )
            )

            if visible(element):

                email_input = element

                break

        except Exception:
            continue

    for by, value in password_selectors:

        try:

            element = WebDriverWait(
                driver,
                5
            ).until(
                EC.presence_of_element_located(
                    (
                        by,
                        value
                    )
                )
            )

            if visible(element):

                password_input = element

                break

        except Exception:
            continue

    if not email_input:

        if (
            "/candidate/dashboard"
            in driver.current_url
        ):

            print(
                "Already logged in."
            )

            return True

        raise RuntimeError(
            "Could not find JobGrin email field."
        )

    if not JOBGRIN_EMAIL:

        raise RuntimeError(
            "JobGrin email is empty in users.xlsx"
        )

    if not JOBGRIN_PASSWORD:

        raise RuntimeError(
            "JobGrin password is empty in users.xlsx"
        )

    email_input.clear()

    email_input.send_keys(
        JOBGRIN_EMAIL
    )

    password_input.clear()

    password_input.send_keys(
        JOBGRIN_PASSWORD
    )

    buttons = driver.find_elements(
        By.XPATH,
        """
        //button[
            contains(
                translate(
                    normalize-space(.),
                    'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
                    'abcdefghijklmnopqrstuvwxyz'
                ),
                'login'
            )
            or
            contains(
                translate(
                    normalize-space(.),
                    'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
                    'abcdefghijklmnopqrstuvwxyz'
                ),
                'sign in'
            )
        ]
        """
    )

    clicked = False

    for button in buttons:

        if (
            visible(button)
            and enabled(button)
        ):

            if safe_click(
                driver,
                button
            ):

                clicked = True

                break

    if not clicked:

        password_input.send_keys(
            Keys.ENTER
        )

    try:

        WebDriverWait(
            driver,
            WAIT_TIMEOUT
        ).until(
            lambda d:
            (
                "/candidate/dashboard"
                in d.current_url
                or "/candidate/"
                in d.current_url
                or "logout"
                in normalize_lower(
                    d.page_source
                )
            )
        )

    except TimeoutException:
        pass

    time.sleep(2)

    print(
        f"Login URL: "
        f"{driver.current_url}"
    )

    if (
        "/candidate/login"
        in driver.current_url
        or "/login"
        in driver.current_url
    ):

        save_debug_artifacts(
            driver,
            "login_failed"
        )

        raise RuntimeError(
            "JobGrin login failed."
        )

    print(
        "Login successful."
    )

    print(
        f"URL: {driver.current_url}"
    )

    return True


# ============================================================
# OPEN JOBS
# ============================================================

def open_find_jobs(driver):

    banner(
        "OPENING FIND JOBS"
    )

    driver.get(
        JOBS_URL
    )

    wait_for_document_ready(
        driver
    )

    time.sleep(2)

    print(
        "Find Jobs opened."
    )

    print(
        f"URL: {driver.current_url}"
    )

    print(
        f"Title: {driver.title}"
    )


# ============================================================
# SEARCH
# ============================================================

def search_jobs(driver):

    banner(
        f"SEARCHING JOBS: {SEARCH_KEYWORD}"
    )

    keyword = SEARCH_KEYWORD.strip()

    if not keyword:

        raise RuntimeError(
            "job_keyword is empty in users.xlsx"
        )

    slug = re.sub(
        r"[^a-z0-9]+",
        "-",
        keyword.lower()
    ).strip("-")

    search_url = (
        f"https://jobgrin.co.in/"
        f"{slug}-jobs"
    )

    driver.get(
        search_url
    )

    wait_for_document_ready(
        driver
    )

    time.sleep(3)

    print(
        f"Search URL: "
        f"{driver.current_url}"
    )

    print(
        f"Page title: "
        f"{driver.title}"
    )

    # FIXED:
    # Do not check for "/jobs" because
    # software-developer-jobs is valid.

    if not is_jobgrin_domain(
        driver.current_url
    ):

        print(
            "[WARNING] Search URL "
            "did not resolve to JobGrin."
        )

    else:

        print(
            "[OK] JobGrin search page confirmed."
        )

    return driver.current_url


# ============================================================
# SEARCH INPUT FALLBACK
# ============================================================

def perform_search_with_input(
    driver
):

    inputs = driver.find_elements(
        By.CSS_SELECTOR,
        "input"
    )

    target = None

    for inp in inputs:

        if not visible(inp):
            continue

        descriptor = " ".join([
            safe_attribute(
                inp,
                "placeholder"
            ),
            safe_attribute(
                inp,
                "name"
            ),
            safe_attribute(
                inp,
                "id"
            ),
            safe_attribute(
                inp,
                "aria-label"
            ),
        ]).lower()

        if any(
            word in descriptor
            for word in [
                "skill",
                "designation",
                "company",
                "search",
            ]
        ):

            target = inp

            break

    if not target:
        return False

    try:

        target.clear()

        target.send_keys(
            SEARCH_KEYWORD
        )

        target.send_keys(
            Keys.ENTER
        )

        time.sleep(4)

        return True

    except Exception:

        return False


# ============================================================
# LOAD MORE
# ============================================================

def load_more_jobs(driver):

    banner(
        "LOADING MORE JOB RESULTS"
    )

    previous_count = 0

    for scroll_number in range(
        1,
        PAGE_SCROLL_LIMIT + 1
    ):

        try:

            cards = driver.find_elements(
                By.CSS_SELECTOR,
                JOB_CARD_SELECTOR
            )

            current_count = len(
                cards
            )

        except Exception:

            current_count = 0

        print(
            f"Scroll {scroll_number}: "
            f"{current_count} cards"
        )

        try:

            driver.execute_script(
                """
                window.scrollTo({
                    top: document.body.scrollHeight,
                    behavior: 'smooth'
                });
                """
            )

        except Exception:
            pass

        time.sleep(1.5)

        try:

            new_cards = driver.find_elements(
                By.CSS_SELECTOR,
                JOB_CARD_SELECTOR
            )

            new_count = len(
                new_cards
            )

        except Exception:

            new_count = current_count

        previous_count = new_count

    try:

        driver.execute_script(
            "window.scrollTo(0, 0);"
        )

    except Exception:
        pass


# ============================================================
# URL EXTRACTION
# ============================================================

def extract_url_from_card(card):

    # --------------------------------------------------------
    # 1. REAL <a href>
    # --------------------------------------------------------

    try:

        links = card.find_elements(
            By.CSS_SELECTOR,
            "a[href]"
        )

        candidates = []

        for link in links:

            href = clean_url(
                safe_attribute(
                    link,
                    "href"
                )
            )

            if not href:
                continue

            if not is_jobgrin_domain(
                href
            ):
                continue

            if is_search_page_url(
                href
            ):
                continue

            candidates.append(
                href
            )

        if candidates:

            candidates.sort(
                key=len
            )

            return candidates[0]

    except Exception:
        pass

    # --------------------------------------------------------
    # 2. DATA ATTRIBUTES
    # --------------------------------------------------------

    attributes = [
        "data-href",
        "data-url",
        "data-link",
        "data-job-url",
        "data-job-link",
        "href",
    ]

    for attribute in attributes:

        try:

            value = clean_url(
                safe_attribute(
                    card,
                    attribute
                )
            )

            if (
                is_jobgrin_domain(value)
                and not is_search_page_url(value)
            ):

                return value

        except Exception:
            continue

    # --------------------------------------------------------
    # 3. CLICK HANDLER
    # --------------------------------------------------------

    for attribute in [
        "onclick",
        "x-on:click",
        "@click",
    ]:

        try:

            value = safe_attribute(
                card,
                attribute
            )

            if not value:
                continue

            matches = re.findall(
                r"""['"]([^'"]+)['"]""",
                value
            )

            for match in matches:

                url = clean_url(
                    match
                )

                if (
                    is_jobgrin_domain(url)
                    and not is_search_page_url(url)
                ):

                    return url

        except Exception:
            continue

    return ""


# ============================================================
# CARD EXTRACTION
# ============================================================

def extract_experience_from_card(
    card,
    text
):

    selectors = [
        "[class*='experience' i]",
        "[class*='exp' i]",
    ]

    for selector in selectors:

        try:

            elements = card.find_elements(
                By.CSS_SELECTOR,
                selector
            )

            for element in elements:

                value = element_text(
                    element
                )

                if re.search(
                    r"\b(?:fresher|\d+\s*[-+]\s*\d*\s*years?|\d+\+?\s*years?)\b",
                    value,
                    flags=re.IGNORECASE
                ):

                    return value

        except Exception:
            continue

    patterns = [
        r"\bFresher\b",
        r"\b\d+\s*-\s*\d+\s*Years?\b",
        r"\b\d+\+\s*Years?\b",
        r"\b\d+\s*Years?\b",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE
        )

        if match:
            return match.group(0)

    return ""


def extract_posted_text(
    card,
    text
):

    patterns = [
        r"\bToday\b",
        r"\bYesterday\b",
        r"\b\d+\s+days?\s+ago\b",
        r"\b\d+\s+hours?\s+ago\b",
        r"\b\d+\s+weeks?\s+ago\b",
        r"\b\d+\s+months?\s+ago\b",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE
        )

        if match:
            return match.group(0)

    return ""


def extract_company_from_card(
    card,
    text
):

    selectors = [
        "[class*='company' i]",
        "[class*='employer' i]",
    ]

    for selector in selectors:

        try:

            elements = card.find_elements(
                By.CSS_SELECTOR,
                selector
            )

            for element in elements:

                value = element_text(
                    element
                )

                if value:
                    return value

        except Exception:
            continue

    return ""


def extract_job_title(card):

    selectors = [
        "h1",
        "h2",
        "h3",
        "h4",
    ]

    candidates = []

    for selector in selectors:

        try:

            elements = card.find_elements(
                By.CSS_SELECTOR,
                selector
            )

            for element in elements:

                text = element_text(
                    element
                )

                if text:
                    candidates.append(
                        text
                    )

        except Exception:
            continue

    for candidate in candidates:

        if len(candidate) >= 3:
            return candidate

    full = element_text(
        card
    )

    lines = [
        normalize_text(x)
        for x in full.split("\n")
        if normalize_text(x)
    ]

    if lines:
        return lines[0]

    return "Unknown Job"


def extract_job_location(
    card,
    text
):

    selectors = [
        "[class*='location' i]",
        "[class*='city' i]",
    ]

    for selector in selectors:

        try:

            elements = card.find_elements(
                By.CSS_SELECTOR,
                selector
            )

            for element in elements:

                value = element_text(
                    element
                )

                if value:
                    return value

        except Exception:
            continue

    match = re.search(
        r"""
        (
            [A-Z][A-Za-z .'-]+,
            \s*
            (?:Maharashtra|Karnataka|Telangana|Tamil Nadu|
               Gujarat|Delhi|Haryana|West Bengal|Kerala|
               Uttar Pradesh|Rajasthan|Madhya Pradesh|India)
            (?:,\s*India)?
        )
        """,
        text,
        flags=re.IGNORECASE | re.VERBOSE
    )

    if match:

        return normalize_text(
            match.group(1)
        )

    return ""


def extract_public_id(card):

    attributes = [
        "data-id",
        "data-job-id",
        "data-public-id",
        "data-doc-name",
    ]

    for attribute in attributes:

        value = safe_attribute(
            card,
            attribute
        )

        if value:
            return value.strip()

    return ""


# ============================================================
# EXTRACT JOBS
# ============================================================

def extract_jobs(driver):

    banner(
        "EXTRACTING JOB CARDS"
    )

    cards = driver.find_elements(
        By.CSS_SELECTOR,
        JOB_CARD_SELECTOR
    )

    print(
        f"Job cards found: "
        f"{len(cards)}"
    )

    jobs = []

    seen_keys = set()

    for index, card in enumerate(
        cards,
        start=1
    ):

        try:

            text = element_text(
                card
            )

            if not text:
                continue

            title = extract_job_title(
                card
            )

            company = extract_company_from_card(
                card,
                text
            )

            location = extract_job_location(
                card,
                text
            )

            experience = extract_experience_from_card(
                card,
                text
            )

            posted_text = extract_posted_text(
                card,
                text
            )

            job_url = extract_url_from_card(
                card
            )

            public_id = extract_public_id(
                card
            )

            job = {
                "title": title,
                "company": company,
                "location": location,
                "experience": experience,
                "posted_text": posted_text,
                "url": job_url,
                "public_id": public_id,
                "doc_name": "",
                "card_text": text,
                "card_index": index,
            }

            key = (
                job_url
                or public_id
                or (
                    normalize_lower(title)
                    + "|"
                    + normalize_lower(location)
                    + "|"
                    + normalize_lower(company)
                )
            )

            if key in seen_keys:
                continue

            seen_keys.add(key)

            jobs.append(job)

            print(
                f"{index:02d}. "
                f"{title} | "
                f"{company or 'Company not found'} | "
                f"{location or 'Location not found'}"
            )

            if job_url:

                print(
                    f"    URL: {job_url}"
                )

            else:

                print(
                    "    URL: NOT FOUND "
                    "(will click card)"
                )

            if experience:

                print(
                    f"    Experience: "
                    f"{experience}"
                )

            if posted_text:

                print(
                    f"    Posted: "
                    f"{posted_text}"
                )

        except StaleElementReferenceException:
            continue

        except Exception as e:

            print(
                f"[WARNING] Card "
                f"{index} failed: {e}"
            )

    print()

    print(
        f"VALID UNIQUE JOBS: "
        f"{len(jobs)}"
    )

    return jobs


# ============================================================
# KEYWORD FILTER
# ============================================================

def job_matches_keyword(job):

    keyword = normalize_lower(
        SEARCH_KEYWORD
    )

    title = normalize_lower(
        job.get("title", "")
    )

    if not keyword:
        return True

    # Exact phrase.
    if keyword in title:
        return True

    # Special related match:
    # Software Developer <-> Software Engineer
    if (
        "software developer"
        in keyword
    ):

        if (
            "software engineer"
            in title
        ):

            return True

        if (
            "software development"
            in title
        ):

            return True

    # Token match only inside title.
    tokens = re.findall(
        r"[a-z0-9+#.]+",
        keyword
    )

    if not tokens:
        return True

    matches = 0

    for token in tokens:

        if token in title:
            matches += 1

    return (
        matches == len(tokens)
    )


def filter_jobs_by_keyword(
    jobs
):

    banner(
        f"FILTERING JOBS: "
        f"{SEARCH_KEYWORD}"
    )

    matched = []

    for job in jobs:

        title = job.get(
            "title",
            "Unknown"
        )

        if job_matches_keyword(
            job
        ):

            print(
                f"[MATCH] {title}"
            )

            matched.append(job)

        else:

            print(
                f"[SKIP]  {title}"
            )

    print()

    print(
        f"KEYWORD-MATCHED JOBS: "
        f"{len(matched)}"
    )

    return matched


# ============================================================
# EXPERIENCE FILTER
# ============================================================

def filter_jobs_by_experience(
    jobs
):

    banner(
        "FILTERING EXPERIENCE"
    )

    eligible = []

    for job in jobs:

        title = job.get(
            "title",
            "Unknown"
        )

        experience = job.get(
            "experience",
            ""
        )

        if not experience:

            print(
                f"[MATCH] {title} | "
                f"Experience not shown"
            )

            eligible.append(job)

            continue

        if experience_is_eligible(
            experience
        ):

            print(
                f"[MATCH] {title} | "
                f"{experience}"
            )

            eligible.append(job)

        else:

            print(
                f"[SKIP]  {title} | "
                f"{experience}"
            )

    print()

    print(
        f"EXPERIENCE-ELIGIBLE JOBS: "
        f"{len(eligible)}"
    )

    return eligible


# ============================================================
# LOCATION FILTER
# ============================================================

def filter_jobs_by_location(
    jobs
):

    banner(
        f"FILTERING LOCATION: "
        f"{SEARCH_CITY or 'Any'}"
    )

    if not SEARCH_CITY:

        print(
            "No city filter configured."
        )

        return jobs

    city = normalize_lower(
        SEARCH_CITY
    )

    result = []

    for job in jobs:

        title = job.get(
            "title",
            "Unknown"
        )

        location = normalize_lower(
            job.get(
                "location",
                ""
            )
        )

        if not location:

            print(
                f"[MATCH] {title} | "
                f"Location not shown"
            )

            result.append(job)

            continue

        if city in location:

            print(
                f"[MATCH] {title} | "
                f"{location}"
            )

            result.append(job)

        elif "india" in location:

            print(
                f"[MATCH] {title} | "
                f"{location} "
                f"(broad JobGrin location)"
            )

            result.append(job)

        else:

            print(
                f"[SKIP]  {title} | "
                f"{location}"
            )

    print()

    print(
        f"LOCATION-ELIGIBLE JOBS: "
        f"{len(result)}"
    )

    return result


# ============================================================
# POSTED FILTER
# ============================================================

def filter_jobs_by_posted_date(
    jobs
):

    if not JOB_POSTED_FILTER:
        return jobs

    banner(
        f"FILTERING POSTED DATE: "
        f"{JOB_POSTED_FILTER}"
    )

    result = []

    for job in jobs:

        title = job.get(
            "title",
            "Unknown"
        )

        posted = job.get(
            "posted_text",
            ""
        )

        if posted_date_is_eligible(
            job
        ):

            print(
                f"[MATCH] {title} | "
                f"{posted or 'Date not shown'}"
            )

            result.append(job)

        else:

            print(
                f"[SKIP]  {title} | "
                f"{posted}"
            )

    print()

    print(
        f"POSTED-DATE ELIGIBLE JOBS: "
        f"{len(result)}"
    )

    return result


# ============================================================
# DUPLICATES
# ============================================================

def remove_processed_jobs(
    jobs,
    processed
):

    banner(
        "REMOVING ALREADY PROCESSED JOBS"
    )

    result = []

    for job in jobs:

        if is_already_processed(
            job,
            processed
        ):

            print(
                f"[SKIP] Already processed: "
                f"{job.get('title', '')}"
            )

        else:

            result.append(job)

    print()

    print(
        f"NEW JOBS AVAILABLE: "
        f"{len(result)}"
    )

    return result


# ============================================================
# FIND CARD AGAIN
# ============================================================

def find_matching_card(
    driver,
    job
):

    cards = driver.find_elements(
        By.CSS_SELECTOR,
        JOB_CARD_SELECTOR
    )

    target_title = normalize_lower(
        job.get("title", "")
    )

    target_location = normalize_lower(
        job.get("location", "")
    )

    # First try exact title.
    for card in cards:

        try:

            title = normalize_lower(
                extract_job_title(card)
            )

            if title == target_title:

                return card

        except Exception:
            continue

    # Second try title + location.
    for card in cards:

        try:

            title = normalize_lower(
                extract_job_title(card)
            )

            text = normalize_lower(
                element_text(card)
            )

            if (
                target_title
                and target_title in text
                and (
                    not target_location
                    or target_location in text
                )
            ):

                return card

        except Exception:
            continue

    return None


# ============================================================
# CLICK JOB CARD AND CAPTURE URL
# ============================================================

def open_job_by_clicking_card(
    driver,
    job,
    search_url
):

    banner(
        "OPENING JOB BY CARD CLICK"
    )

    print(
        f"[CARD] {job.get('title', '')}"
    )

    main_handle = (
        driver.current_window_handle
    )

    handles_before = set(
        driver.window_handles
    )

    old_url = driver.current_url

    card = find_matching_card(
        driver,
        job
    )

    if not card:

        print(
            "[FAIL] Could not locate "
            "matching job card."
        )

        return None

    scroll_into_view(
        driver,
        card
    )

    # Try click.
    if not safe_click(
        driver,
        card
    ):

        print(
            "[FAIL] Could not click job card."
        )

        return None

    # Wait for either:
    # 1. new tab
    # 2. URL change
    # 3. modal/application UI
    end_time = (
        time.time()
        + JOB_CARD_NAVIGATION_TIMEOUT
    )

    while time.time() < end_time:

        try:

            handles_now = set(
                driver.window_handles
            )

            if len(handles_now) > len(
                handles_before
            ):

                new_handles = [
                    h
                    for h in handles_now
                    if h not in handles_before
                ]

                if new_handles:

                    job_handle = (
                        new_handles[-1]
                    )

                    driver.switch_to.window(
                        job_handle
                    )

                    wait_for_document_ready(
                        driver
                    )

                    time.sleep(1)

                    actual_url = (
                        driver.current_url
                    )

                    print(
                        f"[JOB URL] "
                        f"{actual_url}"
                    )

                    return {
                        "mode": "new_tab",
                        "handle": job_handle,
                        "url": actual_url,
                        "main_handle": main_handle,
                    }

        except Exception:
            pass

        try:

            current_url = (
                driver.current_url
            )

            if (
                current_url != old_url
                and is_job_detail_url(
                    current_url,
                    old_url
                )
            ):

                wait_for_document_ready(
                    driver
                )

                print(
                    f"[JOB URL] "
                    f"{current_url}"
                )

                return {
                    "mode": "same_tab",
                    "handle": main_handle,
                    "url": current_url,
                    "main_handle": main_handle,
                }

        except Exception:
            pass

        # Modal may have appeared without URL change.
        try:

            if application_ui_present(
                driver
            ):

                print(
                    "[INFO] Job/application "
                    "UI opened without URL change."
                )

                return {
                    "mode": "same_tab_modal",
                    "handle": main_handle,
                    "url": driver.current_url,
                    "main_handle": main_handle,
                }

        except Exception:
            pass

        time.sleep(0.4)

    # Last check.
    try:

        if (
            driver.current_url
            != old_url
        ):

            print(
                f"[JOB URL] "
                f"{driver.current_url}"
            )

            return {
                "mode": "same_tab",
                "handle": main_handle,
                "url": driver.current_url,
                "main_handle": main_handle,
            }

    except Exception:
        pass

    print(
        "[FAIL] Clicking the card "
        "did not open a job."
    )

    save_debug_artifacts(
        driver,
        "job_card_click_no_navigation"
    )

    return None


# ============================================================
# OPEN JOB DIRECTLY
# ============================================================

def open_job_in_new_tab(
    driver,
    job_url,
    main_handle
):

    print(
        f"[OPEN URL] {job_url}"
    )

    handles_before = set(
        driver.window_handles
    )

    driver.execute_script(
        """
        window.open(arguments[0], '_blank');
        """,
        job_url
    )

    try:

        WebDriverWait(
            driver,
            10
        ).until(
            lambda d:
            len(d.window_handles)
            > len(handles_before)
        )

    except TimeoutException:

        raise RuntimeError(
            "New job tab did not open."
        )

    new_handles = [
        h
        for h in driver.window_handles
        if h not in handles_before
    ]

    if not new_handles:

        raise RuntimeError(
            "Could not identify new job tab."
        )

    job_handle = new_handles[-1]

    driver.switch_to.window(
        job_handle
    )

    wait_for_document_ready(
        driver
    )

    time.sleep(2)

    print(
        f"[JOB TAB URL] "
        f"{driver.current_url}"
    )

    return job_handle


# ============================================================
# APPLY BUTTON
# ============================================================

def apply_button_score(
    element
):

    try:

        text = normalize_lower(
            element_text(element)
        )

        aria = normalize_lower(
            safe_attribute(
                element,
                "aria-label"
            )
        )

        title = normalize_lower(
            safe_attribute(
                element,
                "title"
            )
        )

        combined = " ".join([
            text,
            aria,
            title,
        ]).strip()

        if not combined:
            return -1

        reject_words = [
            "login",
            "log in",
            "sign up",
            "register",
            "share",
            "save",
            "search",
            "filter",
            "profile",
        ]

        if any(
            word in combined
            for word in reject_words
        ):
            return -1

        exact = {
            "apply",
            "apply now",
            "apply for this job",
            "apply for job",
        }

        if combined in exact:
            return 100

        if "apply now" in combined:
            return 95

        if "apply for this job" in combined:
            return 95

        if combined.startswith("apply"):
            return 85

        if (
            "apply"
            in combined
            and len(combined) < 60
        ):
            return 70

        return -1

    except Exception:

        return -1


def find_apply_button(
    driver
):

    selectors = [
        "button",
        "a",
        "input[type='button']",
        "input[type='submit']",
        "[role='button']",
    ]

    candidates = []

    for selector in selectors:

        try:

            elements = driver.find_elements(
                By.CSS_SELECTOR,
                selector
            )

            for element in elements:

                if not visible(element):
                    continue

                if not enabled(element):
                    continue

                score = apply_button_score(
                    element
                )

                if score < 0:
                    continue

                candidates.append(
                    (
                        score,
                        element
                    )
                )

        except Exception:
            continue

    if not candidates:
        return None

    candidates.sort(
        key=lambda x: x[0],
        reverse=True
    )

    return candidates[0][1]


# ============================================================
# APPLICATION UI
# ============================================================

def application_ui_present(
    driver
):

    try:

        forms = driver.find_elements(
            By.CSS_SELECTOR,
            "form"
        )

        for form in forms:

            if not visible(form):
                continue

            fields = form.find_elements(
                By.CSS_SELECTOR,
                "input, textarea, select"
            )

            if fields:
                return True

    except Exception:
        pass

    try:

        inputs = driver.find_elements(
            By.CSS_SELECTOR,
            """
            input:not([type='hidden']),
            textarea,
            select
            """
        )

        visible_inputs = [
            x
            for x in inputs
            if visible(x)
        ]

        if len(visible_inputs) >= 2:
            return True

    except Exception:
        pass

    body = page_body_text(
        driver
    )

    markers = [
        "apply for this job",
        "application form",
        "submit application",
        "your application",
        "candidate details",
        "personal details",
    ]

    return any(
        marker in body
        for marker in markers
    )


# ============================================================
# FIELD DESCRIPTOR
# ============================================================

def field_descriptor(
    driver,
    element
):

    values = []

    for attribute in [
        "name",
        "id",
        "placeholder",
        "aria-label",
        "autocomplete",
    ]:

        value = safe_attribute(
            element,
            attribute
        )

        if value:
            values.append(value)

    element_id = safe_attribute(
        element,
        "id"
    )

    if element_id:

        try:

            labels = driver.find_elements(
                By.CSS_SELECTOR,
                f"label[for='{element_id}']"
            )

            for label in labels:

                value = element_text(
                    label
                )

                if value:
                    values.append(value)

        except Exception:
            pass

    try:

        parent_label = element.find_element(
            By.XPATH,
            "./ancestor::label[1]"
        )

        value = element_text(
            parent_label
        )

        if value:
            values.append(value)

    except Exception:
        pass

    return normalize_lower(
        " ".join(values)
    )


# ============================================================
# FILL ELEMENT
# ============================================================

def fill_element(
    element,
    value
):

    if value is None:
        return False

    value = str(value).strip()

    if not value:
        return False

    try:

        element.click()

        element.send_keys(
            Keys.CONTROL,
            "a"
        )

        element.send_keys(
            value
        )

        return True

    except Exception:

        try:

            element.clear()

            element.send_keys(
                value
            )

            return True

        except Exception:

            return False


# ============================================================
# FILL APPLICATION
# ============================================================

def fill_application_form(
    driver
):

    banner(
        "FILLING APPLICATION FORM"
    )

    filled = set()

    fields = driver.find_elements(
        By.CSS_SELECTOR,
        """
        input:not([type='hidden']),
        textarea
        """
    )

    visible_count = len([
        x
        for x in fields
        if visible(x)
    ])

    print(
        f"Visible form fields found: "
        f"{visible_count}"
    )

    for field in fields:

        try:

            if not visible(field):
                continue

            field_type = normalize_lower(
                safe_attribute(
                    field,
                    "type"
                )
            )

            if field_type in {
                "submit",
                "button",
                "checkbox",
                "radio",
                "file",
            }:
                continue

            descriptor = field_descriptor(
                driver,
                field
            )

            value = None
            field_name = None

            # NAME
            if any(
                word in descriptor
                for word in [
                    "full name",
                    "candidate name",
                    "applicant name",
                    "your name",
                ]
            ):

                value = APPLICANT_NAME
                field_name = "name"

            # EMAIL
            elif (
                "email"
                in descriptor
                or field_type == "email"
            ):

                value = APPLICANT_EMAIL
                field_name = "email"

            # PHONE
            elif any(
                word in descriptor
                for word in [
                    "phone",
                    "mobile",
                    "contact number",
                    "telephone",
                ]
            ):

                value = APPLICANT_PHONE
                field_name = "phone"

            # LINKEDIN
            elif "linkedin" in descriptor:

                value = APPLICANT_LINKEDIN
                field_name = "linkedin"

            # GITHUB
            elif "github" in descriptor:

                value = APPLICANT_GITHUB
                field_name = "github"

            # LOCATION
            elif any(
                word in descriptor
                for word in [
                    "current location",
                    "location",
                    "city",
                ]
            ):

                if (
                    "job location"
                    not in descriptor
                    and
                    "preferred location"
                    not in descriptor
                ):

                    value = APPLICANT_LOCATION
                    field_name = "location"

            # EXPERIENCE
            elif any(
                word in descriptor
                for word in [
                    "years of experience",
                    "total experience",
                    "experience",
                ]
            ):

                value = APPLICANT_EXPERIENCE
                field_name = "experience"

            if (
                field_name
                and value
                and field_name not in filled
            ):

                if fill_element(
                    field,
                    value
                ):

                    filled.add(
                        field_name
                    )

                    print(
                        f"[FILLED] "
                        f"{field_name}"
                    )

        except (
            StaleElementReferenceException
        ):
            continue

        except Exception as e:

            print(
                f"[WARNING] Field error: {e}"
            )

    # ========================================================
    # RESUME
    # ========================================================

    resume_path = (
        resolve_resume_path()
    )

    file_inputs = driver.find_elements(
        By.CSS_SELECTOR,
        "input[type='file']"
    )

    if file_inputs:

        if resume_path:

            print(
                f"[RESUME] Uploading: "
                f"{resume_path}"
            )

            uploaded = False

            for file_input in file_inputs:

                try:

                    descriptor = field_descriptor(
                        driver,
                        file_input
                    )

                    if (
                        "resume"
                        in descriptor
                        or "cv"
                        in descriptor
                        or len(file_inputs) == 1
                    ):

                        file_input.send_keys(
                            str(resume_path)
                        )

                        uploaded = True

                        print(
                            "[RESUME] Uploaded."
                        )

                        break

                except Exception as e:

                    print(
                        f"[WARNING] Resume upload "
                        f"failed: {e}"
                    )

            if not uploaded:

                print(
                    "[WARNING] Resume input "
                    "found but upload failed."
                )

        else:

            print(
                "[WARNING] Resume path not found."
            )

            print(
                f"Excel resume value: "
                f"{APPLICANT_RESUME}"
            )

    print()

    print(
        "Fields filled automatically: "
        f"{', '.join(sorted(filled)) or 'None'}"
    )

    return filled


# ============================================================
# VALIDATION ERRORS
# ============================================================

def find_validation_errors(
    driver
):

    errors = []

    selectors = [
        ".error",
        ".text-red-500",
        ".text-red-600",
        "[role='alert']",
        ".invalid-feedback",
        "p.text-danger",
    ]

    for selector in selectors:

        try:

            elements = driver.find_elements(
                By.CSS_SELECTOR,
                selector
            )

            for element in elements:

                if not visible(element):
                    continue

                text = element_text(
                    element
                )

                if (
                    text
                    and len(text) < 300
                ):

                    errors.append(text)

        except Exception:
            continue

    result = []

    seen = set()

    for error in errors:

        key = normalize_lower(
            error
        )

        if key not in seen:

            seen.add(key)

            result.append(error)

    return result


# ============================================================
# SUCCESS DETECTION
# ============================================================

SUCCESS_PHRASES = [
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
]

ALREADY_APPLIED_PHRASES = [
    "already applied",
    "you have already applied",
    "application already submitted",
]


def page_body_text(
    driver
):

    try:

        return normalize_lower(
            driver.find_element(
                By.TAG_NAME,
                "body"
            ).text
        )

    except Exception:

        return ""


def application_success_detected(
    driver
):

    body = page_body_text(
        driver
    )

    for phrase in SUCCESS_PHRASES:

        if phrase in body:
            return True

    for phrase in ALREADY_APPLIED_PHRASES:

        if phrase in body:
            return True

    try:

        elements = driver.find_elements(
            By.XPATH,
            """
            //*[
                self::button
                or self::a
                or @role='button'
            ]
            """
        )

        for element in elements:

            if not visible(element):
                continue

            text = normalize_lower(
                element_text(element)
            )

            if text in {
                "applied",
                "already applied",
                "application submitted",
            }:

                return True

    except Exception:
        pass

    return False


# ============================================================
# WAIT APPLICATION UI
# ============================================================

def wait_for_application_ui(
    driver
):

    try:

        WebDriverWait(
            driver,
            APPLICATION_UI_TIMEOUT
        ).until(
            lambda d:
            (
                application_ui_present(d)
                or
                application_success_detected(d)
            )
        )

        return True

    except TimeoutException:

        return (
            application_ui_present(
                driver
            )
        )


# ============================================================
# SUBMIT BUTTON
# ============================================================

def submit_button_score(
    element
):

    try:

        text = normalize_lower(
            element_text(element)
        )

        value = normalize_lower(
            safe_attribute(
                element,
                "value"
            )
        )

        aria = normalize_lower(
            safe_attribute(
                element,
                "aria-label"
            )
        )

        combined = " ".join([
            text,
            value,
            aria,
        ]).strip()

        if not combined:
            return -1

        if combined in {
            "apply",
            "apply now",
        }:
            return -1

        if (
            "submit application"
            in combined
        ):
            return 100

        if (
            "send application"
            in combined
        ):
            return 95

        if (
            "confirm application"
            in combined
        ):
            return 95

        if combined == "submit":
            return 90

        if combined.startswith("submit"):
            return 85

        if combined == "send":
            return 80

        if combined == "continue":
            return 30

        return -1

    except Exception:

        return -1


def find_submit_button(
    driver
):

    selectors = [
        "button",
        "input[type='submit']",
        "input[type='button']",
        "[role='button']",
    ]

    candidates = []

    for selector in selectors:

        try:

            elements = driver.find_elements(
                By.CSS_SELECTOR,
                selector
            )

            for element in elements:

                if not visible(element):
                    continue

                if not enabled(element):
                    continue

                score = submit_button_score(
                    element
                )

                if score < 0:
                    continue

                candidates.append(
                    (
                        score,
                        element
                    )
                )

        except Exception:
            continue

    if not candidates:
        return None

    candidates.sort(
        key=lambda x: x[0],
        reverse=True
    )

    return candidates[0][1]


# ============================================================
# SUBMIT APPLICATION
# ============================================================

def submit_application(
    driver
):

    banner(
        "SUBMITTING APPLICATION"
    )

    if not AUTO_SUBMIT:

        print(
            "AUTO_SUBMIT is False."
        )

        return False

    if application_success_detected(
        driver
    ):

        print(
            "[SUCCESS] Application "
            "already confirmed."
        )

        return True

    submit_button = find_submit_button(
        driver
    )

    if not submit_button:

        errors = find_validation_errors(
            driver
        )

        if errors:

            print(
                "[VALIDATION ERRORS]"
            )

            for error in errors:

                print(
                    f"  - {error}"
                )

        print(
            "[FAIL] Submit button not found."
        )

        save_debug_artifacts(
            driver,
            "submit_button_not_found"
        )

        return False

    print(
        "[SUBMIT BUTTON] "
        f"{element_text(submit_button) or 'Submit'}"
    )

    old_url = driver.current_url

    if not safe_click(
        driver,
        submit_button
    ):

        print(
            "[FAIL] Could not click submit."
        )

        save_debug_artifacts(
            driver,
            "submit_click_failed"
        )

        return False

    time.sleep(2)

    if wait_for_application_success(
        driver,
        timeout=15
    ):

        print(
            "[SUCCESS] Application "
            "submission confirmed."
        )

        return True

    if (
        driver.current_url
        != old_url
    ):

        print(
            f"[INFO] URL changed after "
            f"submit: {driver.current_url}"
        )

        if application_success_detected(
            driver
        ):

            print(
                "[SUCCESS] Application confirmed."
            )

            return True

    errors = find_validation_errors(
        driver
    )

    if errors:

        print(
            "[APPLICATION VALIDATION ERRORS]"
        )

        for error in errors:

            print(
                f"  - {error}"
            )

    print(
        "[FAIL] Could not confirm "
        "application submission."
    )

    save_debug_artifacts(
        driver,
        "application_not_confirmed"
    )

    return False


def wait_for_application_success(driver, timeout=15):
    success_phrases = [
        "application submitted",
        "application successful",
        "successfully applied",
        "application has been submitted",
        "your application was submitted",
        "thank you for applying",
        "applied successfully",
    ]

    end_time = time.time() + timeout

    while time.time() < end_time:
        try:
            body_text = driver.find_element(By.TAG_NAME, "body").text.lower()

            for phrase in success_phrases:
                if phrase in body_text:
                    print(f"[SUCCESS] Found confirmation: {phrase}")
                    return True

        except Exception:
            pass

        time.sleep(1)

    return False


# ============================================================
# APPLY TO ONE JOB
# ============================================================

def apply_to_job(
    driver,
    job,
    main_handle,
    search_url
):

    title = job.get(
        "title",
        "Unknown Job"
    )

    company = job.get(
        "company",
        ""
    )

    job_url = job.get(
        "url",
        ""
    )

    banner(
        f"APPLYING: {title}"
    )

    print(
        f"Company : {company}"
    )

    print(
        f"Location: "
        f"{job.get('location', '')}"
    )

    print(
        f"URL     : "
        f"{job_url or 'NOT FOUND - CARD CLICK MODE'}"
    )

    opened = None

    try:

        # ====================================================
        # METHOD 1
        # DIRECT URL
        # ====================================================

        if job_url:

            print(
                "[METHOD] Direct URL"
            )

            if not is_jobgrin_domain(
                job_url
            ):

                print(
                    "[WARNING] Extracted URL "
                    "is not JobGrin."
                )

                job_url = ""

            else:

                job_handle = (
                    open_job_in_new_tab(
                        driver,
                        job_url,
                        main_handle
                    )
                )

                opened = {
                    "mode": "new_tab",
                    "handle": job_handle,
                    "url": driver.current_url,
                    "main_handle": main_handle,
                }

        # ====================================================
        # METHOD 2
        # CLICK CARD
        # ====================================================

        if not opened:

            print(
                "[METHOD] Clicking job card "
                "to discover actual URL..."
            )

            driver.switch_to.window(
                main_handle
            )

            opened = (
                open_job_by_clicking_card(
                    driver,
                    job,
                    search_url
                )
            )

        if not opened:

            return {
                "status": "FAILED",
                "reason": "JOB_OPEN_FAILED",
            }

        current_url = (
            opened["url"]
        )

        print()
        print(
            f"[ACTUAL JOB URL] "
            f"{current_url}"
        )

        # ====================================================
        # CHECK IF URL IS ACTUALLY A JOB
        # ====================================================

        if (
            opened["mode"]
            != "same_tab_modal"
            and
            not is_job_detail_url(
                current_url,
                search_url
            )
        ):

            print(
                "[WARNING] Job URL could "
                "not be confirmed as detail page."
            )

            # Still continue if page contains Apply.
            if not find_apply_button(
                driver
            ):

                print(
                    "[FAIL] No Apply button "
                    "on opened page."
                )

                return {
                    "status": "FAILED",
                    "reason": "JOB_DETAIL_NOT_FOUND",
                }

        # ====================================================
        # ALREADY APPLIED
        # ====================================================

        body = page_body_text(
            driver
        )

        for phrase in ALREADY_APPLIED_PHRASES:

            if phrase in body:

                print(
                    "[INFO] Job already applied."
                )

                return {
                    "status": "APPLIED",
                    "reason": "ALREADY_APPLIED",
                }

        # ====================================================
        # APPLY BUTTON
        # ====================================================

        print(
            "[STEP] Searching for Apply button..."
        )

        apply_button = find_apply_button(
            driver
        )

        if not apply_button:

            # Maybe application form is already open.
            if application_ui_present(
                driver
            ):

                print(
                    "[OK] Application UI "
                    "already present."
                )

            else:

                print(
                    "[FAIL] Apply button not found."
                )

                save_debug_artifacts(
                    driver,
                    "apply_button_not_found"
                )

                return {
                    "status": "FAILED",
                    "reason": "APPLY_BUTTON_NOT_FOUND",
                }

        else:

            print(
                "[APPLY BUTTON] "
                f"{element_text(apply_button) or 'Apply'}"
            )

            handles_before = set(
                driver.window_handles
            )

            old_url = driver.current_url

            if not safe_click(
                driver,
                apply_button
            ):

                print(
                    "[FAIL] Could not click Apply."
                )

                save_debug_artifacts(
                    driver,
                    "apply_click_failed"
                )

                return {
                    "status": "FAILED",
                    "reason": "APPLY_CLICK_FAILED",
                }

            # Wait for new tab or URL change.
            try:

                WebDriverWait(
                    driver,
                    5
                ).until(
                    lambda d:
                    (
                        len(d.window_handles)
                        > len(handles_before)
                        or
                        d.current_url != old_url
                        or
                        application_ui_present(d)
                    )
                )

            except TimeoutException:
                pass

            # New tab.
            if (
                len(driver.window_handles)
                > len(handles_before)
            ):

                new_handles = [
                    h
                    for h in driver.window_handles
                    if h not in handles_before
                ]

                if new_handles:

                    driver.switch_to.window(
                        new_handles[-1]
                    )

                    wait_for_document_ready(
                        driver
                    )

                    print(
                        "[INFO] Apply opened "
                        "a new tab."
                    )

            time.sleep(1.5)

        # ====================================================
        # ACTUAL URL AFTER APPLY
        # ====================================================

        print(
            f"[APPLICATION URL] "
            f"{driver.current_url}"
        )

        # ====================================================
        # EXTERNAL APPLICATION
        # ====================================================

        if not is_jobgrin_domain(
            driver.current_url
        ):

            print(
                "[EXTERNAL] Application "
                "redirected outside JobGrin."
            )

            return {
                "status": "EXTERNAL",
                "reason": "EXTERNAL_APPLICATION_REQUIRED",
                "url": driver.current_url,
            }

        # ====================================================
        # IMMEDIATE SUCCESS
        # ====================================================

        if application_success_detected(
            driver
        ):

            print(
                "[SUCCESS] Application "
                "confirmed immediately."
            )

            return {
                "status": "APPLIED",
                "reason": "APPLICATION_CONFIRMED",
            }

        # ====================================================
        # APPLICATION FORM
        # ====================================================

        print(
            "[STEP] Waiting for "
            "application form..."
        )

        form_found = (
            wait_for_application_ui(
                driver
            )
        )

        if not form_found:

            print(
                "[FAIL] Application form "
                "did not appear."
            )

            save_debug_artifacts(
                driver,
                "application_form_not_found"
            )

            return {
                "status": "FAILED",
                "reason": "APPLICATION_FORM_NOT_FOUND",
            }

        print(
            "[OK] Application form detected."
        )

        # ====================================================
        # FILL
        # ====================================================

        fill_application_form(
            driver
        )

        time.sleep(1)

        # ====================================================
        # SUCCESS AFTER FILL
        # ====================================================

        if application_success_detected(
            driver
        ):

            print(
                "[SUCCESS] Application confirmed."
            )

            return {
                "status": "APPLIED",
                "reason": "APPLICATION_CONFIRMED",
            }

        # ====================================================
        # SUBMIT
        # ====================================================

        submitted = (
            submit_application(
                driver
            )
        )

        if submitted:

            return {
                "status": "APPLIED",
                "reason": "APPLICATION_SUBMITTED",
            }

        return {
            "status": "FAILED",
            "reason": "SUBMISSION_NOT_CONFIRMED",
        }

    except Exception as e:

        print(
            f"[ERROR] Application exception: {e}"
        )

        try:

            save_debug_artifacts(
                driver,
                "application_exception"
            )

        except Exception:
            pass

        return {
            "status": "FAILED",
            "reason": str(e),
        }

    finally:

        # ====================================================
        # CLOSE JOB TABS
        # ====================================================

        try:

            current_handle = (
                driver.current_window_handle
            )

            if (
                current_handle != main_handle
                and current_handle
                in driver.window_handles
            ):

                driver.close()

        except Exception:
            pass

        # Close any unexpected tabs.
        try:

            close_extra_tabs(
                driver,
                main_handle
            )

        except Exception:
            pass

        # ====================================================
        # RETURN TO SEARCH PAGE
        # ====================================================

        try:

            driver.switch_to.window(
                main_handle
            )

        except Exception:
            pass

        # If same-tab card navigation happened,
        # restore the search page.
        try:

            if (
                driver.current_url
                != search_url
            ):

                if (
                    is_jobgrin_domain(
                        driver.current_url
                    )
                    and
                    not is_search_page_url(
                        driver.current_url
                    )
                ):

                    print(
                        "[RETURN] Restoring "
                        "search page..."
                    )

                    driver.get(
                        search_url
                    )

                    wait_for_document_ready(
                        driver
                    )

                    time.sleep(2)

        except Exception as e:

            print(
                f"[WARNING] Could not restore "
                f"search page: {e}"
            )

        time.sleep(1)


# ============================================================
# PAGE SIGNATURE
# ============================================================

def page_signature(
    driver
):

    try:

        cards = driver.find_elements(
            By.CSS_SELECTOR,
            JOB_CARD_SELECTOR
        )

        if not cards:
            return ""

        first = element_text(
            cards[0]
        )

        last = element_text(
            cards[-1]
        )

        return (
            normalize_lower(first)
            + "||"
            + normalize_lower(last)
        )

    except Exception:

        return ""


# ============================================================
# NEXT PAGE
# ============================================================

def find_next_page(
    driver
):

    selectors = [
        "a[aria-label*='next' i]",
        "button[aria-label*='next' i]",
        "a[title*='next' i]",
        "button[title*='next' i]",
    ]

    candidates = []

    for selector in selectors:

        try:

            candidates.extend(
                driver.find_elements(
                    By.CSS_SELECTOR,
                    selector
                )
            )

        except Exception:
            pass

    try:

        candidates.extend(
            driver.find_elements(
                By.XPATH,
                """
                //a[
                    normalize-space(
                        translate(
                            .,
                            'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
                            'abcdefghijklmnopqrstuvwxyz'
                        )
                    )='next'
                ]
                |
                //button[
                    normalize-space(
                        translate(
                            .,
                            'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
                            'abcdefghijklmnopqrstuvwxyz'
                        )
                    )='next'
                ]
                """
            )
        )

    except Exception:
        pass

    seen = set()

    for element in candidates:

        try:

            identifier = (
                safe_attribute(
                    element,
                    "href"
                )
                + "|"
                + element_text(element)
            )

            if identifier in seen:
                continue

            seen.add(identifier)

            if not visible(element):
                continue

            if not enabled(element):
                continue

            aria_disabled = normalize_lower(
                safe_attribute(
                    element,
                    "aria-disabled"
                )
            )

            disabled = safe_attribute(
                element,
                "disabled"
            )

            class_name = normalize_lower(
                safe_attribute(
                    element,
                    "class"
                )
            )

            if aria_disabled == "true":
                continue

            if disabled:
                continue

            if "disabled" in class_name:
                continue

            return element

        except Exception:
            continue

    return None


def go_to_next_page(driver):
    """
    Move JobGrin search results to the next page.

    Strategy:
    1. Look for a visible Next button/link.
    2. Look for numbered pagination and determine current page.
    3. Click the next page number when available.
    4. Verify that the page actually changed.
    """

    print("\n" + "=" * 70)
    print("MOVING TO NEXT PAGE")
    print("=" * 70)

    old_url = driver.current_url

    try:
        old_cards = driver.find_elements(By.CSS_SELECTOR, JOB_CARD_SELECTOR)
        old_first_title = ""

        if old_cards:
            try:
                old_first_title = old_cards[0].text[:150]
            except Exception:
                pass

        # ---------------------------------------------------------
        # METHOD 1: Find explicit NEXT button/link
        # ---------------------------------------------------------

        next_selectors = [
            "a[aria-label*='Next' i]",
            "button[aria-label*='Next' i]",
            "a[title*='Next' i]",
            "button[title*='Next' i]",
            "a[rel='next']",
            "a",
            "button",
        ]

        candidates = []

        for selector in next_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)

                for element in elements:
                    try:
                        if not element.is_displayed():
                            continue

                        text_value = (
                            element.text or
                            element.get_attribute("aria-label") or
                            element.get_attribute("title") or
                            ""
                        ).strip().lower()

                        if (
                            text_value == "next"
                            or "next page" in text_value
                            or text_value == ">"
                            or text_value == "›"
                            or text_value == "→"
                        ):
                            candidates.append(element)

                    except Exception:
                        continue

            except Exception:
                continue

        # Remove duplicate WebElements
        unique_candidates = []

        for element in candidates:
            if element not in unique_candidates:
                unique_candidates.append(element)

        if unique_candidates:

            next_button = unique_candidates[0]

            print("[PAGINATION] Next button found.")

            try:
                driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center'});",
                    next_button
                )

                time.sleep(1)

                driver.execute_script(
                    "arguments[0].click();",
                    next_button
                )

            except Exception as click_error:
                print(f"[WARNING] JS click failed: {click_error}")

                try:
                    next_button.click()
                except Exception as normal_click_error:
                    print(
                        f"[FAIL] Could not click Next: "
                        f"{normal_click_error}"
                    )
                    return False

            # -----------------------------------------------------
            # WAIT FOR PAGE CHANGE
            # -----------------------------------------------------

            end_time = time.time() + 15

            while time.time() < end_time:

                time.sleep(1)

                new_url = driver.current_url

                try:
                    new_cards = driver.find_elements(
                        By.CSS_SELECTOR,
                        JOB_CARD_SELECTOR
                    )

                    new_first_title = ""

                    if new_cards:
                        new_first_title = new_cards[0].text[:150]

                except Exception:
                    new_first_title = ""

                if (
                    new_url != old_url
                    or (
                        new_first_title
                        and new_first_title != old_first_title
                    )
                ):
                    print(
                        f"[OK] Moved to next page."
                    )
                    print(f"[NEW URL] {new_url}")

                    return True

            print(
                "[WARNING] Next was clicked but page did not change."
            )

        # ---------------------------------------------------------
        # METHOD 2: Inspect pagination numbers
        # ---------------------------------------------------------

        print(
            "[INFO] Explicit Next button not usable."
        )

        print(
            "[PAGINATION] Checking numbered pages..."
        )

        pagination_elements = []

        try:
            all_links = driver.find_elements(By.TAG_NAME, "a")

            for element in all_links:

                try:
                    if not element.is_displayed():
                        continue

                    text_value = element.text.strip()

                    if text_value.isdigit():

                        number = int(text_value)

                        if 1 <= number <= 999:
                            pagination_elements.append(
                                (number, element)
                            )

                except Exception:
                    continue

        except Exception:
            pass

        if pagination_elements:

            current_page = None

            # Try to determine active page
            for number, element in pagination_elements:

                try:
                    classes = (
                        element.get_attribute("class") or ""
                    ).lower()

                    aria_current = (
                        element.get_attribute("aria-current")
                        or ""
                    ).lower()

                    if (
                        "active" in classes
                        or "current" in classes
                        or aria_current == "page"
                    ):
                        current_page = number
                        break

                except Exception:
                    continue

            if current_page is None:
                current_page = 1

            print(
                f"[PAGINATION] Current page: {current_page}"
            )

            target_page = current_page + 1

            target_element = None

            for number, element in pagination_elements:

                if number == target_page:
                    target_element = element
                    break

            if target_element:

                print(
                    f"[PAGINATION] Opening page {target_page}"
                )

                try:
                    driver.execute_script(
                        "arguments[0].scrollIntoView({block:'center'});",
                        target_element
                    )

                    time.sleep(1)

                    driver.execute_script(
                        "arguments[0].click();",
                        target_element
                    )

                except Exception as click_error:

                    print(
                        f"[WARNING] Numbered page click failed: "
                        f"{click_error}"
                    )

                    try:
                        target_element.click()
                    except Exception:
                        return False

                end_time = time.time() + 15

                while time.time() < end_time:

                    time.sleep(1)

                    if driver.current_url != old_url:
                        print(
                            f"[OK] Moved to page {target_page}"
                        )
                        print(
                            f"[NEW URL] {driver.current_url}"
                        )
                        return True

                    try:
                        new_cards = driver.find_elements(
                            By.CSS_SELECTOR,
                            JOB_CARD_SELECTOR
                        )

                        new_first_title = ""

                        if new_cards:
                            new_first_title = (
                                new_cards[0].text[:150]
                            )

                        if (
                            new_first_title
                            and new_first_title != old_first_title
                        ):
                            print(
                                f"[OK] Moved to page {target_page}"
                            )
                            return True

                    except Exception:
                        pass

            else:
                print(
                    f"[INFO] Page {target_page} not found."
                )

        print(
            "[INFO] No usable next page found."
        )

        return False

    except Exception as e:

        print(
            f"[ERROR] Pagination exception: {e}"
        )

        return False


# ============================================================
# PROCESS PAGE
# ============================================================

def process_current_page(
    driver,
    processed,
    main_handle,
    current_application_count,
    search_url
):

    jobs = extract_jobs(
        driver
    )

    if not jobs:

        print(
            "[WARNING] No jobs found."
        )

        return current_application_count

    print(
        f"\nPage jobs extracted: "
        f"{len(jobs)}"
    )

    # ========================================================
    # KEYWORD
    # ========================================================

    jobs = filter_jobs_by_keyword(
        jobs
    )

    if not jobs:

        print(
            "No jobs matched keyword."
        )

        return current_application_count

    # ========================================================
    # EXPERIENCE
    # ========================================================

    jobs = filter_jobs_by_experience(
        jobs
    )

    if not jobs:

        print(
            "No jobs passed experience filter."
        )

        return current_application_count

    # ========================================================
    # LOCATION
    # ========================================================

    jobs = filter_jobs_by_location(
        jobs
    )

    if not jobs:

        print(
            "No jobs passed location filter."
        )

        return current_application_count

    # ========================================================
    # POSTED
    # ========================================================

    jobs = filter_jobs_by_posted_date(
        jobs
    )

    if not jobs:

        print(
            "No jobs passed posted-date filter."
        )

        return current_application_count

    # ========================================================
    # DUPLICATES
    # ========================================================

    jobs = remove_processed_jobs(
        jobs,
        processed
    )

    print(
        f"\n[DEBUG] Jobs available "
        f"for application: {len(jobs)}"
    )

    if not jobs:
        return current_application_count

    banner(
        "APPLICATIONS FROM CURRENT PAGE"
    )

    # ========================================================
    # APPLY
    # ========================================================

    for index, job in enumerate(
        jobs,
        start=1
    ):

        if (
            current_application_count
            >= MAX_APPLICATIONS_PER_DAY
        ):

            print(
                "\nDaily application "
                "limit reached."
            )

            break

        print()
        print(
            "#" * 70
        )

        print(
            f"JOB {index}/{len(jobs)}"
        )

        print(
            f"Title   : "
            f"{job.get('title', '')}"
        )

        print(
            f"Company : "
            f"{job.get('company', '')}"
        )

        print(
            f"Location: "
            f"{job.get('location', '')}"
        )

        print(
            f"URL     : "
            f"{job.get('url', '') or 'NOT FOUND - CARD CLICK'}"
        )

        print(
            "#" * 70
        )

        result = apply_to_job(
            driver,
            job,
            main_handle,
            search_url
        )

        status = result.get(
            "status",
            "FAILED"
        )

        reason = result.get(
            "reason",
            ""
        )

        # ====================================================
        # SUCCESS
        # ====================================================

        if status == "APPLIED":

            current_application_count += 1

            record_job(
                processed,
                job,
                "APPLIED",
                reason
            )

            print()
            print(
                "[APPLICATION SUCCESS] "
                f"{job.get('title', '')}"
            )

            print(
                f"Daily applications: "
                f"{current_application_count}/"
                f"{MAX_APPLICATIONS_PER_DAY}"
            )

        # ====================================================
        # EXTERNAL
        # ====================================================

        elif status == "EXTERNAL":

            # External applications need manual review.
            record_job(
                processed,
                job,
                "EXTERNAL",
                reason
            )

            print(
                "[EXTERNAL APPLICATION] "
                "Manual review required."
            )

            print(
                f"External URL: "
                f"{result.get('url', '')}"
            )

        # ====================================================
        # FAILED
        # ====================================================

        else:

            # IMPORTANT:
            #
            # Do NOT permanently mark failed jobs
            # as processed.
            #
            # Otherwise the next run will skip them.
            #
            print(
                f"[APPLICATION FAILED] "
                f"{job.get('title', '')}"
            )

            print(
                f"Reason: {reason}"
            )

            print(
                "[RETRY] Failed job will "
                "NOT be marked as applied."
            )

        time.sleep(1.5)

    return current_application_count


# ============================================================
# MAIN
# ============================================================

def main():

    banner(
        "APPLICANT DETAILS FROM EXCEL"
    )

    print(
        f"Name       : "
        f"{APPLICANT_NAME}"
    )

    print(
    f"Email      : "
    f"{APPLICANT_EMAIL[:3]}***"
    f"{APPLICANT_EMAIL[-10:] if len(APPLICANT_EMAIL) > 10 else ''}"
    )

    print(
        f"Phone      : "
        f"{APPLICANT_PHONE[:3]}***"
        if APPLICANT_PHONE
        else "Phone      : "
    )

    print(
        f"Location   : "
        f"{APPLICANT_LOCATION}"
    )

    print(
        f"Resume     : "
        f"{APPLICANT_RESUME}"
    )

    print(
        f"LinkedIn   : "
        f"{APPLICANT_LINKEDIN}"
    )

    print(
        f"GitHub     : "
        f"{APPLICANT_GITHUB}"
    )

    print(
        f"Experience : "
        f"{APPLICANT_EXPERIENCE}"
    )

    print()

    print(
        "JOBGRIN LOGIN"
    )

    print(
        f"Email    : "
        f"{JOBGRIN_EMAIL}"
    )

    print(
        "Password : "
        + (
            "LOADED"
            if JOBGRIN_PASSWORD
            else "MISSING"
        )
    )

    banner(
        "JOBGRIN JOB AUTOMATION"
    )

    print(
        f"Search keyword: "
        f"{SEARCH_KEYWORD}"
    )

    print(
        f"Search city: "
        f"{SEARCH_CITY or 'Any'}"
    )

    print(
        f"Posted filter: "
        f"{JOB_POSTED_FILTER or 'Any'}"
    )

    print(
        f"Daily application limit: "
        f"{MAX_APPLICATIONS_PER_DAY}"
    )

    print(
        f"Maximum experience: "
        f"{MAX_EXPERIENCE_YEARS} year(s)"
    )

    print(
        f"Auto submit: "
        f"{AUTO_SUBMIT}"
    )

    processed = (
        load_processed_jobs()
    )

    daily_count = (
        applications_today(
            processed
        )
    )

    print(
        f"Applications today: "
        f"{daily_count}"
    )

    driver = None

    try:

        # ====================================================
        # START
        # ====================================================

        driver = start_browser()

        # ====================================================
        # LOGIN
        # ====================================================

        login_jobgrin(
            driver
        )

        # ====================================================
        # JOBS
        # ====================================================

        open_find_jobs(
            driver
        )

        # ====================================================
        # SEARCH
        # ====================================================

        search_url = search_jobs(
            driver
        )

        # ====================================================
        # MAIN HANDLE
        # ====================================================

        main_handle = (
            driver.current_window_handle
        )

        page_number = 1

        pages_checked = 0

        # ====================================================
        # PROCESS PAGES
        # ====================================================

        while (
            page_number <= MAX_PAGES
            and
            daily_count
            < MAX_APPLICATIONS_PER_DAY
        ):

            pages_checked += 1

            banner(
                f"PROCESSING JOB PAGE "
                f"{page_number}"
            )

            # Load results.
            load_more_jobs(
                driver
            )

            # IMPORTANT:
            # If a previous job click restored the page,
            # update the search URL if needed.
            if not is_search_page_url(
                driver.current_url
            ):

                driver.get(
                    search_url
                )

                wait_for_document_ready(
                    driver
                )

                time.sleep(2)

                load_more_jobs(
                    driver
                )

            daily_count = (
                process_current_page(
                    driver,
                    processed,
                    main_handle,
                    daily_count,
                    search_url
                )
            )

            # =================================================
            # DAILY LIMIT
            # =================================================

            if (
                daily_count
                >= MAX_APPLICATIONS_PER_DAY
            ):

                print()
                print(
                    "Daily application "
                    "limit reached."
                )

                break

            # =================================================
            # NEXT PAGE
            # =================================================

            # After applications, make sure we're back
            # on the search page.
            try:

                if (
                    driver.current_url
                    != search_url
                    and
                    is_jobgrin_domain(
                        driver.current_url
                    )
                ):

                    driver.get(
                        search_url
                    )

                    wait_for_document_ready(
                        driver
                    )

                    time.sleep(2)

            except Exception:
                pass

            if not go_to_next_page(
                driver
            ):

                print()
                print(
                    "No more JobGrin "
                    "pages available."
                )

                break

            page_number += 1

        # ====================================================
        # FINAL STATUS
        # ====================================================

        banner(
            "FINAL STATUS"
        )

        print(
            "Login              : DONE"
        )

        print(
            "Job search         : DONE"
        )

        print(
            f"Pages checked      : "
            f"{pages_checked}"
        )

        print(
            "Keyword filtering  : DONE"
        )

        print(
            "Experience filter  : DONE"
        )

        print(
            "Location filter    : DONE"
        )

        print(
            "Posted filter      : DONE"
        )

        print(
            "Duplicate checking : DONE"
        )

        print(
            f"Applications sent  : "
            f"{daily_count}"
        )

        print(
            f"Daily total        : "
            f"{daily_count} / "
            f"{MAX_APPLICATIONS_PER_DAY}"
        )

        print()

        print(
            "Processed jobs file:"
        )

        print(
            APPLIED_FILE
        )

        print()

        print(
            "Debug folder:"
        )

        print(
            DEBUG_DIR
        )

    except KeyboardInterrupt:

        print()

        print(
            "[STOPPED] Automation "
            "stopped by user."
        )

    except Exception as e:

        print()

        print(
            "=" * 70
        )

        print(
            "[FATAL ERROR]"
        )

        print(
            str(e)
        )

        print(
            "=" * 70
        )

        if driver:

            try:

                save_debug_artifacts(
                    driver,
                    "fatal_error"
                )

            except Exception:
                pass

    finally:

        if driver:

            if KEEP_BROWSER_OPEN:

                print()

                print(
                    "=" * 70
                )

                print(
                    "BROWSER LEFT OPEN FOR INSPECTION"
                )

                print(
                    "Press ENTER to close Chrome..."
                )

                try:
                    input()

                except Exception:
                    pass

            try:

                driver.quit()

            except Exception:
                pass


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
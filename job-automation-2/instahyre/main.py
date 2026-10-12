import os
import time
import re
import json
import sys
from pathlib import Path
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from credentials import load_portal_credentials


# ============================================================
# CONFIGURATION
# ============================================================

EMAIL, PASSWORD = load_portal_credentials("INSTAHYRE")


# ============================================================
# TARGET JOB TITLES
# ============================================================

TARGET_JOB_TITLES = [
    "Financial Analyst",
    "Investment Banking Analyst",
    "Equity Research Analyst",
    "FP&A Analyst",
    "FP&A Executive",
    "Credit Analyst",
    "Risk Analyst",
    "Business Analyst",
    "Financial Consultant",
    "Finance Consultant",
    "Consultant",
    "Finance Manager",
    "Finance Associate",
    "Finance Executive",
    "Valuation Analyst",
    "Financial Modelling Analyst",
    "Financial Modeling Analyst",
    "Portfolio Management Analyst",
    "Wealth Management Executive",
    "Wealth Manager",
    "Banking Executive",
    "FinTech Analyst",
    "FinTech Professional",
    "Project Finance Analyst",
    "M&A Analyst",
    "Mergers and Acquisitions Analyst",
    "Private Equity Analyst",
    "MIS Analyst",
    "Strategic Finance Analyst",
    "Strategic Finance Executive"
]


# ============================================================
# TARGET LOCATIONS
# ============================================================

TARGET_LOCATIONS = [
    "Pune",
    "Mumbai",
    "Hyderabad",
    "Bangalore",
    "Bengaluru",
    "Chennai",
    "Delhi",
    "Gurgaon",
    "Gurugram",
    "Noida",
    "Kolkata",
    "Ahmedabad",
    "Jaipur",
    "Indore",
    "Chandigarh",
    "Kochi",
    "Remote",
    "Work From Home"
]


# ============================================================
# EXPERIENCE
# ============================================================

MIN_EXPERIENCE = 0
MAX_EXPERIENCE = 2


# ============================================================
# APPLICATION LIMIT
# ============================================================

MAX_APPLICATIONS = 5


# ============================================================
# JSON FILE
# ============================================================

APPLIED_JOBS_FILE = "applied_jobs.json"


# ============================================================
# DRIVER
# ============================================================

driver = webdriver.Chrome()

driver.maximize_window()

wait = WebDriverWait(
    driver,
    20
)


# ============================================================
# TEXT HELPERS
# ============================================================

def normalize_text(text):

    return " ".join(
        text.lower().split()
    )


# ============================================================
# TITLE MATCH
# ============================================================

def title_matches(job_title):

    title = normalize_text(
        job_title
    )

    for target in TARGET_JOB_TITLES:

        target_normalized = normalize_text(
            target
        )

        if target_normalized in title:

            return True

    return False


# ============================================================
# LOCATION MATCH
# ============================================================

def location_matches(location_text):

    location = normalize_text(
        location_text
    )

    for target in TARGET_LOCATIONS:

        target_normalized = normalize_text(
            target
        )

        if target_normalized in location:

            return True

    return False


# ============================================================
# EXPERIENCE EXTRACTION
# ============================================================

def extract_experience(text):

    text = normalize_text(
        text
    )

    patterns = [

        r"(\d+)\s*-\s*(\d+)\s*years?",

        r"(\d+)\s*-\s*(\d+)\s*yrs?",

        r"(\d+)\s*years?",

        r"(\d+)\s*yrs?"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text
        )

        if match:

            numbers = match.groups()

            if len(numbers) == 2:

                min_exp = int(
                    numbers[0]
                )

                max_exp = int(
                    numbers[1]
                )

                return min_exp, max_exp

            if len(numbers) == 1:

                exp = int(
                    numbers[0]
                )

                return exp, exp

    return None


# ============================================================
# EXPERIENCE MATCH
# ============================================================

def experience_matches(job_text):

    experience = extract_experience(
        job_text
    )

    # If experience isn't visible,
    # don't reject the job.
    if experience is None:

        return True

    job_min, job_max = experience

    if (
        job_max >= MIN_EXPERIENCE
        and
        job_min <= MAX_EXPERIENCE
    ):

        return True

    return False


# ============================================================
# CREATE JSON FILE
# ============================================================

def create_applied_jobs_file():

    if not os.path.exists(
        APPLIED_JOBS_FILE
    ):

        data = {
            "jobs": []
        }

        with open(
            APPLIED_JOBS_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                data,
                file,
                indent=4,
                ensure_ascii=False
            )

        print(
            f"[JSON] Created "
            f"{APPLIED_JOBS_FILE}"
        )


# ============================================================
# LOAD JSON
# ============================================================

def load_applied_jobs():

    create_applied_jobs_file()

    try:

        with open(
            APPLIED_JOBS_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(
                file
            )

        if not isinstance(
            data,
            dict
        ):

            raise ValueError(
                "JSON root must be an object."
            )

        if "jobs" not in data:

            data["jobs"] = []

        if not isinstance(
            data["jobs"],
            list
        ):

            raise ValueError(
                "'jobs' must be a list."
            )

        return data

    except Exception as e:

        raise Exception(
            f"Could not safely read "
            f"{APPLIED_JOBS_FILE}: {e}"
        )


# ============================================================
# SAVE JSON
# ============================================================

def save_applied_jobs(data):

    with open(
        APPLIED_JOBS_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            indent=4,
            ensure_ascii=False
        )


def is_job_already_applied(job_title, job_url=""):

    data = load_applied_jobs()

    current_title = normalize_text(job_title)
    current_url = normalize_text(job_url)

    for saved_job in data["jobs"]:

        saved_title = normalize_text(
            saved_job.get("job_title", "")
        )

        saved_url = normalize_text(
            saved_job.get("job_url", "")
        )

        # ====================================================
        # PRIMARY CHECK: JOB TITLE
        # ====================================================

        if (
            current_title
            and
            saved_title
            and
            current_title == saved_title
        ):

            print(
                f"[DUPLICATE] Already applied: "
                f"{job_title}"
            )

            return True


        # ====================================================
        # SECONDARY CHECK: JOB URL
        # ====================================================

        if (
            current_url
            and
            saved_url
            and
            current_url == saved_url
        ):

            print(
                f"[DUPLICATE URL] Already applied: "
                f"{job_title}"
            )

            return True


    return False

# ============================================================
# ADD APPLIED JOB
# ============================================================

def add_applied_job(
    job_title,
    company="",
    job_url="",
    status="applied"
):

    data = load_applied_jobs()

    now = datetime.now()

    job_record = {

        "job_title": job_title,

        "company": company,

        "job_url": job_url,

        "applied_date": now.strftime(
            "%Y-%m-%d"
        ),

        "applied_time": now.strftime(
            "%H:%M:%S"
        ),

        "status": status
    }

    data["jobs"].append(
        job_record
    )

    save_applied_jobs(
        data
    )

    print(
        f"[JSON] Saved: "
        f"{job_title}"
    )


# ============================================================
# CREATE JSON AT START
# ============================================================

create_applied_jobs_file()


# ============================================================
# APPLICATION COUNTER
# ============================================================

applications_done = 0

page_number = 1


# ============================================================
# MAIN AUTOMATION
# ============================================================

try:

    # ========================================================
    # OPEN INSTAHYRE
    # ========================================================

    print(
        "Opening Instahyre..."
    )

    driver.get(
        "https://www.instahyre.com/"
    )


    # ========================================================
    # EMAIL LOGIN BUTTON
    # ========================================================

    print(
        "Clicking Email Login..."
    )

    email_login_button = wait.until(
        EC.element_to_be_clickable(
            (
                By.CSS_SELECTOR,
                "a.email-login-btn"
            )
        )
    )

    email_login_button.click()


    # ========================================================
    # LOG IN HERE
    # ========================================================

    print(
        "Clicking Log in here..."
    )

    login_here = wait.until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                "//a[contains("
                "normalize-space(.), "
                "'Log in here')]"
            )
        )
    )

    login_here.click()


    # ========================================================
    # EMAIL
    # ========================================================

    print(
        "Entering email..."
    )

    email_input = wait.until(
        EC.presence_of_element_located(
            (
                By.XPATH,
                "//input[@type='email' "
                "or contains("
                "@placeholder, 'email')]"
            )
        )
    )

    email_input.clear()

    email_input.send_keys(
        EMAIL
    )


    # ========================================================
    # PASSWORD
    # ========================================================

    print(
        "Entering password..."
    )

    password_input = wait.until(
        EC.presence_of_element_located(
            (
                By.XPATH,
                "//input[@type='password']"
            )
        )
    )

    password_input.clear()

    password_input.send_keys(
        PASSWORD
    )


    # ========================================================
    # LOGIN
    # ========================================================

    print(
        "Clicking Log in..."
    )

    login_button = wait.until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                "//button[normalize-space()='Log in']"
            )
        )
    )

    login_button.click()


    # ========================================================
    # OPEN OPPORTUNITIES
    # ========================================================

    print(
        "Opening Opportunities..."
    )

    opportunities = wait.until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                "//*[normalize-space()='Opportunities']"
            )
        )
    )

    opportunities.click()

    time.sleep(3)

    print(
        "Opportunities opened."
    )

    print(
        "Current URL:",
        driver.current_url
    )


    # ========================================================
    # SEARCH FINANCE
    # ========================================================

    print(
        "\nSearching for finance..."
    )

    search_box = wait.until(
        EC.presence_of_element_located(
            (
                By.CSS_SELECTOR,
                ".search-bar-wrapper input"
            )
        )
    )

    search_box.clear()

    search_box.send_keys(
        "finance"
    )


    # ========================================================
    # SEARCH
    # ========================================================

    print(
        "Clicking search..."
    )

    search_button = wait.until(
        EC.element_to_be_clickable(
            (
                By.CSS_SELECTOR,
                "button.skills-search-btn"
            )
        )
    )

    search_button.click()

    time.sleep(4)


    # ========================================================
    # PAGINATION LOOP
    # ========================================================

    while applications_done < MAX_APPLICATIONS:

        print(
            "\n========================================"
        )

        print(
            f"SCANNING PAGE {page_number}"
        )

        print(
            "========================================"
        )


        # ----------------------------------------------------
        # GET CURRENT PAGE JOBS
        # ----------------------------------------------------

        try:

            wait.until(
                EC.presence_of_all_elements_located(
                    (
                        By.CSS_SELECTOR,
                        "a#employer-profile-opportunity"
                    )
                )
            )

        except Exception:

            pass


        jobs = driver.find_elements(
            By.CSS_SELECTOR,
            "a#employer-profile-opportunity"
        )


        print(
            f"Jobs found: {len(jobs)}"
        )


        # ----------------------------------------------------
        # IF NO JOBS
        # ----------------------------------------------------

        if not jobs:

            print(
                "[INFO] No jobs found "
                "on current page."
            )

        # ----------------------------------------------------
        # PROCESS CURRENT PAGE
        # ----------------------------------------------------

        job_index = 0


        while (
            job_index < len(jobs)
            and
            applications_done < MAX_APPLICATIONS
        ):


            # ------------------------------------------------
            # RE-FIND JOB CARDS
            # ------------------------------------------------

            jobs = driver.find_elements(
                By.CSS_SELECTOR,
                "a#employer-profile-opportunity"
            )


            if job_index >= len(jobs):

                break


            job = jobs[
                job_index
            ]

            job_index += 1


            # ------------------------------------------------
            # JOB TITLE
            # ------------------------------------------------

            try:

                title_element = job.find_element(
                    By.CSS_SELECTOR,
                    ".employer-job-name"
                )

                job_title = (
                    title_element.text.strip()
                )

            except Exception:

                print(
                    "[SKIP] Could not read "
                    "job title."
                )

                continue


            print(
                "\n----------------------------------------"
            )

            print(
                f"Checking: {job_title}"
            )


            # ------------------------------------------------
            # JOB URL
            # ------------------------------------------------

            job_url = ""

            try:

                job_url = (
                    job.get_attribute(
                        "href"
                    )
                    or
                    ""
                )

            except Exception:

                pass


            # ------------------------------------------------
            # COMPANY
            # ------------------------------------------------

            company = ""

            try:

                company_element = job.find_element(
                    By.CSS_SELECTOR,
                    ".employer-company-name"
                )

                company = (
                    company_element.text.strip()
                )

            except Exception:

                pass


            # ------------------------------------------------
            # JSON DUPLICATE CHECK
            # ------------------------------------------------

            try:

                already_applied = (
                    is_job_already_applied(
                        job_title,
                        job_url
                    )
                )

            except Exception as e:

                print(
                    "[CRITICAL] JSON check failed:"
                )

                print(e)

                print(
                    "[STOP] Automation stopped "
                    "for safety."
                )

                raise


            if already_applied:

                print(
                    "[SKIP] Already applied "
                    "according to JSON."
                )

                continue


            # ------------------------------------------------
            # TITLE FILTER
            # ------------------------------------------------

            if not title_matches(
                job_title
            ):

                print(
                    "[SKIP] Title does not match."
                )

                continue


            # ------------------------------------------------
            # JOB TEXT
            # ------------------------------------------------

            try:

                job_text = job.text

            except Exception:

                job_text = ""


            # ------------------------------------------------
            # EXPERIENCE FILTER
            # ------------------------------------------------

            if not experience_matches(
                job_text
            ):

                print(
                    "[SKIP] Experience does not match."
                )

                continue


            # ------------------------------------------------
            # LOCATION FILTER
            # ------------------------------------------------

            if not location_matches(
                job_text
            ):

                print(
                    "[SKIP] Location does not match."
                )

                continue


            # ------------------------------------------------
            # JOB MATCHED
            # ------------------------------------------------

            print(
                "[MATCH] Job passed filters."
            )

            print(
                f"Title   : {job_title}"
            )

            print(
                f"Company : {company}"
            )

            print(
                f"URL     : {job_url}"
            )


            # ------------------------------------------------
            # SCROLL
            # ------------------------------------------------

            try:

                driver.execute_script(
                    """
                    arguments[0].scrollIntoView({
                        behavior: 'instant',
                        block: 'center'
                    });
                    """,
                    job
                )

                time.sleep(1)

            except Exception:

                pass


            # ------------------------------------------------
            # OPEN JOB
            # ------------------------------------------------

            try:

                job.click()

            except Exception as e:

                print(
                    f"[ERROR] Could not open job: {e}"
                )

                continue


            time.sleep(2)


            # ------------------------------------------------
            # APPLY BUTTON
            # ------------------------------------------------

            try:

                apply_button = wait.until(
                    EC.element_to_be_clickable(
                        (
                            By.XPATH,
                            "//*[normalize-space()='Apply']"
                        )
                    )
                )

            except Exception as e:

                print(
                    "[SKIP] Apply button "
                    "not found."
                )

                print(
                    f"Reason: {e}"
                )

                try:

                    driver.back()

                    time.sleep(3)

                except Exception:

                    pass

                continue


            # ------------------------------------------------
            # CLICK APPLY
            # ------------------------------------------------

            try:

                print(
                    f"[APPLYING] {job_title}"
                )

                apply_button.click()

                time.sleep(3)

            except Exception as e:

                print(
                    f"[ERROR] Apply failed: {e}"
                )

                try:

                    driver.back()

                    time.sleep(3)

                except Exception:

                    pass

                continue


            # ------------------------------------------------
            # SUCCESS
            # ------------------------------------------------

            print(
                f"[SUCCESS] Applied to: "
                f"{job_title}"
            )


            # ------------------------------------------------
            # SAVE JSON
            # ------------------------------------------------

            add_applied_job(
                job_title=job_title,
                company=company,
                job_url=job_url,
                status="applied"
            )


            # ------------------------------------------------
            # INCREMENT COUNTER
            # ------------------------------------------------

            applications_done += 1


            print(
                f"Applications completed: "
                f"{applications_done}/"
                f"{MAX_APPLICATIONS}"
            )


            # ------------------------------------------------
            # RETURN TO OPPORTUNITIES
            # ------------------------------------------------

            try:

                driver.back()

                time.sleep(3)

            except Exception as e:

                print(
                    f"[ERROR] Could not return "
                    f"to job list: {e}"
                )

                raise


            # ------------------------------------------------
            # STOP AT 5
            # ------------------------------------------------

            if (
                applications_done
                >=
                MAX_APPLICATIONS
            ):

                break


        # ====================================================
        # MAX APPLICATIONS
        # ====================================================

        if (
            applications_done
            >=
            MAX_APPLICATIONS
        ):

            print(
                "\n[SUCCESS] Reached "
                "maximum applications."
            )

            break


        # ====================================================
        # CURRENT PAGE FINISHED
        # ====================================================

        print(
            f"\n[INFO] Finished scanning "
            f"page {page_number}."
        )

        print(
            "Looking for Next »..."
        )


        # ====================================================
        # FIND NEXT BUTTON
        # ====================================================

        try:

            next_button = driver.find_element(
                By.XPATH,
                "//li[@ng-click='nextPage()' "
                "and contains("
                "normalize-space(.), "
                "'Next')]"
            )

        except Exception:

            print(
                "[INFO] Next » button not found."
            )

            print(
                "[STOP] No more pages."
            )

            break


        # ====================================================
        # CHECK HIDDEN
        # ====================================================

        try:

            next_classes = (
                next_button
                .get_attribute("class")
                or
                ""
            )

            if "hidden" in next_classes:

                print(
                    "[INFO] Next » is hidden."
                )

                print(
                    "[STOP] Last page reached."
                )

                break

        except Exception:

            pass


        # ====================================================
        # STORE CURRENT FIRST JOB
        # ====================================================

        old_first_job = ""

        try:

            current_jobs = driver.find_elements(
                By.CSS_SELECTOR,
                "a#employer-profile-opportunity"
            )

            if current_jobs:

                old_first_job = (
                    current_jobs[0]
                    .text
                    .strip()
                )

        except Exception:

            pass


        # ====================================================
        # CLICK NEXT
        # ====================================================

        try:

            driver.execute_script(
                """
                arguments[0].scrollIntoView({
                    behavior: 'instant',
                    block: 'center'
                });
                """,
                next_button
            )

            time.sleep(1)


            print(
                "Clicking Next »..."
            )


            next_button.click()

        except Exception as e:

            print(
                f"[ERROR] Could not click "
                f"Next »: {e}"
            )

            break


        # ====================================================
        # WAIT FOR NEXT PAGE
        # ====================================================

        print(
            "Waiting for next page..."
        )

        try:

            WebDriverWait(
                driver,
                15
            ).until(
                lambda d: (
                    len(
                        d.find_elements(
                            By.CSS_SELECTOR,
                            "a#employer-profile-opportunity"
                        )
                    ) > 0
                    and
                    (
                        old_first_job == ""
                        or
                        d.find_elements(
                            By.CSS_SELECTOR,
                            "a#employer-profile-opportunity"
                        )[0]
                        .text
                        .strip()
                        != old_first_job
                    )
                )
            )

        except Exception:

            # Give Angular time to update
            time.sleep(3)


        # ====================================================
        # INCREMENT PAGE
        # ====================================================

        page_number += 1


        print(
            f"[SUCCESS] Now on page "
            f"{page_number}"
        )
except Exception as e:

        print(
            f"[ERROR] An error occurred: {e}"
        )

# ============================================================
# FINAL OUTPUT
# ============================================================

print(
    "\n========================================"
)

print(
    "AUTOMATION COMPLETED"
)

print(
    "========================================"
)

print(
    f"New applications : "
    f"{applications_done}"
)

print(
    f"Maximum allowed  : "
    f"{MAX_APPLICATIONS}"
)

print(
    f"Pages scanned    : "
    f"{page_number}"
)

print(
    f"JSON file        : "
    f"{APPLIED_JOBS_FILE}"
)

print(
    "========================================"
)

print(
    "\nBrowser will remain open "
    "for inspection."
)


# ============================================================
# DO NOT CLOSE BROWSER
# ============================================================

# driver.quit()

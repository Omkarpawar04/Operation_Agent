import os
import time

from urllib.parse import urlparse

from dotenv import load_dotenv

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from iimjobs_login import login_iimjobs


load_dotenv()


# ============================================================
# CONFIG
# ============================================================

IIMJOBS_URL = "https://www.iimjobs.com/"
IIMJOBS_SEARCH_URL = "https://www.iimjobs.com/search"

SEARCH_TERM = "Finance Analyst"

MAX_APPLICATIONS = 5

WAIT_TIME = 15


# ============================================================
# OPTIONAL PROFILE DATA
# ============================================================
# Add these to .env only if a form actually needs them.
#
# Example:
#
# IIMJOBS_NAME=Sidheshwar Kokalge
# IIMJOBS_PHONE=XXXXXXXXXX
# IIMJOBS_LOCATION=Pune
# IIMJOBS_EXPERIENCE=0
#
# DO NOT put sensitive information here unless you actually
# need it for a form.

PROFILE = {
    "name": os.getenv("IIMJOBS_NAME", "").strip(),
    "phone": os.getenv("IIMJOBS_PHONE", "").strip(),
    "location": os.getenv("IIMJOBS_LOCATION", "").strip(),
    "experience": os.getenv("IIMJOBS_EXPERIENCE", "").strip(),
}


# ============================================================
# OPEN IIMJOBS
# ============================================================

def open_iimjobs(driver):

    print("\nOpening IIMJobs...")

    driver.get(IIMJOBS_URL)

    WebDriverWait(driver, WAIT_TIME).until(
        EC.presence_of_element_located(
            (By.TAG_NAME, "body")
        )
    )

    print("IIMJobs opened.")
    print("Title:", driver.title)
    print("URL:", driver.current_url)


# ============================================================
# SEARCH IIMJOBS
# ============================================================

def search_iimjobs(driver, search_term):

    print("\n" + "=" * 60)
    print("SEARCHING IIMJOBS")
    print("=" * 60)

    print("Search term:", search_term)

    # --------------------------------------------------------
    # CREATE IIMJOBS SEARCH URL
    # --------------------------------------------------------

    from urllib.parse import quote_plus

    encoded_term = quote_plus(search_term)

    search_url = (
        f"https://www.iimjobs.com/search/"
        f"{encoded_term}-jobs"
    )

    print("\nOpening search URL:")
    print(search_url)

    # --------------------------------------------------------
    # OPEN SEARCH RESULTS
    # --------------------------------------------------------

    try:

        driver.get(search_url)

        WebDriverWait(
            driver,
            WAIT_TIME
        ).until(
            EC.presence_of_element_located(
                (By.TAG_NAME, "body")
            )
        )

    except Exception as error:

        print(
            "\nCould not open search page."
        )

        print(error)

        return False

    # Give the page a moment to render
    time.sleep(2)

    print("\nSearch page loaded.")

    print(
        "Current URL:",
        driver.current_url
    )

    print(
        "Title:",
        driver.title
    )

    # --------------------------------------------------------
    # CHECK FOR JOB LINKS
    # --------------------------------------------------------

    try:

        WebDriverWait(
            driver,
            WAIT_TIME
        ).until(
            lambda d: len(
                d.find_elements(
                    By.XPATH,
                    "//a[contains(@href, '/j/')]"
                )
            ) > 0
        )

    except Exception:

        print(
            "\nNo job links found."
        )

        # Print body text so we can understand
        # what IIMJobs returned.
        try:

            body_text = driver.find_element(
                By.TAG_NAME,
                "body"
            ).text

            print(
                "\nPAGE TEXT:"
            )

            print(
                body_text[:3000]
            )

        except Exception:
            pass

        return False

    # --------------------------------------------------------
    # SUCCESS
    # --------------------------------------------------------

    job_links = driver.find_elements(
        By.XPATH,
        "//a[contains(@href, '/j/')]"
    )

    print(
        f"\nSearch completed successfully."
    )

    print(
        f"Job links detected: {len(job_links)}"
    )

    return True


# ============================================================
# GET DOMAIN
# ============================================================

def get_domain(url):

    try:
        return urlparse(url).netloc.lower()

    except Exception:
        return ""


# ============================================================
# FIND JOB LINKS
# ============================================================

def get_job_links(driver):

    print("\nCollecting job links...")

    elements = driver.find_elements(
        By.XPATH,
        "//a[contains(@href, '/j/')]"
    )

    jobs = []

    seen_urls = set()

    for element in elements:

        try:

            href = element.get_attribute("href")

            if not href:
                continue

            # Remove duplicate URLs
            clean_url = href.split("?")[0]

            if clean_url in seen_urls:
                continue

            seen_urls.add(clean_url)

            title = element.text.strip()

            # Sometimes anchor text is empty.
            # Use title attribute if available.
            if not title:

                title = (
                    element.get_attribute("title")
                    or "Unknown Job"
                ).strip()

            jobs.append(
                
                {
                    "title": title,
                    "url": href
                }
            )

        except Exception:
            continue

    print(
        f"Job links found: {len(jobs)}"
    )

    return jobs


# ============================================================
# FIND APPLY BUTTON
# ============================================================

def find_apply_button(driver):

    selectors = [

        (
            By.XPATH,
            "//button[contains("
            "translate(normalize-space(.),"
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
            "'abcdefghijklmnopqrstuvwxyz'),"
            "'apply'"
            ")]"
        ),

        (
            By.XPATH,
            "//a[contains("
            "translate(normalize-space(.),"
            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
            "'abcdefghijklmnopqrstuvwxyz'),"
            "'apply'"
            ")]"
        ),
    ]

    candidates = []

    for selector in selectors:

        try:

            elements = driver.find_elements(*selector)

            candidates.extend(elements)

        except Exception:
            continue

    for element in candidates:

        try:

            if (
                element.is_displayed()
                and element.is_enabled()
            ):

                return element

        except Exception:
            continue

    return None


# ============================================================
# DETECT CAPTCHA / OTP
# ============================================================

def contains_blocking_challenge(driver):

    try:

        body_text = driver.find_element(
            By.TAG_NAME,
            "body"
        ).text.lower()

    except Exception:

        return False

    challenge_words = [

        "captcha",

        "verify you are human",

        "verification code",

        "otp",

        "one time password",

        "security code",

        "verify your phone",

        "verify your email",
    ]

    for word in challenge_words:

        if word in body_text:

            return True

    return False


# ============================================================
# CLICK APPLY AND DETECT DESTINATION
# ============================================================

def click_apply_and_check(driver):

    print("\nLooking for Apply button...")

    apply_button = find_apply_button(driver)

    if not apply_button:

        print("No Apply button found.")

        return False

    original_url = driver.current_url

    original_handles = list(
        driver.window_handles
    )

    try:

        driver.execute_script(
            "arguments[0].scrollIntoView({block:'center'});",
            apply_button
        )

        time.sleep(0.5)

        print("Clicking Apply...")

        apply_button.click()

    except Exception as error:

        print("Could not click Apply.")
        print("Error:", error)

        return False

    # --------------------------------------------------------
    # WAIT FOR URL OR NEW TAB
    # --------------------------------------------------------

    print("Waiting for application destination...")

    try:

        WebDriverWait(driver, 10).until(
            lambda d: (
                d.current_url != original_url
                or len(d.window_handles)
                != len(original_handles)
            )
        )

    except Exception:

        print(
            "No application destination detected."
        )

        return False

    # --------------------------------------------------------
    # HANDLE NEW TAB
    # --------------------------------------------------------

    try:

        current_handles = driver.window_handles

        if len(current_handles) > len(original_handles):

            new_handles = [
                handle
                for handle in current_handles
                if handle not in original_handles
            ]

            if new_handles:

                driver.switch_to.window(
                    new_handles[-1]
                )

                WebDriverWait(
                    driver,
                    WAIT_TIME
                ).until(
                    EC.presence_of_element_located(
                        (By.TAG_NAME, "body")
                    )
                )

    except Exception as error:

        print(
            "Could not switch to application tab."
        )

        print(error)

        return False

    time.sleep(1)

    current_url = driver.current_url

    current_domain = get_domain(
        current_url
    )

    print("\nAfter Apply:")
    print("URL:", current_url)
    print("Domain:", current_domain)

    # --------------------------------------------------------
    # EXTERNAL APPLICATION
    # --------------------------------------------------------

    if "iimjobs.com" not in current_domain:

        print("\nEXTERNAL APPLICATION")
        print("Skipping:", current_url)

        # New tab
        if len(driver.window_handles) > 1:

            try:

                driver.close()

                driver.switch_to.window(
                    driver.window_handles[0]
                )

            except Exception:
                pass

        # Same tab
        else:

            try:

                driver.get(original_url)

                WebDriverWait(
                    driver,
                    WAIT_TIME
                ).until(
                    EC.presence_of_element_located(
                        (By.TAG_NAME, "body")
                    )
                )

            except Exception:
                pass

        return False

    # --------------------------------------------------------
    # INTERNAL IIMJOBS
    # --------------------------------------------------------

    print("\nINTERNAL IIMJOBS APPLICATION")

    return True


# ============================================================
# GET FIELD LABEL
# ============================================================

def get_field_context(element):

    pieces = []

    try:

        aria = element.get_attribute(
            "aria-label"
        )

        if aria:
            pieces.append(aria)

    except Exception:
        pass

    try:

        placeholder = element.get_attribute(
            "placeholder"
        )

        if placeholder:
            pieces.append(placeholder)

    except Exception:
        pass

    # --------------------------------------------------------
    # Nearby DOM text
    # --------------------------------------------------------

    for xpath in [
        "./..",
        "../..",
        "../../..",
    ]:

        try:

            parent = element.find_element(
                By.XPATH,
                xpath
            )

            text = parent.text.strip()

            if text:
                pieces.append(text)

        except Exception:
            continue

    # --------------------------------------------------------
    # Associated label
    # --------------------------------------------------------

    try:

        element_id = element.get_attribute("id")

        if element_id:

            labels = driver.find_elements(
                By.XPATH,
                f"//label[@for='{element_id}']"
            )

            for label in labels:

                text = label.text.strip()

                if text:
                    pieces.append(text)

    except Exception:
        pass

    return " ".join(pieces).strip()


# ============================================================
# GET SAFE ANSWER
# ============================================================

def get_safe_answer(context, element):

    context_lower = context.lower()

    # --------------------------------------------------------
    # NAME
    # --------------------------------------------------------

    if (
        "full name" in context_lower
        or "candidate name" in context_lower
        or context_lower.strip() == "name"
    ):

        if PROFILE["name"]:
            return PROFILE["name"]

    # --------------------------------------------------------
    # PHONE
    # --------------------------------------------------------

    if (
        "phone" in context_lower
        or "mobile" in context_lower
        or "contact number" in context_lower
    ):

        if PROFILE["phone"]:
            return PROFILE["phone"]

    # --------------------------------------------------------
    # LOCATION
    # --------------------------------------------------------

    if (
        "location" in context_lower
        or "current city" in context_lower
        or "city" in context_lower
    ):

        if PROFILE["location"]:
            return PROFILE["location"]

    # --------------------------------------------------------
    # EXPERIENCE
    # --------------------------------------------------------

    if (
        "years of experience" in context_lower
        or "total experience" in context_lower
        or "work experience" in context_lower
    ):

        if PROFILE["experience"]:
            return PROFILE["experience"]

    # --------------------------------------------------------
    # UNKNOWN
    # --------------------------------------------------------

    return None


# ============================================================
# FILL SAFE APPLICATION FIELDS
# ============================================================

def fill_safe_fields(driver):

    print("\nChecking application fields...")

    fields = driver.find_elements(
        By.XPATH,
        "//input | //textarea | //select"
    )

    unknown_required_fields = []

    filled_count = 0

    for field in fields:

        try:

            if not field.is_displayed():
                continue

            field_type = (
                field.get_attribute("type")
                or ""
            ).lower()

            # Skip hidden/non-user fields
            if field_type in [
                "hidden",
                "submit",
                "button",
                "file",
            ]:
                continue

            # ------------------------------------------------
            # CONTEXT
            # ------------------------------------------------

            context_parts = []

            for xpath in [
                "./..",
                "../..",
                "../../..",
            ]:

                try:

                    parent = field.find_element(
                        By.XPATH,
                        xpath
                    )

                    text = parent.text.strip()

                    if text:
                        context_parts.append(text)

                except Exception:
                    continue

            aria = (
                field.get_attribute("aria-label")
                or ""
            )

            placeholder = (
                field.get_attribute("placeholder")
                or ""
            )

            name = (
                field.get_attribute("name")
                or ""
            )

            context = " ".join(
                context_parts
            )

            context = (
                context
                + " "
                + aria
                + " "
                + placeholder
                + " "
                + name
            ).strip()

            # ------------------------------------------------
            # FIND SAFE ANSWER
            # ------------------------------------------------

            answer = get_safe_answer(
                context,
                field
            )

            if answer is None:

                # Only treat required fields as blockers.
                required = (
                    field.get_attribute("required")
                )

                if required:

                    unknown_required_fields.append(
                        context
                    )

                continue

            # ------------------------------------------------
            # FILL FIELD
            # ------------------------------------------------

            try:

                driver.execute_script(
                    """
                    arguments[0].scrollIntoView({
                        block: 'center'
                    });
                    """,
                    field
                )

                time.sleep(0.2)

                field.click()
                field.clear()
                field.send_keys(answer)

                filled_count += 1

                print(
                    "Filled:",
                    context[:100]
                )

            except Exception as error:

                print(
                    "Could not fill field:",
                    error
                )

                return False

        except Exception:
            continue

    print(
        f"Fields automatically filled: "
        f"{filled_count}"
    )

    if unknown_required_fields:

        print(
            "\nUnknown required fields detected."
        )

        for question in unknown_required_fields:

            print(
                " -",
                question[:200]
            )

        print(
            "\nSkipping this job instead of "
            "guessing an answer."
        )

        return False

    return True


# ============================================================
# FIND NEXT / SUBMIT BUTTON
# ============================================================

def find_next_or_submit_button(driver):

    buttons = driver.find_elements(
        By.XPATH,
        "//button | //input[@type='submit']"
    )

    preferred = []

    for button in buttons:

        try:

            if not button.is_displayed():
                continue

            if not button.is_enabled():
                continue

            text = (
                button.text.strip()
                or button.get_attribute("value")
                or ""
            ).lower()

            if (
                "next" in text
                or "continue" in text
                or "submit" in text
                or "apply" in text
            ):

                preferred.append(button)

        except Exception:
            continue

    if preferred:

        # Prefer Submit/Apply over generic buttons
        for button in preferred:

            try:

                text = (
                    button.text.strip()
                    or button.get_attribute("value")
                    or ""
                ).lower()

                if (
                    "submit" in text
                    or "apply" in text
                ):

                    return button

            except Exception:
                continue

        return preferred[0]

    return None


# ============================================================
# PROCESS INTERNAL APPLICATION
# ============================================================

def process_internal_application(driver):

    print("\n" + "-" * 60)
    print("PROCESSING INTERNAL APPLICATION")
    print("-" * 60)

    # --------------------------------------------------------
    # CAPTCHA / OTP CHECK
    # --------------------------------------------------------

    if contains_blocking_challenge(driver):

        print(
            "CAPTCHA/OTP/verification detected."
        )

        print(
            "Skipping this application."
        )

        return False

    # --------------------------------------------------------
    # HANDLE MULTI-STEP APPLICATION
    # --------------------------------------------------------

    max_steps = 5

    for step in range(1, max_steps + 1):

        print(
            f"\nApplication step {step}/{max_steps}"
        )

        # --------------------------------------------
        # CHECK CHALLENGE
        # --------------------------------------------

        if contains_blocking_challenge(driver):

            print(
                "Verification challenge detected."
            )

            return False

        # --------------------------------------------
        # FILL SAFE FIELDS
        # --------------------------------------------

        fields_ok = fill_safe_fields(
            driver
        )

        if not fields_ok:

            return False

        # --------------------------------------------
        # FIND BUTTON
        # --------------------------------------------

        button = find_next_or_submit_button(
            driver
        )

        if not button:

            print(
                "No Next/Submit/Apply button found."
            )

            return False

        button_text = (
            button.text.strip()
            or button.get_attribute("value")
            or ""
        )

        print(
            "Clicking:",
            button_text
        )

        previous_url = driver.current_url

        try:

            driver.execute_script(
                "arguments[0].scrollIntoView({block:'center'});",
                button
            )

            time.sleep(0.5)

            button.click()

        except Exception as error:

            print(
                "Could not click application button."
            )

            print(error)

            return False

        # --------------------------------------------
        # WAIT FOR PAGE CHANGE / FORM UPDATE
        # --------------------------------------------

        time.sleep(1)

        # --------------------------------------------
        # CHECK SUCCESS
        # --------------------------------------------

        body_text = ""

        try:

            body_text = driver.find_element(
                By.TAG_NAME,
                "body"
            ).text.lower()

        except Exception:
            pass

        success_words = [
            "application submitted",
            "successfully applied",
            "application successful",
            "thank you for applying",
            "your application has been submitted",
        ]

        for word in success_words:

            if word in body_text:

                print("\nAPPLICATION SUBMITTED")

                return True

        # --------------------------------------------
        # URL CHANGE
        # --------------------------------------------

        if driver.current_url != previous_url:

            print(
                "Application page changed."
            )

        # --------------------------------------------
        # IF BUTTON WAS SUBMIT/APPLY
        # --------------------------------------------

        lower_button_text = (
            button_text.lower()
        )

        if (
            "submit" in lower_button_text
            or "apply" in lower_button_text
        ):

            time.sleep(2)

            try:

                body_text = driver.find_element(
                    By.TAG_NAME,
                    "body"
                ).text.lower()

            except Exception:

                body_text = ""

            for word in success_words:

                if word in body_text:

                    print(
                        "\nAPPLICATION SUBMITTED"
                    )

                    return True

            # If we reached a different page after
            # Submit/Apply, consider it submitted only
            # when the page indicates success.
            print(
                "\nSubmit button clicked, "
                "but success was not confirmed."
            )

            return False

    print(
        "\nMaximum application steps reached."
    )

    return False


# ============================================================
# PROCESS JOBS
# ============================================================

def apply_to_jobs(driver):

    print("\n" + "=" * 60)
    print("STARTING AUTOMATIC JOB APPLICATION")
    print("=" * 60)

    jobs = get_job_links(driver)

    if not jobs:

        print("No jobs found.")

        return

    print(
        f"\nFound {len(jobs)} jobs."
    )

    print(
        f"Target applications: "
        f"{MAX_APPLICATIONS}"
    )

    submitted_count = 0
    skipped_count = 0

    # --------------------------------------------------------
    # PROCESS JOBS
    # --------------------------------------------------------

    for index, job in enumerate(
        jobs,
        start=1
    ):

        if submitted_count >= MAX_APPLICATIONS:

            break

        print("\n" + "=" * 60)

        print(
            f"JOB {index}/{len(jobs)}"
        )

        print("=" * 60)

        print(
            "Title:",
            job["title"]
        )

        print(
            "URL:",
            job["url"]
        )

        # ----------------------------------------------------
        # OPEN JOB
        # ----------------------------------------------------

        try:

            driver.get(job["url"])

            WebDriverWait(
                driver,
                WAIT_TIME
            ).until(
                EC.presence_of_element_located(
                    (By.TAG_NAME, "body")
                )
            )

        except Exception as error:

            print(
                "Could not open job."
            )

            print(error)

            skipped_count += 1

            continue

        # ----------------------------------------------------
        # CHECK CAPTCHA
        # ----------------------------------------------------

        if contains_blocking_challenge(driver):

            print(
                "Verification challenge detected."
            )

            print(
                "Skipping job."
            )

            skipped_count += 1

            continue

        # ----------------------------------------------------
        # APPLY
        # ----------------------------------------------------

        is_internal = (
            click_apply_and_check(driver)
        )

        if not is_internal:

            skipped_count += 1

            continue

        # ----------------------------------------------------
        # PROCESS INTERNAL APPLICATION
        # ----------------------------------------------------

        success = (
            process_internal_application(
                driver
            )
        )

        if success:

            submitted_count += 1

            print("\n" + "=" * 60)

            print(
                f"APPLICATION SUCCESS "
                f"{submitted_count}/"
                f"{MAX_APPLICATIONS}"
            )

            print(
                "Job:",
                job["title"]
            )

            print("=" * 60)

        else:

            skipped_count += 1

            print(
                "\nApplication was not submitted."
            )

        # ----------------------------------------------------
        # SMALL DELAY BEFORE NEXT JOB
        # ----------------------------------------------------

        time.sleep(1)

    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    print("\n" + "=" * 60)
    print("AUTOMATION FINISHED")
    print("=" * 60)

    print(
        "Applications submitted:",
        submitted_count
    )

    print(
        "Jobs skipped:",
        skipped_count
    )

    print(
        "Target:",
        MAX_APPLICATIONS
    )

    if submitted_count >= MAX_APPLICATIONS:

        print(
            "\n5 applications completed."
        )

    else:

        print(
            "\nCould not reach the target of 5 "
            "with the available safe applications."
        )


# ============================================================
# MAIN WORKFLOW
# ============================================================

def run_iimjobs(driver):

    print("\n")
    print("=" * 60)
    print("IIMJOBS AUTOMATIC APPLICATION BOT")
    print("=" * 60)

    # --------------------------------------------------------
    # OPEN
    # --------------------------------------------------------

    open_iimjobs(driver)

    # --------------------------------------------------------
    # LOGIN
    # --------------------------------------------------------

    login_success = login_iimjobs(
        driver
    )

    if not login_success:

        print(
            "\nLogin failed."
        )

        return

    print(
        "\nLogin successful."
    )

    # --------------------------------------------------------
    # AUTOMATIC SEARCH
    # --------------------------------------------------------

    search_success = search_iimjobs(
        driver,
        SEARCH_TERM
    )

    if not search_success:

        print(
            "\nSearch failed."
        )

        return

    # --------------------------------------------------------
    # AUTOMATIC APPLICATION
    # --------------------------------------------------------

    apply_to_jobs(driver)


# ============================================================
# DIRECT RUN
# ============================================================

if __name__ == "__main__":

    from browser import start_browser

    driver = start_browser()

    try:

        run_iimjobs(driver)

    except KeyboardInterrupt:

        print(
            "\n\nAutomation stopped by user."
        )

    except Exception as error:

        print(
            "\nAutomation error:"
        )

        print(error)

    finally:

        try:

            driver.quit()

        except Exception:

            print(
                "Browser was already disconnected."
            )
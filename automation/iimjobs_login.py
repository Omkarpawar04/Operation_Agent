import re
import time
from urllib.parse import urlsplit, urlunsplit

from selenium.common.exceptions import (
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from excel_users import get_user


# ============================================================
# CONFIG
# ============================================================

WAIT_TIME = 20


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


def _is_existing_jobfeed_session(driver):
    try:
        parsed_url = urlsplit(driver.current_url)
        title = re.sub(r"\s+", " ", driver.title or "").strip()
        title = re.sub(r"^\(\d+\)\s*", "", title).casefold()

        if not (
            parsed_url.hostname
            and parsed_url.hostname.casefold() in {
                "www.iimjobs.com",
                "iimjobs.com",
            }
            and parsed_url.path.rstrip("/").casefold() == "/jobfeed"
            and title == "my jobfeed"
        ):
            return False

        login_controls = driver.find_elements(
            By.XPATH,
            "//button[normalize-space()='Use Password to Login' "
            "or (@type='submit' and normalize-space()='Login')]",
        )
        password_fields = driver.find_elements(
            By.XPATH,
            "//input[@type='password']",
        )
        dialogs = driver.find_elements(
            By.CSS_SELECTOR,
            "[role='dialog'], dialog",
        )
        if any(
            element.is_displayed()
            for element in login_controls + password_fields + dialogs
        ):
            return False

        visible_control_labels = set()
        for element in driver.find_elements(
            By.CSS_SELECTOR,
            "button, a, [role='button']",
        ):
            try:
                if element.is_displayed():
                    label = re.sub(
                        r"\s+",
                        " ",
                        element.text or "",
                    ).strip().casefold()
                    if label:
                        visible_control_labels.add(label)
            except StaleElementReferenceException:
                continue

        account_indicators = {
            "edit profile",
            "customize jobfeed",
        }
        if not account_indicators.issubset(visible_control_labels):
            return False
    except WebDriverException:
        return False

    return True


def log_login_diagnostic(driver):
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
        title = _safe_diagnostic_value(driver.title)
    except WebDriverException:
        title = "<unavailable>"

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
        modal_exists = bool(
            driver.find_elements(
                By.CSS_SELECTOR,
                "[role='dialog'], dialog",
            )
        )
    except WebDriverException:
        modal_exists = "unavailable"

    try:
        iframe_count = len(
            driver.find_elements(By.TAG_NAME, "iframe")
        )
    except WebDriverException:
        iframe_count = "unavailable"

    print(
        "[IIMJobs login diagnostic] "
        f"URL={safe_url!r}; title={title!r}; "
        f"visible_buttons_links={visible_controls[:30]!r}; "
        f"modal_exists={modal_exists}; iframe_count={iframe_count}. "
        "No credentials, cookies, query strings, or page body text logged."
    )


# ============================================================
# GET IIMJOBS CREDENTIALS FROM USERS.XLSX
# ============================================================

def get_iimjobs_credentials():

    print("\nLoading IIMJobs credentials from users.xlsx...")

    try:

        # Get first user from data/users.xlsx
        user = get_user()

    except Exception as error:

        print("\nCould not load user from users.xlsx.")
        print("Error:", error)

        return None, None

    # --------------------------------------------------------
    # READ IIMJOBS EMAIL
    # --------------------------------------------------------

    iimjobs_email = str(
        user.get("iimjobs_email", "")
    ).strip()

    # --------------------------------------------------------
    # READ IIMJOBS PASSWORD
    # --------------------------------------------------------

    iimjobs_password = str(
        user.get("iimjobs_password", "")
    ).strip()

    # --------------------------------------------------------
    # VALIDATE EMAIL
    # --------------------------------------------------------

    if not iimjobs_email:

        print(
            "\nERROR: 'iimjobs_email' column is empty "
            "in users.xlsx."
        )

        return None, None

    # --------------------------------------------------------
    # VALIDATE PASSWORD
    # --------------------------------------------------------

    if not iimjobs_password:

        print(
            "\nERROR: 'iimjobs_password' column is empty "
            "in users.xlsx."
        )

        return None, None

    # --------------------------------------------------------
    # SUCCESS
    # --------------------------------------------------------

    print(
        "IIMJobs credentials source: users.xlsx"
    )

    print("Login email: loaded from Excel")

    print(
        "Login password: loaded from Excel"
    )

    return iimjobs_email, iimjobs_password


# ============================================================
# IIMJOBS LOGIN
# ============================================================

def login_iimjobs(driver):

    print("\nStarting IIMJobs login...")

    if _is_existing_jobfeed_session(driver):
        print(
            "Authentication branch: existing account session verified "
            "by visible Edit Profile and Customize Jobfeed controls."
        )
        return True

    print(
        "Authentication branch: account indicators not verified; "
        "continuing the existing login flow."
    )

    # ========================================================
    # LOAD CREDENTIALS FROM EXCEL
    # ========================================================

    IIMJOBS_EMAIL, IIMJOBS_PASSWORD = (
        get_iimjobs_credentials()
    )

    if not IIMJOBS_EMAIL or not IIMJOBS_PASSWORD:

        print(
            "\nIIMJobs login stopped because "
            "credentials could not be loaded."
        )

        return False

    wait = WebDriverWait(
        driver,
        WAIT_TIME
    )

    # ========================================================
    # STEP 1 â€” CLICK "USE PASSWORD TO LOGIN"
    # ========================================================

    print(
        "Looking for 'Use Password to Login' button..."
    )

    try:

        password_login = wait.until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//button[normalize-space()='Use Password to Login']"
                )
            )
        )

    except TimeoutException:

        print(
            "\nCould not find 'Use Password to Login' button."
        )

        log_login_diagnostic(driver)

        return False

    try:

        driver.execute_script(
            """
            arguments[0].scrollIntoView({
                block: 'center'
            });
            """,
            password_login
        )

        time.sleep(0.5)

        driver.execute_script(
            "arguments[0].click();",
            password_login
        )

        print(
            "'Use Password to Login' clicked."
        )

    except Exception as error:

        print(
            "\nCould not click 'Use Password to Login'."
        )

        print("Error:", error)

        return False

    time.sleep(2)

    # ========================================================
    # STEP 2 â€” ENTER EMAIL
    # ========================================================

    print(
        "Looking for email/mobile field..."
    )

    try:

        email_input = wait.until(
            EC.visibility_of_element_located(
                (
                    By.XPATH,
                    "//input["
                    "@type='email' "
                    "or @name='email' "
                    "or @name='mobile' "
                    "or contains("
                    "translate("
                    "@placeholder,"
                    "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
                    "'abcdefghijklmnopqrstuvwxyz'"
                    "),"
                    "'email'"
                    ") "
                    "or contains("
                    "translate("
                    "@placeholder,"
                    "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
                    "'abcdefghijklmnopqrstuvwxyz'"
                    "),"
                    "'mobile'"
                    ")"
                    "]"
                )
            )
        )

    except Exception as error:

        print(
            "\nCould not find email/mobile field."
        )

        print("Error:", error)

        return False

    try:

        driver.execute_script(
            """
            arguments[0].scrollIntoView({
                block: 'center'
            });
            """,
            email_input
        )

        time.sleep(0.3)

        email_input.clear()

        email_input.send_keys(
            IIMJOBS_EMAIL
        )

        print(
            "Email/mobile entered."
        )

    except Exception as error:

        print(
            "\nCould not enter email."
        )

        print("Error:", error)

        return False

    # ========================================================
    # STEP 3 â€” ENTER PASSWORD
    # ========================================================

    print(
        "Looking for password field..."
    )

    try:

        password_input = wait.until(
            EC.visibility_of_element_located(
                (
                    By.XPATH,
                    "//input[@type='password']"
                )
            )
        )

    except Exception as error:

        print(
            "\nCould not find password field."
        )

        print("Error:", error)

        return False

    try:

        driver.execute_script(
            """
            arguments[0].scrollIntoView({
                block: 'center'
            });
            """,
            password_input
        )

        time.sleep(0.3)

        password_input.clear()

        password_input.send_keys(
            IIMJOBS_PASSWORD
        )

        print(
            "Password entered."
        )

    except Exception as error:

        print(
            "\nCould not enter password."
        )

        print("Error:", error)

        return False

    time.sleep(1)

    # ========================================================
    # STEP 4 â€” CLICK LOGIN
    # ========================================================

    print(
        "\nLooking for Login button..."
    )

    try:

        login_button = wait.until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//button["
                    "@type='submit' "
                    "and "
                    "normalize-space()='Login'"
                    "]"
                )
            )
        )

    except Exception as error:

        print(
            "\nCould not find Login button."
        )

        print("Error:", error)

        return False

    try:

        driver.execute_script(
            """
            arguments[0].scrollIntoView({
                block: 'center'
            });
            """,
            login_button
        )

        time.sleep(0.5)

        print(
            "Login button found."
        )

        # JavaScript click for Material UI
        driver.execute_script(
            "arguments[0].click();",
            login_button
        )

        print(
            "Login button clicked."
        )

    except Exception as error:

        print(
            "\nCould not click Login button."
        )

        print("Error:", error)

        return False

    # ========================================================
    # STEP 5 â€” WAIT FOR LOGIN RESPONSE
    # ========================================================

    print(
        "\nWaiting for login response..."
    )

    time.sleep(5)

    print(
        "Current URL:",
        driver.current_url
    )

    print(
        "Page title:",
        driver.title
    )

    # ========================================================
    # STEP 6 â€” CHECK LOGIN FORM
    # ========================================================

    try:

        login_forms = driver.find_elements(
            By.XPATH,
            "//button["
            "@type='submit' "
            "and "
            "normalize-space()='Login'"
            "]"
        )

        visible_login_buttons = []

        for button in login_forms:

            try:

                if button.is_displayed():

                    visible_login_buttons.append(
                        button
                    )

            except Exception:

                continue

        # ----------------------------------------------------
        # LOGIN BUTTON STILL VISIBLE
        # ----------------------------------------------------

        if visible_login_buttons:

            print(
                "\nLogin button is still visible."
            )

            try:

                body_text = driver.find_element(
                    By.TAG_NAME,
                    "body"
                ).text.lower()

            except Exception:

                body_text = ""

            # ------------------------------------------------
            # INVALID CREDENTIALS
            # ------------------------------------------------

            if "invalid" in body_text:

                print(
                    "Login failed: invalid credentials."
                )

                return False

            # ------------------------------------------------
            # INCORRECT CREDENTIALS
            # ------------------------------------------------

            if "incorrect" in body_text:

                print(
                    "Login failed: incorrect credentials."
                )

                return False

            # ------------------------------------------------
            # VERIFICATION
            # ------------------------------------------------

            verification_words = [
                "otp",
                "verification code",
                "verify your phone",
                "verify your email",
                "captcha",
            ]

            for word in verification_words:

                if word in body_text:

                    print(
                        "Additional verification detected:"
                    )

                    print(word)

                    print(
                        "Automatic login stopped."
                    )

                    return False

            print(
                "Login may require additional verification "
                "or credentials were not accepted."
            )

            return False

    except Exception:
        pass

    # ========================================================
    # LOGIN SUCCESS
    # ========================================================

    print("\n" + "=" * 60)
    print("LOGIN STEP COMPLETED")
    print("=" * 60)

    return True

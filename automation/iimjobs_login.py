import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from excel_users import get_user


# ============================================================
# CONFIG
# ============================================================

WAIT_TIME = 20


# ============================================================
# GET IIMJOBS CREDENTIALS FROM USERS.XLSX
# ============================================================

def get_iimjobs_credentials():

    print("\nLoading IIMJobs credentials from users.xlsx...")

    try:

        # Get first user from data/users.xlsx
        user = get_user(0)

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

    print(
        "Login email:",
        iimjobs_email
    )

    print(
        "Login password: loaded from Excel"
    )

    return iimjobs_email, iimjobs_password


# ============================================================
# IIMJOBS LOGIN
# ============================================================

def login_iimjobs(driver):

    print("\nStarting IIMJobs login...")

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
    # STEP 1 — CLICK "USE PASSWORD TO LOGIN"
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

    except Exception as error:

        print(
            "\nCould not find 'Use Password to Login' button."
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
    # STEP 2 — ENTER EMAIL
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
    # STEP 3 — ENTER PASSWORD
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
    # STEP 4 — CLICK LOGIN
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
    # STEP 5 — WAIT FOR LOGIN RESPONSE
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
    # STEP 6 — CHECK LOGIN FORM
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
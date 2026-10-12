from dotenv import load_dotenv

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import os
import time


load_dotenv()


def login_foundit(driver):

    email = os.getenv("FOUNDIT_EMAIL")
    password = os.getenv("FOUNDIT_PASSWORD")

    if not email or not password:
        raise ValueError(
            "FOUNDIT_EMAIL or FOUNDIT_PASSWORD is missing from .env"
        )

    wait = WebDriverWait(driver, 20)

    # --------------------------------------------------
    # Open Foundit
    # --------------------------------------------------

    driver.get("https://www.foundit.in/")

    print("Foundit opened.")
    print("URL:", driver.current_url)
    print("Title:", driver.title)

    # --------------------------------------------------
    # IMPORTANT:
    # Check whether Foundit returned Access Denied
    # --------------------------------------------------

    if "Access Denied" in driver.page_source:

        print("\nFoundit returned ACCESS DENIED.")
        print("Selenium cannot continue with the login flow.")

        input(
            "\nIf you want to inspect the browser manually, "
            "do so and press ENTER..."
        )

        return driver

    # --------------------------------------------------
    # 1. Click LOGIN
    # --------------------------------------------------

    login_button = wait.until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                "//a[contains(translate(normalize-space(.),"
                "'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),"
                "'login')]"
                "|//button[contains(translate(normalize-space(.),"
                "'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),"
                "'login')]"
            )
        )
    )

    driver.execute_script(
        "arguments[0].click();",
        login_button
    )

    print("Login clicked.")

    # --------------------------------------------------
    # 2. Enter Email / Mobile
    # --------------------------------------------------

    email_input = wait.until(
        EC.visibility_of_element_located(
            (
                By.XPATH,
                "//input["
                "@type='email' "
                "or contains(translate(@placeholder,"
                "'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),"
                "'email') "
                "or contains(translate(@placeholder,"
                "'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),"
                "'mobile') "
                "or contains(translate(@placeholder,"
                "'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),"
                "'phone')"
                "]"
            )
        )
    )

    email_input.clear()
    email_input.send_keys(email)

    print("Email entered.")

    # --------------------------------------------------
    # 3. Click Via Password
    # --------------------------------------------------

    via_password = wait.until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                "//*[contains(translate(normalize-space(.),"
                "'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),"
                "'via password')]"
            )
        )
    )

    driver.execute_script(
        "arguments[0].click();",
        via_password
    )

    print("Via Password clicked.")

    # --------------------------------------------------
    # 4. Enter Password
    # --------------------------------------------------

    password_input = wait.until(
        EC.visibility_of_element_located(
            (
                By.XPATH,
                "//input[@type='password']"
            )
        )
    )

    password_input.clear()
    password_input.send_keys(password)

    print("Password entered.")

    # --------------------------------------------------
    # 5. Click Submit
    # --------------------------------------------------

    submit_button = wait.until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                "//button["
                "contains(translate(normalize-space(.),"
                "'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),"
                "'submit')"
                "]"
                "|//input[@type='submit']"
            )
        )
    )

    driver.execute_script(
        "arguments[0].click();",
        submit_button
    )

    print("Submit clicked.")

    time.sleep(5)

    print("\nLogin process finished.")
    print("Current URL:", driver.current_url)
    print("Page title:", driver.title)

    return driver

if __name__ == "__main__":
    print("SCRIPT STARTED", flush=True)

    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options

    print("Starting Chrome...", flush=True)

    options = Options()
    options.add_argument("--start-maximized")

    driver = webdriver.Chrome(options=options)

    print("Chrome started.", flush=True)

    try:
        login_foundit(driver)

        input(
            "\nBrowser is open. Press ENTER to close..."
        )

    except Exception as e:
        print(
            "\nERROR:",
            type(e).__name__,
            str(e),
            flush=True,
        )

        import traceback
        traceback.print_exc()

        input(
            "\nPress ENTER to close..."
        )

    finally:
        driver.quit()
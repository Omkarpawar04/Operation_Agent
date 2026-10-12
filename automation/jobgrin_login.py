import os
import time

from dotenv import load_dotenv

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


load_dotenv()

JOBGRIN_EMAIL = os.getenv("JOBGRIN_EMAIL")
JOBGRIN_PASSWORD = os.getenv("JOBGRIN_PASSWORD")

LOGIN_URL = "https://jobgrin.co.in/candidate/login"


def handle_cookie_popup(driver):

    print("\nChecking cookie consent...")

    wait = WebDriverWait(driver, 5)

    try:

        # JobGrin cookie consent button
        cookie_button = wait.until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//div[contains(@class,'jobgrin-cookie-consent__panel')]"
                    "//button[contains(translate(normalize-space(.),"
                    "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
                    "'abcdefghijklmnopqrstuvwxyz'),'got it')]"
                )
            )
        )

        cookie_button.click()

        print("Cookie consent accepted.")

        time.sleep(1)

    except Exception:

        print("Cookie popup not displayed or already accepted.")


def login_jobgrin(driver):

    print("\n" + "=" * 60)
    print("JOBGRIN LOGIN")
    print("=" * 60)

    if not JOBGRIN_EMAIL or not JOBGRIN_PASSWORD:

        raise ValueError(
            "JOBGRIN_EMAIL or JOBGRIN_PASSWORD is missing from .env"
        )

    print("Opening JobGrin login...")

    driver.get(LOGIN_URL)

    wait = WebDriverWait(driver, 15)

    wait.until(
        lambda d: d.execute_script(
            "return document.readyState"
        ) == "complete"
    )

    time.sleep(2)

    print("Login page loaded.")
    print("Title:", driver.title)

    # --------------------------------------------------------
    # HANDLE COOKIE POPUP FIRST
    # --------------------------------------------------------

    handle_cookie_popup(driver)

    # --------------------------------------------------------
    # EMAIL
    # --------------------------------------------------------

    email_input = wait.until(
        EC.element_to_be_clickable(
            (By.ID, "email")
        )
    )

    email_input.clear()
    email_input.send_keys(JOBGRIN_EMAIL)

    print("Email entered.")

    # --------------------------------------------------------
    # PASSWORD
    # --------------------------------------------------------

    password_input = wait.until(
        EC.element_to_be_clickable(
            (By.ID, "password")
        )
    )

    password_input.clear()
    password_input.send_keys(JOBGRIN_PASSWORD)

    print("Password entered.")

    # --------------------------------------------------------
    # LOGIN BUTTON
    # --------------------------------------------------------

    login_button = wait.until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                "//button[@type='submit' and "
                "contains(normalize-space(.),'Login')]"
            )
        )
    )

    # Scroll button into view
    driver.execute_script(
        "arguments[0].scrollIntoView({block:'center'});",
        login_button
    )

    time.sleep(0.5)

    login_button.click()

    print("Login button clicked.")

    # --------------------------------------------------------
    # WAIT FOR LOGIN
    # --------------------------------------------------------

    time.sleep(5)

    print("\nAfter login:")
    print("URL:", driver.current_url)
    print("Title:", driver.title)

    return driver
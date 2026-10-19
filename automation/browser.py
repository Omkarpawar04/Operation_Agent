import os

from selenium import webdriver
from selenium.webdriver.chrome.options import Options


def start_browser():

    options = Options()

    options.add_argument("--start-maximized")

    profile_dir = os.environ.get("JOB_AUTOMATION_PROFILE_DIR")
    if profile_dir:
        options.add_argument(f"--user-data-dir={profile_dir}")

    options.binary_location = (
        r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    )

    driver = webdriver.Chrome(options=options)

    return driver

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from automation.wellfound_login import (
    login_wellfound,
    process_wellfound_jobs,
)


def main():
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")

    driver = webdriver.Chrome(options=options)

    try:
        print("[Wellfound] Opening jobs page...", flush=True)
        driver.get("https://wellfound.com/jobs")

        print("[Wellfound] Starting login...", flush=True)
        login_wellfound(driver)

        print("[Wellfound] Starting job processing...", flush=True)
        process_wellfound_jobs(driver)

        print("[Wellfound] Workflow finished.", flush=True)

    except Exception as error:
        print(
            f"[Wellfound] {type(error).__name__}: {error}",
            flush=True,
        )
        raise

    finally:
        driver.quit()


if __name__ == "__main__":
    main()
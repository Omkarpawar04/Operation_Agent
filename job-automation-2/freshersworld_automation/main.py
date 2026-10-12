import os
import time
import json
import sys
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from credentials import load_portal_credentials


APPLIED_JOBS_FILE = Path(__file__).with_name("applied_jobs.json")


def normalize_job_url(job_url):
    return (job_url or "").strip().split("#", 1)[0].rstrip("/")


def load_applied_job_urls():
    if not APPLIED_JOBS_FILE.exists():
        return set()

    with APPLIED_JOBS_FILE.open("r", encoding="utf-8") as file:
        saved_urls = json.load(file)

    if not isinstance(saved_urls, list):
        raise ValueError(f"{APPLIED_JOBS_FILE.name} must contain a JSON list.")

    return {normalize_job_url(url) for url in saved_urls if normalize_job_url(url)}


def save_applied_job_urls(applied_urls):
    temporary_file = APPLIED_JOBS_FILE.with_suffix(".tmp")
    temporary_file.write_text(
        json.dumps(sorted(applied_urls), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    temporary_file.replace(APPLIED_JOBS_FILE)


# ============================================================
# LOAD CREDENTIALS
# ============================================================

try:
    EMAIL, PASSWORD = load_portal_credentials("FRESHERSWORLD")
except Exception as e:
    print("ERROR: Could not load Freshersworld credentials from users.xlsx:", e)
    input("Press ENTER to close...")
    exit()


# ============================================================
# CHROME
# ============================================================

options = Options()
options.add_argument("--start-maximized")

driver = webdriver.Chrome(options=options)

wait = WebDriverWait(driver, 20)


# ============================================================
# OPEN FRESHERSWORLD
# ============================================================

print("=" * 60)
print("FRESHERSWORLD - LOGIN + FINANCE SEARCH")
print("=" * 60)

driver.get("https://www.freshersworld.com/")

time.sleep(4)

print("\nOpened FreshersWorld")
print("URL:", driver.current_url)


# ============================================================
# JOBSEEKER LOGIN
# ============================================================

print("\nFinding Jobseeker Login...")

try:

    jobseeker_login = wait.until(
        EC.element_to_be_clickable(
            (
                By.CSS_SELECTOR,
                "div.candidate-login"
            )
        )
    )

    print("✓ Jobseeker Login found")

    jobseeker_login.click()

    print("✓ Jobseeker Login clicked")

except Exception as e:

    print("✗ Jobseeker Login error:", e)

    driver.save_screenshot("jobseeker_login_error.png")

    input("Press ENTER to close...")

    driver.quit()

    exit()


# ============================================================
# EMAIL
# ============================================================

print("\nFinding email field...")

try:

    email_input = wait.until(
        EC.visibility_of_element_located(
            (By.ID, "emailpop")
        )
    )

    email_input.clear()
    email_input.send_keys(EMAIL)

    print("✓ Email entered")

except Exception as e:

    print("✗ Email error:", e)

    driver.save_screenshot("email_error.png")

    input("Press ENTER to close...")

    driver.quit()

    exit()


# ============================================================
# PASSWORD
# ============================================================

print("\nFinding password field...")

try:

    password_input = wait.until(
        EC.visibility_of_element_located(
            (By.ID, "passwordpop")
        )
    )

    password_input.clear()
    password_input.send_keys(PASSWORD)

    print("✓ Password entered")

except Exception as e:

    print("✗ Password error:", e)

    driver.save_screenshot("password_error.png")

    input("Press ENTER to close...")

    driver.quit()

    exit()


# ============================================================
# LOGIN
# ============================================================

print("\nLogging in...")

try:

    login_button = wait.until(
        EC.element_to_be_clickable(
            (By.ID, "loginSubmitpop")
        )
    )

    login_button.click()

    print("✓ Login button clicked")

except Exception as e:

    print("✗ Login error:", e)

    driver.save_screenshot("login_error.png")

    input("Press ENTER to close...")

    driver.quit()

    exit()


# ============================================================
# WAIT FOR LOGIN
# ============================================================

print("\nWaiting for login...")

time.sleep(6)

print("Current URL:")
print(driver.current_url)

print("Page title:")
print(driver.title)


# ============================================================
# OPEN JOBS
# ============================================================

print("\nOpening Jobs...")

try:

    jobs_link = wait.until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                "//a[normalize-space()='Jobs']"
            )
        )
    )

    jobs_link.click()

    print("✓ Jobs clicked")

except Exception as e:

    print("✗ Jobs error:", e)

    driver.save_screenshot("jobs_error.png")

    input("Press ENTER to close...")

    driver.quit()

    exit()


# ============================================================
# WAIT FOR JOBS PAGE
# ============================================================

time.sleep(5)

print("\nJobs page:")
print(driver.current_url)


# ============================================================
# CLICK SEARCH BAR
# ============================================================

print("\nFinding FreshersWorld search bar...")

try:

    search_bar = wait.until(
        EC.visibility_of_element_located(
            (By.ID, "seach-new-bar")
        )
    )

    print("✓ Search bar found")

    print("Clicking search bar...")

    search_bar.click()

    print("✓ Search bar clicked")

    time.sleep(2)

except Exception as e:

    print("✗ Search bar error:", e)

    driver.save_screenshot("search_bar_error.png")

    input("Press ENTER to close...")

    driver.quit()

    exit()


# ============================================================
# SEARCH FOR FINANCE JOBS
# ============================================================

print("\nSearching for finance jobs...")

try:
    # Instead of fighting the readonly dropdown modal UI, we directly navigate to the search results
    print("Navigating directly to Finance keyword search...")
    driver.get("https://www.freshersworld.com/jobs/jobsearch/finance-jobs")
    time.sleep(5)
    print("✓ Search submitted successfully")

except Exception as e:
    print("\n✗ Search error:", e)
    driver.save_screenshot("search_error.png")

# ============================================================
# WAIT FOR RESULTS
# ============================================================

print("\nWaiting for search results...")
time.sleep(3)

# ============================================================
# RESULT
# ============================================================

print("\n" + "=" * 60)
print("SEARCH COMPLETE")
print("=" * 60)

print("\nCurrent URL:")
print(driver.current_url)

print("\nPage title:")
print(driver.title)

# ============================================================
# APPLY FOR MULTIPLE MATCHING JOBS
# ============================================================

print("\nLooking for job cards...")

import re
resume_path = os.path.abspath("Aditya Sajeev Financial Analyst Resume.pdf")
jobs_applied_count = 0
MAX_JOBS = 6

try:
    time.sleep(3)

    applied_job_urls = load_applied_job_urls()
    processed_job_urls = set()
    page_number = 1

    while jobs_applied_count < MAX_JOBS:
        print(f"\nScanning Freshersworld results page {page_number}...")
        # Strictly find the "View & Apply" buttons to avoid clicking random navbar links
        job_links = driver.find_elements(By.XPATH, "//a[contains(text(), 'View & Apply') or contains(., 'View & Apply')]")
    
        valid_jobs = []
        for link in job_links:
            href = link.get_attribute("href")
            if href and "/jobs/" in href:
                valid_jobs.append(link)

        print(f"Found {len(valid_jobs)} potential job cards with View & Apply buttons.")

        for link in valid_jobs:
            if jobs_applied_count >= MAX_JOBS:
                break

            try:
                # We can check the text of the parent container to see if it matches 0-2 years
                parent_text = ""
                try:
                    # Traverse up to the job card body
                    parent_text = link.find_element(By.XPATH, "../../..").text.lower()
                except:
                    parent_text = link.text.lower()

                # Filter: Experience should be 0 to 2 years, Location within India
                if ("0" in parent_text or "1" in parent_text or "2" in parent_text or "fresher" in parent_text):
                    print(f"\nChecking job matching criteria (Applied so far: {jobs_applied_count}/{MAX_JOBS})...")

                    job_url = link.get_attribute("href")
                    normalized_job_url = normalize_job_url(job_url)
                    if not normalized_job_url:
                        print("Skipping job without a usable URL.")
                        continue
                    if normalized_job_url in applied_job_urls or normalized_job_url in processed_job_urls:
                        print("Skipping job already applied to or already checked:", job_url)
                        continue
                    processed_job_urls.add(normalized_job_url)

                    # Open in new tab
                    driver.execute_script(f"window.open('{job_url}', '_blank');")
                    time.sleep(4)

                    driver.switch_to.window(driver.window_handles[-1])
                    time.sleep(4)

                    # Look for apply button
                    try:
                        # Find all elements that might be the apply button
                        possible_btns = driver.find_elements(By.XPATH, "//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'apply')] | //button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'apply')] | //span[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'apply')]")
                    
                        apply_btn = None
                        for btn in possible_btns:
                            if btn.is_displayed():
                                apply_btn = btn
                                break
                    
                        if apply_btn:
                            print("Found visible Apply button on job page, clicking...")
                            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", apply_btn)
                            time.sleep(1)
                        
                            try:
                                # Try native click first to trigger modals properly
                                apply_btn.click()
                            except:
                                driver.execute_script("arguments[0].click();", apply_btn)
                            
                            time.sleep(5)
                        
                            # Handle case if it opened an external tab
                            if len(driver.window_handles) > 2:
                                print("External application tab detected. Switching...")
                                driver.switch_to.window(driver.window_handles[-1])
                                time.sleep(4)

                            # Look for resume upload in the modal or new page
                            file_inputs = driver.find_elements(By.XPATH, "//input[@type='file']")
                            if file_inputs:
                                for file_input in file_inputs:
                                    try:
                                        file_input.send_keys(resume_path)
                                        print("Resume uploaded to modal.")
                                        time.sleep(2)
                                        break
                                    except:
                                        pass

                            # Now click the final submit/apply inside the modal or new page!
                            final_btns = driver.find_elements(By.XPATH, "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'submit') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'apply')] | //a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'submit')] | //input[contains(translate(@value, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'submit')]")
                        
                            for f_btn in final_btns:
                                if f_btn.is_displayed():
                                    # Prevent re-clicking the exact same main page button if we didn't go anywhere
                                    if f_btn == apply_btn:
                                        continue
                                    print("Clicking final submit button inside modal/page...")
                                    try:
                                        f_btn.click()
                                    except:
                                        driver.execute_script("arguments[0].click();", f_btn)
                                    time.sleep(4)
                                    break

                            applied_job_urls.add(normalized_job_url)
                            save_applied_job_urls(applied_job_urls)
                            jobs_applied_count += 1
                            driver.save_screenshot(f"successfully_applied_{jobs_applied_count}.png")
                            print(f"✓ Successfully applied for the job! (Screenshot saved as successfully_applied_{jobs_applied_count}.png)")
                        
                        else:
                            print("Could not find a VISIBLE Apply button on the page.")

                    except Exception as e:
                        print("Could not apply to this job (Apply button missing or error):", e)

                    # Close tab and switch back
                    driver.close()
                    driver.switch_to.window(driver.window_handles[0])
                    time.sleep(2)

            except Exception as e:
                print("Error processing a job card:", e)

            # Safety check, close any extra tabs if opened by accident
            while len(driver.window_handles) > 1:
                driver.switch_to.window(driver.window_handles[-1])
                driver.close()
            driver.switch_to.window(driver.window_handles[0])


        if jobs_applied_count >= MAX_JOBS:
            break

        old_page_url = driver.current_url
        old_first_job_url = ""
        if valid_jobs:
            old_first_job_url = normalize_job_url(valid_jobs[0].get_attribute("href"))

        try:
            next_span = driver.find_element(
                By.XPATH,
                "//span[@aria-hidden='true' and normalize-space(.)='Next >']"
            )
        except Exception:
            print("[INFO] Next > button not found; no further results page.")
            break

        try:
            next_parent = next_span.find_element(
                By.XPATH,
                "./ancestor::*[self::li or self::a or self::button][1]"
            )
            parent_classes = (next_parent.get_attribute("class") or "").lower()
            disabled = (
                "disabled" in parent_classes
                or next_parent.get_attribute("aria-disabled") == "true"
            )
            if disabled:
                print("[INFO] Next > button is disabled; last page reached.")
                break
        except Exception:
            pass

        print("Clicking Next >...")
        try:
            next_span.click()
        except Exception:
            driver.execute_script("arguments[0].click();", next_span)

        def results_page_changed(browser):
            if browser.current_url != old_page_url:
                return True
            current_links = browser.find_elements(
                By.XPATH,
                "//a[contains(text(), 'View & Apply') or contains(., 'View & Apply')]"
            )
            current_urls = [
                normalize_job_url(item.get_attribute("href"))
                for item in current_links
                if item.get_attribute("href") and "/jobs/" in item.get_attribute("href")
            ]
            first_current_url = current_urls[0] if current_urls else ""
            return first_current_url != old_first_job_url

        try:
            WebDriverWait(driver, 15).until(results_page_changed)
        except Exception:
            time.sleep(3)

        current_links = driver.find_elements(
            By.XPATH,
            "//a[contains(text(), 'View & Apply') or contains(., 'View & Apply')]"
        )
        current_urls = [
            normalize_job_url(item.get_attribute("href"))
            for item in current_links
            if item.get_attribute("href") and "/jobs/" in item.get_attribute("href")
        ]
        first_current_url = current_urls[0] if current_urls else ""
        if driver.current_url == old_page_url and first_current_url == old_first_job_url:
            print("[INFO] Results did not advance after clicking Next >; stopping pagination.")
            break

        page_number += 1
    if jobs_applied_count == 0:
        print("\n✗ Could not find or apply to any job matching the criteria.")
    else:
        print(f"\n✓ Finished application phase. Total jobs applied to: {jobs_applied_count}")

except Exception as e:
    print("\n✗ Error during job application phase:", e)
    driver.save_screenshot("job_apply_error.png")


# ============================================================
# KEEP BROWSER OPEN
# ============================================================

print("\nBrowser is still open.")

input("\nPress ENTER to close browser...")

driver.quit()

print("\nDone.")

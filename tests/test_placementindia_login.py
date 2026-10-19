import contextlib
import io
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from selenium.common.exceptions import TimeoutException

AUTOMATION_DIR = Path(__file__).resolve().parents[1] / "automation"
sys.path.insert(0, str(AUTOMATION_DIR))

import placementindia


class _LoginElement:
    def __init__(self, text="", attributes=None):
        self.clicked = False
        self.text = text
        self.attributes = attributes or {}

    def is_displayed(self):
        return True

    def is_enabled(self):
        return True

    def get_attribute(self, name):
        return self.attributes.get(name, "")


class _BodyElement:
    def __init__(self, text=""):
        self.text = text


class _LoginDriver:
    current_url = "https://jobseeker.placementindia.com/?token=private"
    title = "Job Seeker My Folder - PlacementIndia.Com"

    def __init__(self, element_after_poll=None, body_text=""):
        self.element_after_poll = element_after_poll
        self.polls = 0
        self.element = _LoginElement()
        self.body = _BodyElement(body_text)
        self.executed_scripts = []

    def find_element(self, by, selector):
        if by == placementindia.By.TAG_NAME and selector == "body":
            return self.body
        raise AssertionError(f"Unexpected single-element selector: {selector}")

    def find_elements(self, by, selector):
        if by == placementindia.By.TAG_NAME and selector == "iframe":
            return []

        if by == placementindia.By.CSS_SELECTOR:
            return []

        if self.element_after_poll is None:
            return []

        if (
            selector.startswith("//a[contains")
            or selector.startswith("//button[contains")
            or selector == "Login"
        ):
            self.polls += 1
            if self.polls >= self.element_after_poll:
                return [self.element]

        return []

    def execute_script(self, script, element):
        self.executed_scripts.append(script)
        element.clicked = True


class _FakeWait:
    timeout_values = []

    def __init__(self, driver, timeout):
        self.driver = driver
        self.timeout = timeout
        self.timeout_values.append(timeout)

    def until(self, predicate):
        for _ in range(4):
            result = predicate(self.driver)
            if result:
                return result
        raise TimeoutException()


class PlacementIndiaLoginTests(unittest.TestCase):
    def test_login_control_waits_for_existing_login_selector(self):
        driver = _LoginDriver(element_after_poll=2)

        with patch.object(placementindia, "WebDriverWait", _FakeWait):
            with patch.object(placementindia.time, "sleep"):
                self.assertTrue(placementindia.click_login(driver))

        self.assertTrue(driver.element.clicked)
        self.assertEqual(_FakeWait.timeout_values[-1], 10)

    def test_missing_login_control_logs_safe_page_diagnostics(self):
        driver = _LoginDriver()
        output = io.StringIO()

        with patch.object(placementindia, "WebDriverWait", _FakeWait):
            with contextlib.redirect_stdout(output):
                self.assertFalse(placementindia.click_login(driver))

        diagnostic = output.getvalue()
        self.assertIn("jobseeker.placementindia.com", diagnostic)
        self.assertIn("Job Seeker My Folder", diagnostic)
        self.assertIn("visible_fields=[]", diagnostic)
        self.assertIn("visible_buttons_links=[]", diagnostic)
        self.assertIn("iframe_count=0", diagnostic)
        self.assertNotIn("private", diagnostic)
        self.assertIn(
            "Field values, cookies, and page body text were not logged.",
            diagnostic,
        )

    def test_existing_authenticated_session_skips_login_flow(self):
        driver = _LoginDriver(body_text="My Profile")

        with patch.object(placementindia.time, "sleep"):
            with patch.object(placementindia, "click_login") as click_login:
                self.assertTrue(
                    placementindia.login_placementindia(driver)
                )

        click_login.assert_not_called()

    def test_login_required_state_uses_login_flow(self):
        driver = _LoginDriver(
            element_after_poll=1,
            body_text="Please login to continue",
        )

        def complete_login(_driver):
            _driver.body.text = "My Profile"
            return True

        with patch.object(placementindia.time, "sleep"):
            with patch.object(
                placementindia,
                "enter_email",
                return_value=True,
            ) as enter_email:
                with patch.object(
                    placementindia,
                    "click_continue",
                    return_value=True,
                ) as click_continue:
                    with patch.object(
                        placementindia,
                        "enter_password",
                        return_value=True,
                    ) as enter_password:
                        with patch.object(
                            placementindia,
                            "click_final_login",
                            side_effect=lambda _driver: complete_login(_driver),
                        ):
                            self.assertTrue(
                                placementindia.login_placementindia(driver)
                            )

        enter_email.assert_called_once_with(driver)
        click_continue.assert_called_once_with(driver)
        enter_password.assert_called_once_with(driver)


if __name__ == "__main__":
    unittest.main()

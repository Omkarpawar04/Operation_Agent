import contextlib
import io
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from selenium.common.exceptions import TimeoutException

AUTOMATION_DIR = Path(__file__).resolve().parents[1] / "automation"
sys.path.insert(0, str(AUTOMATION_DIR))

import iimjobs_login


class _Element:
    def __init__(self, text=""):
        self.text = text

    def is_displayed(self):
        return True

    def get_attribute(self, name):
        return ""


class _Driver:
    def __init__(
        self,
        current_url="https://www.iimjobs.com/",
        title="Management Job Vacancies",
        login_required=False,
        account_indicators=False,
        iframe_count=0,
    ):
        self.current_url = current_url
        self.title = title
        self.login_required = login_required
        self.account_indicators = account_indicators
        self.iframe_count = iframe_count

    def find_elements(self, by, selector):
        if by == iimjobs_login.By.XPATH and self.login_required:
            if "Use Password to Login" in selector:
                return [_Element("Use Password to Login")]
            if "@type='password'" in selector:
                return [_Element()]
        if (
            by == iimjobs_login.By.CSS_SELECTOR
            and selector == "[role='dialog'], dialog"
            and self.login_required
        ):
            return [_Element()]
        if by == iimjobs_login.By.CSS_SELECTOR:
            if selector == "button, a, [role='button']":
                if self.account_indicators:
                    return [
                        _Element("Edit Profile"),
                        _Element("Customize Jobfeed"),
                        _Element("Filter"),
                    ]
                return [_Element("Use Password to Login")]
            if selector == "[role='dialog'], dialog":
                return []
        if by == iimjobs_login.By.TAG_NAME and selector == "iframe":
            return [_Element() for _ in range(self.iframe_count)]
        return []


class _TimedOutWait:
    def __init__(self, driver, timeout):
        self.driver = driver
        self.timeout = timeout

    def until(self, _condition):
        raise TimeoutException()


class IIMJobsLoginTests(unittest.TestCase):
    def test_account_indicators_verify_session_even_with_iframe(self):
        driver = _Driver(
            current_url="https://www.iimjobs.com/jobfeed",
            title="My Jobfeed",
            account_indicators=True,
            iframe_count=1,
        )

        with patch.object(
            iimjobs_login,
            "get_iimjobs_credentials",
            side_effect=AssertionError("credentials must not be needed"),
        ):
            self.assertTrue(iimjobs_login.login_iimjobs(driver))

    def test_jobfeed_url_and_title_alone_do_not_verify_session(self):
        driver = _Driver(
            current_url="https://www.iimjobs.com/jobfeed",
            title="My Jobfeed",
            account_indicators=False,
            iframe_count=1,
        )

        self.assertFalse(
            iimjobs_login._is_existing_jobfeed_session(driver)
        )

    def test_visible_login_modal_rejects_dashboard_markers(self):
        driver = _Driver(
            current_url="https://www.iimjobs.com/jobfeed",
            title="My Jobfeed",
            login_required=True,
            account_indicators=True,
            iframe_count=1,
        )

        self.assertFalse(
            iimjobs_login._is_existing_jobfeed_session(driver)
        )

    def test_unverified_jobfeed_continues_login_flow(self):
        driver = _Driver(
            current_url="https://www.iimjobs.com/jobfeed",
            title="My Jobfeed",
            account_indicators=False,
            iframe_count=1,
        )
        output = io.StringIO()

        with patch.object(
            iimjobs_login,
            "get_iimjobs_credentials",
            return_value=("student@example.test", "not-a-real-password"),
        ):
            with patch.object(
                iimjobs_login,
                "WebDriverWait",
                _TimedOutWait,
            ):
                with contextlib.redirect_stdout(output):
                    self.assertFalse(iimjobs_login.login_iimjobs(driver))

        self.assertIn(
            "Authentication branch: account indicators not verified",
            output.getvalue(),
        )
        self.assertIn("iframe_count=1", output.getvalue())

    def test_login_control_timeout_logs_safe_page_diagnostics(self):
        driver = _Driver(
            current_url="https://www.iimjobs.com/login?token=secret-value",
            title="IIMJobs Login",
        )
        output = io.StringIO()

        with patch.object(
            iimjobs_login,
            "get_iimjobs_credentials",
            return_value=("student@example.test", "not-a-real-password"),
        ):
            with patch.object(
                iimjobs_login,
                "WebDriverWait",
                _TimedOutWait,
            ):
                with contextlib.redirect_stdout(output):
                    self.assertFalse(iimjobs_login.login_iimjobs(driver))

        diagnostic = output.getvalue()
        self.assertIn("https://www.iimjobs.com/login", diagnostic)
        self.assertIn("IIMJobs Login", diagnostic)
        self.assertIn(
            "visible_buttons_links=['Use Password to Login']",
            diagnostic,
        )
        self.assertIn("modal_exists=False", diagnostic)
        self.assertIn("iframe_count=0", diagnostic)
        self.assertNotIn("secret-value", diagnostic)
        self.assertNotIn("student@example.test", diagnostic)
        self.assertNotIn("not-a-real-password", diagnostic)


if __name__ == "__main__":
    unittest.main()

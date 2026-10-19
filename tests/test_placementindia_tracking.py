import tempfile
import unittest
from datetime import date
from pathlib import Path

from automation.placementindia_tracking import (
    get_today_application_count,
    has_submission_confirmation,
    has_application_record,
    load_application_history,
    save_application_history,
)


class PlacementIndiaTrackingTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.tracker_path = Path(self.temp_dir.name) / "scoped.json"
        self.today = date(2026, 10, 16)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_student_histories_duplicate_checks_and_daily_counts_are_independent(
        self,
    ):
        first_history = {
            "same-job-url": {
                "status": "submitted",
                "timestamp": "2026-10-16T09:00:00",
            },
            "second-job-url": {
                "status": "submitted",
                "timestamp": "2026-10-16T09:15:00",
            },
        }
        second_history = {
            "different-job-url": {
                "status": "submitted",
                "timestamp": "2026-10-16T10:00:00",
            }
        }
        save_application_history(
            self.tracker_path,
            "student-a",
            "first@example.test",
            first_history,
        )
        save_application_history(
            self.tracker_path,
            "student-b",
            "first@example.test",
            second_history,
        )

        first_loaded = load_application_history(
            self.tracker_path,
            "student-a",
            "first@example.test",
        )
        second_loaded = load_application_history(
            self.tracker_path,
            "student-b",
            "first@example.test",
        )

        self.assertEqual(first_loaded, first_history)
        self.assertEqual(second_loaded, second_history)
        self.assertTrue(has_application_record("same-job-url", first_loaded))
        self.assertFalse(has_application_record("same-job-url", second_loaded))
        self.assertEqual(
            get_today_application_count(first_loaded, self.today),
            2,
        )
        self.assertEqual(
            get_today_application_count(second_loaded, self.today),
            1,
        )

    def test_account_history_and_daily_count_are_independent(self):
        history = {
            "same-job-url": {
                "status": "processed",
                "timestamp": "2026-10-16T09:00:00",
            }
        }
        save_application_history(
            self.tracker_path,
            "student-a",
            "first@example.test",
            history,
        )

        other_account_history = load_application_history(
            self.tracker_path,
            "student-a",
            "second@example.test",
        )
        self.assertEqual(other_account_history, {})
        self.assertFalse(
            has_application_record("same-job-url", other_account_history)
        )
        self.assertEqual(
            get_today_application_count(other_account_history, self.today),
            0,
        )

    def test_any_existing_record_prevents_reapplication(self):
        history = {
            "failed-job-url": {"status": "open_failed"},
            "processed-job-url": {"status": "processed"},
        }

        self.assertTrue(
            has_application_record("failed-job-url", history)
        )
        self.assertTrue(
            has_application_record("processed-job-url", history)
        )
        self.assertFalse(
            has_application_record("unseen-job-url", history)
        )

    def test_daily_count_only_includes_confirmed_submissions(self):
        history = {
            "today-submitted": {
                "status": "submitted",
                "timestamp": "2026-10-16T09:00:00",
            },
            "today-clicked-but-unconfirmed": {
                "status": "processed",
                "timestamp": "2026-10-16T09:05:00",
            },
            "today-failed": {
                "status": "apply_button_not_found",
                "timestamp": "2026-10-16T09:10:00",
            },
            "today-open-failed": {
                "status": "open_failed",
                "timestamp": "2026-10-16T09:15:00",
            },
            "old-submitted": {
                "status": "submitted",
                "timestamp": "2026-10-15T09:00:00",
            },
            "invalid-timestamp": {
                "status": "submitted",
                "timestamp": "invalid",
            },
        }

        self.assertEqual(
            get_today_application_count(history, self.today),
            1,
        )

    def test_submission_confirmation_requires_success_message(self):
        self.assertTrue(
            has_submission_confirmation(
                "Your application has been submitted successfully."
            )
        )
        self.assertFalse(
            has_submission_confirmation("Apply button clicked.")
        )
        self.assertFalse(
            has_submission_confirmation(
                "Application was not submitted."
            )
        )

    def test_five_confirmed_applications_reach_the_daily_limit(self):
        history = {
            f"job-{index}": {
                "status": "submitted",
                "timestamp": f"2026-10-16T09:{index:02d}:00",
            }
            for index in range(5)
        }
        history["failed"] = {
            "status": "apply_button_not_found",
            "timestamp": "2026-10-16T10:00:00",
        }

        self.assertEqual(
            get_today_application_count(history, self.today),
            5,
        )


if __name__ == "__main__":
    unittest.main()

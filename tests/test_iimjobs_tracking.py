import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from automation.iimjobs_tracking import (
    get_today_submitted_count,
    has_been_submitted,
    load_application_log,
    record_application,
    save_application_log,
)


class IIMJobsTrackingTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.tracker_path = Path(self.temp_dir.name) / "iimjobs.json"
        self.today = datetime(2026, 10, 16, 12, 0, 0)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_student_histories_and_daily_limits_are_independent(self):
        first = load_application_log(
            self.tracker_path,
            "student-a",
            "first@example.test",
        )
        second = load_application_log(
            self.tracker_path,
            "student-b",
            "first@example.test",
        )
        for index in range(5):
            record_application(
                first,
                {"url": f"https://jobs.test/{index}", "title": "Role"},
                submitted=True,
                now=self.today,
            )
        record_application(
            second,
            {"url": "https://jobs.test/other", "title": "Role"},
            submitted=True,
            now=self.today,
        )
        save_application_log(
            self.tracker_path,
            "student-a",
            "first@example.test",
            first,
        )
        save_application_log(
            self.tracker_path,
            "student-b",
            "first@example.test",
            second,
        )

        first_loaded = load_application_log(
            self.tracker_path,
            "student-a",
            "first@example.test",
        )
        second_loaded = load_application_log(
            self.tracker_path,
            "student-b",
            "first@example.test",
        )
        today = self.today.date().isoformat()
        first_count = get_today_submitted_count(first_loaded, today)
        second_count = get_today_submitted_count(second_loaded, today)

        self.assertEqual(first_count, 5)
        self.assertEqual(second_count, 1)
        self.assertGreaterEqual(first_count, 5)
        self.assertLess(second_count, 5)

    def test_account_history_and_daily_limit_are_independent(self):
        history = load_application_log(
            self.tracker_path,
            "student-a",
            "first@example.test",
        )
        record_application(
            history,
            {"url": "https://jobs.test/1", "title": "Role"},
            submitted=True,
            now=self.today,
        )
        save_application_log(
            self.tracker_path,
            "student-a",
            "first@example.test",
            history,
        )

        other_account = load_application_log(
            self.tracker_path,
            "student-a",
            "second@example.test",
        )
        self.assertEqual(
            get_today_submitted_count(
                other_account,
                self.today.date().isoformat(),
            ),
            0,
        )
        self.assertFalse(
            has_been_submitted(
                other_account,
                {"url": "https://jobs.test/1"},
            )
        )

    def test_duplicate_prevention_applies_to_confirmed_submissions(self):
        history = load_application_log(
            self.tracker_path,
            "student-a",
            "first@example.test",
        )
        submitted_job = {"url": "https://jobs.test/submitted"}
        failed_job = {"url": "https://jobs.test/failed"}
        record_application(
            history,
            submitted_job,
            submitted=True,
            now=self.today,
        )
        record_application(
            history,
            failed_job,
            submitted=False,
            now=self.today,
        )

        self.assertTrue(has_been_submitted(history, submitted_job))
        self.assertFalse(has_been_submitted(history, failed_job))
        self.assertEqual(
            get_today_submitted_count(
                history,
                self.today.date().isoformat(),
            ),
            1,
        )

    def test_failed_attempts_do_not_reduce_remaining_daily_capacity(self):
        history = load_application_log(
            self.tracker_path,
            "student-a",
            "first@example.test",
        )
        for index in range(4):
            record_application(
                history,
                {"url": f"https://jobs.test/confirmed-{index}"},
                submitted=True,
                now=self.today,
            )
        record_application(
            history,
            {"url": "https://jobs.test/unconfirmed"},
            submitted=False,
            now=self.today,
        )

        self.assertEqual(
            get_today_submitted_count(
                history,
                self.today.date().isoformat(),
            ),
            4,
        )


if __name__ == "__main__":
    unittest.main()

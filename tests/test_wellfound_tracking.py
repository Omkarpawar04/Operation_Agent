import tempfile
import unittest
from datetime import date
from pathlib import Path

from automation.wellfound_tracking import (
    empty_application_log,
    get_today_submitted_count,
    get_today_attempt_count,
    record_application_attempt,
    has_been_processed,
    load_application_log,
    save_application_log,
)

from automation.application_limits import has_reached_daily_limit


class WellfoundTrackingTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.tracker_path = Path(self.temp_dir.name) / "tracker.json"
        self.today = date(2026, 10, 16).isoformat()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_students_have_independent_job_and_daily_history(self):
        first = empty_application_log()
        first["jobs"]["wellfound:1"] = {"status": "submitted"}
        first["daily_submissions"][self.today] = ["wellfound:1"]
        second = empty_application_log()
        second["jobs"]["wellfound:2"] = {"status": "submitted"}
        second["daily_submissions"][self.today] = ["wellfound:2"]

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

        self.assertIn("wellfound:1", first_loaded["jobs"])
        self.assertNotIn("wellfound:1", second_loaded["jobs"])
        self.assertEqual(
            get_today_submitted_count(first_loaded, self.today),
            1,
        )
        self.assertEqual(
            get_today_submitted_count(second_loaded, self.today),
            1,
        )

    def test_account_history_and_daily_counts_are_independent(self):
        log = empty_application_log()
        log["jobs"]["wellfound:1"] = {"status": "submitted"}
        log["daily_submissions"][self.today] = ["wellfound:1"]
        save_application_log(
            self.tracker_path,
            "student-a",
            "first@example.test",
            log,
        )

        other_account_log = load_application_log(
            self.tracker_path,
            "student-a",
            "second@example.test",
        )
        self.assertEqual(other_account_log, empty_application_log())
        self.assertEqual(
            get_today_submitted_count(other_account_log, self.today),
            0,
        )

    def test_duplicate_prevention_is_scoped_to_student_and_account(self):
        log = empty_application_log()
        log["jobs"]["wellfound:1"] = {"status": "submitted"}
        save_application_log(
            self.tracker_path,
            "student-a",
            "first@example.test",
            log,
        )

        student_history = load_application_log(
            self.tracker_path,
            "student-a",
            "first@example.test",
        )
        other_student_history = load_application_log(
            self.tracker_path,
            "student-b",
            "first@example.test",
        )
        other_account_history = load_application_log(
            self.tracker_path,
            "student-a",
            "second@example.test",
        )

        terminal_statuses = {"submitted", "rejected"}
        self.assertTrue(
            has_been_processed(
                student_history,
                "wellfound:1",
                terminal_statuses,
            )
        )
        self.assertFalse(
            has_been_processed(
                other_student_history,
                "wellfound:1",
                terminal_statuses,
            )
        )
        self.assertFalse(
            has_been_processed(
                other_account_history,
                "wellfound:1",
                terminal_statuses,
            )
        )

    def test_daily_counts_only_include_submitted_jobs_on_selected_date(self):
        log = empty_application_log()
        log["jobs"] = {
            "wellfound:1": {"status": "submitted"},
            "wellfound:2": {"status": "failed"},
        }
        log["daily_submissions"] = {
            self.today: ["wellfound:1", "wellfound:2"],
            "2026-10-15": ["wellfound:1"],
        }

        self.assertEqual(get_today_submitted_count(log, self.today), 1)
        self.assertEqual(
            get_today_submitted_count(log, "2026-10-15"),
            1,
        )

    def test_five_attempts_persist_and_reach_hard_limit(self):
        log = empty_application_log()

        for index in range(5):
            record_application_attempt(
                log, f"wellfound:attempt-{index}", self.today
            )

        self.assertEqual(get_today_attempt_count(log, self.today), 5)
        self.assertTrue(
            has_reached_daily_limit(get_today_attempt_count(log, self.today))
        )
        self.assertEqual(get_today_submitted_count(log, self.today), 0)

        save_application_log(
            self.tracker_path, "student-a", "first@example.test", log
        )
        loaded = load_application_log(
            self.tracker_path, "student-a", "first@example.test"
        )

        self.assertEqual(get_today_attempt_count(loaded, self.today), 5)
        self.assertTrue(
            has_reached_daily_limit(get_today_attempt_count(loaded, self.today))
        )

    def test_attempt_counts_are_independent_by_student_and_account(self):
        log = empty_application_log()

        for index in range(5):
            record_application_attempt(
                log, f"wellfound:attempt-{index}", self.today
            )

        save_application_log(
            self.tracker_path, "student-a", "first@example.test", log
        )

        same_student = load_application_log(
            self.tracker_path, "student-a", "first@example.test"
        )
        other_student = load_application_log(
            self.tracker_path, "student-b", "first@example.test"
        )
        other_account = load_application_log(
            self.tracker_path, "student-a", "second@example.test"
        )

        self.assertEqual(get_today_attempt_count(same_student, self.today), 5)
        self.assertEqual(get_today_attempt_count(other_student, self.today), 0)
        self.assertEqual(get_today_attempt_count(other_account, self.today), 0)


    def test_five_confirmed_applications_reach_limit_but_failures_do_not_count(self):
        log = empty_application_log()
        log["jobs"] = {
            **{
                f"wellfound:{index}": {"status": "submitted"}
                for index in range(5)
            },
            "wellfound:failed": {"status": "failed"},
        }
        log["daily_submissions"][self.today] = [
            *(f"wellfound:{index}" for index in range(5)),
            "wellfound:failed",
        ]

        self.assertEqual(get_today_submitted_count(log, self.today), 5)


if __name__ == "__main__":
    unittest.main()

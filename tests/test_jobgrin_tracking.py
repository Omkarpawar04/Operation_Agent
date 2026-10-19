import tempfile
import unittest
from pathlib import Path

from automation.excel_users import get_student_id
from automation.jobgrin_tracking import (
    applications_today,
    has_processed_job,
    load_student_history,
    save_student_history,
    submission_confirmation_detected,
)


class JobGrinTrackingTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.tracker_path = Path(self.temp_dir.name) / "tracker.json"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_student_histories_and_daily_limits_are_independent(self):
        first_history = {
            f"job-{index}": {
                "status": "APPLIED",
                "timestamp": f"2026-10-16T09:{index:02d}:00",
            }
            for index in range(5)
        }
        second_history = {
            "job-other-student": {
                "status": "APPLIED",
                "timestamp": "2026-10-16T10:00:00",
            }
        }

        save_student_history(
            self.tracker_path,
            "student-a",
            "first@example.test",
            first_history,
        )
        save_student_history(
            self.tracker_path,
            "student-b",
            "first@example.test",
            second_history,
        )

        loaded_first = load_student_history(
            self.tracker_path,
            "student-a",
            "first@example.test",
        )
        loaded_second = load_student_history(
            self.tracker_path,
            "student-b",
            "first@example.test",
        )

        self.assertEqual(loaded_first, first_history)
        self.assertEqual(loaded_second, second_history)
        self.assertTrue(has_processed_job("job-0", loaded_first))
        self.assertFalse(has_processed_job("job-0", loaded_second))
        first_daily_count = applications_today(
            loaded_first,
            "2026-10-16",
        )
        second_daily_count = applications_today(
            loaded_second,
            "2026-10-16",
        )
        self.assertEqual(first_daily_count, 5)
        self.assertEqual(second_daily_count, 1)
        self.assertGreaterEqual(first_daily_count, 5)
        self.assertLess(second_daily_count, 5)

    def test_failed_and_unconfirmed_jobs_do_not_count_toward_limit(self):
        history = {
            "confirmed": {
                "status": "APPLIED",
                "timestamp": "2026-10-16T09:00:00",
            },
            "failed": {
                "status": "FAILED",
                "timestamp": "2026-10-16T09:15:00",
            },
            "external": {
                "status": "EXTERNAL",
                "timestamp": "2026-10-16T09:30:00",
            },
        }

        self.assertEqual(
            applications_today(history, "2026-10-16"),
            1,
        )

    def test_existing_application_is_duplicate_not_new_daily_success(self):
        history = {
            "previously-applied": {
                "status": "ALREADY_APPLIED",
                "timestamp": "2026-10-16T09:00:00",
            },
            "legacy-already-applied": {
                "status": "APPLIED",
                "reason": "ALREADY_APPLIED",
                "timestamp": "2026-10-16T09:15:00",
            },
        }

        self.assertTrue(
            has_processed_job("previously-applied", history)
        )
        self.assertTrue(
            has_processed_job("legacy-already-applied", history)
        )
        self.assertEqual(
            applications_today(history, "2026-10-16"),
            0,
        )

    def test_submission_confirmation_excludes_already_applied_message(self):
        self.assertTrue(
            submission_confirmation_detected(
                "Your application has been submitted successfully."
            )
        )
        self.assertFalse(
            submission_confirmation_detected(
                "You have already applied for this job."
            )
        )
        self.assertFalse(
            submission_confirmation_detected(
                "Apply button clicked; application form opened."
            )
        )

    def test_portal_accounts_are_independent_for_one_student(self):
        history = {
            "job-1": {
                "status": "APPLIED",
                "timestamp": "2026-10-16T09:00:00",
            }
        }
        save_student_history(
            self.tracker_path,
            "student-a",
            "first@example.test",
            history,
        )

        self.assertEqual(
            applications_today(
                load_student_history(
                    self.tracker_path,
                    "student-a",
                    "first@example.test",
                ),
                "2026-10-16",
            ),
            1,
        )
        self.assertEqual(
            applications_today(
                load_student_history(
                    self.tracker_path,
                    "student-a",
                    "second@example.test",
                ),
                "2026-10-16",
            ),
            0,
        )

    def test_account_identity_is_case_insensitive(self):
        history = {"job-1": {"status": "EXTERNAL"}}
        save_student_history(
            self.tracker_path,
            "Student-A",
            "Applicant@Example.Test",
            history,
        )

        self.assertEqual(
            load_student_history(
                self.tracker_path,
                "student-a",
                "applicant@example.test",
            ),
            history,
        )

    def test_student_id_is_required(self):
        self.assertEqual(
            get_student_id({"student_id": " student-a "}),
            "student-a",
        )

        with self.assertRaisesRegex(ValueError, "student_id"):
            get_student_id({"student_id": ""})

        with self.assertRaisesRegex(ValueError, "student_id"):
            get_student_id({"student_id": None})


if __name__ == "__main__":
    unittest.main()

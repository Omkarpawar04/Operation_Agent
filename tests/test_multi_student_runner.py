import asyncio
import unittest
from pathlib import Path
from unittest.mock import patch

from automation.excel_users import (
    get_user,
    select_student,
    select_valid_students,
)
import main as runner
from main import (
    PortalResult,
    portal_account_identifier,
    process_student_queue,
    run_all_portals,
    student_profile_path,
)


class MultiStudentRunnerTests(unittest.TestCase):
    def test_student_selection_preserves_order_and_skips_invalid_rows(self):
        rows = [
            {"student_id": "student-b", "name": "B"},
            {"student_id": "", "name": "missing ID"},
            {"student_id": "student-a", "name": "A"},
            {"student_id": "", "name": ""},
        ]

        selected = select_valid_students(rows)

        self.assertEqual(
            [row["student_id"] for row in selected],
            ["student-b", "student-a"],
        )

    def test_duplicate_student_ids_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "Duplicate student_id"):
            select_valid_students(
                [
                    {"student_id": "student-a"},
                    {"student_id": "STUDENT-A"},
                ]
            )

    def test_selected_student_controls_account_row(self):
        users = [
            {"student_id": "student-a", "iimjobs_email": "a@example.test"},
            {"student_id": "student-b", "iimjobs_email": "b@example.test"},
        ]

        self.assertEqual(
            select_student(users, "student-b")["iimjobs_email"],
            "b@example.test",
        )
        with patch("automation.excel_users.load_users", return_value=users):
            with patch.dict(
                "os.environ",
                {"JOB_AUTOMATION_STUDENT_ID": "student-b"},
            ):
                self.assertEqual(get_user(0), users[1])

    def test_student_portal_browser_profiles_are_isolated(self):
        student_a = student_profile_path("student-a", "IIMJobs")
        student_b = student_profile_path("student-b", "IIMJobs")
        different_portal = student_profile_path("student-a", "JobGrin")
        different_account = student_profile_path(
            "student-a",
            "IIMJobs",
            "different@example.test",
        )

        self.assertNotEqual(student_a, student_b)
        self.assertNotEqual(student_a, different_portal)
        self.assertNotEqual(student_a, different_account)
        self.assertEqual(
            student_a,
            student_profile_path("STUDENT-A", "iimjobs"),
        )

    def test_portal_account_identity_comes_from_selected_student(self):
        student = {
            "student_id": "student-b",
            "iimjobs_email": "student-b@example.test",
            "email": "fallback@example.test",
        }

        self.assertEqual(
            portal_account_identifier(student, "IIMJobs"),
            "student-b@example.test",
        )
        self.assertEqual(
            portal_account_identifier(student, "PlacementIndia"),
            "fallback@example.test",
        )

    def test_queue_runs_students_and_portals_in_order_after_failure(self):
        students = [
            {"student_id": "student-a"},
            {"student_id": "student-b"},
        ]
        events = []

        async def process_student(student):
            student_id = student["student_id"]
            events.append((student_id, "IIMJobs"))
            if student_id == "student-a":
                events.append(("IIMJobs", "failed"))
            events.append((student_id, "JobGrin"))
            return [(student_id, "result")]

        results = asyncio.run(
            process_student_queue(students, process_student)
        )

        self.assertEqual(
            events,
            [
                ("student-a", "IIMJobs"),
                ("IIMJobs", "failed"),
                ("student-a", "JobGrin"),
                ("student-b", "IIMJobs"),
                ("student-b", "JobGrin"),
            ],
        )
        self.assertEqual(
            results,
            [("student-a", "result"), ("student-b", "result")],
        )

    def test_portal_exception_does_not_stop_remaining_portals(self):
        available = [
            ("IIMJobs", "iimjobs.py", Path("iimjobs.py")),
            ("JobGrin", "jobgrin.py", Path("jobgrin.py")),
        ]
        student = {
            "student_id": "student-a",
            "iimjobs_email": "iim@example.test",
            "jobgrin_email": "jobgrin@example.test",
        }
        calls = []

        async def fake_run_portal(**kwargs):
            calls.append(kwargs["portal_name"])
            if kwargs["portal_name"] == "IIMJobs":
                raise RuntimeError("test portal failure")
            return PortalResult(
                student_id=kwargs["student_id"],
                portal=kwargs["portal_name"],
                script=kwargs["script_name"],
                status="FINISHED",
                exit_code=0,
                duration=0.0,
                log_path=kwargs["log_path"],
            )

        with patch.object(runner, "run_portal", side_effect=fake_run_portal):
            results = asyncio.run(
                run_all_portals(available, student)
            )

        self.assertEqual(calls, ["IIMJobs", "JobGrin"])
        self.assertIsNone(results[0].exit_code)
        self.assertEqual(results[1].exit_code, 0)


if __name__ == "__main__":
    unittest.main()

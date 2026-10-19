import unittest
import tempfile
from datetime import date, datetime
from pathlib import Path

from automation.application_limits import (
    DAILY_APPLICATION_LIMIT,
    has_reached_daily_limit,
)
from automation.iimjobs_tracking import (
    get_today_submitted_count as get_iimjobs_count,
    load_application_log as load_iimjobs_log,
    record_application as record_iimjobs_application,
    save_application_log as save_iimjobs_log,
)
from automation.jobgrin_tracking import (
    applications_today as get_jobgrin_count,
    load_student_history as load_jobgrin_history,
    save_student_history as save_jobgrin_history,
)
from automation.placementindia_tracking import (
    get_today_application_count as get_placementindia_count,
    load_application_history as load_placementindia_history,
    save_application_history as save_placementindia_history,
)
from automation.wellfound_tracking import (
    empty_application_log as empty_wellfound_log,
    get_today_submitted_count as get_wellfound_count,
    load_application_log as load_wellfound_log,
    save_application_log as save_wellfound_log,
)


class ApplicationLimitTests(unittest.TestCase):
    def test_limit_is_five_confirmed_applications(self):
        self.assertEqual(DAILY_APPLICATION_LIMIT, 5)
        self.assertFalse(has_reached_daily_limit(4))
        self.assertTrue(has_reached_daily_limit(5))
        self.assertTrue(has_reached_daily_limit(6))

    def test_reaching_one_portals_limit_does_not_stop_other_portals(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tracker_dir = Path(temp_dir)
            today = date(2026, 10, 16)
            now = datetime(2026, 10, 16, 9, 0)
            student_id = "student-a"
            account_id = "account@example.test"

            iimjobs_path = tracker_dir / "iimjobs.json"
            iimjobs_log = load_iimjobs_log(
                iimjobs_path,
                student_id,
                account_id,
            )
            for index in range(DAILY_APPLICATION_LIMIT):
                record_iimjobs_application(
                    iimjobs_log,
                    {"url": f"https://iimjobs.test/{index}"},
                    submitted=True,
                    now=now,
                )
            save_iimjobs_log(
                iimjobs_path,
                student_id,
                account_id,
                iimjobs_log,
            )

            jobgrin_path = tracker_dir / "jobgrin.json"
            save_jobgrin_history(
                jobgrin_path,
                student_id,
                account_id,
                {},
            )
            placementindia_path = tracker_dir / "placementindia.json"
            save_placementindia_history(
                placementindia_path,
                student_id,
                account_id,
                {},
            )
            wellfound_path = tracker_dir / "wellfound.json"
            save_wellfound_log(
                wellfound_path,
                student_id,
                account_id,
                empty_wellfound_log(),
            )

            counts = {
                "IIMJobs": get_iimjobs_count(
                    load_iimjobs_log(
                        iimjobs_path,
                        student_id,
                        account_id,
                    ),
                    today.isoformat(),
                ),
                "JobGrin": get_jobgrin_count(
                    load_jobgrin_history(
                        jobgrin_path,
                        student_id,
                        account_id,
                    ),
                    today.isoformat(),
                ),
                "PlacementIndia": get_placementindia_count(
                    load_placementindia_history(
                        placementindia_path,
                        student_id,
                        account_id,
                    ),
                    today,
                ),
                "Wellfound": get_wellfound_count(
                    load_wellfound_log(
                        wellfound_path,
                        student_id,
                        account_id,
                    ),
                    today.isoformat(),
                ),
            }

            self.assertTrue(
                has_reached_daily_limit(counts["IIMJobs"])
            )
            for portal in ("JobGrin", "PlacementIndia", "Wellfound"):
                self.assertFalse(
                    has_reached_daily_limit(counts[portal]),
                    portal,
                )


if __name__ == "__main__":
    unittest.main()

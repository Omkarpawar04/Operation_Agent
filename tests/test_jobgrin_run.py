import unittest
from datetime import date

from automation.jobgrin_run import (
    MAX_JOBS_PER_RUN,
    JobGrinRunState,
)
from automation.jobgrin_tracking import applications_today


class JobGrinRunTests(unittest.TestCase):
    def test_stops_after_five_distinct_attempts(self):
        state = JobGrinRunState()

        for index in range(MAX_JOBS_PER_RUN):
            self.assertTrue(state.begin_attempt(f"job-{index}"))

        self.assertEqual(state.jobs_attempted, 5)
        self.assertTrue(state.has_reached_limit())
        self.assertFalse(state.begin_attempt("job-six"))
        self.assertEqual(len(state.attempted_job_keys), 5)
        self.assertEqual(
            state.termination_reason,
            "per-run job attempt limit reached (5/5)",
        )
        self.assertTrue(state.stop_if_limited(1))
        self.assertEqual(state.jobs_attempted, 5)

    def test_fewer_available_jobs_stop_when_search_is_exhausted(self):
        state = JobGrinRunState()

        for job_key in ("job-a", "job-b", "job-c"):
            self.assertTrue(state.begin_attempt(job_key))

        state.stop("no more JobGrin search pages available")

        self.assertEqual(state.jobs_attempted, 3)
        self.assertFalse(state.has_reached_limit())
        self.assertEqual(
            state.termination_reason,
            "no more JobGrin search pages available",
        )

    def test_failed_attempt_counts_for_run_but_not_daily_successes(self):
        state = JobGrinRunState()
        history = {
            "failed-job": {
                "status": "FAILED",
                "timestamp": f"{date.today().isoformat()}T10:00:00",
            }
        }

        self.assertTrue(state.begin_attempt("failed-job"))
        self.assertEqual(state.jobs_attempted, 1)
        self.assertEqual(applications_today(history), 0)

    def test_daily_confirmed_limit_blocks_more_attempts(self):
        state = JobGrinRunState()
        confirmed_today = 5

        self.assertFalse(
            state.begin_attempt(
                "job-a",
                confirmed_applications_today=confirmed_today,
            )
        )
        self.assertEqual(state.jobs_attempted, 0)
        self.assertEqual(
            state.termination_reason,
            "daily confirmed application limit reached (5/5)",
        )

    def test_one_existing_daily_submission_allows_only_four_more_successes(self):
        state = JobGrinRunState()
        confirmed_today = 1
        successful_additions = 0

        for index in range(4):
            self.assertTrue(
                state.begin_attempt(
                    f"job-{index}",
                    confirmed_applications_today=confirmed_today,
                )
            )
            successful_additions += 1
            confirmed_today += 1

        self.assertEqual(successful_additions, 4)
        self.assertEqual(confirmed_today, 5)
        self.assertFalse(
            state.begin_attempt(
                "job-six",
                confirmed_applications_today=confirmed_today,
            )
        )
        self.assertEqual(state.jobs_attempted, 4)
        self.assertEqual(
            state.termination_reason,
            "daily confirmed application limit reached (5/5)",
        )

    def test_same_job_cannot_be_attempted_twice_in_one_run(self):
        state = JobGrinRunState()

        self.assertTrue(state.begin_attempt("same-job"))
        self.assertFalse(state.begin_attempt("same-job"))
        self.assertEqual(state.jobs_attempted, 1)


if __name__ == "__main__":
    unittest.main()

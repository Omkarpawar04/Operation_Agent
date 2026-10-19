from dataclasses import dataclass, field

if __package__:
    from .application_limits import (
        DAILY_APPLICATION_LIMIT,
        has_reached_daily_limit,
    )
else:
    from application_limits import (
        DAILY_APPLICATION_LIMIT,
        has_reached_daily_limit,
    )


MAX_JOBS_PER_RUN = 5


@dataclass
class JobGrinRunState:
    jobs_attempted: int = 0
    attempted_job_keys: set[str] = field(default_factory=set)
    termination_reason: str = ""

    def has_attempted(self, job_key):
        return job_key in self.attempted_job_keys

    def has_reached_limit(self):
        return self.jobs_attempted >= MAX_JOBS_PER_RUN

    def stop_if_limited(self, confirmed_applications_today):
        if has_reached_daily_limit(confirmed_applications_today):
            self.stop(
                "daily confirmed application limit reached "
                f"({confirmed_applications_today}/"
                f"{DAILY_APPLICATION_LIMIT})"
            )
            return True

        if self.has_reached_limit():
            self.stop(
                f"per-run job attempt limit reached "
                f"({self.jobs_attempted}/{MAX_JOBS_PER_RUN})"
            )
            return True

        return False

    def begin_attempt(self, job_key, confirmed_applications_today=0):
        if self.stop_if_limited(confirmed_applications_today):
            return False

        if self.has_attempted(job_key):
            return False

        self.attempted_job_keys.add(job_key)
        self.jobs_attempted += 1
        if self.has_reached_limit():
            self.termination_reason = (
                f"per-run job attempt limit reached "
                f"({self.jobs_attempted}/{MAX_JOBS_PER_RUN})"
            )
        return True

    def stop(self, reason):
        if not self.termination_reason:
            self.termination_reason = reason

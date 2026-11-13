from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from uuid import UUID, uuid4


class AttemptState(StrEnum):
    IN_PROGRESS = "in_progress"
    PASSED = "passed"
    FAILED = "failed"


@dataclass(slots=True)
class AssessmentAttempt:
    student_id: UUID
    stage: str
    idempotency_key: str
    course_id: UUID | None = None
    id: UUID = field(default_factory=uuid4)
    state: AttemptState = AttemptState.IN_PROGRESS

    def finish(self, passed: bool) -> None:
        if self.state is not AttemptState.IN_PROGRESS:
            raise ValueError("Completed assessment attempts are immutable")
        self.state = AttemptState.PASSED if passed else AttemptState.FAILED

    def infrastructure_failure(self) -> None:
        # Infrastructure failure leaves the assessment attempt active/retryable.
        if self.state is not AttemptState.IN_PROGRESS:
            raise ValueError("Only an in-progress attempt can be retried")


@dataclass(frozen=True, slots=True)
class RetakePolicy:
    """Configurable cap/cooldown; None means no configured cap."""

    max_attempts: int | None = None
    cooldown: timedelta = timedelta(0)

    def __post_init__(self) -> None:
        if self.max_attempts is not None and self.max_attempts < 1:
            raise ValueError("Maximum attempts must be positive")
        if self.cooldown < timedelta(0):
            raise ValueError("Retake cooldown cannot be negative")

    def allows_start(
        self,
        completed_attempt_count: int,
        last_completed_at: datetime | None,
        now: datetime | None = None,
    ) -> bool:
        if completed_attempt_count < 0:
            raise ValueError("Completed attempt count cannot be negative")
        if self.max_attempts is not None and completed_attempt_count >= self.max_attempts:
            return False
        if last_completed_at is None or not self.cooldown:
            return True
        current = now or datetime.now(UTC)
        if last_completed_at.tzinfo is None:
            last_completed_at = last_completed_at.replace(tzinfo=UTC)
        return current >= last_completed_at + self.cooldown

from dataclasses import dataclass
from enum import StrEnum

from app.domain.interviews.models import InterviewStage


class ProgressionStatus(StrEnum):
    LOCKED = "locked"
    AVAILABLE = "available"
    IN_PROGRESS = "in_progress"
    PASSED = "passed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class StageOutcome:
    stage: InterviewStage
    passed: bool
    course_id: str | None = None


def available_stage(
    outcomes: tuple[StageOutcome, ...], course_id: str | None = None
) -> InterviewStage:
    passed = {
        outcome.stage
        for outcome in outcomes
        if outcome.passed and (not outcome.stage.technical or outcome.course_id == course_id)
    }
    for stage in InterviewStage:
        if stage not in passed:
            return stage
    raise ValueError("all_stages_complete")

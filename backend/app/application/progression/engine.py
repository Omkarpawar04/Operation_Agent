from app.domain.interviews.models import InterviewStage
from app.domain.progression.models import StageOutcome, available_stage


class ProgressionEngine:
    def next_stage(
        self, outcomes: tuple[StageOutcome, ...], course_id: str | None = None
    ) -> InterviewStage:
        return available_stage(outcomes, course_id)

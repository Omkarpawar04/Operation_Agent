from dataclasses import dataclass
from enum import StrEnum

from app.domain.interviews.models import InterviewSession, InterviewState


class InterviewAction(StrEnum):
    FOLLOW_UP = "follow_up"
    CLARIFICATION = "clarification"
    NEXT_QUESTION = "next_question"
    COMPLETE = "complete"


@dataclass(frozen=True, slots=True)
class DecisionLimits:
    max_base_questions: int = 5
    max_follow_ups_per_question: int = 2
    max_clarifications_per_question: int = 1

    def __post_init__(self) -> None:
        if (
            self.max_base_questions < 1
            or self.max_follow_ups_per_question < 0
            or self.max_clarifications_per_question < 0
        ):
            raise ValueError("Question limits are invalid")


@dataclass(frozen=True, slots=True)
class AnalysisRecommendation:
    follow_up_text: str | None = None
    clarification_text: str | None = None
    answer_needs_clarification: bool = False


def decide(
    session: InterviewSession, limits: DecisionLimits, recommendation: AnalysisRecommendation
) -> InterviewAction:
    if session.state is not InterviewState.ANSWER_PROCESSING:
        raise ValueError("decision_requires_answer_processing")
    if (
        recommendation.answer_needs_clarification
        and recommendation.clarification_text
        and session.clarification_count < limits.max_clarifications_per_question
    ):
        return InterviewAction.CLARIFICATION
    if (
        recommendation.follow_up_text
        and session.follow_up_count < limits.max_follow_ups_per_question
    ):
        return InterviewAction.FOLLOW_UP
    return (
        InterviewAction.NEXT_QUESTION
        if session.base_question_count < limits.max_base_questions
        else InterviewAction.COMPLETE
    )

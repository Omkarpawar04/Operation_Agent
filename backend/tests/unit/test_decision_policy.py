from uuid import uuid4

import pytest

from app.domain.interviews.decision import (
    AnalysisRecommendation,
    DecisionLimits,
    InterviewAction,
    decide,
)
from app.domain.interviews.models import InterviewSession, InterviewStage, InterviewState


def processing_session(**kwargs) -> InterviewSession:
    result = InterviewSession(student_id=uuid4(), stage=InterviewStage.SOFT_1, **kwargs)
    result.state = InterviewState.ANSWER_PROCESSING
    return result


def test_follow_up_only_when_recommended_and_under_limit() -> None:
    subject = processing_session(base_question_count=1)
    assert (
        decide(subject, DecisionLimits(), AnalysisRecommendation(follow_up_text="Why?"))
        is InterviewAction.FOLLOW_UP
    )
    subject.follow_up_count = 2
    assert (
        decide(subject, DecisionLimits(), AnalysisRecommendation(follow_up_text="Why?"))
        is InterviewAction.NEXT_QUESTION
    )


def test_clarification_precedes_follow_up_within_limit() -> None:
    subject = processing_session(base_question_count=1)
    recommendation = AnalysisRecommendation(
        follow_up_text="Explain",
        clarification_text="Please clarify",
        answer_needs_clarification=True,
    )
    assert decide(subject, DecisionLimits(), recommendation) is InterviewAction.CLARIFICATION
    subject.clarification_count = 1
    assert decide(subject, DecisionLimits(), recommendation) is InterviewAction.FOLLOW_UP


def test_question_budget_completes_deterministically() -> None:
    subject = processing_session(base_question_count=5)
    assert (
        decide(
            subject,
            DecisionLimits(max_base_questions=5),
            AnalysisRecommendation(),
        )
        is InterviewAction.COMPLETE
    )


def test_last_base_question_can_still_receive_allowed_follow_up() -> None:
    subject = processing_session(base_question_count=5)
    action = decide(
        subject,
        DecisionLimits(max_base_questions=5),
        AnalysisRecommendation(follow_up_text="Explain your example"),
    )
    assert action is InterviewAction.FOLLOW_UP


def test_invalid_limits_rejected() -> None:
    with pytest.raises(ValueError):
        DecisionLimits(max_base_questions=0)


def test_decision_requires_processing_session_state() -> None:
    subject = InterviewSession(student_id=uuid4(), stage=InterviewStage.SOFT_1)
    with pytest.raises(ValueError, match="answer_processing"):
        decide(subject, DecisionLimits(), AnalysisRecommendation())

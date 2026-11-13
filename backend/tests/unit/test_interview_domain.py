from uuid import uuid4

import pytest

from app.domain.interviews.models import (
    ALLOWED_TRANSITIONS,
    InterviewSession,
    InterviewStage,
    InterviewState,
    transition,
)


def session() -> InterviewSession:
    return InterviewSession(student_id=uuid4(), stage=InterviewStage.SOFT_1)


@pytest.mark.parametrize(
    "start,target",
    [
        (InterviewState.CREATED, InterviewState.AWAITING_ANSWER),
        (InterviewState.AWAITING_ANSWER, InterviewState.ANSWER_PROCESSING),
        (InterviewState.ANSWER_PROCESSING, InterviewState.AWAITING_FOLLOW_UP_ANSWER),
        (InterviewState.ANSWER_PROCESSING, InterviewState.AWAITING_ANSWER),
        (InterviewState.ANSWER_PROCESSING, InterviewState.COMPLETED),
        (InterviewState.AWAITING_FOLLOW_UP_ANSWER, InterviewState.ANSWER_PROCESSING),
        (InterviewState.CREATED, InterviewState.ABANDONED),
        (InterviewState.AWAITING_ANSWER, InterviewState.FAILED),
    ],
)
def test_legal_transitions(start: InterviewState, target: InterviewState) -> None:
    aggregate = session()
    aggregate.state = start
    transition(aggregate, target, 0)
    assert aggregate.state is target
    assert aggregate.version == 1


@pytest.mark.parametrize(
    "start,target",
    [
        (InterviewState.CREATED, InterviewState.COMPLETED),
        (InterviewState.COMPLETED, InterviewState.AWAITING_ANSWER),
        (InterviewState.ABANDONED, InterviewState.ANSWER_PROCESSING),
        (InterviewState.AWAITING_ANSWER, InterviewState.AWAITING_FOLLOW_UP_ANSWER),
    ],
)
def test_illegal_transitions(start: InterviewState, target: InterviewState) -> None:
    aggregate = session()
    aggregate.state = start
    with pytest.raises(ValueError, match="illegal_transition"):
        transition(aggregate, target, 0)


def test_stale_version_conflicts() -> None:
    with pytest.raises(ValueError, match="stale_version"):
        transition(session(), InterviewState.AWAITING_ANSWER, 2)


def test_entire_transition_table_accepts_only_declared_edges() -> None:
    for source, targets in ALLOWED_TRANSITIONS.items():
        for target in InterviewState:
            aggregate = session()
            aggregate.state = source
            if target in targets:
                transition(aggregate, target, 0)
                assert aggregate.state is target
            else:
                with pytest.raises(ValueError, match="illegal_transition"):
                    transition(aggregate, target, 0)


def test_technical_requires_pinned_course_revision() -> None:
    with pytest.raises(ValueError, match="course and pinned"):
        InterviewSession(student_id=uuid4(), stage=InterviewStage.TECHNICAL_1)

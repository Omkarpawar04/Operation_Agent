from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

if TYPE_CHECKING:
    from app.domain.assessments.content import QuestionProvenance


class InterviewState(StrEnum):
    CREATED = "created"
    AWAITING_ANSWER = "awaiting_answer"
    ANSWER_PROCESSING = "answer_processing"
    AWAITING_FOLLOW_UP_ANSWER = "awaiting_follow_up_answer"
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    FAILED = "failed"


class InterviewStage(StrEnum):
    SOFT_1 = "soft_1"
    SOFT_2 = "soft_2"
    SOFT_3 = "soft_3"
    TECHNICAL_1 = "technical_1"
    TECHNICAL_2 = "technical_2"
    TECHNICAL_3 = "technical_3"

    @property
    def order(self) -> int:
        return list(InterviewStage).index(self)

    @property
    def technical(self) -> bool:
        return self.value.startswith("technical")


class QuestionKind(StrEnum):
    BASE = "base"
    FOLLOW_UP = "follow_up"
    CLARIFICATION = "clarification"


@dataclass(slots=True)
class InterviewSession:
    student_id: UUID
    stage: InterviewStage
    course_id: UUID | None = None
    content_revision_id: UUID | None = None
    id: UUID = field(default_factory=uuid4)
    state: InterviewState = InterviewState.CREATED
    version: int = 0
    base_question_count: int = 0
    follow_up_count: int = 0
    clarification_count: int = 0
    active_question_id: UUID | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.stage.technical and (self.course_id is None or self.content_revision_id is None):
            raise ValueError("Technical interviews require a course and pinned content revision")
        if not self.stage.technical and self.content_revision_id is not None:
            raise ValueError("Soft-skills interviews cannot pin technical course content")
        if (
            self.version < 0
            or min(self.base_question_count, self.follow_up_count, self.clarification_count) < 0
        ):
            raise ValueError("Session versions and question counts cannot be negative")


@dataclass(frozen=True, slots=True)
class Question:
    session_id: UUID
    text: str
    sequence: int
    kind: QuestionKind = QuestionKind.BASE
    id: UUID = field(default_factory=uuid4)
    parent_question_id: UUID | None = None
    provenance: QuestionProvenance | None = None

    def __post_init__(self) -> None:
        if not self.text.strip() or self.sequence < 1:
            raise ValueError("Question text and positive sequence are required")
        if self.kind is not QuestionKind.BASE and self.parent_question_id is None:
            raise ValueError("Follow-up and clarification questions require a parent")


@dataclass(frozen=True, slots=True)
class Answer:
    session_id: UUID
    question_id: UUID
    text: str
    idempotency_key: str
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.text.strip() or not self.idempotency_key.strip():
            raise ValueError("Answer text and idempotency key are required")


ALLOWED_TRANSITIONS: dict[InterviewState, frozenset[InterviewState]] = {
    InterviewState.CREATED: frozenset(
        {InterviewState.AWAITING_ANSWER, InterviewState.ABANDONED, InterviewState.FAILED}
    ),
    InterviewState.AWAITING_ANSWER: frozenset(
        {InterviewState.ANSWER_PROCESSING, InterviewState.ABANDONED, InterviewState.FAILED}
    ),
    InterviewState.ANSWER_PROCESSING: frozenset(
        {
            InterviewState.AWAITING_FOLLOW_UP_ANSWER,
            InterviewState.AWAITING_ANSWER,
            InterviewState.COMPLETED,
            InterviewState.FAILED,
        }
    ),
    InterviewState.AWAITING_FOLLOW_UP_ANSWER: frozenset(
        {InterviewState.ANSWER_PROCESSING, InterviewState.ABANDONED, InterviewState.FAILED}
    ),
    InterviewState.COMPLETED: frozenset(),
    InterviewState.ABANDONED: frozenset(),
    InterviewState.FAILED: frozenset(),
}


def transition(session: InterviewSession, target: InterviewState, expected_version: int) -> None:
    if session.version != expected_version:
        raise ValueError("stale_version")
    if target not in ALLOWED_TRANSITIONS[session.state]:
        raise ValueError(f"illegal_transition:{session.state}:{target}")
    session.state = target
    session.version += 1
    if target in {InterviewState.COMPLETED, InterviewState.ABANDONED, InterviewState.FAILED}:
        session.completed_at = datetime.now(UTC)

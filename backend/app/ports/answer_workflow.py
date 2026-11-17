from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from app.domain.assessments.content import QuestionProvenance
from app.domain.assessments.models import AssessmentResult, EvaluationEvidence
from app.domain.interviews.decision import InterviewAction
from app.domain.interviews.models import InterviewSession, Question


@dataclass(frozen=True, slots=True)
class AnswerCommand:
    session_id: UUID
    student_id: UUID
    question_id: UUID
    expected_version: int
    idempotency_key: str
    text: str
    is_skip: bool = False


@dataclass(frozen=True, slots=True)
class AnswerReservation:
    session: InterviewSession
    previous_state: str
    processing_version: int
    lease_seconds: int
    active_question: Question
    attempt_id: UUID
    course_metadata: dict[str, object]
    prior_answers: tuple[str, ...]
    previous_questions: tuple[str, ...]
    previous_evidence: tuple[EvaluationEvidence, ...]
    follow_up_index: int
    original_question_text: str | None = None
    previous_follow_up_questions: tuple[str, ...] = ()
    root_question_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class AnswerReplay:
    state: str
    version: int
    question_text: str | None


@dataclass(frozen=True, slots=True)
class AnswerCompletion:
    state: str
    version: int
    action: InterviewAction | None
    question_text: str | None
    score: Decimal | None = None


class AnswerWorkflowPort(Protocol):
    """Owns short reservation/release/finalization transactions for an answer command."""

    def reserve(
        self, command: AnswerCommand, lease_seconds: int
    ) -> AnswerReservation | AnswerReplay: ...

    def release(self, reservation: AnswerReservation) -> None: ...

    def complete(
        self,
        command: AnswerCommand,
        reservation: AnswerReservation,
        evidence: tuple[EvaluationEvidence, ...],
        rubric_version: str,
        action: InterviewAction,
        next_question_text: str | None,
        result: AssessmentResult | None,
        next_question_provenance: QuestionProvenance | None = None,
    ) -> AnswerCompletion: ...

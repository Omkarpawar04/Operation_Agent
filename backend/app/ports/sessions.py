from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.domain.assessments.content import QuestionProvenance
from app.domain.interviews.models import InterviewStage


@dataclass(frozen=True, slots=True)
class StartSessionCommand:
    student_id: UUID
    stage: InterviewStage
    idempotency_key: str
    course_id: UUID | None
    initial_question_text: str | None = None
    expected_content_revision_id: UUID | None = None
    initial_question_provenance: QuestionProvenance | None = None


@dataclass(frozen=True, slots=True)
class SessionRecord:
    id: UUID
    stage: str
    state: str
    version: int
    active_question_id: UUID | None
    course_id: UUID | None


class SessionStartPort(Protocol):
    """Atomic persistence operations required to create or resume a session."""

    def find_existing(self, student_id: UUID, key: str) -> SessionRecord | None: ...

    def enrolled(self, student_id: UUID, course_id: UUID) -> bool: ...

    def approved_revision(self, course_id: UUID) -> UUID | None: ...

    def stage_passed(
        self, student_id: UUID, stage: InterviewStage, course_id: UUID | None
    ) -> bool: ...

    def completed_attempt_history(
        self, student_id: UUID, stage: InterviewStage, course_id: UUID | None
    ) -> tuple[int, datetime | None]: ...

    def create(
        self,
        command: StartSessionCommand,
        revision_id: UUID | None,
        revalidate: Callable[[], UUID | None],
    ) -> SessionRecord: ...

    def rollback_read_transaction(self) -> None: ...

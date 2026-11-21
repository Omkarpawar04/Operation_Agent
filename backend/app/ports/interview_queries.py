from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from app.domain.assessments.content import QuestionProvenance
from app.domain.interviews.models import InterviewStage, InterviewState


@dataclass(frozen=True, slots=True)
class SessionView:
    id: UUID
    stage: InterviewStage
    state: InterviewState
    version: int
    active_question_id: UUID | None


@dataclass(frozen=True, slots=True)
class QuestionView:
    id: UUID
    text: str
    kind: str
    sequence: int
    session_version: int
    provenance: QuestionProvenance | None = None


@dataclass(frozen=True, slots=True)
class AssessmentCompetencyFeedback:
    competency_id: str
    title: str
    strengths: tuple[str, ...]
    areas_for_improvement: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AssessmentView:
    attempt_id: UUID
    score: str
    passed: bool
    rubric_version: str
    competency_feedback: tuple[AssessmentCompetencyFeedback, ...] = ()


@dataclass(frozen=True, slots=True)
class ProgressionRecords:
    passed: frozenset[tuple[str, str]]
    active: frozenset[tuple[str, str]]


class InterviewQueryPort(Protocol):
    """Owned interview reads and versioned abandonment persistence."""

    def get_owned(self, session_id: UUID, student_id: UUID) -> SessionView | None: ...

    def get_active_question(self, session_id: UUID, student_id: UUID) -> QuestionView | None: ...

    def get_assessment(self, session_id: UUID, student_id: UUID) -> AssessmentView | None: ...

    def get_active_session(self, student_id: UUID) -> SessionView | None: ...

    def abandon(
        self, session_id: UUID, student_id: UUID, expected_version: int
    ) -> SessionView | None: ...


class ProgressionQueryPort(Protocol):
    def is_enrolled(self, student_id: UUID, course_id: UUID) -> bool: ...

    def records(self, student_id: UUID) -> ProgressionRecords: ...


class UserQueryPort(Protocol):
    def get_or_create_user(self, user_id: UUID) -> tuple[UUID, str]: ...


@dataclass(frozen=True, slots=True)
class ApprovedCourseConfiguration:
    revision_id: UUID
    metadata: dict[str, object]


class CourseContentPort(Protocol):
    def approved_configuration(self, course_id: UUID) -> ApprovedCourseConfiguration | None: ...

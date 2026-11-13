from dataclasses import dataclass
from uuid import UUID

from app.application.workflow import is_development_placeholder_question
from app.core.config import Settings
from app.core.errors import AssessmentNotReady, Conflict, EnrollmentRequired, NotFound
from app.domain.interviews.models import InterviewStage
from app.ports.interview_queries import (
    AssessmentView,
    InterviewQueryPort,
    ProgressionQueryPort,
    QuestionView,
    SessionView,
    UserQueryPort,
)


class GetInterview:
    def __init__(self, queries: InterviewQueryPort) -> None:
        self._queries = queries

    def execute(self, session_id: UUID, student_id: UUID) -> SessionView:
        view = self._queries.get_owned(session_id, student_id)
        if view is None:
            raise NotFound("Interview not found")
        return view


class GetActiveSession:
    def __init__(self, queries: InterviewQueryPort) -> None:
        self._queries = queries

    def execute(self, student_id: UUID) -> SessionView | None:
        return self._queries.get_active_session(student_id)


class GetActiveQuestion:
    def __init__(self, queries: InterviewQueryPort, settings: Settings | None = None) -> None:
        self._queries = queries
        self._settings = settings

    def execute(self, session_id: UUID, student_id: UUID) -> QuestionView:
        if self._queries.get_owned(session_id, student_id) is None:
            raise NotFound("Interview not found")
        question = self._queries.get_active_question(session_id, student_id)
        if question is None:
            raise Conflict("No active question")
        if is_development_placeholder_question(question.text):
            raise Conflict(
                "This interview contains a development question. Start a fresh interview."
            )
        if (
            self._settings
            and self._settings.app_env.lower() == "production"
            and (
                question.provenance is None
                or question.provenance.origin != "approved_assessment_bank"
                or question.provenance.approval_status != "approved"
            )
        ):
            raise Conflict("This interview does not contain approved assessment content")
        return question


class GetAssessment:
    def __init__(self, queries: InterviewQueryPort) -> None:
        self._queries = queries

    def execute(self, session_id: UUID, student_id: UUID) -> AssessmentView:
        # Distinguish an unknown/unowned session from an incomplete assessment.
        if self._queries.get_owned(session_id, student_id) is None:
            raise NotFound("Interview not found")
        assessment = self._queries.get_assessment(session_id, student_id)
        if assessment is None:
            raise AssessmentNotReady("assessment_not_ready")
        return assessment


class AbandonInterview:
    def __init__(self, queries: InterviewQueryPort) -> None:
        self._queries = queries

    def execute(self, session_id: UUID, student_id: UUID, expected_version: int) -> SessionView:
        view = self._queries.abandon(session_id, student_id, expected_version)
        if view is None:
            raise NotFound("Interview not found")
        return view


@dataclass(frozen=True, slots=True)
class StageProgress:
    stage: InterviewStage
    status: str


class GetProgression:
    def __init__(self, queries: ProgressionQueryPort) -> None:
        self._queries = queries

    def execute(self, student_id: UUID, course_id: UUID | None = None) -> tuple[StageProgress, ...]:
        if course_id is not None and not self._queries.is_enrolled(student_id, course_id):
            raise EnrollmentRequired("Active course enrollment required")
        records = self._queries.records(student_id)
        available_index = 0
        stages = tuple(InterviewStage)
        for index, stage in enumerate(stages):
            scope = str(course_id) if stage.technical and course_id else "global"
            if (stage.value, scope) not in records.passed:
                available_index = index
                break
            available_index = index + 1
        result = []
        for index, stage in enumerate(stages):
            scope = str(course_id) if stage.technical and course_id else "global"
            status = (
                "passed"
                if (stage.value, scope) in records.passed
                else "in_progress"
                if (stage.value, scope) in records.active
                else "available"
                if index == available_index
                else "locked"
            )
            if stage.technical and course_id is None:
                status = "course_required"
            result.append(StageProgress(stage, status))
        return tuple(result)


class GetCurrentUser:
    def __init__(self, queries: UserQueryPort) -> None:
        self._queries = queries

    def execute(self, user_id: UUID) -> tuple[UUID, str]:
        return self._queries.get_or_create_user(user_id)

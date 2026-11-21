from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from app.core.errors import Conflict
from app.db.models import (
    AssessmentAttemptRow,
    AssessmentResultRow,
    CompetencyDefinitionRow,
    CourseContentRevisionRow,
    EnrollmentRow,
    InterviewSessionRow,
    QuestionRow,
    UserRow,
)
from app.domain.assessments.content import QuestionProvenance
from app.domain.interviews.models import (
    InterviewSession,
    InterviewStage,
    InterviewState,
    transition,
)
from app.ports.interview_queries import (
    ApprovedCourseConfiguration,
    AssessmentCompetencyFeedback,
    AssessmentView,
    CourseContentPort,
    InterviewQueryPort,
    ProgressionQueryPort,
    ProgressionRecords,
    QuestionView,
    SessionView,
    UserQueryPort,
)


class SqlAlchemyQueryAdapter(
    InterviewQueryPort, ProgressionQueryPort, UserQueryPort, CourseContentPort
):
    """SQLAlchemy implementation of application read and small command ports."""

    def __init__(self, session: Session) -> None:
        self._session = session

    @staticmethod
    def _session_view(row: InterviewSessionRow) -> SessionView:
        return SessionView(
            row.id,
            InterviewStage(row.stage),
            InterviewState(row.state),
            row.version,
            row.active_question_id,
        )

    def get_owned(self, session_id: UUID, student_id: UUID) -> SessionView | None:
        row = self._session.scalar(
            select(InterviewSessionRow).where(
                InterviewSessionRow.id == session_id,
                InterviewSessionRow.student_id == student_id,
            )
        )
        return self._session_view(row) if row else None

    def get_active_question(self, session_id: UUID, student_id: UUID) -> QuestionView | None:
        row = self._session.scalar(
            select(InterviewSessionRow).where(
                InterviewSessionRow.id == session_id,
                InterviewSessionRow.student_id == student_id,
            )
        )
        if row is None or row.active_question_id is None:
            return None
        question = self._session.get(QuestionRow, row.active_question_id)
        if question is None:
            return None
        return QuestionView(
            question.id,
            question.text,
            question.kind,
            question.sequence,
            row.version,
            QuestionProvenance.from_json(question.provenance_json),
        )

    def get_assessment(self, session_id: UUID, student_id: UUID) -> AssessmentView | None:
        attempt = self._session.scalar(
            select(AssessmentAttemptRow).where(
                AssessmentAttemptRow.session_id == session_id,
                AssessmentAttemptRow.student_id == student_id,
            )
        )
        if attempt is None:
            return None
        result = self._session.get(AssessmentResultRow, attempt.id)
        if result is None:
            return None
        feedback: dict[str, tuple[str, set[str], set[str]]] = {}
        for item in result.evidence_json:
            if not isinstance(item, dict):
                continue
            root_question_id = item.get("root_question_id")
            if not isinstance(root_question_id, str):
                continue
            question = self._session.get(QuestionRow, UUID(root_question_id))
            if question is None:
                continue
            provenance = QuestionProvenance.from_json(question.provenance_json)
            if provenance is None or provenance.competency_id is None:
                continue
            competency = self._session.get(CompetencyDefinitionRow, provenance.competency_id)
            if competency is None:
                continue
            aggregate = feedback.setdefault(
                competency.competency_id, (competency.title, set(), set())
            )
            strengths = item.get("evidence", [])
            areas = item.get("missing", [])
            if isinstance(strengths, list):
                aggregate[1].update(
                    value for value in strengths if isinstance(value, str) and value.strip()
                )
            if isinstance(areas, list):
                aggregate[2].update(
                    value for value in areas if isinstance(value, str) and value.strip()
                )
        competency_feedback = tuple(
            AssessmentCompetencyFeedback(
                competency_id, values[0], tuple(sorted(values[1])), tuple(sorted(values[2]))
            )
            for competency_id, values in sorted(feedback.items())
        )
        return AssessmentView(
            attempt.id,
            result.score,
            result.passed,
            result.rubric_version,
            competency_feedback,
        )

    def get_active_session(self, student_id: UUID) -> SessionView | None:
        active_states = (
            InterviewState.CREATED.value,
            InterviewState.AWAITING_ANSWER.value,
            InterviewState.ANSWER_PROCESSING.value,
            InterviewState.AWAITING_FOLLOW_UP_ANSWER.value,
        )
        row = self._session.scalar(
            select(InterviewSessionRow)
            .where(
                InterviewSessionRow.student_id == student_id,
                InterviewSessionRow.state.in_(active_states),
            )
            .order_by(InterviewSessionRow.created_at.desc())
            .limit(1)
        )
        return self._session_view(row) if row else None

    def abandon(
        self, session_id: UUID, student_id: UUID, expected_version: int
    ) -> SessionView | None:
        row = self._session.scalar(
            select(InterviewSessionRow).where(
                InterviewSessionRow.id == session_id,
                InterviewSessionRow.student_id == student_id,
            )
        )
        if row is None:
            return None
        if row.state == InterviewState.ABANDONED.value and row.version == expected_version + 1:
            return self._session_view(row)
        aggregate = InterviewSession(
            student_id=row.student_id,
            stage=InterviewStage(row.stage),
            course_id=row.course_id,
            content_revision_id=row.content_revision_id,
            id=row.id,
            state=InterviewState(row.state),
            version=row.version,
            base_question_count=row.base_question_count,
            follow_up_count=row.follow_up_count,
            clarification_count=row.clarification_count,
            active_question_id=row.active_question_id,
            created_at=row.created_at,
            completed_at=row.completed_at,
        )
        try:
            transition(aggregate, InterviewState.ABANDONED, expected_version)
            row.state = aggregate.state.value
            row.version = aggregate.version
            row.completed_at = aggregate.completed_at
            self._session.commit()
        except ValueError as exc:
            self._session.rollback()
            raise Conflict(str(exc)) from exc
        except StaleDataError as exc:
            self._session.rollback()
            raise Conflict("stale_version") from exc
        return self._session_view(row)

    def is_enrolled(self, student_id: UUID, course_id: UUID) -> bool:
        return (
            self._session.scalar(
                select(EnrollmentRow.id).where(
                    EnrollmentRow.student_id == student_id,
                    EnrollmentRow.course_id == course_id,
                    EnrollmentRow.active.is_(True),
                )
            )
            is not None
        )

    def records(self, student_id: UUID) -> ProgressionRecords:
        results = self._session.execute(
            select(AssessmentAttemptRow.stage, AssessmentAttemptRow.scope_key)
            .join(AssessmentResultRow, AssessmentAttemptRow.id == AssessmentResultRow.attempt_id)
            .where(
                AssessmentAttemptRow.student_id == student_id,
                AssessmentResultRow.passed.is_(True),
            )
        ).all()
        active_rows = self._session.execute(
            select(InterviewSessionRow.stage, InterviewSessionRow.course_id).where(
                InterviewSessionRow.student_id == student_id,
                InterviewSessionRow.state.notin_(
                    (
                        InterviewState.COMPLETED.value,
                        InterviewState.ABANDONED.value,
                        InterviewState.FAILED.value,
                    )
                ),
            )
        ).all()
        return ProgressionRecords(
            passed=frozenset((stage, scope) for stage, scope in results),
            active=frozenset(
                (stage, str(course_id) if course_id else "global")
                for stage, course_id in active_rows
            ),
        )

    def get_or_create_user(self, user_id: UUID) -> tuple[UUID, str]:
        user = self._session.get(UserRow, user_id)
        if user is None:
            user = UserRow(id=user_id, auth_subject=f"dev:{user_id}", role="student")
            self._session.add(user)
            try:
                self._session.commit()
            except IntegrityError:
                self._session.rollback()
                user = self._session.get(UserRow, user_id)
                if user is None:
                    raise
        return user.id, user.role

    def approved_configuration(self, course_id: UUID) -> ApprovedCourseConfiguration | None:
        revision = self._session.scalar(
            select(CourseContentRevisionRow)
            .where(
                CourseContentRevisionRow.course_id == course_id,
                CourseContentRevisionRow.approved.is_(True),
            )
            .order_by(CourseContentRevisionRow.created_at.desc())
        )
        if revision is None:
            return None
        return ApprovedCourseConfiguration(revision.id, dict(revision.metadata_json))

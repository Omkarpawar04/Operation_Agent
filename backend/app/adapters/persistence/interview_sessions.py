from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.adapters.persistence.uow import SqlAlchemyUnitOfWork
from app.core.errors import Conflict
from app.db.models import (
    AssessmentAttemptRow,
    AssessmentResultRow,
    CourseContentRevisionRow,
    EnrollmentRow,
    InterviewSessionRow,
    QuestionRow,
    UserRow,
)
from app.domain.interviews.models import (
    InterviewSession,
    InterviewStage,
    InterviewState,
    transition,
)
from app.ports.sessions import SessionRecord, SessionStartPort, StartSessionCommand


class SqlAlchemySessionStartAdapter(SessionStartPort):
    """Persistence adapter for the session manager; owns a short commit only."""

    def __init__(self, db: Session) -> None:
        self._db = db

    @staticmethod
    def _record(row: InterviewSessionRow) -> SessionRecord:
        return SessionRecord(
            id=row.id,
            stage=row.stage,
            state=row.state,
            version=row.version,
            active_question_id=row.active_question_id,
            course_id=row.course_id,
        )

    def find_existing(self, student_id: UUID, key: str) -> SessionRecord | None:
        row = self._db.scalar(
            select(InterviewSessionRow).where(
                InterviewSessionRow.student_id == student_id,
                InterviewSessionRow.idempotency_key == key,
            )
        )
        return self._record(row) if row else None

    def enrolled(self, student_id: UUID, course_id: UUID) -> bool:
        return (
            self._db.scalar(
                select(EnrollmentRow.id).where(
                    EnrollmentRow.student_id == student_id,
                    EnrollmentRow.course_id == course_id,
                    EnrollmentRow.active.is_(True),
                )
            )
            is not None
        )

    def approved_revision(self, course_id: UUID) -> UUID | None:
        row = self._db.scalar(
            select(CourseContentRevisionRow)
            .where(
                CourseContentRevisionRow.course_id == course_id,
                CourseContentRevisionRow.approved.is_(True),
            )
            .order_by(CourseContentRevisionRow.created_at.desc())
        )
        return row.id if row else None

    def stage_passed(self, student_id: UUID, stage: InterviewStage, course_id: UUID | None) -> bool:
        query = (
            select(AssessmentAttemptRow.id)
            .join(
                AssessmentResultRow,
                AssessmentResultRow.attempt_id == AssessmentAttemptRow.id,
            )
            .where(
                AssessmentAttemptRow.student_id == student_id,
                AssessmentAttemptRow.stage == stage.value,
                AssessmentResultRow.passed.is_(True),
            )
        )
        if stage.technical:
            query = query.where(AssessmentAttemptRow.scope_key == str(course_id))
        return self._db.scalar(query.limit(1)) is not None

    def completed_attempt_history(
        self, student_id: UUID, stage: InterviewStage, course_id: UUID | None
    ) -> tuple[int, datetime | None]:
        scope_key = str(course_id) if course_id else "global"
        query = (
            select(func.count(AssessmentAttemptRow.id), func.max(AssessmentResultRow.completed_at))
            .join(
                AssessmentResultRow,
                AssessmentResultRow.attempt_id == AssessmentAttemptRow.id,
            )
            .where(
                AssessmentAttemptRow.student_id == student_id,
                AssessmentAttemptRow.stage == stage.value,
                AssessmentAttemptRow.scope_key == scope_key,
            )
        )
        count, latest = self._db.execute(query).one()
        return int(count), latest

    def create(
        self,
        command: StartSessionCommand,
        revision_id: UUID | None,
        revalidate: Callable[[], UUID | None],
    ) -> SessionRecord:
        row: InterviewSessionRow
        try:
            self._db.rollback()
            with SqlAlchemyUnitOfWork(self._db):
                user = self._db.get(UserRow, command.student_id)
                if user is None:
                    user = UserRow(
                        id=command.student_id,
                        auth_subject=f"dev:{command.student_id}",
                        role="student",
                    )
                    self._db.add(user)
                    self._db.flush()
                self._db.scalar(
                    select(UserRow.id).where(UserRow.id == command.student_id).with_for_update()
                )
                atomic_revision_id = revalidate()
                if revision_id is not None and atomic_revision_id != revision_id:
                    raise Conflict("Interview eligibility or course content changed")
                revision_id = atomic_revision_id
                row = InterviewSessionRow(
                    student_id=command.student_id,
                    stage=command.stage.value,
                    course_id=command.course_id,
                    content_revision_id=revision_id,
                    idempotency_key=command.idempotency_key,
                )
                self._db.add(row)
                self._db.flush()
                self._db.add(
                    AssessmentAttemptRow(
                        student_id=command.student_id,
                        session_id=row.id,
                        stage=command.stage.value,
                        scope_key=str(command.course_id) if command.course_id else "global",
                        idempotency_key=command.idempotency_key,
                    )
                )
                if command.initial_question_text:
                    question = QuestionRow(
                        session_id=row.id,
                        sequence=1,
                        kind="base",
                        text=command.initial_question_text,
                        provenance_json=(
                            command.initial_question_provenance.to_json()
                            if command.initial_question_provenance
                            else None
                        ),
                    )
                    self._db.add(question)
                    self._db.flush()
                    aggregate = InterviewSession(
                        student_id=row.student_id,
                        stage=InterviewStage(row.stage),
                        course_id=row.course_id,
                        content_revision_id=revision_id,
                        id=row.id,
                    )
                    aggregate.active_question_id = question.id
                    aggregate.base_question_count = 1
                    transition(aggregate, InterviewState.AWAITING_ANSWER, row.version)
                    row.active_question_id = question.id
                    row.base_question_count = aggregate.base_question_count
                    row.state = aggregate.state.value
                    row.version = aggregate.version
        except IntegrityError as exc:
            self._db.rollback()
            existing = self.find_existing(command.student_id, command.idempotency_key)
            if existing is not None:
                if (
                    existing.stage == command.stage.value
                    and existing.course_id == command.course_id
                ):
                    return existing
                raise Conflict("Idempotency key reused with a different request") from exc
            constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
            message = str(exc.orig)
            if (
                constraint
                in {
                    "uq_active_soft_interview_scope",
                    "uq_active_technical_interview_scope",
                }
                or "uq_active_" in message
            ):
                raise Conflict("An active interview already exists for this stage") from exc
            raise
        self._db.refresh(row)
        return self._record(row)

    def rollback_read_transaction(self) -> None:
        self._db.rollback()

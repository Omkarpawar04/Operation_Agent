from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def now_utc() -> datetime:
    return datetime.now(UTC)


class UserRow(Base):
    __tablename__ = "users"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    auth_subject: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    role: Mapped[str] = mapped_column(String(30), default="student")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class CourseRow(Base):
    __tablename__ = "courses"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(60), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class EnrollmentRow(Base):
    __tablename__ = "enrollments"
    __table_args__ = (UniqueConstraint("student_id", "course_id"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    student_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    course_id: Mapped[UUID] = mapped_column(ForeignKey("courses.id"), index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class CourseContentRevisionRow(Base):
    __tablename__ = "course_content_revisions"
    __table_args__ = (UniqueConstraint("course_id", "revision"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    course_id: Mapped[UUID] = mapped_column(ForeignKey("courses.id"), index=True)
    revision: Mapped[str] = mapped_column(String(80))
    approved: Mapped[bool] = mapped_column(Boolean, default=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class InterviewSessionRow(Base):
    __tablename__ = "interview_sessions"
    __table_args__ = (
        CheckConstraint("version >= 0", name="version_nonnegative"),
        CheckConstraint(
            "base_question_count >= 0 AND follow_up_count >= 0 AND clarification_count >= 0",
            name="question_counts_nonnegative",
        ),
        UniqueConstraint("student_id", "idempotency_key"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    student_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    stage: Mapped[str] = mapped_column(String(30), index=True)
    course_id: Mapped[UUID | None] = mapped_column(ForeignKey("courses.id"), nullable=True)
    content_revision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("course_content_revisions.id"), nullable=True
    )
    state: Mapped[str] = mapped_column(String(40), default="created", index=True)
    version: Mapped[int] = mapped_column(Integer, default=0)
    __mapper_args__ = {"version_id_col": version, "version_id_generator": False}
    base_question_count: Mapped[int] = mapped_column(Integer, default=0)
    follow_up_count: Mapped[int] = mapped_column(Integer, default=0)
    clarification_count: Mapped[int] = mapped_column(Integer, default=0)
    active_question_id: Mapped[UUID | None] = mapped_column(nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processing_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    questions: Mapped[list["QuestionRow"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


_ACTIVE_SESSION_STATES = (
    "created",
    "awaiting_answer",
    "answer_processing",
    "awaiting_follow_up_answer",
)
Index(
    "uq_active_soft_interview_scope",
    InterviewSessionRow.student_id,
    InterviewSessionRow.stage,
    unique=True,
    sqlite_where=(
        InterviewSessionRow.course_id.is_(None)
        & InterviewSessionRow.state.in_(_ACTIVE_SESSION_STATES)
    ),
    postgresql_where=(
        InterviewSessionRow.course_id.is_(None)
        & InterviewSessionRow.state.in_(_ACTIVE_SESSION_STATES)
    ),
)
Index(
    "uq_active_technical_interview_scope",
    InterviewSessionRow.student_id,
    InterviewSessionRow.stage,
    InterviewSessionRow.course_id,
    unique=True,
    sqlite_where=(
        InterviewSessionRow.course_id.is_not(None)
        & InterviewSessionRow.state.in_(_ACTIVE_SESSION_STATES)
    ),
    postgresql_where=(
        InterviewSessionRow.course_id.is_not(None)
        & InterviewSessionRow.state.in_(_ACTIVE_SESSION_STATES)
    ),
)


class QuestionRow(Base):
    __tablename__ = "questions"
    __table_args__ = (
        UniqueConstraint("session_id", "sequence"),
        CheckConstraint("sequence >= 1", name="sequence_positive"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(ForeignKey("interview_sessions.id"), index=True)
    parent_question_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("questions.id"), nullable=True
    )
    sequence: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(30))
    text: Mapped[str] = mapped_column(Text)
    provenance_json: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    session: Mapped[InterviewSessionRow] = relationship(back_populates="questions")


class CompetencyDefinitionRow(Base):
    __tablename__ = "assessment_competencies"
    __table_args__ = (
        CheckConstraint(
            "stage_id IN ('soft_1','soft_2','soft_3','technical_1','technical_2','technical_3')",
            name="stage_valid",
        ),
        CheckConstraint(
            "approval_status IN ('draft','review','approved','retired')",
            name="approval_status_valid",
        ),
    )
    competency_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    stage_id: Mapped[str] = mapped_column(String(30), index=True)
    stage_ids_json: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    title: Mapped[str] = mapped_column(String(240))
    definition: Mapped[str] = mapped_column(Text)
    content_version: Mapped[str] = mapped_column(String(80))
    approval_status: Mapped[str] = mapped_column(String(20), index=True)
    content_source: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content_metadata_json: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)


class AssessmentRubricRow(Base):
    __tablename__ = "assessment_rubrics"
    __table_args__ = (
        CheckConstraint(
            "approval_status IN ('draft','review','approved','retired')",
            name="approval_status_valid",
        ),
    )
    rubric_version_id: Mapped[str] = mapped_column(String(160), primary_key=True)
    rubric_id: Mapped[str] = mapped_column(String(120), index=True)
    competency_id: Mapped[str] = mapped_column(
        ForeignKey("assessment_competencies.competency_id", name="fk_rubric_competency"),
        index=True,
    )
    dimensions_json: Mapped[list[dict[str, object]]] = mapped_column(JSON)
    scoring_scale_json: Mapped[list[dict[str, object]]] = mapped_column(JSON)
    evidence_requirements_json: Mapped[list[str]] = mapped_column(JSON)
    insufficient_evidence_json: Mapped[list[str]] = mapped_column(JSON)
    content_version: Mapped[str] = mapped_column(String(80))
    approval_status: Mapped[str] = mapped_column(String(20), index=True)
    content_source: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content_metadata_json: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)


class QuestionBankRow(Base):
    __tablename__ = "assessment_question_bank"
    __table_args__ = (
        CheckConstraint(
            "stage_id IN ('soft_1','soft_2','soft_3','technical_1','technical_2','technical_3')",
            name="stage_valid",
        ),
        CheckConstraint("category IN ('base','follow_up','clarification')", name="category_valid"),
        CheckConstraint(
            "approval_status IN ('draft','review','approved','retired')",
            name="approval_status_valid",
        ),
        ForeignKeyConstraint(
            ["parent_question_id", "parent_content_version"],
            ["assessment_question_bank.question_id", "assessment_question_bank.content_version"],
            name="fk_qbank_parent_question",
        ),
    )
    question_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    stage_id: Mapped[str] = mapped_column(String(30), index=True)
    competency_id: Mapped[str] = mapped_column(
        ForeignKey("assessment_competencies.competency_id", name="fk_qbank_competency"),
        index=True,
    )
    text: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(30))
    difficulty: Mapped[str] = mapped_column(String(40))
    expected_answer_json: Mapped[list[str]] = mapped_column(JSON)
    rubric_version_id: Mapped[str] = mapped_column(
        ForeignKey("assessment_rubrics.rubric_version_id", name="fk_qbank_rubric"),
        index=True,
    )
    content_version: Mapped[str] = mapped_column(String(80), primary_key=True)
    approval_status: Mapped[str] = mapped_column(String(20), index=True)
    content_source: Mapped[str] = mapped_column(String(255))
    parent_question_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    parent_content_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    development_eligible: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    content_metadata_json: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)


Index(
    "uq_assessment_question_bank_approved_version",
    QuestionBankRow.question_id,
    unique=True,
    sqlite_where=QuestionBankRow.approval_status == "approved",
    postgresql_where=QuestionBankRow.approval_status == "approved",
)

Index(
    "ix_assessment_question_bank_development_eligible",
    QuestionBankRow.development_eligible,
)


class AnswerRow(Base):
    __tablename__ = "answers"
    __table_args__ = (
        UniqueConstraint("session_id", "idempotency_key"),
        UniqueConstraint("question_id"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(ForeignKey("interview_sessions.id"), index=True)
    question_id: Mapped[UUID] = mapped_column(ForeignKey("questions.id"), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(120))
    transcript: Mapped[str] = mapped_column(Text)
    is_skipped: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class AssessmentAttemptRow(Base):
    __tablename__ = "assessment_attempts"
    __table_args__ = (UniqueConstraint("student_id", "stage", "scope_key", "idempotency_key"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    student_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    session_id: Mapped[UUID] = mapped_column(ForeignKey("interview_sessions.id"), unique=True)
    stage: Mapped[str] = mapped_column(String(30))
    scope_key: Mapped[str] = mapped_column(String(80), default="global")
    idempotency_key: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(30), default="in_progress")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class EvaluationRow(Base):
    __tablename__ = "evaluations"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    answer_id: Mapped[UUID] = mapped_column(ForeignKey("answers.id"), index=True)
    rubric_version: Mapped[str] = mapped_column(String(80))
    evidence_json: Mapped[list[dict[str, object]]] = mapped_column(JSON, default=list)


class AssessmentResultRow(Base):
    __tablename__ = "assessment_results"
    attempt_id: Mapped[UUID] = mapped_column(ForeignKey("assessment_attempts.id"), primary_key=True)
    score: Mapped[str] = mapped_column(String(20))
    passed: Mapped[bool] = mapped_column(Boolean)
    rubric_version: Mapped[str] = mapped_column(String(80))
    evidence_json: Mapped[list[dict[str, object]]] = mapped_column(JSON, default=list)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class TranscriptDeletionAuditRow(Base):
    __tablename__ = "transcript_deletion_audit"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    student_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    deleted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class RateLimitCounterRow(Base):
    __tablename__ = "rate_limit_counters"
    scope: Mapped[str] = mapped_column(String(120), primary_key=True)
    window_started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    hits: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

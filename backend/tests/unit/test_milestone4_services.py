from datetime import UTC, datetime, timedelta
from time import sleep

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.adapters.persistence.lease_recovery import SqlAlchemyExpiredLeaseRecovery
from app.adapters.persistence.transcript_lifecycle import SqlAlchemyTranscriptLifecycle
from app.application.use_cases.recover_leases import RecoverExpiredLeases
from app.application.use_cases.transcripts import EnforceTranscriptRetention
from app.core.config import Settings
from app.db.base import Base
from app.db.models import (
    AnswerRow,
    AssessmentAttemptRow,
    AssessmentResultRow,
    EvaluationRow,
    InterviewSessionRow,
    QuestionRow,
    TranscriptDeletionAuditRow,
    UserRow,
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_recovery_use_case_restores_only_expired_processing_sessions(db_session: Session) -> None:
    owner = UserRow(auth_subject="recovery-test")
    db_session.add(owner)
    db_session.flush()
    expired = InterviewSessionRow(
        student_id=owner.id,
        stage="soft_1",
        state="answer_processing",
        processing_started_at=datetime.now(UTC) - timedelta(minutes=5),
        idempotency_key="expired",
    )
    active = InterviewSessionRow(
        student_id=owner.id,
        stage="soft_2",
        state="answer_processing",
        processing_started_at=datetime.now(UTC),
        idempotency_key="active",
    )
    completed = InterviewSessionRow(
        student_id=owner.id,
        stage="soft_3",
        state="completed",
        processing_started_at=datetime.now(UTC) - timedelta(hours=2),
        idempotency_key="completed",
    )
    db_session.add_all([expired, active, completed])
    db_session.flush()
    db_session.add(
        QuestionRow(session_id=expired.id, sequence=1, kind="base", text="Question text")
    )
    db_session.commit()

    recovered = RecoverExpiredLeases(SqlAlchemyExpiredLeaseRecovery(db_session, 60)).execute()
    assert recovered == 1
    db_session.refresh(expired)
    db_session.refresh(active)
    db_session.refresh(completed)
    assert expired.state == "awaiting_answer"
    assert expired.processing_started_at is None
    assert active.state == "answer_processing"
    assert completed.state == "completed"


def test_transcript_deletion_is_scoped_and_keeps_result_for_progression(
    db_session: Session,
) -> None:
    owner = UserRow(auth_subject="delete-owner")
    other = UserRow(auth_subject="delete-other")
    db_session.add_all([owner, other])
    db_session.flush()
    sessions = [
        InterviewSessionRow(
            student_id=student.id,
            stage="soft_1",
            state="completed",
            idempotency_key=f"session-{student.id}",
        )
        for student in (owner, other)
    ]
    db_session.add_all(sessions)
    db_session.flush()
    questions = [
        QuestionRow(session_id=item.id, sequence=1, kind="base", text="Generated question")
        for item in sessions
    ]
    db_session.add_all(questions)
    db_session.flush()
    attempts = [
        AssessmentAttemptRow(
            student_id=session.student_id,
            session_id=session.id,
            stage="soft_1",
            scope_key="global",
            idempotency_key=f"attempt-{session.id}",
            status="passed",
        )
        for session in sessions
    ]
    db_session.add_all(attempts)
    db_session.flush()
    answers = [
        AnswerRow(
            session_id=session.id,
            question_id=question.id,
            idempotency_key=f"answer-{session.id}",
            transcript="private answer",
        )
        for session, question in zip(sessions, questions, strict=True)
    ]
    db_session.add_all(answers)
    db_session.flush()
    db_session.add_all(
        [
            EvaluationRow(
                answer_id=answer.id,
                rubric_version="v1",
                evidence_json=[{"evidence": ["private"]}],
            )
            for answer in answers
        ]
    )
    db_session.add_all(
        [
            AssessmentResultRow(
                attempt_id=attempt.id,
                score="80",
                passed=True,
                rubric_version="v1",
                evidence_json=[{"evidence": ["private"]}],
            )
            for attempt in attempts
        ]
    )
    db_session.commit()

    deleted = SqlAlchemyTranscriptLifecycle(db_session).delete_student_transcripts(owner.id)
    assert deleted == 1
    for entity in [*answers, *questions]:
        db_session.refresh(entity)
    assert answers[0].transcript == "[deleted]"
    assert questions[0].text == "[deleted]"
    evaluation = db_session.scalar(
        select(EvaluationRow).where(EvaluationRow.answer_id == answers[0].id)
    )
    assert evaluation is not None and evaluation.evidence_json == []
    result = db_session.get(AssessmentResultRow, attempts[0].id)
    assert (
        result is not None and result.passed and result.score == "80" and result.evidence_json == []
    )
    assert answers[1].transcript == "private answer"
    assert questions[1].text == "Generated question"
    assert len(db_session.scalars(select(TranscriptDeletionAuditRow)).all()) == 1
    assert SqlAlchemyTranscriptLifecycle(db_session).delete_student_transcripts(owner.id) == 0
    assert len(db_session.scalars(select(TranscriptDeletionAuditRow)).all()) == 1


def test_transcript_erasure_rolls_back_on_commit_failure(db_session: Session, monkeypatch) -> None:
    owner = UserRow(auth_subject="rollback-owner")
    db_session.add(owner)
    db_session.flush()
    session = InterviewSessionRow(
        student_id=owner.id,
        stage="soft_1",
        state="completed",
        idempotency_key="rollback-session",
    )
    db_session.add(session)
    db_session.flush()
    question = QuestionRow(session_id=session.id, sequence=1, kind="base", text="Question")
    db_session.add(question)
    db_session.flush()
    answer = AnswerRow(
        session_id=session.id,
        question_id=question.id,
        idempotency_key="rollback-answer",
        transcript="Private answer",
    )
    db_session.add(answer)
    db_session.commit()

    def fail_commit() -> None:
        raise RuntimeError("simulated transaction failure")

    monkeypatch.setattr(db_session, "commit", fail_commit)
    with pytest.raises(RuntimeError, match="transaction failure"):
        SqlAlchemyTranscriptLifecycle(db_session).delete_student_transcripts(owner.id)
    db_session.rollback()
    monkeypatch.undo()
    db_session.refresh(answer)
    assert answer.transcript == "Private answer"
    assert db_session.scalars(select(TranscriptDeletionAuditRow)).all() == []


def test_retention_policy_rejects_naive_clock() -> None:
    class NoOpLifecycle:
        def delete_student_transcripts(self, _student_id):
            return 0

        def delete_expired_transcripts(self, _before, _limit):
            return 0

    policy = EnforceTranscriptRetention(NoOpLifecycle(), retention_days=30)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="timezone-aware"):
        policy.execute(datetime(2026, 1, 1))


def test_production_settings_require_real_adapters_and_explicit_policies() -> None:
    with pytest.raises(ValidationError, match="configured Gemini provider"):
        Settings(_env_file=None, app_env="production")
    production = Settings(
        _env_file=None,
        app_env="production",
        database_url="postgresql+psycopg://localhost:5432/finxl",
        llm_provider="gemini",
        gemini_api_key="test-placeholder-only",
        cors_allowed_origins=["https://example.invalid"],
        trusted_hosts=["api.example.invalid"],
        transcript_retention_days=365,
    )
    assert not production.development_auth_enabled


def test_recovery_worker_starts_and_shuts_down_with_lifespan(monkeypatch) -> None:
    import app.main as main

    worker_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(worker_engine)
    factory = sessionmaker(bind=worker_engine, expire_on_commit=False)
    monkeypatch.setattr(
        main,
        "get_settings",
        lambda: Settings(
            _env_file=None,
            app_env="test",
            database_url="sqlite://",
            lease_recovery_interval_seconds=3600,
        ),
    )
    monkeypatch.setattr(main, "make_session_factory", lambda _engine: factory)
    application = main.create_app()

    with TestClient(application):
        for _attempt in range(20):
            if application.state.worker_status.get("last_run") is not None:
                break
            sleep(0.01)
        assert application.state.worker_status["lease_recovery"] == "running"
        assert application.state.worker_status["last_run"] is not None

    assert application.state.worker_status == {"lease_recovery": "stopped"}
    Base.metadata.drop_all(worker_engine)
    worker_engine.dispose()

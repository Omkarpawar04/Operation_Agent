from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier, Event
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError

from app.adapters.llm.fake import FakeLLMProvider
from app.adapters.persistence.interview_sessions import SqlAlchemySessionStartAdapter
from app.adapters.persistence.lease_recovery import SqlAlchemyExpiredLeaseRecovery
from app.adapters.persistence.rate_limiting import SqlAlchemyRateLimitStore
from app.adapters.persistence.transcript_lifecycle import SqlAlchemyTranscriptLifecycle
from app.adapters.persistence.uow import SqlAlchemyUnitOfWork
from app.api.dependencies import get_db, get_llm_provider
from app.application.sessions.manager import SessionManager
from app.core.config import Settings, get_settings
from app.core.errors import Conflict, ProviderUnavailable
from app.db.models import (
    AnswerRow,
    AssessmentAttemptRow,
    AssessmentResultRow,
    CourseContentRevisionRow,
    CourseRow,
    EnrollmentRow,
    EvaluationRow,
    InterviewSessionRow,
    QuestionRow,
    RateLimitCounterRow,
    TranscriptDeletionAuditRow,
    UserRow,
)
from app.domain.interviews.models import InterviewStage
from app.main import create_app
from app.ports.sessions import StartSessionCommand

pytestmark = pytest.mark.postgres


def _postgres_client(postgres_factory, provider=None, settings=None):
    application = create_app()

    def override_db():
        with postgres_factory() as session:
            yield session

    application.dependency_overrides[get_db] = override_db
    selected_settings = settings or Settings(app_env="test", max_base_questions=1)
    application.dependency_overrides[get_settings] = lambda: selected_settings
    application.dependency_overrides[get_llm_provider] = lambda: provider or FakeLLMProvider()
    return TestClient(application)


def _answer_text() -> str:
    return (
        "I compared two approaches, selected an evidence based option, implemented the change, "
        "and verified its result using follow up measurements."
    )


def test_postgres_competing_recovery_workers_claim_expired_lease_once(postgres_factory) -> None:
    student_id = uuid4()
    session_id = uuid4()
    with postgres_factory.begin() as db:
        db.add(UserRow(id=student_id, auth_subject=f"recovery:{student_id}"))
        db.flush()
        session = InterviewSessionRow(
            id=session_id,
            student_id=student_id,
            stage="soft_1",
            state="answer_processing",
            processing_started_at=datetime.now(UTC) - timedelta(minutes=20),
            idempotency_key=f"recovery:{uuid4()}",
        )
        db.add(session)
        db.flush()
        question = QuestionRow(
            session_id=session_id, sequence=1, kind="base", text="Recovery test question"
        )
        db.add(question)
        db.flush()
        session.active_question_id = question.id

    def recover_once() -> int:
        with postgres_factory() as db:
            return SqlAlchemyExpiredLeaseRecovery(db, lease_seconds=60).recover_expired(10)

    with ThreadPoolExecutor(max_workers=2) as pool:
        counts = list(pool.map(lambda _index: recover_once(), range(2)))
    assert sum(counts) == 1
    with postgres_factory() as db:
        session = db.get(InterviewSessionRow, session_id)
        assert session is not None
        assert session.state == "awaiting_answer"
        assert session.processing_started_at is None
        assert session.version == 1


def test_postgres_shared_rate_counter_is_atomic_across_workers(postgres_factory) -> None:
    scope = f"postgres-rate-test-{uuid4()}"
    now = datetime.now(UTC)

    def consume_once(_index: int) -> int:
        with postgres_factory() as db:
            return SqlAlchemyRateLimitStore(db).consume(scope, now, 60)

    with ThreadPoolExecutor(max_workers=8) as pool:
        counts = list(pool.map(consume_once, range(24)))
    assert sorted(counts) == list(range(1, 25))
    with postgres_factory() as db:
        assert db.get(RateLimitCounterRow, scope).hits == 24


def test_postgres_transcript_erasure_is_owned_and_atomic(postgres_factory) -> None:
    owner_id, other_id = uuid4(), uuid4()
    session_ids = (uuid4(), uuid4())
    answer_ids = (uuid4(), uuid4())
    question_ids = (uuid4(), uuid4())
    with postgres_factory.begin() as db:
        db.add_all(
            [
                UserRow(id=owner_id, auth_subject=f"erase:{owner_id}"),
                UserRow(id=other_id, auth_subject=f"erase:{other_id}"),
            ]
        )
        db.flush()
        sessions = [
            InterviewSessionRow(
                id=session_ids[index],
                student_id=student_id,
                stage="soft_1",
                state="completed",
                idempotency_key=f"erase-session:{uuid4()}",
            )
            for index, student_id in enumerate((owner_id, other_id))
        ]
        db.add_all(sessions)
        db.flush()
        questions = [
            QuestionRow(
                id=question_ids[index],
                session_id=session_ids[index],
                sequence=1,
                kind="base",
                text="Generated question with personal context",
            )
            for index in range(2)
        ]
        db.add_all(questions)
        db.flush()
        db.add_all(
            [
                AnswerRow(
                    id=answer_ids[index],
                    session_id=session_ids[index],
                    question_id=question_ids[index],
                    idempotency_key=f"erase-answer:{uuid4()}",
                    transcript="Private response",
                )
                for index in range(2)
            ]
        )

    with postgres_factory() as db:
        assert SqlAlchemyTranscriptLifecycle(db).delete_student_transcripts(owner_id) == 1
    with postgres_factory() as db:
        erased = db.get(AnswerRow, answer_ids[0])
        untouched = db.get(AnswerRow, answer_ids[1])
        assert erased is not None and erased.transcript == "[deleted]"
        assert untouched is not None and untouched.transcript == "Private response"
        assert db.get(QuestionRow, question_ids[0]).text == "[deleted]"
        assert (
            db.get(QuestionRow, question_ids[1]).text
            == "Generated question with personal context"
        )
        audits = db.scalars(
            select(TranscriptDeletionAuditRow).where(
                TranscriptDeletionAuditRow.student_id == owner_id
            )
        ).all()
        assert len(audits) == 1


def test_postgres_connectivity_and_all_models_round_trip(postgres_engine, postgres_factory) -> None:
    with postgres_engine.connect() as connection:
        assert connection.scalar(select(1)) == 1
        assert connection.exec_driver_sql("SELECT current_database()").scalar_one() == "finxl_test"

    student_id = uuid4()
    course_id = uuid4()
    with postgres_factory.begin() as db:
        student = UserRow(id=student_id, auth_subject=f"pg-model:{student_id}")
        course = CourseRow(id=course_id, code=f"PG-{uuid4().hex[:12]}", name="PG model test")
        db.add_all([student, course])
        db.flush()
        enrollment = EnrollmentRow(student_id=student_id, course_id=course_id)
        revision = CourseContentRevisionRow(
            course_id=course_id,
            revision="test-r1",
            approved=True,
            metadata_json={"source": "integration-test"},
        )
        db.add_all([enrollment, revision])
        db.flush()
        session = InterviewSessionRow(
            student_id=student_id,
            stage="technical_1",
            course_id=course_id,
            content_revision_id=revision.id,
            idempotency_key=f"pg-model:{uuid4()}",
        )
        db.add(session)
        db.flush()
        question = QuestionRow(
            session_id=session.id, sequence=1, kind="base", text="Integration question"
        )
        db.add(question)
        db.flush()
        session.active_question_id = question.id
        answer = AnswerRow(
            session_id=session.id,
            question_id=question.id,
            idempotency_key=f"answer:{uuid4()}",
            transcript="Transient text transcript only",
        )
        db.add(answer)
        db.flush()
        attempt = AssessmentAttemptRow(
            student_id=student_id,
            session_id=session.id,
            stage="technical_1",
            scope_key=str(course_id),
            idempotency_key=f"attempt:{uuid4()}",
            status="passed",
        )
        db.add(attempt)
        db.flush()
        db.add_all(
            [
                EvaluationRow(
                    answer_id=answer.id,
                    rubric_version="test-v1",
                    evidence_json=[{"dimension": "reasoning", "confidence": 0.8}],
                ),
                AssessmentResultRow(
                    attempt_id=attempt.id,
                    score="75",
                    passed=True,
                    rubric_version="test-v1",
                    evidence_json=[{"dimension": "reasoning"}],
                ),
            ]
        )
        session_id, question_id, attempt_id = session.id, question.id, attempt.id

    with postgres_factory() as db:
        saved_session = db.get(InterviewSessionRow, session_id)
        assert saved_session is not None
        assert saved_session.content_revision_id is not None
        assert db.get(QuestionRow, question_id) is not None
        assert db.get(AssessmentResultRow, attempt_id).passed is True


def test_unit_of_work_commits_and_rolls_back(postgres_factory) -> None:
    committed_subject = f"uow-commit:{uuid4()}"
    with postgres_factory() as db:
        with SqlAlchemyUnitOfWork(db):
            db.add(UserRow(auth_subject=committed_subject))
    with postgres_factory() as db:
        assert (
            db.scalar(select(UserRow.id).where(UserRow.auth_subject == committed_subject))
            is not None
        )

    rolled_back_subject = f"uow-rollback:{uuid4()}"
    with pytest.raises(RuntimeError, match="rollback sentinel"):
        with postgres_factory() as db:
            with SqlAlchemyUnitOfWork(db):
                db.add(UserRow(auth_subject=rolled_back_subject))
                raise RuntimeError("rollback sentinel")
    with postgres_factory() as db:
        assert (
            db.scalar(select(UserRow.id).where(UserRow.auth_subject == rolled_back_subject)) is None
        )


def test_unit_of_work_rolls_back_a_failed_commit(postgres_factory) -> None:
    subject = f"uow-commit-failure:{uuid4()}"
    with postgres_factory.begin() as db:
        db.add(UserRow(auth_subject=subject))
    with pytest.raises(IntegrityError):
        with postgres_factory() as db:
            with SqlAlchemyUnitOfWork(db):
                db.add(UserRow(auth_subject=subject))
    with postgres_factory() as db:
        assert len(db.scalars(select(UserRow.id).where(UserRow.auth_subject == subject)).all()) == 1


def test_repository_repeated_start_is_idempotent(postgres_factory) -> None:
    student_id = uuid4()
    command = StartSessionCommand(
        student_id=student_id,
        stage=InterviewStage.SOFT_1,
        idempotency_key=f"repo-idem:{uuid4()}",
        course_id=None,
    )
    with postgres_factory() as db:
        manager = SessionManager(SqlAlchemySessionStartAdapter(db))
        first = manager.start(command)
        repeated = manager.start(command)
        assert first.id == repeated.id

    with postgres_factory() as db:
        sessions = db.scalars(
            select(InterviewSessionRow).where(
                InterviewSessionRow.student_id == student_id,
                InterviewSessionRow.idempotency_key == command.idempotency_key,
            )
        ).all()
        attempts = db.scalars(
            select(AssessmentAttemptRow).where(
                AssessmentAttemptRow.student_id == student_id,
                AssessmentAttemptRow.idempotency_key == command.idempotency_key,
            )
        ).all()
        assert len(sessions) == len(attempts) == 1


def test_postgres_unique_constraints_reject_duplicate_enrollment_and_answer(
    postgres_factory,
) -> None:
    student_id, course_id = uuid4(), uuid4()
    with postgres_factory.begin() as db:
        db.add_all(
            [
                UserRow(id=student_id, auth_subject=f"pg-unique:{student_id}"),
                CourseRow(id=course_id, code=f"PG-{uuid4().hex[:12]}", name="Unique test"),
            ]
        )
        db.flush()
        db.add(EnrollmentRow(student_id=student_id, course_id=course_id))
        session = InterviewSessionRow(
            student_id=student_id, stage="soft_1", idempotency_key=f"unique:{uuid4()}"
        )
        db.add(session)
        db.flush()
        question = QuestionRow(
            session_id=session.id, sequence=1, kind="base", text="Unique test question"
        )
        db.add(question)
        db.flush()
        session_id, question_id = session.id, question.id

    with pytest.raises(IntegrityError):
        with postgres_factory.begin() as db:
            db.add(EnrollmentRow(student_id=student_id, course_id=course_id))

    with postgres_factory.begin() as db:
        db.add(
            AnswerRow(
                session_id=session_id,
                question_id=question_id,
                idempotency_key=f"answer-one:{uuid4()}",
                transcript="first",
            )
        )
    with pytest.raises(IntegrityError):
        with postgres_factory.begin() as db:
            db.add(
                AnswerRow(
                    session_id=session_id,
                    question_id=question_id,
                    idempotency_key=f"answer-two:{uuid4()}",
                    transcript="duplicate active-question answer",
                )
            )


def test_postgres_optimistic_lock_rejects_stale_concurrent_update(postgres_factory) -> None:
    student_id = uuid4()
    with postgres_factory.begin() as db:
        db.add(UserRow(id=student_id, auth_subject=f"pg-version:{student_id}"))
        db.flush()
        subject = InterviewSessionRow(
            student_id=student_id,
            stage="soft_1",
            idempotency_key=f"pg-version:{uuid4()}",
        )
        db.add(subject)
        db.flush()
        session_id = subject.id

    first, second = postgres_factory(), postgres_factory()
    try:
        one = first.get(InterviewSessionRow, session_id)
        two = second.get(InterviewSessionRow, session_id)
        assert one is not None and two is not None
        assert one.version == two.version == 0
        one.state, one.version = "awaiting_answer", 1
        first.commit()
        two.state, two.version = "abandoned", 1
        with pytest.raises(StaleDataError):
            second.commit()
        second.rollback()
        assert second.get(InterviewSessionRow, session_id).state == "awaiting_answer"
    finally:
        first.close()
        second.close()


def test_postgres_concurrent_starts_cannot_create_two_active_stage_attempts(
    postgres_factory,
) -> None:
    student_id = uuid4()
    with postgres_factory.begin() as db:
        db.add(UserRow(id=student_id, auth_subject=f"concurrent-start:{student_id}"))
    barrier = Barrier(2)

    def start(key: str) -> str:
        with postgres_factory() as db:
            manager = SessionManager(SqlAlchemySessionStartAdapter(db))
            command = StartSessionCommand(student_id, InterviewStage.SOFT_1, key, None)
            barrier.wait(timeout=5)
            try:
                manager.start(command)
                return "created"
            except Conflict:
                return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(start, (f"concurrent:{uuid4()}", f"concurrent:{uuid4()}")))
    assert sorted(outcomes) == ["conflict", "created"]
    with postgres_factory() as db:
        count = db.scalar(
            select(func.count(InterviewSessionRow.id)).where(
                InterviewSessionRow.student_id == student_id,
                InterviewSessionRow.stage == InterviewStage.SOFT_1.value,
                InterviewSessionRow.state.in_(
                    ("created", "awaiting_answer", "answer_processing", "awaiting_follow_up_answer")
                ),
            )
        )
        assert count == 1


def test_postgres_concurrent_duplicate_answer_command_is_applied_once(postgres_factory) -> None:
    student_id = uuid4()
    with postgres_factory.begin() as db:
        db.add(UserRow(id=student_id, auth_subject=f"concurrent-answer:{student_id}"))
        db.flush()
        session = InterviewSessionRow(
            student_id=student_id,
            stage="soft_1",
            idempotency_key=f"concurrent-answer-session:{uuid4()}",
        )
        db.add(session)
        db.flush()
        question = QuestionRow(
            session_id=session.id,
            sequence=1,
            kind="base",
            text="Describe your evidence.",
        )
        db.add(question)
        db.flush()
        session_id, question_id = session.id, question.id
    barrier = Barrier(2)

    def submit() -> str:
        try:
            with postgres_factory.begin() as db:
                barrier.wait(timeout=5)
                db.add(
                    AnswerRow(
                        session_id=session_id,
                        question_id=question_id,
                        idempotency_key="same-answer-command",
                        transcript="One application of this command.",
                    )
                )
            return "created"
        except IntegrityError:
            return "duplicate"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _index: submit(), range(2)))
    assert sorted(outcomes) == ["created", "duplicate"]
    with postgres_factory() as db:
        count = db.scalar(
            select(func.count(AnswerRow.id)).where(
                AnswerRow.session_id == session_id,
                AnswerRow.idempotency_key == "same-answer-command",
            )
        )
        assert count == 1


def test_postgres_http_concurrent_start_replays_same_idempotent_session(postgres_factory) -> None:
    student_id = uuid4()
    barrier = Barrier(2)
    payload = {"stage": "soft_1", "idempotency_key": f"start:{uuid4()}"}
    with _postgres_client(postgres_factory) as client:

        def start() -> object:
            barrier.wait(timeout=5)
            return client.post(
                "/api/v1/interviews",
                json=payload,
                headers={"X-Dev-User-ID": str(student_id)},
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(lambda _index: start(), range(2)))
        assert [response.status_code for response in responses] == [201, 201]
        assert responses[0].json()["id"] == responses[1].json()["id"]
        assert (
            responses[0].json()["active_question_id"] == responses[1].json()["active_question_id"]
        )

    with postgres_factory() as db:
        sessions = db.scalars(
            select(InterviewSessionRow).where(
                InterviewSessionRow.student_id == student_id,
                InterviewSessionRow.idempotency_key == payload["idempotency_key"],
            )
        ).all()
        assert len(sessions) == 1
        attempts = db.scalars(
            select(AssessmentAttemptRow).where(AssessmentAttemptRow.session_id == sessions[0].id)
        ).all()
        assert len(attempts) == 1
        assert (
            db.scalar(
                select(func.count(QuestionRow.id)).where(QuestionRow.session_id == sessions[0].id)
            )
            == 1
        )


def test_postgres_http_concurrent_answers_persist_once_and_replay(postgres_factory) -> None:
    student_id = uuid4()
    with _postgres_client(postgres_factory) as client:
        started = client.post(
            "/api/v1/interviews",
            json={"stage": "soft_1", "idempotency_key": f"answer-start:{uuid4()}"},
            headers={"X-Dev-User-ID": str(student_id)},
        )
        session_id = started.json()["id"]
        payload = {
            "question_id": started.json()["active_question_id"],
            "expected_version": started.json()["version"],
            "idempotency_key": f"answer:{uuid4()}",
            "text": _answer_text(),
        }
        barrier = Barrier(2)

        def submit() -> object:
            barrier.wait(timeout=5)
            return client.post(
                f"/api/v1/interviews/{session_id}/answers",
                json=payload,
                headers={"X-Dev-User-ID": str(student_id)},
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(lambda _index: submit(), range(2)))
        assert all(response.status_code in {200, 409} for response in responses)
        assert any(response.status_code == 200 for response in responses)
        replay = client.post(
            f"/api/v1/interviews/{session_id}/answers",
            json=payload,
            headers={"X-Dev-User-ID": str(student_id)},
        )
        assert replay.status_code == 200
        conflict = client.post(
            f"/api/v1/interviews/{session_id}/answers",
            json={**payload, "text": "Different content for the same idempotency key."},
            headers={"X-Dev-User-ID": str(student_id)},
        )
        assert conflict.status_code == 409
        stale = client.post(
            f"/api/v1/interviews/{session_id}/answers",
            json={**payload, "idempotency_key": f"stale:{uuid4()}", "expected_version": 0},
            headers={"X-Dev-User-ID": str(student_id)},
        )
        assert stale.status_code == 409

    with postgres_factory() as db:
        answers = db.scalars(
            select(AnswerRow).where(
                AnswerRow.session_id == session_id,
                AnswerRow.idempotency_key == payload["idempotency_key"],
            )
        ).all()
        assert len(answers) == 1 and answers[0].transcript == payload["text"]
        evaluations = db.scalars(
            select(EvaluationRow).where(EvaluationRow.answer_id == answers[0].id)
        ).all()
        assert len(evaluations) == 1
        session = db.get(InterviewSessionRow, session_id)
        assert session is not None and session.version == 3
        assert session.state == "awaiting_follow_up_answer"
        attempt = db.scalar(
            select(AssessmentAttemptRow).where(AssessmentAttemptRow.session_id == session_id)
        )
        assert attempt is not None
        assert db.get(AssessmentResultRow, attempt.id) is None


def test_postgres_late_provider_response_cannot_overwrite_recovered_session(
    postgres_factory,
) -> None:
    student_id = uuid4()
    provider_started = Event()
    allow_provider_result = Event()

    class BlockingProvider(FakeLLMProvider):
        def analyze_answer(self, prompt):
            provider_started.set()
            if not allow_provider_result.wait(timeout=10):
                raise TimeoutError("test synchronization timed out")
            return super().analyze_answer(prompt)

    blocking_provider = BlockingProvider()
    with _postgres_client(postgres_factory, blocking_provider) as client:
        headers = {"X-Dev-User-ID": str(student_id)}
        started = client.post(
            "/api/v1/interviews",
            json={"stage": "soft_1", "idempotency_key": f"late-start:{uuid4()}"},
            headers=headers,
        )
        session_id = started.json()["id"]
        payload = {
            "question_id": started.json()["active_question_id"],
            "expected_version": started.json()["version"],
            "idempotency_key": f"late-answer:{uuid4()}",
            "text": _answer_text(),
        }

        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(
                client.post,
                f"/api/v1/interviews/{session_id}/answers",
                json=payload,
                headers=headers,
            )
            assert provider_started.wait(timeout=5)
            with postgres_factory.begin() as db:
                session = db.get(InterviewSessionRow, session_id)
                assert session is not None and session.state == "answer_processing"
                session.processing_started_at = datetime.now(UTC) - timedelta(hours=1)
            recovered = client.post(
                f"/api/v1/interviews/{session_id}/answers", json=payload, headers=headers
            )
            assert recovered.status_code == 409
            with postgres_factory() as db:
                session = db.get(InterviewSessionRow, session_id)
                assert session is not None
                assert session.state == "awaiting_answer"
                recovered_version = session.version
                assert session.processing_started_at is None
            allow_provider_result.set()
            late = pending.result(timeout=10)
            assert late.status_code == 409

        with postgres_factory() as db:
            session = db.get(InterviewSessionRow, session_id)
            assert session is not None
            assert session.state == "awaiting_answer"
            assert session.version == recovered_version
            assert db.scalar(select(AnswerRow.id).where(AnswerRow.session_id == session_id)) is None
            assert (
                db.scalar(
                    select(EvaluationRow.id)
                    .join(AnswerRow, AnswerRow.id == EvaluationRow.answer_id)
                    .where(AnswerRow.session_id == session_id)
                )
                is None
            )
            attempt = db.scalar(
                select(AssessmentAttemptRow).where(AssessmentAttemptRow.session_id == session_id)
            )
            assert attempt is not None and attempt.status == "in_progress"


def test_postgres_provider_failure_releases_attempt_and_same_key_can_retry(
    postgres_factory,
) -> None:
    student_id = uuid4()

    class FlakyProvider(FakeLLMProvider):
        fail_analysis = True

        def analyze_answer(self, prompt):
            if self.fail_analysis:
                raise ProviderUnavailable("private provider diagnostic")
            return super().analyze_answer(prompt)

    provider = FlakyProvider()
    with _postgres_client(postgres_factory, provider) as client:
        headers = {"X-Dev-User-ID": str(student_id)}
        started = client.post(
            "/api/v1/interviews",
            json={"stage": "soft_1", "idempotency_key": f"failure-start:{uuid4()}"},
            headers=headers,
        )
        session_id = started.json()["id"]
        question = client.get(f"/api/v1/interviews/{session_id}/question", headers=headers).json()
        payload = {
            "question_id": question["id"],
            "expected_version": question["version"],
            "idempotency_key": f"failure-retry:{uuid4()}",
            "text": _answer_text(),
        }
        failed = client.post(
            f"/api/v1/interviews/{session_id}/answers", json=payload, headers=headers
        )
        assert failed.status_code == 503
        assert "private provider diagnostic" not in failed.text
        with postgres_factory() as db:
            row = db.get(InterviewSessionRow, session_id)
            assert row is not None
            assert row.state == "awaiting_answer" and row.version == 3
            assert row.processing_started_at is None
            assert db.scalar(select(AnswerRow.id).where(AnswerRow.session_id == session_id)) is None
            assert (
                db.scalar(
                    select(EvaluationRow.id)
                    .join(AnswerRow, AnswerRow.id == EvaluationRow.answer_id)
                    .where(AnswerRow.session_id == session_id)
                )
                is None
            )
            attempt = db.scalar(
                select(AssessmentAttemptRow).where(AssessmentAttemptRow.session_id == session_id)
            )
            assert attempt is not None and attempt.status == "in_progress"
            assert db.get(AssessmentResultRow, attempt.id) is None

        provider.fail_analysis = False
        refreshed = client.get(f"/api/v1/interviews/{session_id}/question", headers=headers).json()
        payload["expected_version"] = refreshed["version"]
        retried = client.post(
            f"/api/v1/interviews/{session_id}/answers", json=payload, headers=headers
        )
        assert retried.status_code == 200
        assert retried.json()["action"] == "follow_up"

    with postgres_factory() as db:
        answers = db.scalars(
            select(AnswerRow).where(
                AnswerRow.session_id == session_id,
                AnswerRow.idempotency_key == payload["idempotency_key"],
            )
        ).all()
        assert len(answers) == 1 and answers[0].transcript == payload["text"]
        assert (
            len(
                db.scalars(
                    select(EvaluationRow).where(EvaluationRow.answer_id == answers[0].id)
                ).all()
            )
            == 1
        )


def test_postgres_expired_reservation_rejects_provider_response_without_recovery_request(
    postgres_factory,
) -> None:
    student_id = uuid4()
    provider_started = Event()
    allow_provider_result = Event()

    class BlockingProvider(FakeLLMProvider):
        def analyze_answer(self, prompt):
            provider_started.set()
            if not allow_provider_result.wait(timeout=10):
                raise TimeoutError("test synchronization timed out")
            return super().analyze_answer(prompt)

    with _postgres_client(postgres_factory, BlockingProvider()) as client:
        headers = {"X-Dev-User-ID": str(student_id)}
        started = client.post(
            "/api/v1/interviews",
            json={"stage": "soft_1", "idempotency_key": f"expired-start:{uuid4()}"},
            headers=headers,
        )
        session_id = started.json()["id"]
        payload = {
            "question_id": started.json()["active_question_id"],
            "expected_version": started.json()["version"],
            "idempotency_key": f"expired-answer:{uuid4()}",
            "text": _answer_text(),
        }
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(
                client.post,
                f"/api/v1/interviews/{session_id}/answers",
                json=payload,
                headers=headers,
            )
            assert provider_started.wait(timeout=5)
            with postgres_factory.begin() as db:
                session = db.get(InterviewSessionRow, session_id)
                assert session is not None
                session.processing_started_at = datetime.now(UTC) - timedelta(hours=1)
            allow_provider_result.set()
            late = pending.result(timeout=10)
            assert late.status_code == 409

        with postgres_factory() as db:
            session = db.get(InterviewSessionRow, session_id)
            assert session is not None
            assert session.state == "awaiting_answer" and session.version == 3
            assert session.processing_started_at is None
            assert db.scalar(select(AnswerRow.id).where(AnswerRow.session_id == session_id)) is None
            attempt = db.scalar(
                select(AssessmentAttemptRow).where(AssessmentAttemptRow.session_id == session_id)
            )
            assert attempt is not None and attempt.status == "in_progress"


def test_postgres_start_revalidates_retake_policy_after_concurrent_completion(
    postgres_factory,
) -> None:
    student_id = uuid4()
    policy_settings = Settings(
        app_env="test",
        max_base_questions=1,
        max_follow_ups_per_question=0,
        max_clarifications_per_question=0,
        max_attempts_per_stage=1,
    )
    with _postgres_client(postgres_factory, settings=policy_settings) as regular_client:
        started = regular_client.post(
            "/api/v1/interviews",
            json={"stage": "soft_1", "idempotency_key": f"race-base:{uuid4()}"},
            headers={"X-Dev-User-ID": str(student_id)},
        )
        session_id = started.json()["id"]

    provider_started = Event()
    allow_question_result = Event()

    class BlockingQuestionProvider(FakeLLMProvider):
        def generate_question(self, prompt):
            provider_started.set()
            if not allow_question_result.wait(timeout=10):
                raise TimeoutError("test synchronization timed out")
            return super().generate_question(prompt)

    blocker = BlockingQuestionProvider()
    with (
        _postgres_client(postgres_factory, blocker, policy_settings) as start_client,
        _postgres_client(postgres_factory, settings=policy_settings) as answer_client,
    ):
        headers = {"X-Dev-User-ID": str(student_id)}
        start_payload = {"stage": "soft_1", "idempotency_key": f"race-retake:{uuid4()}"}
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending_start = pool.submit(
                start_client.post, "/api/v1/interviews", json=start_payload, headers=headers
            )
            assert provider_started.wait(timeout=5)
            answer_payload = {
                "question_id": started.json()["active_question_id"],
                "expected_version": started.json()["version"],
                "idempotency_key": f"race-completion:{uuid4()}",
                "text": _answer_text(),
            }
            completed = answer_client.post(
                f"/api/v1/interviews/{session_id}/answers",
                json=answer_payload,
                headers=headers,
            )
            assert completed.status_code == 200
            assert completed.json()["state"] == "completed"
            allow_question_result.set()
            rejected_start = pending_start.result(timeout=10)
            assert rejected_start.status_code == 409
            assert rejected_start.json()["error"]["code"] == "retake_policy_restriction"

    with postgres_factory() as db:
        sessions = db.scalars(
            select(InterviewSessionRow).where(InterviewSessionRow.student_id == student_id)
        ).all()
        assert len(sessions) == 1
        attempt = db.scalar(
            select(AssessmentAttemptRow).where(AssessmentAttemptRow.session_id == session_id)
        )
        assert attempt is not None and attempt.status in {"passed", "failed"}
        result = db.get(AssessmentResultRow, attempt.id)
        assert result is not None


def test_postgres_new_application_instance_recovers_persisted_expired_reservation(
    postgres_factory,
) -> None:
    student_id = uuid4()
    headers = {"X-Dev-User-ID": str(student_id)}
    with _postgres_client(postgres_factory) as first_instance:
        started = first_instance.post(
            "/api/v1/interviews",
            json={"stage": "soft_1", "idempotency_key": f"restart-start:{uuid4()}"},
            headers=headers,
        )
    session_id = started.json()["id"]
    with postgres_factory.begin() as db:
        session = db.get(InterviewSessionRow, session_id)
        assert session is not None
        session.state = "answer_processing"
        session.version += 1
        session.processing_started_at = datetime.now(UTC) - timedelta(hours=1)

    with _postgres_client(postgres_factory) as restarted_instance:
        payload = {
            "question_id": started.json()["active_question_id"],
            "expected_version": started.json()["version"] + 1,
            "idempotency_key": f"restart-answer:{uuid4()}",
            "text": _answer_text(),
        }
        recovered = restarted_instance.post(
            f"/api/v1/interviews/{session_id}/answers", json=payload, headers=headers
        )
        assert recovered.status_code == 409
        question = restarted_instance.get(
            f"/api/v1/interviews/{session_id}/question", headers=headers
        ).json()
        payload["expected_version"] = question["version"]
        retried = restarted_instance.post(
            f"/api/v1/interviews/{session_id}/answers", json=payload, headers=headers
        )
        assert retried.status_code == 200

    with postgres_factory() as db:
        session = db.get(InterviewSessionRow, session_id)
        assert session is not None and session.state == "awaiting_follow_up_answer"
        assert session.processing_started_at is None
        answers = db.scalars(select(AnswerRow).where(AnswerRow.session_id == session_id)).all()
        assert len(answers) == 1
        assert answers[0].idempotency_key == payload["idempotency_key"]
        evaluation = db.scalar(
            select(EvaluationRow).where(EvaluationRow.answer_id == answers[0].id)
        )
        assert evaluation is not None

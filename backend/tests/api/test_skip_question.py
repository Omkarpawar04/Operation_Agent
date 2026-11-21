import json
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from sqlalchemy import delete, select

from app.adapters.llm.fake import FakeLLMProvider
from app.api.dependencies import get_llm_provider, get_settings
from app.core.config import Settings
from app.db.models import (
    AnswerRow,
    AssessmentAttemptRow,
    AssessmentResultRow,
    EvaluationRow,
    QuestionBankRow,
)
from scripts.import_assessment_content import import_content

PACK_PATH = (
    Path(__file__).resolve().parents[3]
    / "docs"
    / "assessment-content"
    / "v1"
    / "finxl_assessment_content_v1.json"
)


def _load_pack() -> dict[str, object]:
    return json.loads(PACK_PATH.read_text(encoding="utf-8"))


def _bank_client(client_and_factory):
    client, factory = client_and_factory
    with factory() as db:
        import_content(db, _load_pack(), apply=True)
    client.app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None,
        app_env="test",
        dev_assessment_content_mode="question_bank",
        dev_assessment_allow_draft=True,
        max_base_questions=2,
        max_follow_ups_per_question=1,
    )
    client.app.dependency_overrides[get_llm_provider] = FakeLLMProvider
    return client, factory


def _start(client, user_id: str, key: str = "skip-test-start"):
    headers = {"X-Dev-User-ID": user_id}
    started = client.post(
        "/api/v1/interviews",
        json={"stage": "soft_1", "idempotency_key": key},
        headers=headers,
    )
    assert started.status_code == 201, started.text
    question = client.get(f"/api/v1/interviews/{started.json()['id']}/question", headers=headers)
    assert question.status_code == 200
    return started.json(), question.json(), headers


def test_skip_main_is_versioned_idempotent_and_rejects_later_answer(
    client_and_factory, dev_user_id
):
    client, factory = _bank_client(client_and_factory)
    started, question, headers = _start(client, dev_user_id)
    payload = {
        "question_id": question["id"],
        "expected_version": question["version"],
        "idempotency_key": "skip-main-once",
    }
    skipped = client.post(f"/api/v1/interviews/{started['id']}/skip", json=payload, headers=headers)
    assert skipped.status_code == 200, skipped.text
    assert skipped.json()["action"] == "next_question"
    current = client.get(f"/api/v1/interviews/{started['id']}/question", headers=headers).json()
    assert current["bank_question_id"] == "Q_CURR_FIN_11_soft_1_02"
    repeated = client.post(
        f"/api/v1/interviews/{started['id']}/skip", json=payload, headers=headers
    )
    assert repeated.status_code == 200
    assert repeated.json()["version"] == skipped.json()["version"]
    stale = client.post(
        f"/api/v1/interviews/{started['id']}/skip",
        json={**payload, "idempotency_key": "skip-main-stale"},
        headers=headers,
    )
    assert stale.status_code == 409
    later_answer = client.post(
        f"/api/v1/interviews/{started['id']}/answers",
        json={
            "question_id": question["id"],
            "expected_version": question["version"],
            "idempotency_key": "answer-after-skip",
            "text": "This answer must not apply to a skipped question.",
        },
        headers=headers,
    )
    assert later_answer.status_code == 409
    with factory() as db:
        rows = db.scalars(
            select(AnswerRow).where(AnswerRow.session_id == UUID(started["id"]))
        ).all()
        assert len(rows) == 1 and rows[0].is_skipped and rows[0].transcript == ""
        evaluations = db.scalars(
            select(EvaluationRow).where(EvaluationRow.answer_id == rows[0].id)
        ).one()
        assert evaluations.evidence_json
        assert all(item["correctness"] == 0 for item in evaluations.evidence_json)
    assert current["version"] == skipped.json()["version"]


def test_skipping_follow_up_advances_to_main_question_without_scoring_it(
    client_and_factory, dev_user_id
):
    client, factory = _bank_client(client_and_factory)
    started, question, headers = _start(client, dev_user_id, "skip-followup-start")
    answer = client.post(
        f"/api/v1/interviews/{started['id']}/answers",
        json={
            "question_id": question["id"],
            "expected_version": question["version"],
            "idempotency_key": "skip-followup-first-answer",
            "text": (
                "I compared both options, checked the assumptions, chose an approach "
                "and measured the outcome against the original target."
            ),
        },
        headers=headers,
    )
    assert answer.status_code == 200 and answer.json()["action"] == "follow_up"
    follow_up = client.get(f"/api/v1/interviews/{started['id']}/question", headers=headers).json()
    skipped = client.post(
        f"/api/v1/interviews/{started['id']}/skip",
        json={
            "question_id": follow_up["id"],
            "expected_version": follow_up["version"],
            "idempotency_key": "skip-followup-once",
        },
        headers=headers,
    )
    assert skipped.status_code == 200 and skipped.json()["action"] == "next_question"
    next_question = client.get(
        f"/api/v1/interviews/{started['id']}/question", headers=headers
    ).json()
    assert next_question["bank_question_id"] == "Q_CURR_FIN_11_soft_1_02"
    with factory() as db:
        answers = db.scalars(
            select(AnswerRow).where(AnswerRow.session_id == UUID(started["id"]))
        ).all()
        assert len(answers) == 2
        assert next(row for row in answers if row.question_id == UUID(follow_up["id"])).is_skipped
        followup_evaluation = db.scalar(
            select(EvaluationRow).where(
                EvaluationRow.answer_id
                == next(row.id for row in answers if row.question_id == UUID(follow_up["id"]))
            )
        )
        assert followup_evaluation is not None and followup_evaluation.evidence_json == []


def test_main_skip_is_zero_in_question_denominator(client_and_factory, dev_user_id):
    client, factory = _bank_client(client_and_factory)
    started, question, headers = _start(client, dev_user_id, "skip-scoring-start")
    first = client.post(
        f"/api/v1/interviews/{started['id']}/answers",
        json={
            "question_id": question["id"],
            "expected_version": question["version"],
            "idempotency_key": "skip-score-answer-one",
            "text": (
                "I compared both options, checked the assumptions, chose an approach "
                "and measured the outcome against the original target."
            ),
        },
        headers=headers,
    )
    assert first.status_code == 200 and first.json()["action"] == "follow_up"
    follow_up = client.get(f"/api/v1/interviews/{started['id']}/question", headers=headers).json()
    second = client.post(
        f"/api/v1/interviews/{started['id']}/answers",
        json={
            "question_id": follow_up["id"],
            "expected_version": follow_up["version"],
            "idempotency_key": "skip-score-answer-two",
            "text": (
                "I checked the result against the target and confirmed the expected improvement."
            ),
        },
        headers=headers,
    )
    assert second.status_code == 200 and second.json()["action"] == "next_question"
    next_question = client.get(
        f"/api/v1/interviews/{started['id']}/question", headers=headers
    ).json()
    completed = client.post(
        f"/api/v1/interviews/{started['id']}/skip",
        json={
            "question_id": next_question["id"],
            "expected_version": next_question["version"],
            "idempotency_key": "skip-score-main-two",
        },
        headers=headers,
    )
    assert completed.status_code == 200 and completed.json()["state"] == "completed"
    result_response = client.get(f"/api/v1/interviews/{started['id']}/assessment", headers=headers)
    assert result_response.status_code == 200
    assert Decimal(result_response.json()["score"]) == Decimal("37.5")
    with factory() as db:
        attempt = db.scalar(select(AssessmentAttemptRow))
        result = db.scalar(select(AssessmentResultRow))
        assert attempt is not None and attempt.status == "failed"
        assert result is not None and Decimal(result.score) == Decimal("37.5") and not result.passed


def test_no_eligible_follow_up_advances_to_next_base_question(client_and_factory, dev_user_id):
    client, factory = _bank_client(client_and_factory)
    with factory() as db:
        db.execute(delete(QuestionBankRow).where(QuestionBankRow.category == "follow_up"))
        db.commit()
    started, question, headers = _start(client, dev_user_id, "no-followup-start")
    answer = client.post(
        f"/api/v1/interviews/{started['id']}/answers",
        json={
            "question_id": question["id"],
            "expected_version": question["version"],
            "idempotency_key": "no-followup-answer",
            "text": (
                "I compared both options, checked assumptions and measured the outcome "
                "against the target."
            ),
        },
        headers=headers,
    )
    assert answer.status_code == 200 and answer.json()["action"] == "next_question"
    current = client.get(f"/api/v1/interviews/{started['id']}/question", headers=headers).json()
    assert current["bank_question_id"] == "Q_CURR_FIN_11_soft_1_02"

import json
from pathlib import Path
from uuid import UUID

from sqlalchemy import select

from app.adapters.llm.fake import FakeLLMProvider
from app.api.dependencies import get_llm_provider
from app.core.config import Settings, get_settings
from app.db.models import AssessmentAttemptRow, AssessmentResultRow, QuestionRow
from scripts.import_assessment_content import import_content

PACK_PATH = (
    Path(__file__).resolve().parents[3]
    / "docs"
    / "assessment-content"
    / "v1"
    / "finxl_assessment_content_v1.json"
)


def _load_pack():
    return json.loads(PACK_PATH.read_text(encoding="utf-8"))


class QuestionCallSpy(FakeLLMProvider):
    question_calls = 0

    def generate_question(self, prompt):
        self.question_calls += 1
        return super().generate_question(prompt)


def test_development_bank_mode_starts_with_imported_draft_and_persists_provenance(
    client_and_factory, dev_user_id: str
) -> None:
    client, factory = client_and_factory
    with factory() as session:
        import_content(session, _load_pack(), apply=True)
    settings = Settings(
        _env_file=None,
        app_env="test",
        dev_assessment_content_mode="question_bank",
        dev_assessment_allow_draft=True,
    )
    client.app.dependency_overrides[get_settings] = lambda: settings
    provider = QuestionCallSpy()
    client.app.dependency_overrides[get_llm_provider] = lambda: provider
    headers = {"X-Dev-User-ID": dev_user_id}

    started = client.post(
        "/api/v1/interviews",
        json={"stage": "soft_1", "idempotency_key": "imported-bank-start"},
        headers=headers,
    )
    assert started.status_code == 201, started.text
    question_response = client.get(
        f"/api/v1/interviews/{started.json()['id']}/question", headers=headers
    )
    assert question_response.status_code == 200
    body = question_response.json()
    expected = next(
        item["text"]
        for item in _load_pack()["questions"]
        if item["question_id"] == "Q_CURR_FIN_11_soft_1_01"
    )
    assert body["text"] == expected
    assert body["stage_id"] == "soft_1"
    assert body["content_origin"] == "development_assessment_bank"
    assert body["content_approval_status"] == "draft"
    assert body["bank_question_id"] == "Q_CURR_FIN_11_soft_1_01"
    assert body["competency_id"] == "FIN_FOUNDATIONS_COMM"
    assert body["rubric_version_id"] == "R_FIN_FOUNDATIONS_COMM_V1_1"
    assert body["content_version"] == "1.1.0"
    assert body["development_only"] is True
    assert provider.question_calls == 0

    with factory() as session:
        stored = session.get(QuestionRow, UUID(body["id"]))
        assert stored is not None
        provenance = stored.provenance_json
        assert provenance is not None
        assert provenance["provider_name"] == "question_bank"
        assert provenance["origin"] == "development_assessment_bank"
        assert provenance["approval_status"] == "draft"
        assert provenance["bank_question_id"] == "Q_CURR_FIN_11_soft_1_01"
        assert provenance["competency_id"] == "FIN_FOUNDATIONS_COMM"
        assert provenance["rubric_version_id"] == "R_FIN_FOUNDATIONS_COMM_V1_1"
        assert provenance["content_version"] == "1.1.0"

    answer = client.post(
        f"/api/v1/interviews/{started.json()['id']}/answers",
        json={
            "question_id": body["id"],
            "expected_version": body["version"],
            "idempotency_key": "bank-follow-up-answer",
            "text": (
                "I compared the available options, reviewed the financial statements, "
                "discussed assumptions, selected an approach, implemented it, and measured "
                "the outcome against the original target."
            ),
        },
        headers=headers,
    )
    assert answer.status_code == 200, answer.text
    assert answer.json()["action"] == "follow_up"
    follow_up = client.get(f"/api/v1/interviews/{started.json()['id']}/question", headers=headers)
    assert follow_up.status_code == 200
    follow_up_body = follow_up.json()
    assert follow_up_body["kind"] == "follow_up"
    assert follow_up_body["content_origin"] == "development_assessment_bank"
    assert follow_up_body["content_approval_status"] == "draft"
    assert follow_up_body["bank_question_id"] == "FU_Q_CURR_FIN_11_soft_1_01_01"
    assert follow_up_body["parent_question_id"] == "Q_CURR_FIN_11_soft_1_01"
    assert provider.question_calls == 0


def test_short_bank_answer_uses_follow_up_candidate_instead_of_missing_clarification(
    client_and_factory, dev_user_id: str
) -> None:
    client, factory = client_and_factory
    with factory() as session:
        import_content(session, _load_pack(), apply=True)
    settings = Settings(
        _env_file=None,
        app_env="test",
        dev_assessment_content_mode="question_bank",
        dev_assessment_allow_draft=True,
    )
    client.app.dependency_overrides[get_settings] = lambda: settings
    provider = QuestionCallSpy()
    client.app.dependency_overrides[get_llm_provider] = lambda: provider
    headers = {"X-Dev-User-ID": dev_user_id}
    started = client.post(
        "/api/v1/interviews",
        json={"stage": "soft_1", "idempotency_key": "short-bank-answer-start"},
        headers=headers,
    )
    question = client.get(
        f"/api/v1/interviews/{started.json()['id']}/question", headers=headers
    ).json()
    response = client.post(
        f"/api/v1/interviews/{started.json()['id']}/answers",
        json={
            "question_id": question["id"],
            "expected_version": question["version"],
            "idempotency_key": "short-bank-answer-submit",
            "text": "I reviewed the options and chose one.",
        },
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["action"] == "follow_up"
    current = client.get(
        f"/api/v1/interviews/{started.json()['id']}/question", headers=headers
    ).json()
    assert current["kind"] == "follow_up"
    assert current["bank_question_id"] == "FU_Q_CURR_FIN_11_soft_1_01_01"
    assert provider.question_calls == 0
    with factory() as session:
        attempt = session.scalar(select(AssessmentAttemptRow))
        assert attempt is not None and attempt.status == "in_progress"
        assert session.scalar(select(AssessmentResultRow.attempt_id)) is None


def test_draft_bank_without_explicit_draft_opt_in_fails_without_fixture_fallback(
    client_and_factory, dev_user_id: str
) -> None:
    client, factory = client_and_factory
    with factory() as session:
        import_content(session, _load_pack(), apply=True)
    settings = Settings(
        _env_file=None,
        app_env="test",
        dev_assessment_content_mode="question_bank",
        dev_assessment_allow_draft=False,
    )
    client.app.dependency_overrides[get_settings] = lambda: settings
    provider = QuestionCallSpy()
    client.app.dependency_overrides[get_llm_provider] = lambda: provider

    response = client.post(
        "/api/v1/interviews",
        json={"stage": "soft_1", "idempotency_key": "draft-not-enabled"},
        headers={"X-Dev-User-ID": dev_user_id},
    )
    assert response.status_code == 409
    assert "No eligible development assessment questions" in response.text
    assert provider.question_calls == 0

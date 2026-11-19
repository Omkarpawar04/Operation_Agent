"""Integration coverage for document intake, history, and reconnect APIs."""

import asyncio

import pytest
from fastapi.testclient import TestClient

import main
from storage.db import Database


@pytest.fixture
def api_environment(tmp_path, monkeypatch):
    db = Database(tmp_path / "api_interviews.db")
    monkeypatch.setattr(main, "database", db)
    with TestClient(main.app) as client:
        yield client, db


def test_upload_text_extraction_and_history(api_environment):
    client, _ = api_environment
    response = client.post(
        "/api/extract",
        files={"file": ("resume.txt", b"Python engineer", "text/plain")},
    )
    assert response.status_code == 200
    assert response.json()["text"] == "Python engineer"
    assert client.get("/api/interviews").json() == {"interviews": []}


def test_upload_rejects_unsupported_type(api_environment):
    client, _ = api_environment
    response = client.post(
        "/api/extract",
        files={"file": ("resume.exe", b"not a resume", "application/octet-stream")},
    )
    assert response.status_code == 415


def test_resume_session_restores_question(api_environment):
    client, db = api_environment
    plan = {"total_questions": 1, "questions": [
        {"id": "q1", "question": "Tell me about your work.", "category": "warmup"}
    ]}
    asyncio.run(db.create_session(
        session_id="resumable", candidate_name="Test",
        interview_plan=plan,
        tts_voice="bm_george",
    ))
    asyncio.run(db.update_session("resumable", status="in_progress"))
    asyncio.run(db.save_turn("resumable", "assistant", "Tell me about your work.",
                             "question", {"question_id": "q1"}))
    with client.websocket_connect("/ws/interview") as websocket:
        assert websocket.receive_json()["event"] == "connection_ready"
        websocket.send_json({"event": "recording_consent", "accepted": True})
        assert websocket.receive_json()["event"] == "recording_consent_status"
        websocket.send_json({"event": "recording_status", "active": True})
        assert websocket.receive_json()["event"] == "recording_status"
        websocket.send_json({"event": "resume_session", "session_id": "resumable"})
        resumed = websocket.receive_json()
    assert resumed["event"] == "interview_started"
    assert resumed["resumed"] is True
    assert resumed["question"]["id"] == "q1"
    assert resumed["tts_voice"] == "bm_george"


def test_voice_catalog_and_preview_use_supported_or_default_voice(api_environment, monkeypatch):
    client, _ = api_environment
    requested = []

    async def fake_preview(text, *, voice):
        requested.append((text, voice))
        return b"RIFF-preview"

    monkeypatch.setattr(
        main.kokoro_tts_service,
        "synthesize_wav",
        fake_preview,
    )

    catalog = client.get("/api/tts/voices").json()
    valid_preview = client.post("/api/tts/preview", json={"voice_id": "bm_george"})
    invalid_preview = client.post("/api/tts/preview", json={"voice_id": "unknown_voice"})

    assert len(catalog["voices"]) == 28
    assert catalog["default_voice"] == "af_heart"
    assert valid_preview.status_code == 200
    assert valid_preview.headers["content-type"].startswith("audio/wav")
    assert valid_preview.headers["X-Kokoro-Voice"] == "bm_george"
    assert invalid_preview.headers["X-Kokoro-Voice"] == "af_heart"
    assert [voice for _, voice in requested] == ["bm_george", "af_heart"]


def test_report_not_found_until_evaluation_saved(api_environment):
    client, db = api_environment
    asyncio.run(db.create_session(session_id="pending-report"))
    response = client.get("/api/interviews/pending-report/report")
    assert response.status_code == 404


def test_evaluation_retry_persists_report(api_environment, monkeypatch):
    client, db = api_environment
    asyncio.run(db.create_session(
        session_id="completed-session",
        candidate_profile={"name": "Test"},
        job_profile={"job_title": "Engineer"},
        interview_plan={"questions": []},
    ))
    asyncio.run(db.update_session("completed-session", status="completed"))
    asyncio.run(db.save_turn("completed-session", "user", "I built a reliable API."))

    class FakeEvaluation:
        def model_dump(self, mode=None):
            return {"overall_score": 7.5, "recommendation": "advance"}

    class FakeEvaluator:
        async def evaluate_interview(self, **kwargs):
            assert kwargs["conversation_history"]
            return FakeEvaluation()

        @staticmethod
        def calculate_overall_score(_evaluation):
            return 7.5

    monkeypatch.setattr(main, "evaluator", FakeEvaluator())
    response = client.post("/api/interviews/completed-session/evaluate")
    assert response.status_code == 200
    assert response.json()["overall_score"] == 7.5
    saved = asyncio.run(db.get_session("completed-session"))
    assert saved["evaluation_report"]["recommendation"] == "advance"
    assert client.get("/api/interviews/completed-session/report").status_code == 200


"""
WebSocket integration tests.

Tests the interview lifecycle without making real AI API calls.
"""

import asyncio
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import main
from storage.db import Database


# --------------------------------------------------
# MOCK INTERVIEW DATA
# --------------------------------------------------

CANDIDATE_PROFILE = {
    "name": "Test Candidate",
    "skills": ["Python", "SQL"],
}

JOB_PROFILE = {
    "job_title": "Junior Python Developer",
    "required_skills": ["Python", "SQL"],
}

INTERVIEW_PLAN = {
    "total_questions": 2,
    "questions": [
        {
            "id": "Q1",
            "category": "warmup",
            "difficulty": "easy",
            "question": "Tell me about yourself.",
        },
        {
            "id": "Q2",
            "category": "technical",
            "difficulty": "medium",
            "question": "What is the difference between a list and a tuple?",
        },
    ],
}


# --------------------------------------------------
# MOCK AI PLANNER
# --------------------------------------------------

class FakePlanner:

    async def generate_plan(
        self,
        resume_text: str,
        job_description: str,
    ):
        return SimpleNamespace(
            candidate_profile=SimpleNamespace(
                model_dump=lambda mode=None: CANDIDATE_PROFILE
            ),
            job_profile=SimpleNamespace(
                model_dump=lambda mode=None: JOB_PROFILE
            ),
            interview_plan=SimpleNamespace(
                model_dump=lambda mode=None: INTERVIEW_PLAN
            ),
        )


# --------------------------------------------------
# MOCK AI INTERVIEWER
# --------------------------------------------------

class FakeInterviewerReply:

    def __init__(
        self,
        text="Good explanation. Let's move to the next question.",
        action="continue",
        question_id="Q2",
        interview_complete=False,
    ):
        self.text = text
        self.action = action
        self.question_id = question_id
        self.interview_complete = interview_complete


async def fake_generate_response(**kwargs):
    """Return a predictable interviewer response."""

    assert kwargs["candidate_message"]

    return FakeInterviewerReply()


# --------------------------------------------------
# TEST FIXTURE
# --------------------------------------------------

@pytest.fixture
def test_environment(tmp_path, monkeypatch):
    """Create an isolated database and mock AI agents."""

    test_database = Database(
        tmp_path / "test_interviews.db"
    )

    monkeypatch.setattr(
        main,
        "database",
        test_database,
    )

    monkeypatch.setattr(
        main,
        "InterviewPlanner",
        FakePlanner,
    )

    monkeypatch.setattr(main, "voice_services_missing", lambda: [])

    monkeypatch.setattr(
        main.interviewer,
        "generate_response",
        fake_generate_response,
    )

    with TestClient(main.app) as client:
        yield client, test_database


# --------------------------------------------------
# HELPER: START AN INTERVIEW
# --------------------------------------------------

def start_test_interview(websocket):

    websocket.send_json({
        "event": "start_interview",
        "candidate_name": "Test Candidate",
        "resume_text": "Python developer with SQL experience.",
        "job_description": (
            "We are looking for a junior Python developer."
        ),
    })

    planning_event = websocket.receive_json()
    started_event = websocket.receive_json()

    assert planning_event["event"] == "planning_started"
    assert started_event["event"] == "interview_started"

    return started_event


# --------------------------------------------------
# TEST 1: WEBSOCKET CONNECTION
# --------------------------------------------------

def test_websocket_connection(test_environment):

    client, _ = test_environment

    with client.websocket_connect("/ws/interview") as websocket:

        response = websocket.receive_json()

        assert response["event"] == "connection_ready"
        assert response["success"] is True


# --------------------------------------------------
# TEST 2: START INTERVIEW
# --------------------------------------------------

def test_start_interview(test_environment):

    client, test_database = test_environment

    with client.websocket_connect("/ws/interview") as websocket:

        connection_event = websocket.receive_json()

        assert connection_event["event"] == "connection_ready"

        response = start_test_interview(websocket)

        assert response["success"] is True
        assert response["candidate_profile"]["name"] == "Test Candidate"
        assert response["total_questions"] == 2

        assert response["question"]["id"] == "Q1"
        assert response["question"]["text"] == "Tell me about yourself."

        session_id = response["session_id"]

        # Verify session persistence.
        session = asyncio.run(
            test_database.get_session(session_id)
        )

        assert session is not None
        assert session["status"] == "in_progress"

        # Verify the first question was saved.
        turns = asyncio.run(
            test_database.get_turns(session_id)
        )

        assert len(turns) == 2
        assert turns[0]["role"] == "assistant"
        assert turns[0]["turn_type"] == "greeting"
        assert turns[1]["content"] == "Tell me about yourself."


def test_voice_session_refuses_text_only_provider_fallback(test_environment, monkeypatch):
    client, _ = test_environment
    monkeypatch.setattr(main, "voice_services_missing", lambda: ["DEEPGRAM_API_KEY"])
    with client.websocket_connect("/ws/interview") as websocket:
        websocket.receive_json()
        websocket.send_json({
            "event": "start_interview",
            "resume_text": "Python developer.",
            "job_description": "Python role.",
        })
        error = websocket.receive_json()
    assert error["event"] == "interview_error"
    assert error["code"] == "VOICE_CONFIGURATION_MISSING"


# --------------------------------------------------
# TEST 3: SUBMIT ANSWER
# --------------------------------------------------

def test_submit_answer(test_environment):

    client, test_database = test_environment

    with client.websocket_connect("/ws/interview") as websocket:

        websocket.receive_json()

        started_event = start_test_interview(websocket)

        session_id = started_event["session_id"]

        websocket.send_json({
            "event": "submit_answer",
            "text": (
                "I am a Python developer with experience "
                "in SQL and backend development."
            ),
        })

        response = websocket.receive_json()

        assert response["event"] == "interviewer_response"
        assert response["success"] is True
        assert response["text"] == (
            "Good explanation. Let's move to the next question."
        )

        assert response["action"] == "continue"
        assert response["interview_complete"] is False

        # Verify candidate answer and AI response were saved.
        turns = asyncio.run(
            test_database.get_turns(session_id)
        )

        assert len(turns) == 4

        assert turns[0]["role"] == "assistant"
        assert turns[2]["role"] == "user"
        assert turns[3]["role"] == "assistant"

        assert "Python developer" in turns[2]["content"]


# --------------------------------------------------
# TEST 4: REJECT ANSWER WITHOUT ACTIVE SESSION
# --------------------------------------------------

def test_submit_answer_without_session(test_environment):

    client, _ = test_environment

    with client.websocket_connect("/ws/interview") as websocket:

        websocket.receive_json()

        websocket.send_json({
            "event": "submit_answer",
            "text": "My answer.",
        })

        response = websocket.receive_json()

        assert response["event"] == "interview_error"
        assert response["code"] == "NO_ACTIVE_SESSION"


# --------------------------------------------------
# TEST 5: END INTERVIEW
# --------------------------------------------------

def test_end_interview(test_environment):

    client, test_database = test_environment

    with client.websocket_connect("/ws/interview") as websocket:

        websocket.receive_json()

        started_event = start_test_interview(websocket)

        session_id = started_event["session_id"]

        websocket.send_json({
            "event": "end_interview",
        })

        response = websocket.receive_json()

        assert response["event"] == "interview_completed"
        assert response["success"] is True
        assert response["session_id"] == session_id

        session = asyncio.run(
            test_database.get_session(session_id)
        )

        assert session["status"] == "completed"

# --------------------------------------------------
# TEST 6: REJECT AUDIO BEFORE AUDIO IS ENABLED
# --------------------------------------------------

def test_binary_audio_before_start(test_environment):

    client, _ = test_environment

    with client.websocket_connect("/ws/interview") as websocket:

        websocket.receive_json()

        websocket.send_bytes(bytes(640))

        response = websocket.receive_json()

        assert response["event"] == "interview_error"
        assert response["code"] == "AUDIO_NOT_STARTED"


# --------------------------------------------------
# TEST 7: START AUDIO PROCESSING
# --------------------------------------------------

def test_start_audio(test_environment):

    client, _ = test_environment

    with client.websocket_connect("/ws/interview") as websocket:

        websocket.receive_json()

        start_test_interview(websocket)

        websocket.send_json({
            "event": "start_audio",
        })

        response = websocket.receive_json()

        assert response["event"] == "audio_ready"
        assert response["success"] is True
        assert response["input_sample_rate"] == 16000
        assert response["output_sample_rate"] == 24000
        assert response["format"] == "pcm_s16le"


# --------------------------------------------------
# TEST 8: RECEIVE BINARY AUDIO AND STOP AUDIO
# --------------------------------------------------

def test_receive_binary_audio_and_stop(test_environment):

    client, _ = test_environment

    with client.websocket_connect("/ws/interview") as websocket:

        websocket.receive_json()

        start_test_interview(websocket)

        websocket.send_json({
            "event": "start_audio",
        })

        ready = websocket.receive_json()

        assert ready["event"] == "audio_ready"

        # Send one 20 ms frame of silent PCM audio.
        websocket.send_bytes(bytes(640))

        # Stop audio processing.
        websocket.send_json({
            "event": "stop_audio",
        })

        response = websocket.receive_json()

        assert response["event"] == "audio_stopped"
        assert response["success"] is True

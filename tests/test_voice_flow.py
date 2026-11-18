
"""
End-to-end voice pipeline tests.

Tests:
- Binary audio reception.
- Speech detection events.
- Audio transcription.
- AI interviewer response.
- Streaming TTS audio.
- Multiple utterances in one audio chunk.

All external services are mocked.
No API keys or real API calls are required.
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
# MOCK PLANNER
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
# MOCK INTERVIEWER
# --------------------------------------------------

class FakeInterviewerReply:

    def __init__(self):
        self.text = "Good explanation. Let's move to the next question."
        self.action = "continue"
        self.question_id = "Q2"
        self.interview_complete = False


async def fake_generate_response(**kwargs):

    assert kwargs["candidate_message"].strip()

    return FakeInterviewerReply()


# --------------------------------------------------
# MOCK AUDIO PROCESSOR
# --------------------------------------------------

class FakeAudioProcessor:

    instances = []

    def __init__(self):

        self.sample_rate = 16000
        self.result = None

        FakeAudioProcessor.instances.append(self)

    def process_audio(self, audio_chunk: bytes):

        assert isinstance(audio_chunk, bytes)
        assert audio_chunk

        if self.result is None:
            raise AssertionError(
                "No fake audio processing result configured."
            )

        return self.result

    def reset(self):
        self.result = None


# --------------------------------------------------
# MOCK FALLBACK VOICE PIPELINE
# --------------------------------------------------

class FakeFallbackVoicePipeline:

    instances = []

    def __init__(self, interviewer=None):

        self.interviewer = interviewer
        self.transcribed_audio = []
        self.spoken_texts = []

        self.transcripts = {
            b"utterance-1": (
                "I have experience working with Python."
            ),
            b"utterance-2": (
                "A list is mutable while a tuple is immutable."
            ),
        }

        FakeFallbackVoicePipeline.instances.append(self)

    async def transcribe_audio(
        self,
        audio: bytes,
        sample_rate: int | None = None,
        keyterms: list[str] | None = None,
    ):

        assert sample_rate == 16000

        self.transcribed_audio.append(audio)

        transcript = self.transcripts.get(audio)

        if transcript is None:
            raise AssertionError(
                f"Unexpected audio received: {audio!r}"
            )

        return transcript

    async def stream_speech(self, text: str):

        assert text.strip()
        self.spoken_texts.append(text)

        yield b"fake-tts-audio-chunk-1"
        yield b"fake-tts-audio-chunk-2"

    async def close(self):
        pass


# --------------------------------------------------
# TEST FIXTURE
# --------------------------------------------------

@pytest.fixture
def voice_environment(tmp_path, monkeypatch):
    """Prepare isolated database and mocked voice services."""

    test_database = Database(
        tmp_path / "voice_test_interviews.db"
    )

    FakeAudioProcessor.instances.clear()
    FakeFallbackVoicePipeline.instances.clear()

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

    monkeypatch.setattr(
        main,
        "WebSocketAudioProcessor",
        FakeAudioProcessor,
    )

    monkeypatch.setattr(
        main,
        "FallbackVoicePipeline",
        FakeFallbackVoicePipeline,
    )

    with TestClient(main.app) as client:
        yield (
            client,
            test_database,
        )


# --------------------------------------------------
# HELPER: START INTERVIEW
# --------------------------------------------------

def start_test_interview(websocket):

    websocket.send_json({
        "event": "start_interview",
        "candidate_name": "Test Candidate",
        "resume_text": (
            "Python developer with SQL experience."
        ),
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
# HELPER: ENABLE AUDIO
# --------------------------------------------------

def enable_audio(websocket):

    websocket.send_json({
        "event": "start_audio",
    })

    response = websocket.receive_json()

    assert response["event"] == "audio_ready"
    assert response["success"] is True


# --------------------------------------------------
# HELPER: CREATE COMPLETED AUDIO RESULT
# --------------------------------------------------

def create_audio_result(utterances):

    return SimpleNamespace(
        events=[
            "speech_started",
            "speech",
            "speech_ended",
        ],
        speech_started=True,
        speech_ended=True,
        completed_audio=(
            utterances[0] if utterances else None
        ),
        completed_utterances=utterances,
        audio_duration_ms=1000.0,
    )


# --------------------------------------------------
# HELPER: VERIFY ONE COMPLETE VOICE TURN
# --------------------------------------------------

def receive_voice_turn(websocket, expected_transcript):

    # Transcription begins.
    event = websocket.receive_json()

    assert event["event"] == "transcription_started"
    assert event["success"] is True

    # Transcription result.
    event = websocket.receive_json()

    assert event["event"] == "transcript_received"
    assert event["success"] is True
    assert event["text"] == expected_transcript

    # AI interviewer response.
    event = websocket.receive_json()

    assert event["event"] == "interviewer_response"
    assert event["success"] is True
    assert event["source"] == "voice"
    assert event["text"] == (
        "Good explanation. Let's move to the next question."
    )

    # Kokoro synthesis begins; it may load local model assets on first use.
    event = websocket.receive_json()
    assert event["event"] == "audio_generating"
    assert event["provider"] == "kokoro-local"

    # Audio is sent after the local WAV has been generated and validated.
    event = websocket.receive_json()

    assert event["event"] == "audio_started"
    assert event["success"] if "success" in event else True
    assert event["sample_rate"] == 24000
    assert event["format"] == "pcm_s16le"

    # Receive streamed binary audio.
    audio_chunk_1 = websocket.receive_bytes()
    audio_chunk_2 = websocket.receive_bytes()

    assert audio_chunk_1 == b"fake-tts-audio-chunk-1"
    assert audio_chunk_2 == b"fake-tts-audio-chunk-2"

    # TTS completes.
    event = websocket.receive_json()

    assert event["event"] == "audio_completed"
    assert event["success"] is True


# --------------------------------------------------
# TEST 1: COMPLETE SINGLE VOICE TURN
# --------------------------------------------------

def test_complete_voice_interview_turn(voice_environment):

    client, test_database = voice_environment

    with client.websocket_connect("/ws/interview") as websocket:

        # Establish connection.
        connection = websocket.receive_json()

        assert connection["event"] == "connection_ready"

        # Start interview.
        started = start_test_interview(websocket)

        session_id = started["session_id"]

        # Enable microphone processing.
        enable_audio(websocket)

        processor = FakeAudioProcessor.instances[-1]

        processor.result = create_audio_result([
            b"utterance-1",
        ])

        # Send simulated microphone audio.
        websocket.send_bytes(bytes(640))

        # Speech detection events.
        event = websocket.receive_json()

        assert event["event"] == "speech_started"

        event = websocket.receive_json()

        assert event["event"] == "speech_ended"
        assert event["completed_utterances"] == 1

        # Verify transcription, AI response and TTS.
        receive_voice_turn(
            websocket,
            "I have experience working with Python.",
        )

        # Verify audio was transcribed.
        pipeline = FakeFallbackVoicePipeline.instances[-1]

        assert pipeline.transcribed_audio == [
            b"utterance-1",
        ]

        # Verify conversation persistence.
        turns = asyncio.run(
            test_database.get_turns(session_id)
        )

        assert len(turns) == 4

        assert turns[0]["role"] == "assistant"
        assert turns[2]["role"] == "user"
        assert turns[3]["role"] == "assistant"

        assert turns[2]["content"] == (
            "I have experience working with Python."
        )


def test_start_automatically_speaks_greeting_and_first_question(voice_environment):
    client, _ = voice_environment
    with client.websocket_connect("/ws/interview") as websocket:
        websocket.receive_json()
        started = start_test_interview(websocket)
        assert started["greeting"].startswith("Hello Test Candidate")
        enable_audio(websocket)
        websocket.send_json({"event": "audio_client_ready"})
        assert websocket.receive_json()["event"] == "audio_generating"
        assert websocket.receive_json()["event"] == "audio_started"
        assert websocket.receive_bytes() == b"fake-tts-audio-chunk-1"
        assert websocket.receive_bytes() == b"fake-tts-audio-chunk-2"
        assert websocket.receive_json()["event"] == "audio_completed"
        spoken = FakeFallbackVoicePipeline.instances[-1].spoken_texts[0]
        assert len(FakeFallbackVoicePipeline.instances[-1].spoken_texts) == 1
        assert "Hello Test Candidate" in spoken
        assert "Tell me about yourself." in spoken


# --------------------------------------------------
# TEST 2: MULTIPLE UTTERANCES IN ONE AUDIO CHUNK
# --------------------------------------------------

def test_process_multiple_voice_utterances(voice_environment):

    client, test_database = voice_environment

    with client.websocket_connect("/ws/interview") as websocket:

        websocket.receive_json()

        started = start_test_interview(websocket)

        session_id = started["session_id"]

        enable_audio(websocket)

        processor = FakeAudioProcessor.instances[-1]

        processor.result = create_audio_result([
            b"utterance-1",
            b"utterance-2",
        ])

        # One incoming audio chunk contains two utterances.
        websocket.send_bytes(bytes(1280))

        # Speech events are sent once for this processing call.
        event = websocket.receive_json()

        assert event["event"] == "speech_started"

        event = websocket.receive_json()

        assert event["event"] == "speech_ended"
        assert event["completed_utterances"] == 2

        # First utterance.
        receive_voice_turn(
            websocket,
            "I have experience working with Python.",
        )

        # Second utterance.
        receive_voice_turn(
            websocket,
            "A list is mutable while a tuple is immutable.",
        )

        # Verify both utterances reached transcription.
        pipeline = FakeFallbackVoicePipeline.instances[-1]

        assert pipeline.transcribed_audio == [
            b"utterance-1",
            b"utterance-2",
        ]

        # Verify both answers were persisted.
        turns = asyncio.run(
            test_database.get_turns(session_id)
        )

        assert len(turns) == 6

        assert turns[2]["role"] == "user"
        assert turns[2]["content"] == (
            "I have experience working with Python."
        )

        assert turns[4]["role"] == "user"
        assert turns[4]["content"] == (
            "A list is mutable while a tuple is immutable."
        )


# --------------------------------------------------
# TEST 3: STOP AUDIO AFTER VOICE PROCESSING
# --------------------------------------------------

def test_stop_audio_after_voice_turn(voice_environment):

    client, _ = voice_environment

    with client.websocket_connect("/ws/interview") as websocket:

        websocket.receive_json()

        start_test_interview(websocket)

        enable_audio(websocket)

        websocket.send_json({
            "event": "stop_audio",
        })

        response = websocket.receive_json()

        assert response["event"] == "audio_stopped"
        assert response["success"] is True

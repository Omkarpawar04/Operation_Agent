
"""
Database integration tests.

Tests session creation, conversation persistence,
retrieval, and session updates.
"""

import pytest

from storage.db import Database, ActiveSessionLimitError


@pytest.mark.asyncio
async def test_database_initialization(tmp_path):
    """Database initialization should create the database file."""

    database_path = tmp_path / "test_interviews.db"
    db = Database(database_path)

    await db.initialize()

    assert database_path.exists()


@pytest.mark.asyncio
async def test_create_and_retrieve_session(tmp_path):
    """A created session should be retrievable."""

    db = Database(tmp_path / "test_interviews.db")
    await db.initialize()

    session = await db.create_session(
        session_id="test-session-001",
        candidate_name="Test Candidate",
        job_title="Software Developer",
        candidate_profile={"skills": ["Python", "SQL"]},
        job_profile={"title": "Software Developer"},
        interview_plan={"questions": []},
    )

    assert session is not None
    assert session["id"] == "test-session-001"
    assert session["candidate_name"] == "Test Candidate"
    assert session["status"] == "created"
    assert session["candidate_profile"]["skills"] == [
        "Python",
        "SQL",
    ]


@pytest.mark.asyncio
async def test_save_and_retrieve_conversation_turns(tmp_path):
    """Conversation turns should be stored in order."""

    db = Database(tmp_path / "test_interviews.db")
    await db.initialize()

    await db.create_session(
        session_id="test-session-002",
    )

    await db.save_turn(
        session_id="test-session-002",
        role="assistant",
        content="Tell me about yourself.",
    )

    await db.save_turn(
        session_id="test-session-002",
        role="user",
        content="I am a computer science graduate.",
    )

    turns = await db.get_turns("test-session-002")

    assert len(turns) == 2
    assert turns[0]["role"] == "assistant"
    assert turns[1]["role"] == "user"
    assert turns[1]["content"] == (
        "I am a computer science graduate."
    )


@pytest.mark.asyncio
async def test_update_session_status(tmp_path):
    """Session status should be updated successfully."""

    db = Database(tmp_path / "test_interviews.db")
    await db.initialize()

    await db.create_session(
        session_id="test-session-003",
    )

    updated = await db.update_session(
        session_id="test-session-003",
        status="completed",
        evaluation_report={
            "overall_score": 8.5,
            "recommendation": "advance",
        },
    )

    session = await db.get_session("test-session-003")

    assert updated is True
    assert session["status"] == "completed"
    assert session["evaluation_report"]["overall_score"] == 8.5


@pytest.mark.asyncio
async def test_get_nonexistent_session(tmp_path):
    """Retrieving an unknown session should return None."""

    db = Database(tmp_path / "test_interviews.db")
    await db.initialize()

    session = await db.get_session("does-not-exist")

    assert session is None


@pytest.mark.asyncio
async def test_invalid_conversation_role(tmp_path):
    """Unsupported conversation roles should be rejected."""

    db = Database(tmp_path / "test_interviews.db")
    await db.initialize()

    await db.create_session(
        session_id="test-session-004",
    )

    with pytest.raises(ValueError):
        await db.save_turn(
            session_id="test-session-004",
            role="hacker",
            content="Invalid message",
        )


@pytest.mark.asyncio
async def test_concurrent_session_limit_is_enforced_atomically(tmp_path):
    db = Database(tmp_path / "session_limit.db")
    await db.initialize()
    await db.create_session("active-1", client_ip="127.0.0.1", max_active_per_ip=1)
    with pytest.raises(ActiveSessionLimitError):
        await db.create_session("active-2", client_ip="127.0.0.1", max_active_per_ip=1)


@pytest.mark.asyncio
async def test_idle_sessions_expire(tmp_path):
    db = Database(tmp_path / "expiry.db")
    await db.initialize()
    await db.create_session("idle-session")
    await db.update_session("idle-session", status="in_progress")
    # A zero second timeout expires sessions on the next cleanup pass.
    await db.expire_idle_sessions(0)
    session = await db.get_session("idle-session")
    assert session["status"] == "expired"

from uuid import UUID, uuid4

from sqlalchemy import select

from app.core.config import Settings, get_settings
from app.db.models import AssessmentAttemptRow, AssessmentResultRow


def test_complete_interview_workflow_acceptance(client_and_factory, dev_user_id: str) -> None:
    client, factory = client_and_factory

    # Configure deterministic 1-base question + 1-follow-up interview
    client.app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None,
        app_env="test",
        max_base_questions=1,
        max_follow_ups_per_question=1,
        max_clarifications_per_question=0,
        passing_threshold=50,
    )
    headers = {"X-Dev-User-ID": dev_user_id}

    # Verify initial progression status: soft_1 is available, soft_2 and soft_3 are locked
    initial_prog = client.get("/api/v1/progression", headers=headers)
    assert initial_prog.status_code == 200
    stages = {s["stage"]: s["status"] for s in initial_prog.json()["stages"]}
    assert stages["soft_1"] == "available"
    assert stages["soft_2"] == "locked"
    assert stages["soft_3"] == "locked"

    # Step 1: Start Soft Skills 1
    start_payload = {
        "stage": "soft_1",
        "idempotency_key": f"acc-start-{uuid4()}",
    }
    started = client.post("/api/v1/interviews", json=start_payload, headers=headers)
    assert started.status_code == 201
    session_data = started.json()
    session_id = session_data["id"]
    assert session_data["stage"] == "soft_1"
    assert session_data["state"] == "awaiting_answer"
    assert session_data["active_question_id"] is not None
    base_q_id = session_data["active_question_id"]
    v1 = session_data["version"]

    # Step 2: Retrieve the initial question
    q_resp = client.get(f"/api/v1/interviews/{session_id}/question", headers=headers)
    assert q_resp.status_code == 200
    base_question = q_resp.json()
    assert base_question["id"] == base_q_id
    assert len(base_question["text"]) > 0

    # Step 3: Submit an answer to the initial question
    first_answer_text = (
        "I analyzed the requirements, evaluated multiple trade-offs, selected the safest "
        "architecture, and verified the outcome with concrete metrics."
    )
    first_answer_key = f"acc-ans1-{uuid4()}"
    ans1_resp = client.post(
        f"/api/v1/interviews/{session_id}/answers",
        json={
            "question_id": base_q_id,
            "expected_version": v1,
            "idempotency_key": first_answer_key,
            "text": first_answer_text,
        },
        headers=headers,
    )
    assert ans1_resp.status_code == 200
    ans1_data = ans1_resp.json()

    # Step 4: Verify follow-up questions are generated
    assert ans1_data["action"] == "follow_up"
    assert ans1_data["state"] == "awaiting_follow_up_answer"
    assert ans1_data["question"] is not None
    v2 = ans1_data["version"]

    follow_up_resp = client.get(f"/api/v1/interviews/{session_id}/question", headers=headers)
    assert follow_up_resp.status_code == 200
    follow_up_q = follow_up_resp.json()
    follow_up_q_id = follow_up_q["id"]
    assert follow_up_q_id != base_q_id
    assert follow_up_q["kind"] == "follow_up"

    # Step 5: Continue until the interview is complete
    second_answer_text = (
        "The measured result demonstrated zero downtime, reduced latency by 35%, and "
        "prevented regressions over the subsequent quarterly deployment cycle."
    )
    second_answer_key = f"acc-ans2-{uuid4()}"
    ans2_resp = client.post(
        f"/api/v1/interviews/{session_id}/answers",
        json={
            "question_id": follow_up_q_id,
            "expected_version": v2,
            "idempotency_key": second_answer_key,
            "text": second_answer_text,
        },
        headers=headers,
    )
    assert ans2_resp.status_code == 200
    ans2_data = ans2_resp.json()
    assert ans2_data["action"] == "complete"
    assert ans2_data["state"] == "completed"

    # Verify duplicate answer submission returns recorded response idempotently
    dup_resp = client.post(
        f"/api/v1/interviews/{session_id}/answers",
        json={
            "question_id": follow_up_q_id,
            "expected_version": v2,
            "idempotency_key": second_answer_key,
            "text": second_answer_text,
        },
        headers=headers,
    )
    assert dup_resp.status_code == 200
    assert dup_resp.json()["state"] == "completed"

    # Verify same idempotency key with different content conflicts
    conflict_resp = client.post(
        f"/api/v1/interviews/{session_id}/answers",
        json={
            "question_id": follow_up_q_id,
            "expected_version": v2,
            "idempotency_key": second_answer_key,
            "text": "Different answer content with same key.",
        },
        headers=headers,
    )
    assert conflict_resp.status_code == 409

    # Verify stale session version returns conflict
    stale_resp = client.post(
        f"/api/v1/interviews/{session_id}/answers",
        json={
            "question_id": follow_up_q_id,
            "expected_version": 1,  # Stale version
            "idempotency_key": f"acc-stale-{uuid4()}",
            "text": "Valid text but stale version.",
        },
        headers=headers,
    )
    assert stale_resp.status_code == 409

    # Step 6: Retrieve the final assessment
    assess_resp = client.get(f"/api/v1/interviews/{session_id}/assessment", headers=headers)
    assert assess_resp.status_code == 200
    assessment = assess_resp.json()

    # Step 7: Verify score calculation
    score = float(assessment["score"])
    assert score >= 50.0

    # Step 8: Verify pass/fail determination
    assert assessment["passed"] is True
    assert assessment["attempt_id"] is not None
    assert assessment["rubric_version"] is not None

    # Step 9: Verify progression eligibility
    after_prog = client.get("/api/v1/progression", headers=headers)
    assert after_prog.status_code == 200
    stages_after = {s["stage"]: s["status"] for s in after_prog.json()["stages"]}
    assert stages_after["soft_1"] == "passed"
    assert stages_after["soft_2"] == "available"  # Now available!
    assert stages_after["soft_3"] == "locked"  # Still locked!

    # Step 10: Start the next eligible stage (soft_2)
    start_soft2 = client.post(
        "/api/v1/interviews",
        json={"stage": "soft_2", "idempotency_key": f"acc-soft2-{uuid4()}"},
        headers=headers,
    )
    assert start_soft2.status_code == 201
    assert start_soft2.json()["stage"] == "soft_2"

    # Step 11: Verify that an ineligible stage (soft_3) cannot be started
    start_soft3 = client.post(
        "/api/v1/interviews",
        json={"stage": "soft_3", "idempotency_key": f"acc-soft3-{uuid4()}"},
        headers=headers,
    )
    assert start_soft3.status_code in {403, 409}

    # Verify that un-enrolled technical stage cannot be started
    start_tech = client.post(
        "/api/v1/interviews",
        json={
            "stage": "technical_1",
            "course_id": str(uuid4()),
            "idempotency_key": f"acc-tech-{uuid4()}",
        },
        headers=headers,
    )
    assert start_tech.status_code == 403

    # Student ownership isolation: another student cannot access session or assessment
    other_student_id = str(uuid4())
    other_headers = {"X-Dev-User-ID": other_student_id}
    iso_session = client.get(f"/api/v1/interviews/{session_id}", headers=other_headers)
    assert iso_session.status_code == 404
    iso_assess = client.get(f"/api/v1/interviews/{session_id}/assessment", headers=other_headers)
    assert iso_assess.status_code == 404

    # Assessment persistence in DB
    with factory() as db:
        attempt = db.scalar(
            select(AssessmentAttemptRow).where(AssessmentAttemptRow.session_id == UUID(session_id))
        )
        assert attempt is not None
        assert attempt.status == "passed"
        result = db.get(AssessmentResultRow, attempt.id)
        assert result is not None
        assert result.passed is True
        assert float(result.score) >= 50.0

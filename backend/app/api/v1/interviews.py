from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.dependencies import (
    current_principal,
    enforce_rate_limit,
    get_abandon_interview,
    get_active_session_reader,
    get_assessment_reader,
    get_interview_reader,
    get_question_reader,
    get_start_interview,
    get_submit_answer,
)
from app.application.use_cases.queries import (
    AbandonInterview,
    GetActiveQuestion,
    GetActiveSession,
    GetAssessment,
    GetInterview,
)
from app.application.use_cases.start_interview import StartInterview
from app.application.use_cases.submit_answer import SubmitAnswer
from app.ports.answer_workflow import AnswerCommand
from app.ports.interview_queries import SessionView
from app.ports.services import Principal
from app.ports.sessions import StartSessionCommand
from app.schemas.interviews import (
    AbandonRequest,
    AnswerRequest,
    InterviewResponse,
    StartInterviewRequest,
)

router = APIRouter()


@router.post(
    "/interviews", status_code=201, dependencies=[Depends(enforce_rate_limit("interview-start"))]
)
def start_interview(
    body: StartInterviewRequest,
    principal: Principal = Depends(current_principal),
    use_case: StartInterview = Depends(get_start_interview),
) -> dict[str, object]:
    started = use_case.execute(
        StartSessionCommand(
            student_id=principal.user_id,
            stage=body.stage,
            idempotency_key=body.idempotency_key,
            course_id=body.course_id,
        )
    )
    return {
        "id": started.record.id,
        "stage": started.record.stage,
        "state": started.record.state,
        "version": started.record.version,
        "active_question_id": started.record.active_question_id,
        "question": started.question_text,
    }


@router.get(
    "/interviews/active",
    response_model=InterviewResponse | None,
    dependencies=[Depends(enforce_rate_limit("interview-read"))],
)
def get_active_interview(
    principal: Principal = Depends(current_principal),
    reader: GetActiveSession = Depends(get_active_session_reader),
) -> SessionView | None:
    return reader.execute(principal.user_id)


@router.get(
    "/interviews/{session_id}",
    response_model=InterviewResponse,
    dependencies=[Depends(enforce_rate_limit("interview-read"))],
)
def get_interview(
    session_id: UUID,
    principal: Principal = Depends(current_principal),
    reader: GetInterview = Depends(get_interview_reader),
) -> SessionView:
    return reader.execute(session_id, principal.user_id)


@router.get(
    "/interviews/{session_id}/question",
    dependencies=[Depends(enforce_rate_limit("interview-read"))],
)
def current_question(
    session_id: UUID,
    principal: Principal = Depends(current_principal),
    reader: GetActiveQuestion = Depends(get_question_reader),
    interview_reader: GetInterview = Depends(get_interview_reader),
) -> dict[str, object]:
    question = reader.execute(session_id, principal.user_id)
    session = interview_reader.execute(session_id, principal.user_id)
    provenance = question.provenance
    return {
        "id": question.id,
        "text": question.text,
        "kind": question.kind,
        "sequence": question.sequence,
        "version": question.session_version,
        "stage_id": session.stage.value,
        "content_origin": provenance.origin if provenance else "unknown",
        "content_approval_status": provenance.approval_status if provenance else "unknown",
        "bank_question_id": provenance.bank_question_id if provenance else None,
        "competency_id": provenance.competency_id if provenance else None,
        "rubric_version_id": provenance.rubric_version_id if provenance else None,
        "content_version": provenance.content_version if provenance else None,
        "parent_question_id": provenance.parent_question_id if provenance else None,
        "development_only": bool(
            provenance
            and (
                provenance.origin.startswith("development_")
                or provenance.approval_status == "development_only"
            )
        ),
    }


@router.post(
    "/interviews/{session_id}/answers",
    dependencies=[Depends(enforce_rate_limit("answer-submit"))],
)
def submit_answer(
    session_id: UUID,
    body: AnswerRequest,
    principal: Principal = Depends(current_principal),
    use_case: SubmitAnswer = Depends(get_submit_answer),
) -> dict[str, object]:
    result = use_case.execute(
        AnswerCommand(
            session_id=session_id,
            student_id=principal.user_id,
            question_id=body.question_id,
            expected_version=body.expected_version,
            idempotency_key=body.idempotency_key,
            text=body.text,
        )
    )
    response: dict[str, object] = {
        "state": result.state,
        "version": result.version,
        "question": result.question_text,
    }
    if result.action is not None:
        response["action"] = result.action.value
    return response


@router.post(
    "/interviews/{session_id}/abandon",
    response_model=InterviewResponse,
    dependencies=[Depends(enforce_rate_limit("interview-write"))],
)
def abandon(
    session_id: UUID,
    body: AbandonRequest,
    principal: Principal = Depends(current_principal),
    use_case: AbandonInterview = Depends(get_abandon_interview),
) -> SessionView:
    return use_case.execute(session_id, principal.user_id, body.expected_version)


@router.get(
    "/interviews/{session_id}/assessment",
    dependencies=[Depends(enforce_rate_limit("interview-read"))],
)
def assessment(
    session_id: UUID,
    principal: Principal = Depends(current_principal),
    reader: GetAssessment = Depends(get_assessment_reader),
) -> dict[str, str | bool]:
    result = reader.execute(session_id, principal.user_id)
    return {
        "attempt_id": str(result.attempt_id),
        "score": result.score,
        "passed": result.passed,
        "rubric_version": result.rubric_version,
    }

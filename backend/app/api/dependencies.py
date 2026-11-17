from collections.abc import Callable, Generator
from datetime import UTC, datetime, timedelta
from math import ceil

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.adapters.auth.development import DevelopmentIdentityAdapter
from app.adapters.auth.jwt_oidc import JwtIdentityAdapter
from app.adapters.llm.factory import make_provider
from app.adapters.persistence.answers import SqlAlchemyAnswerWorkflowAdapter
from app.adapters.persistence.assessment_content import SqlAlchemyAssessmentContentAdapter
from app.adapters.persistence.interview_sessions import SqlAlchemySessionStartAdapter
from app.adapters.persistence.queries import SqlAlchemyQueryAdapter
from app.adapters.persistence.rate_limiting import SqlAlchemyRateLimitStore, rate_limit_scope
from app.adapters.persistence.readiness import SqlAlchemyReadinessAdapter
from app.adapters.persistence.transcript_lifecycle import SqlAlchemyTranscriptLifecycle
from app.application.sessions.manager import SessionManager
from app.application.use_cases.queries import (
    AbandonInterview,
    GetActiveQuestion,
    GetActiveSession,
    GetAssessment,
    GetCurrentUser,
    GetInterview,
    GetProgression,
)
from app.application.use_cases.readiness import CheckReadiness
from app.application.use_cases.skip_question import SkipQuestion
from app.application.use_cases.start_interview import StartInterview
from app.application.use_cases.submit_answer import SubmitAnswer
from app.application.use_cases.transcripts import DeleteStudentTranscripts
from app.core.config import Settings, get_settings
from app.core.network import get_client_ip
from app.domain.assessments.attempts import RetakePolicy
from app.ports.answer_workflow import AnswerWorkflowPort
from app.ports.assessment_content import AssessmentContentPort
from app.ports.authentication import IdentityProvider
from app.ports.interview_queries import (
    CourseContentPort,
    InterviewQueryPort,
    ProgressionQueryPort,
    UserQueryPort,
)
from app.ports.llm import LLMProvider
from app.ports.readiness import ReadinessPort
from app.ports.services import Principal


def get_db(request: Request) -> Generator[Session, None, None]:
    factory = request.app.state.session_factory
    session = factory()
    try:
        yield session
    finally:
        session.close()


def get_identity_provider(settings: Settings = Depends(get_settings)) -> IdentityProvider:
    if settings.jwt_configured:
        return JwtIdentityAdapter(settings)
    if settings.development_auth_enabled:
        return DevelopmentIdentityAdapter(settings)
    raise HTTPException(
        status_code=401, detail="Production authentication adapter is not configured"
    )


def current_principal(
    authorization: str | None = Header(default=None),
    x_dev_user_id: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
    identity: IdentityProvider = Depends(get_identity_provider),
) -> Principal:
    if authorization:
        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid authorization scheme")
        token = authorization[7:].strip()
        try:
            return identity.resolve(token)
        except ValueError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc

    if settings.development_auth_enabled and x_dev_user_id:
        try:
            dev_adapter = DevelopmentIdentityAdapter(settings)
            return dev_adapter.resolve(x_dev_user_id)
        except ValueError as exc:
            raise HTTPException(status_code=401, detail="Invalid development identity") from exc

    if not settings.development_auth_enabled and x_dev_user_id:
        raise HTTPException(
            status_code=401, detail="Development identity is disabled in production"
        )

    raise HTTPException(status_code=401, detail="Authentication credentials were not provided")


def enforce_rate_limit(category: str) -> Callable[..., None]:
    def dependency(
        request: Request,
        db: Session = Depends(get_db),
        settings: Settings = Depends(get_settings),
    ) -> None:
        now = datetime.now(UTC)
        window = settings.request_rate_limit_window_seconds
        epoch = int(now.timestamp())
        start_epoch = epoch - epoch % window
        window_start = datetime.fromtimestamp(start_epoch, UTC)
        address = get_client_ip(request, settings.trusted_proxies)
        scope = rate_limit_scope(category, address, window_start)
        hits = SqlAlchemyRateLimitStore(db).consume(scope, now, window)
        if hits > settings.request_rate_limit_count:
            retry_after = max(1, ceil(window - (now.timestamp() - start_epoch)))
            raise HTTPException(
                status_code=429,
                detail="Too many requests; retry later",
                headers={"Retry-After": str(retry_after)},
            )

    return dependency


def get_session_manager(
    db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
) -> SessionManager:
    policy = RetakePolicy(
        max_attempts=settings.max_attempts_per_stage,
        cooldown=timedelta(seconds=settings.retake_cooldown_seconds),
    )
    return SessionManager(SqlAlchemySessionStartAdapter(db), policy)


def get_llm_provider(settings: Settings = Depends(get_settings)) -> LLMProvider:
    try:
        return make_provider(settings)
    except ValueError as exc:
        raise HTTPException(503, "Interview provider is not configured") from exc


def get_interview_queries(db: Session = Depends(get_db)) -> InterviewQueryPort:
    return SqlAlchemyQueryAdapter(db)


def get_progression_queries(db: Session = Depends(get_db)) -> ProgressionQueryPort:
    return SqlAlchemyQueryAdapter(db)


def get_user_queries(db: Session = Depends(get_db)) -> UserQueryPort:
    return SqlAlchemyQueryAdapter(db)


def get_course_content(db: Session = Depends(get_db)) -> CourseContentPort:
    return SqlAlchemyQueryAdapter(db)


def get_assessment_content(db: Session = Depends(get_db)) -> AssessmentContentPort:
    return SqlAlchemyAssessmentContentAdapter(db)


def get_answer_workflow(db: Session = Depends(get_db)) -> AnswerWorkflowPort:
    return SqlAlchemyAnswerWorkflowAdapter(db)


def get_start_interview(
    sessions: SessionManager = Depends(get_session_manager),
    content: CourseContentPort = Depends(get_course_content),
    interviews: InterviewQueryPort = Depends(get_interview_queries),
    provider: LLMProvider = Depends(get_llm_provider),
    settings: Settings = Depends(get_settings),
    assessment_content: AssessmentContentPort = Depends(get_assessment_content),
) -> StartInterview:
    return StartInterview(sessions, content, interviews, provider, settings, assessment_content)


def get_submit_answer(
    persistence: AnswerWorkflowPort = Depends(get_answer_workflow),
    provider: LLMProvider = Depends(get_llm_provider),
    settings: Settings = Depends(get_settings),
    assessment_content: AssessmentContentPort = Depends(get_assessment_content),
) -> SubmitAnswer:
    return SubmitAnswer(persistence, provider, settings, assessment_content)


def get_skip_question(
    persistence: AnswerWorkflowPort = Depends(get_answer_workflow),
    provider: LLMProvider = Depends(get_llm_provider),
    settings: Settings = Depends(get_settings),
    assessment_content: AssessmentContentPort = Depends(get_assessment_content),
) -> SkipQuestion:
    return SkipQuestion(persistence, provider, settings, assessment_content)


def get_readiness(request: Request) -> CheckReadiness:
    adapter: ReadinessPort = SqlAlchemyReadinessAdapter(request.app.state.engine)
    return CheckReadiness(adapter)


def get_interview_reader(
    queries: InterviewQueryPort = Depends(get_interview_queries),
) -> GetInterview:
    return GetInterview(queries)


def get_active_session_reader(
    queries: InterviewQueryPort = Depends(get_interview_queries),
) -> GetActiveSession:
    return GetActiveSession(queries)


def get_question_reader(
    queries: InterviewQueryPort = Depends(get_interview_queries),
    settings: Settings = Depends(get_settings),
) -> GetActiveQuestion:
    return GetActiveQuestion(queries, settings)


def get_assessment_reader(
    queries: InterviewQueryPort = Depends(get_interview_queries),
) -> GetAssessment:
    return GetAssessment(queries)


def get_abandon_interview(
    queries: InterviewQueryPort = Depends(get_interview_queries),
) -> AbandonInterview:
    return AbandonInterview(queries)


def get_progression_reader(
    queries: ProgressionQueryPort = Depends(get_progression_queries),
) -> GetProgression:
    return GetProgression(queries)


def get_current_user(
    queries: UserQueryPort = Depends(get_user_queries),
) -> GetCurrentUser:
    return GetCurrentUser(queries)


def get_delete_student_transcripts(
    db: Session = Depends(get_db),
) -> DeleteStudentTranscripts:
    return DeleteStudentTranscripts(SqlAlchemyTranscriptLifecycle(db))

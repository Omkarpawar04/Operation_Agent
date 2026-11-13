import asyncio
import logging
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm.exc import StaleDataError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import RequestResponseEndpoint
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import Response

from app.adapters.persistence.lease_recovery import SqlAlchemyExpiredLeaseRecovery
from app.adapters.persistence.transcript_lifecycle import SqlAlchemyTranscriptLifecycle
from app.api.v1 import interviews, progression, system, users
from app.application.use_cases.recover_leases import RecoverExpiredLeases
from app.application.use_cases.transcripts import EnforceTranscriptRetention
from app.core.config import get_settings
from app.core.errors import ApplicationError
from app.core.observability import JsonLogFormatter, request_id_context
from app.db.session import make_session_factory


def create_app() -> FastAPI:
    settings = get_settings()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonLogFormatter())
    logging.basicConfig(level=settings.log_level, handlers=[handler], force=True)

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        engine = create_engine(settings.database_url, pool_pre_ping=True)
        application.state.engine = engine
        factory = make_session_factory(engine)
        application.state.session_factory = factory
        application.state.worker_status = {"lease_recovery": "running", "last_run": None}
        stopped = asyncio.Event()
        last_retention_run: datetime | None = None

        async def recover_leases() -> None:
            nonlocal last_retention_run
            while not stopped.is_set():
                try:

                    def run_batch() -> int:
                        with factory() as session:
                            return RecoverExpiredLeases(
                                SqlAlchemyExpiredLeaseRecovery(
                                    session, settings.provider_operation_lease_seconds
                                ),
                                settings.lease_recovery_batch_size,
                            ).execute()

                    count = await asyncio.to_thread(run_batch)
                    now = datetime.now(UTC)
                    retention_count = 0
                    if settings.transcript_retention_days is not None and (
                        last_retention_run is None or now - last_retention_run >= timedelta(days=1)
                    ):

                        def run_retention(reference_time: datetime = now) -> int:
                            with factory() as session:
                                return EnforceTranscriptRetention(
                                    SqlAlchemyTranscriptLifecycle(session),
                                    settings.transcript_retention_days or 1,
                                ).execute(reference_time)

                        retention_count = await asyncio.to_thread(run_retention)
                        if retention_count < settings.lease_recovery_batch_size:
                            last_retention_run = now
                    application.state.worker_status = {
                        "lease_recovery": "running",
                        "last_run": now.isoformat(),
                        "last_recovered": count,
                        "last_retention_deleted": retention_count,
                    }
                except Exception as exc:
                    application.state.worker_status = {"lease_recovery": "degraded"}
                    logging.getLogger(__name__).error(
                        "lease_recovery_failed category=%s", type(exc).__name__
                    )
                try:
                    await asyncio.wait_for(
                        stopped.wait(), timeout=settings.lease_recovery_interval_seconds
                    )
                except TimeoutError:
                    pass

        worker = (
            asyncio.create_task(recover_leases(), name="lease-recovery")
            if not getattr(application.state, "disable_workers", False)
            else None
        )
        try:
            yield
        finally:
            stopped.set()
            if worker is not None:
                await worker
                application.state.worker_status = {"lease_recovery": "stopped"}
            engine.dispose()

    application = FastAPI(title="FINXL AI Interviewer API", version="0.1.0", lifespan=lifespan)
    application.state.settings = settings
    if settings.cors_allowed_origins:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_allowed_origins,
            allow_credentials=False,
            allow_methods=["GET", "POST", "DELETE"],
            allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Request-ID"],
        )
    if settings.app_env.lower() == "production":
        application.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)
    application.include_router(system.router, prefix="/api/v1")
    application.include_router(users.router, prefix="/api/v1")
    application.include_router(interviews.router, prefix="/api/v1")
    application.include_router(progression.router, prefix="/api/v1")

    @application.middleware("http")
    async def request_id_middleware(
        request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        supplied = request.headers.get("X-Request-ID", "")
        request_id = (
            supplied[:80]
            if supplied.isascii() and supplied.isprintable() and supplied
            else str(uuid4())
        )
        request.state.request_id = request_id
        token = request_id_context.set(request_id)
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            request_id_context.reset(token)

    @application.exception_handler(ApplicationError)
    async def application_error_handler(request: Request, exc: ApplicationError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": str(exc),
                    "request_id": getattr(request.state, "request_id", ""),
                }
            },
        )

    @application.exception_handler(StaleDataError)
    async def stale_data_handler(request: Request, _exc: StaleDataError) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content={
                "error": {
                    "code": "stale_version",
                    "message": "The resource changed; reload and retry",
                    "request_id": getattr(request.state, "request_id", ""),
                }
            },
        )

    @application.exception_handler(SQLAlchemyError)
    async def persistence_error_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "")
        logging.getLogger(__name__).error(
            "persistence_failure category=%s request_id=%s",
            type(exc).__name__,
            request_id,
        )
        return JSONResponse(
            status_code=503,
            content={
                "error": {
                    "code": "persistence_unavailable",
                    "message": "Persistence operation is temporarily unavailable",
                    "request_id": request_id,
                }
            },
        )

    @application.exception_handler(StarletteHTTPException)
    async def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        message = exc.detail if isinstance(exc.detail, str) else "Request could not be completed"
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": "rate_limit_exceeded" if exc.status_code == 429 else "http_error",
                    "message": message,
                    "request_id": getattr(request.state, "request_id", ""),
                }
            },
            headers=exc.headers,
        )

    @application.exception_handler(Exception)
    async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "")
        logging.getLogger(__name__).error(
            "request_failed category=%s request_id=%s", type(exc).__name__, request_id
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "internal_error",
                    "message": "Request could not be completed",
                    "request_id": request_id,
                }
            },
        )

    return application


app = create_app()

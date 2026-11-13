from fastapi import APIRouter, Depends, Request

from app.api.dependencies import get_readiness
from app.application.use_cases.readiness import CheckReadiness
from app.core.config import Settings, get_settings

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
def ready(use_case: CheckReadiness = Depends(get_readiness)) -> dict[str, str]:
    return use_case.execute()


@router.get("/worker-health")
def worker_health(request: Request) -> dict[str, object]:
    return dict(getattr(request.app.state, "worker_status", {"lease_recovery": "starting"}))


@router.get("/provider-health")
def provider_health(settings: Settings = Depends(get_settings)) -> dict[str, str]:
    configured = settings.llm_provider == "fake" or bool(settings.gemini_api_key)
    return {
        "provider": settings.llm_provider,
        "status": "configured" if configured else "unavailable",
    }

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from app.application.assessment.manager import AssessmentManager
from app.domain.assessments.attempts import AssessmentAttempt, AttemptState, RetakePolicy
from app.domain.assessments.models import EvaluationEvidence, Rubric, RubricDimension


def test_infrastructure_failure_does_not_consume_attempt() -> None:
    attempt = AssessmentAttempt(uuid4(), "soft_1", "idem")
    attempt.infrastructure_failure()
    assert attempt.state is AttemptState.IN_PROGRESS


def test_completed_attempt_is_immutable() -> None:
    attempt = AssessmentAttempt(uuid4(), "soft_1", "idem")
    attempt.finish(True)
    assert attempt.state is AttemptState.PASSED
    with pytest.raises(ValueError, match="immutable"):
        attempt.finish(False)


def test_insufficient_evidence_does_not_consume_attempt() -> None:
    attempt = AssessmentAttempt(uuid4(), "soft_1", "idem")
    rubric = Rubric("v1", (RubricDimension("clarity", Decimal("1")),))
    evidence = (EvaluationEvidence("clarity", (), ("clarity",), True, Decimal("0.2"), None),)
    with pytest.raises(ValueError, match="Insufficient evidence"):
        AssessmentManager().complete(attempt, rubric, evidence)
    assert attempt.state is AttemptState.IN_PROGRESS


def test_retake_policy_supports_optional_cap_and_cooldown() -> None:
    now = datetime.now(UTC)
    limited = RetakePolicy(max_attempts=2, cooldown=timedelta(hours=1))
    assert limited.allows_start(1, now - timedelta(hours=2), now)
    assert not limited.allows_start(1, now - timedelta(minutes=10), now)
    assert not limited.allows_start(2, now - timedelta(hours=2), now)
    assert RetakePolicy().allows_start(20, now, now)


def test_development_identity_adapter_fails_closed_in_production() -> None:
    from app.adapters.auth.development import DevelopmentIdentityAdapter
    from app.core.config import Settings

    settings = Settings(
        app_env="production",
        llm_provider="gemini",
        gemini_api_key="test-placeholder-only",
        cors_allowed_origins=["https://example.invalid"],
        trusted_hosts=["example.invalid"],
        transcript_retention_days=365,
    )
    with pytest.raises(RuntimeError, match="cannot run outside"):
        DevelopmentIdentityAdapter(settings)

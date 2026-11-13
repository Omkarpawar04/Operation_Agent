from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"), extra="ignore", env_ignore_empty=True
    )
    app_env: str = "production"
    database_url: str = "postgresql+psycopg://localhost:5432/finxl"
    finxl_test_postgres_url: str | None = None
    log_level: str = "INFO"
    passing_threshold: float = Field(default=50, ge=0, le=100)
    max_base_questions: int = Field(default=5, ge=1)
    max_follow_ups_per_question: int = Field(default=2, ge=0)
    max_clarifications_per_question: int = Field(default=1, ge=0)
    max_attempts_per_stage: int | None = Field(default=None, ge=1)
    retake_cooldown_seconds: int = Field(default=0, ge=0)
    llm_provider: str = "fake"
    dev_assessment_content_mode: Literal["fixture", "question_bank"] = "fixture"
    dev_assessment_allow_draft: bool = False
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.5-flash-lite"
    llm_timeout_seconds: float = Field(default=20, gt=0, le=120)
    provider_operation_lease_seconds: int = Field(default=600, ge=30, le=900)
    lease_recovery_interval_seconds: float = Field(default=30, gt=0, le=3600)
    lease_recovery_batch_size: int = Field(default=100, ge=1, le=1000)
    transcript_retention_days: int | None = Field(default=None, ge=1, le=36500)
    request_rate_limit_count: int = Field(default=120, ge=1, le=100000)
    request_rate_limit_window_seconds: int = Field(default=60, ge=1, le=3600)
    cors_allowed_origins: list[str] = Field(default_factory=list)
    trusted_hosts: list[str] = Field(default_factory=list)
    trusted_proxies: list[str] = Field(default_factory=list)
    jwt_issuer: str | None = None
    jwt_audience: str | None = None
    jwt_algorithms: list[str] = Field(default_factory=lambda: ["RS256"])
    jwt_jwks_url: str | None = None
    jwt_public_key: str | None = None
    jwt_user_id_claim: str = "sub"
    jwt_role_claim: str | None = "role"
    jwt_leeway_seconds: int = Field(default=60, ge=0, le=3600)

    @model_validator(mode="after")
    def validate_provider_lease(self) -> "Settings":
        if self.provider_operation_lease_seconds <= self.llm_timeout_seconds * 4 + 2:
            raise ValueError(
                "Provider operation lease must exceed worst-case provider call duration"
            )
        return self

    @model_validator(mode="after")
    def validate_production_adapters(self) -> "Settings":
        development_content_enabled = (
            self.dev_assessment_content_mode != "fixture" or self.dev_assessment_allow_draft
        )
        if development_content_enabled and self.app_env.lower() not in {"development", "test"}:
            raise ValueError(
                "Development assessment content is available only in development or test"
            )
        if self.app_env.lower() == "production":
            if development_content_enabled:
                raise ValueError("Production cannot enable development assessment content")
            if self.llm_provider != "gemini" or not self.gemini_api_key:
                raise ValueError("Production requires a configured Gemini provider")
            if self.database_url.startswith("sqlite"):
                raise ValueError("Production requires PostgreSQL")
            if not self.cors_allowed_origins or "*" in self.cors_allowed_origins:
                raise ValueError("Production requires explicit CORS origins")
            if not self.trusted_hosts or "*" in self.trusted_hosts:
                raise ValueError("Production requires explicit trusted hosts")
            if self.transcript_retention_days is None:
                raise ValueError("Production requires an approved transcript retention period")
        return self

    @property
    def development_auth_enabled(self) -> bool:
        return self.app_env.lower() in {"development", "test"}

    @property
    def jwt_configured(self) -> bool:
        return bool(self.jwt_jwks_url or self.jwt_public_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()

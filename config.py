
"""
Application configuration.

Loads environment variables from .env and validates their values.

Primary AI provider:
- Groq: interview planning, interviewer responses, evaluation.

Optional provider:
- OpenAI: reserved for future Realtime API integration.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the AI Voice Interview Agent."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_ignore_empty=True,
    )

    @field_validator("debug", mode="before")
    @classmethod
    def normalize_debug_setting(cls, value):
        """Accept common environment names as well as boolean strings."""
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"release", "production", "prod"}:
                return False
            if normalized in {"development", "dev"}:
                return True
        return value

    # --------------------------------------------------
    # APPLICATION
    # --------------------------------------------------

    app_name: str = "AI Voice Interview Agent"
    app_env: str = "development"
    debug: bool = True
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)
    log_level: str = "INFO"

    # --------------------------------------------------
    # PRIMARY AI PROVIDER: GROQ
    # --------------------------------------------------

    groq_api_key: SecretStr = SecretStr("")

    groq_base_url: str = (
        "https://api.groq.com/openai/v1"
    )

    groq_text_model: str = "openai/gpt-oss-120b"

    @property
    def groq_key(self) -> str:
        """Return the Groq API key."""

        return self.groq_api_key.get_secret_value()

    # --------------------------------------------------
    # OPTIONAL OPENAI CONFIGURATION
    # Reserved for future Realtime API integration.
    # --------------------------------------------------

    openai_api_key: SecretStr = SecretStr("")

    openai_realtime_model: str = "gpt-realtime-2.1"

    realtime_enabled: bool = False

    @property
    def openai_key(self) -> str:
        """Return the OpenAI API key."""

        return self.openai_api_key.get_secret_value()

    # --------------------------------------------------
    # BACKWARD-COMPATIBILITY MODEL ALIAS
    # Existing agent files will be migrated to groq_text_model.
    # --------------------------------------------------

    @property
    def openai_text_model(self) -> str:
        """Return the primary text model during migration."""

        return self.groq_text_model

    # --------------------------------------------------
    # VOICE SERVICES
    # --------------------------------------------------

    deepgram_api_key: SecretStr = SecretStr("")

    # Nova-3 defaults to broad English when this is omitted. Keep that default
    # accent-inclusive, while allowing an installation to choose en-IN, en-US,
    # or another supported language explicitly.
    deepgram_language: str = "en"

    kokoro_enabled: bool = True

    # Kokoro-82M supports English voices in American and British accents,
    # but no Indian-English voice. Use its highest-graded male English option.
    kokoro_voice: str = "am_michael"

    kokoro_speed: float = Field(default=1.0, gt=0, le=2)

    kokoro_sample_rate: Literal[24000] = 24000

    kokoro_device: Literal["cpu", "cuda", "mps"] = "cpu"

    @property
    def deepgram_key(self) -> str:
        """Return the Deepgram API key."""

        return self.deepgram_api_key.get_secret_value()

    # --------------------------------------------------
    # DATABASE AND REDIS
    # --------------------------------------------------

    database_path: Path = Path("./data/interviews.db")

    redis_url: str = ""

    # --------------------------------------------------
    # SESSION LIMITS
    # --------------------------------------------------

    session_idle_timeout_seconds: int = Field(
        default=900,
        gt=0,
    )

    max_concurrent_sessions_per_ip: int = Field(
        default=3,
        gt=0,
    )

    max_session_cost_usd: float = Field(
        default=5.0,
        gt=0,
    )

    # --------------------------------------------------
    # AUDIO
    # --------------------------------------------------

    vad_silence_duration_ms: int = Field(
        default=450,
        gt=0,
    )

    audio_input_sample_rate: int = Field(
        default=16000,
        gt=0,
    )

    # --------------------------------------------------
    # CORS
    # --------------------------------------------------

    cors_origins: str = (
        "http://127.0.0.1:8000,http://localhost:8000"
    )

    @property
    def allowed_origins(self) -> list[str]:
        """Convert comma-separated CORS origins into a list."""

        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]


# --------------------------------------------------
# SHARED SETTINGS INSTANCE
# --------------------------------------------------

@lru_cache
def get_settings() -> Settings:
    """
    Return one shared Settings instance.

    Caching avoids repeatedly reading and validating .env.
    """

    return Settings()


settings = get_settings()

from app.adapters.llm.fake import FakeLLMProvider
from app.adapters.llm.gemini import GeminiProvider
from app.core.config import Settings
from app.ports.llm import LLMProvider


def make_provider(settings: Settings) -> LLMProvider:
    if settings.llm_provider == "fake":
        if not settings.development_auth_enabled:
            raise ValueError("The fake interview provider is available only in development or test")
        return FakeLLMProvider()
    if settings.llm_provider == "gemini" and settings.gemini_api_key:
        return GeminiProvider(
            settings.gemini_api_key,
            settings.gemini_model,
            settings.llm_timeout_seconds,
        )
    raise ValueError("Configure LLM_PROVIDER=fake or set GEMINI_API_KEY for gemini")

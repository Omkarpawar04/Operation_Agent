import pytest

from app.adapters.llm.gemini import GeminiProvider, ProviderUnavailable
from app.ports.llm import GeneratedQuestion, InterviewPrompt


def test_gemini_adapter_validates_structured_response_without_live_call() -> None:
    provider = GeminiProvider(
        "test-only-secret",
        "test-model",
        generate=lambda _prompt, _schema, _model: (
            '{"text":"Explain your decision with evidence","topic":"testing"}'
        ),
    )
    response = provider.generate_question(InterviewPrompt("question", {}))
    assert isinstance(response, GeneratedQuestion)
    assert response.topic == "testing"


def test_gemini_adapter_rejects_malformed_output_safely() -> None:
    provider = GeminiProvider(
        "test-only-secret",
        "test-model",
        generate=lambda _prompt, _schema, _model: '{"text":"","topic":""}',
    )
    with pytest.raises(ProviderUnavailable, match="invalid output"):
        provider.generate_question(InterviewPrompt("question", {}))


def test_gemini_adapter_retries_only_transient_failures() -> None:
    calls = 0

    def transient_then_success(_prompt: str, _schema: str, _model: str) -> str:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise TimeoutError("private detail")
        return '{"text":"Explain your decision with evidence","topic":"testing"}'

    provider = GeminiProvider("test-only-secret", "test-model", generate=transient_then_success)
    provider.generate_question(InterviewPrompt("question", {}))
    assert calls == 2


def test_gemini_adapter_rejects_unexpected_fields_and_empty_output() -> None:
    for output in (
        '{"text":"A valid generated interview question","topic":"testing","score":100}',
        "",
    ):
        provider = GeminiProvider(
            "test-only-secret", "test-model", generate=lambda *_, response=output: response
        )
        with pytest.raises(ProviderUnavailable):
            provider.generate_question(InterviewPrompt("question", {}))


def test_gemini_authentication_error_is_not_retried() -> None:
    calls = 0

    class AuthenticationError(Exception):
        status_code = 401

    def fail(_prompt: str, _schema: str, _model: str) -> str:
        nonlocal calls
        calls += 1
        raise AuthenticationError("private credentials")

    provider = GeminiProvider("test-only-secret", "test-model", generate=fail)
    with pytest.raises(ProviderUnavailable):
        provider.generate_question(InterviewPrompt("question", {}))
    assert calls == 1


def test_gemini_retry_exhaustion_hides_provider_error() -> None:
    calls = 0

    def fail(_prompt: str, _schema: str, _model: str) -> str:
        nonlocal calls
        calls += 1
        raise TimeoutError("secret and student data")

    provider = GeminiProvider("test-only-secret", "test-model", attempts=2, generate=fail)
    with pytest.raises(ProviderUnavailable) as error:
        provider.generate_question(InterviewPrompt("question", {}))
    assert calls == 2
    assert "secret" not in str(error.value)

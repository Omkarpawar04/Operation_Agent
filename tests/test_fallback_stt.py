"""Deepgram request options and transcript preservation tests."""

import asyncio

from pydantic import SecretStr

from audio.fallback_pipeline import FallbackVoicePipeline


class FakeResponse:
    def raise_for_status(self):
        pass

    @staticmethod
    def json():
        return {
            "results": {
                "channels": [{
                    "alternatives": [{"transcript": "FastAPI uses PostgreSQL."}],
                }],
            },
        }


class FakeHTTPClient:
    def __init__(self):
        self.request = None

    async def post(self, url, **kwargs):
        self.request = (url, kwargs)
        return FakeResponse()

    async def aclose(self):
        pass


def test_deepgram_gets_language_formatting_and_repeated_keyterms(monkeypatch):
    monkeypatch.setattr(
        "audio.fallback_pipeline.settings.deepgram_api_key",
        SecretStr("test-key"),
    )
    monkeypatch.setattr(
        "audio.fallback_pipeline.settings.deepgram_language", "en-IN"
    )
    client = FakeHTTPClient()
    pipeline = FallbackVoicePipeline(http_client=client)

    transcript = asyncio.run(pipeline.transcribe_audio(
        b"\x00\x00" * 320,
        sample_rate=16000,
        keyterms=["Python", "FastAPI", "Python"],
    ))

    assert transcript == "FastAPI uses PostgreSQL."
    _, request = client.request
    params = request["params"]
    assert ("language", "en-IN") in params
    assert ("smart_format", "true") in params
    assert ("keyterm", "Python") in params
    assert ("keyterm", "FastAPI") in params
    assert params.count(("keyterm", "Python")) == 1
    asyncio.run(pipeline.close())


def test_interview_keyterms_include_common_stack_and_plan_skills():
    terms = FallbackVoicePipeline.interview_keyterms(
        {
            "questions": [{
                "skills_tested": ["Redis", "Python"],
                "followup_topics": ["connection pooling"],
            }],
        },
        {"skills_tested": ["FastAPI"]},
    )

    assert "Python" in terms
    assert "PostgreSQL" in terms
    assert "Redis" in terms
    assert "connection pooling" in terms
    assert len(terms) == len({term.casefold() for term in terms})

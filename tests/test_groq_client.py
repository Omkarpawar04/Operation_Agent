"""The interview agents share one reusable async Groq connection pool."""

import asyncio

from pydantic import SecretStr

import agents.groq_client as groq_client


class FakeAsyncOpenAI:
    def __init__(self, **kwargs):
        self.options = kwargs
        self.closed = False

    async def close(self):
        self.closed = True


def test_groq_client_is_reused_and_closed(monkeypatch):
    monkeypatch.setattr(groq_client.settings, "groq_api_key", SecretStr("test-key"))
    monkeypatch.setattr(groq_client, "AsyncOpenAI", FakeAsyncOpenAI)
    monkeypatch.setattr(groq_client, "_client", None)

    first = groq_client.get_groq_client()
    second = groq_client.get_groq_client()

    assert first is second
    assert first.options["max_retries"] == 1
    assert first.options["timeout"] == 30.0
    asyncio.run(groq_client.close_groq_client())
    assert first.closed
    assert groq_client._client is None

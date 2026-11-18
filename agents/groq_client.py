"""Shared asynchronous Groq client for all interview agents."""

from openai import AsyncOpenAI

from config import settings


_client: AsyncOpenAI | None = None


def get_groq_client() -> AsyncOpenAI:
    """Create one pooled client lazily and reuse it across agent calls."""
    global _client
    if not settings.groq_key:
        raise RuntimeError("GROQ_API_KEY is missing from the environment.")
    if _client is None:
        _client = AsyncOpenAI(
            api_key=settings.groq_key,
            base_url=settings.groq_base_url,
            timeout=30.0,
            max_retries=1,
        )
    return _client


async def close_groq_client() -> None:
    """Close the shared connection pool during application shutdown."""
    global _client
    client, _client = _client, None
    if client is not None:
        await client.close()

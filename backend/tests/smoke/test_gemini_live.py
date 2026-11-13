import os
from time import perf_counter

import pytest

from app.adapters.llm.gemini import GeminiProvider
from app.ports.llm import InterviewPrompt

pytestmark = pytest.mark.gemini_live


def test_live_gemini_question_generation(record_property) -> None:
    if os.environ.get("RUN_GEMINI_SMOKE") != "1":
        pytest.skip("Set RUN_GEMINI_SMOKE=1 to explicitly enable the live provider call")
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        pytest.fail("RUN_GEMINI_SMOKE=1 requires GEMINI_API_KEY")
    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    started = perf_counter()
    generated = GeminiProvider(api_key, model).generate_question(
        InterviewPrompt("Generate a short interview prompt about teamwork.", {"stage": "soft_1"})
    )
    duration_ms = round((perf_counter() - started) * 1000)
    assert len(generated.text.split()) >= 5
    record_property("provider", "gemini")
    record_property("model", model)
    record_property("duration_ms", duration_ms)

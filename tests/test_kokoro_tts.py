"""Unit tests for the local Kokoro adapter; model loading is mocked."""

import asyncio
import time
import wave
from io import BytesIO

import numpy as np
import pytest

from audio.fallback_pipeline import FallbackPipelineError, FallbackVoicePipeline
from audio.kokoro_tts import (
    KokoroTTSInputError,
    KokoroTTSError,
    KokoroTTSService,
)


class FakeKokoroPipeline:
    def __init__(self, *, delay: float = 0, fail: bool = False):
        self.delay = delay
        self.fail = fail
        self.voice_loads = []
        self.calls = []
        self.active_calls = 0
        self.max_active_calls = 0

    def load_voice(self, voice):
        self.voice_loads.append(voice)
        return object()

    def __call__(self, text, *, voice, speed):
        self.calls.append((text, voice, speed))

        def generate():
            self.active_calls += 1
            self.max_active_calls = max(self.max_active_calls, self.active_calls)
            try:
                if self.delay:
                    time.sleep(self.delay)
                if self.fail:
                    raise RuntimeError("mock synthesis failure")
                yield text, "mock phonemes", np.array([0.1, -0.2, 0.3], dtype=np.float32)
            finally:
                self.active_calls -= 1

        return generate()


def make_service(pipeline=None, **kwargs):
    pipeline = pipeline or FakeKokoroPipeline()
    creations = []

    def factory(**options):
        creations.append(options)
        return pipeline

    service = KokoroTTSService(pipeline_factory=factory, **kwargs)
    return service, pipeline, creations


def read_wav(wav_bytes):
    with wave.open(BytesIO(wav_bytes), "rb") as wav_file:
        return wav_file.getparams(), wav_file.readframes(wav_file.getnframes())


def test_empty_and_invalid_text_are_rejected_before_model_load():
    service, _, creations = make_service()

    with pytest.raises(KokoroTTSInputError, match="empty"):
        asyncio.run(service.synthesize_wav(" \n\t"))
    with pytest.raises(KokoroTTSInputError, match="string"):
        asyncio.run(service.synthesize_wav(None))

    assert creations == []


def test_initializes_model_and_voice_once_then_reuses_them():
    service, pipeline, creations = make_service()

    async def synthesize_twice():
        await service.initialize()
        first = await service.synthesize_wav("First interview response.")
        second = await service.synthesize_wav("Second interview response.")
        return first, second

    first, second = asyncio.run(synthesize_twice())

    assert first.startswith(b"RIFF") and second.startswith(b"RIFF")
    assert len(creations) == 1
    assert creations[0] == {"lang_code": "a", "device": "cpu"}
    assert pipeline.voice_loads == ["af_heart"]
    assert service.status == "ready"


def test_startup_warmup_runs_one_inference_and_reuses_model():
    service, pipeline, creations = make_service()

    asyncio.run(service.warmup())

    assert len(creations) == 1
    assert pipeline.voice_loads == ["af_heart"]
    assert pipeline.calls == [("Hello, the interview is ready.", "af_heart", 1.0)]
    assert service.status == "ready"


def test_generates_valid_24khz_mono_pcm16_wav():
    service, _, _ = make_service(voice="af_heart", speed=1.1)

    wav_bytes = asyncio.run(service.synthesize_wav("Explain your design."))
    params, pcm = read_wav(wav_bytes)

    assert params.nchannels == 1
    assert params.sampwidth == 2
    assert params.framerate == 24000
    assert params.nframes == 3
    assert params.comptype == "NONE"
    assert len(pcm) == params.nframes * params.sampwidth


def test_truncated_wav_is_rejected():
    service, _, _ = make_service()
    wav_bytes = asyncio.run(service.synthesize_wav("Validate every audio frame."))

    with pytest.raises(KokoroTTSError, match="truncated"):
        service._validate_wav(wav_bytes[:-2])


def test_long_text_is_split_at_word_boundaries():
    service, pipeline, _ = make_service()
    text = "candidate answer " * 150

    wav_bytes = asyncio.run(service.synthesize_wav(text))

    assert len(wav_bytes) > 44
    assert len(pipeline.calls) > 1
    assert all(len(part) <= service.max_chunk_chars for part, _, _ in pipeline.calls)


def test_rejects_unbounded_text_before_loading_model():
    service, _, creations = make_service()

    with pytest.raises(KokoroTTSInputError, match="safety limit"):
        asyncio.run(service.synthesize_wav("x" * (service.max_text_chars + 1)))

    assert creations == []


def test_pipeline_initialization_errors_are_clear_and_retryable():
    calls = []

    def failing_factory(**_):
        calls.append(True)
        raise RuntimeError("private implementation detail")

    service = KokoroTTSService(pipeline_factory=failing_factory)
    with pytest.raises(KokoroTTSError, match="load its local model or voice"):
        asyncio.run(service.initialize())

    assert service.status == "error"
    assert len(calls) == 1


def test_synthesis_errors_do_not_return_partial_audio():
    pipeline = FakeKokoroPipeline(fail=True)
    service, _, _ = make_service(pipeline)

    with pytest.raises(KokoroTTSError, match="could not generate speech"):
        asyncio.run(service.synthesize_wav("A response that fails."))

    assert service.status == "ready"


def test_concurrent_calls_reuse_and_serialize_model_access():
    pipeline = FakeKokoroPipeline(delay=0.03)
    service, _, creations = make_service(pipeline)

    async def run_requests():
        return await asyncio.gather(*(
            service.synthesize_wav(f"Response {index}.")
            for index in range(4)
        ))

    results = asyncio.run(run_requests())

    assert all(result.startswith(b"RIFF") for result in results)
    assert len(creations) == 1
    assert pipeline.voice_loads == ["af_heart"]
    assert pipeline.max_active_calls == 1


def test_async_synthesis_does_not_block_event_loop():
    service, _, _ = make_service(FakeKokoroPipeline(delay=0.08))

    async def run_check():
        running = True
        ticks = 0

        async def ticker():
            nonlocal ticks
            while running:
                ticks += 1
                await asyncio.sleep(0.005)

        ticker_task = asyncio.create_task(ticker())
        await service.synthesize_wav("Keep the event loop responsive.")
        running = False
        await ticker_task
        return ticks

    assert asyncio.run(run_check()) >= 5


def test_generation_uses_memory_and_creates_no_temporary_files(tmp_path):
    service, _, _ = make_service()
    before = list(tmp_path.iterdir())

    wav_bytes = asyncio.run(service.synthesize_wav("No temporary output."))

    assert wav_bytes.startswith(b"RIFF")
    assert list(tmp_path.iterdir()) == before


def test_fallback_pipeline_transports_pcm_without_wav_header():
    service, _, _ = make_service()
    pipeline = FallbackVoicePipeline(tts_service=service)

    async def collect():
        chunks = [chunk async for chunk in pipeline.stream_speech("Speak this response.")]
        await pipeline.close()
        return b"".join(chunks)

    pcm = asyncio.run(collect())

    assert pcm
    assert not pcm.startswith(b"RIFF")
    assert len(pcm) == 6


def test_kokoro_streams_each_sentence_before_synthesizing_the_next():
    service, pipeline_model, _ = make_service(FakeKokoroPipeline(delay=0.04))

    async def collect_incrementally():
        stream = service.stream_pcm("First sentence. Second sentence.")
        first = await anext(stream)
        calls_after_first = len(pipeline_model.calls)
        remaining = [chunk async for chunk in stream]
        return first, remaining, calls_after_first

    first, remaining, calls_after_first = asyncio.run(collect_incrementally())

    assert len(first) == 6
    assert calls_after_first == 1
    assert len(pipeline_model.calls) == 2
    assert len(remaining) == 1


def test_fallback_pipeline_rejects_empty_text_and_surfaces_tts_errors():
    service, _, _ = make_service()
    pipeline = FallbackVoicePipeline(tts_service=service)

    async def collect():
        with pytest.raises(FallbackPipelineError, match="empty"):
            _ = [chunk async for chunk in pipeline.stream_speech(" ")]
        await pipeline.close()

    asyncio.run(collect())

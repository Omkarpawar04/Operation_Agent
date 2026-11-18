r"""Measure real Deepgram, Groq, and Kokoro turn latency.

Run from the project root with the Kokoro environment and configured keys:
    .\venv-kokoro\Scripts\python.exe tests\benchmark_voice_latency.py

The test utterance is generated locally by Kokoro, transcribed by Deepgram,
then passed through the real interviewer and Kokoro response path. No audio
files are written. This measures clean synthetic speech, not room noise or a
physical microphone.
"""

import asyncio
import io
import json
import re
import sys
import time
import wave
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.groq_client import close_groq_client
from agents.interviewer import InterviewerAgent
from audio.fallback_pipeline import FallbackVoicePipeline
from audio.kokoro_tts import kokoro_tts_service
from config import settings


SAMPLE_ANSWER = (
    "I built a Python service with FastAPI, used SQL and PostgreSQL, "
    "applied object oriented programming, and used inheritance to share "
    "behavior between classes."
)
EXPECTED_TERMS = ["Python", "FastAPI", "SQL", "PostgreSQL", "inheritance"]
TTS_STREAMING_PROBE = (
    "Thanks for the overview. Could you walk me through the testing and "
    "monitoring you implemented to ensure the API’s reliability?"
)


def resample_wav_to_pcm16(wav_bytes: bytes, output_rate: int = 16000) -> bytes:
    with wave.open(io.BytesIO(wav_bytes), "rb") as wav_file:
        sample_rate = wav_file.getframerate()
        channels = wav_file.getnchannels()
        samples = np.frombuffer(
            wav_file.readframes(wav_file.getnframes()), dtype="<i2"
        ).astype(np.float32) / 32768.0
    if channels > 1:
        samples = samples.reshape(-1, channels).mean(axis=1)
    output_count = int(len(samples) * output_rate / sample_rate)
    positions = np.arange(output_count, dtype=np.float64) * sample_rate / output_rate
    converted = np.interp(positions, np.arange(len(samples)), samples)
    return (np.clip(converted, -1.0, 1.0) * 32767).astype("<i2").tobytes()


def words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.casefold())


def word_error_rate(reference: str, hypothesis: str) -> tuple[float, int, int]:
    expected, actual = words(reference), words(hypothesis)
    row = list(range(len(actual) + 1))
    for index, expected_word in enumerate(expected, start=1):
        next_row = [index]
        for column, actual_word in enumerate(actual, start=1):
            next_row.append(min(
                next_row[-1] + 1,
                row[column] + 1,
                row[column - 1] + (expected_word != actual_word),
            ))
        row = next_row
    errors = row[-1]
    return errors / max(1, len(expected)), len(expected), errors


def make_interview_plan() -> dict:
    questions = [
        {
            "id": index,
            "category": "technical",
            "question": "How would you design a reliable Python API?",
            "difficulty": "medium",
            "skills_tested": ["Python", "FastAPI", "SQL"],
            "followup_topics": ["testing", "performance"],
        }
        for index in range(1, 9)
    ]
    return {
        "total_questions": len(questions),
        "questions": questions,
        "closing_prompt": "Thank you. The interview is complete.",
    }


async def run_benchmark() -> dict:
    if not settings.deepgram_key or not settings.groq_key:
        raise SystemExit(
            "Set DEEPGRAM_API_KEY and GROQ_API_KEY in .env before benchmarking."
        )

    report: dict[str, object] = {}
    started = time.perf_counter()
    await kokoro_tts_service.warmup()
    report["kokoro_startup_warmup_s"] = round(time.perf_counter() - started, 3)

    started = time.perf_counter()
    sample_wav = await kokoro_tts_service.synthesize_wav(SAMPLE_ANSWER)
    report["synthetic_answer_synthesis_s"] = round(time.perf_counter() - started, 3)
    audio = resample_wav_to_pcm16(sample_wav)

    pipeline = FallbackVoicePipeline(interviewer=InterviewerAgent())
    try:
        plan = make_interview_plan()
        question = plan["questions"][1]
        keyterms = pipeline.interview_keyterms(plan, question)

        started = time.perf_counter()
        transcript = await pipeline.transcribe_audio(
            audio, sample_rate=16000, keyterms=keyterms
        )
        report["deepgram_stt_s"] = round(time.perf_counter() - started, 3)
        report["input_speech_s"] = round(len(audio) / 32000, 3)
        report["transcript"] = transcript
        error_rate, reference_count, error_count = word_error_rate(
            SAMPLE_ANSWER, transcript
        )
        report["word_error_rate"] = round(error_rate, 4)
        report["reference_word_count"] = reference_count
        report["word_errors"] = error_count
        report["technical_terms_found"] = [
            term for term in EXPECTED_TERMS
            if re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", transcript, re.I)
        ]

        agent = pipeline.interviewer
        started = time.perf_counter()
        reply = await agent.generate_response(
            candidate_message=transcript,
            interview_plan=plan,
            conversation_history=[
                {"role": "assistant", "turn_type": "question", "content": question["question"]},
                {"role": "user", "turn_type": "answer", "content": transcript},
            ],
            current_question=question,
        )
        report["groq_response_s"] = round(time.perf_counter() - started, 3)
        report["groq_first_text_delta_s"] = (
            round(agent.last_first_token_seconds, 3)
            if agent.last_first_token_seconds is not None else None
        )
        report["interviewer_text"] = reply.text

        started = time.perf_counter()
        stream = pipeline.stream_speech(reply.text).__aiter__()
        first_chunk = await anext(stream, None)
        report["kokoro_first_audio_s"] = round(time.perf_counter() - started, 3)
        total_bytes = len(first_chunk or b"")
        async for chunk in stream:
            total_bytes += len(chunk)
        report["kokoro_audio_complete_s"] = round(time.perf_counter() - started, 3)
        report["response_audio_bytes"] = total_bytes

        # Compare progressive delivery against the same two-sentence text used
        # by the recorded pre-change baseline.
        probe_started = time.perf_counter()
        probe = pipeline.stream_speech(TTS_STREAMING_PROBE).__aiter__()
        probe_first = await anext(probe, None)
        report["kokoro_two_sentence_first_audio_s"] = round(
            time.perf_counter() - probe_started, 3
        )
        async for _ in probe:
            pass
        report["kokoro_two_sentence_complete_s"] = round(
            time.perf_counter() - probe_started, 3
        )

        report["end_to_end_turn_s"] = round(
            report["deepgram_stt_s"]
            + report["groq_response_s"]
            + report["kokoro_audio_complete_s"],
            3,
        )
        report["endpointing_wait_ms"] = settings.vad_silence_duration_ms
        report["notes"] = (
            "End-to-end begins after local VAD declares speech ended; the listed "
            "endpointing wait is configured separately. Synthetic clean speech "
            "does not measure a physical microphone or room noise."
        )
        return report
    finally:
        await pipeline.close()
        await close_groq_client()


if __name__ == "__main__":
    print(json.dumps(asyncio.run(run_benchmark()), indent=2))

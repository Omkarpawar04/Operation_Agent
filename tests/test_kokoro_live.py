"""Generate and validate a real Kokoro WAV; run explicitly, not in pytest."""

from __future__ import annotations

import asyncio
import sys
import wave
from io import BytesIO
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from audio.kokoro_tts import kokoro_tts_service


TEST_TEXT = (
    "Hello Rahul, welcome to your technical interview. Let's begin with a "
    "simple question. Can you explain the difference between a Python list "
    "and a tuple?"
)


async def main() -> None:
    wav_bytes = await kokoro_tts_service.synthesize_wav(TEST_TEXT)
    output_path = PROJECT_ROOT / "tests" / "output" / "kokoro_live.wav"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(wav_bytes)

    if not output_path.is_file() or output_path.stat().st_size <= 44:
        raise SystemExit("Kokoro did not produce a non-empty WAV file.")

    with wave.open(BytesIO(wav_bytes), "rb") as wav_file:
        duration = wav_file.getnframes() / wav_file.getframerate()
        if (
            wav_file.getnchannels() != 1
            or wav_file.getsampwidth() != 2
            or wav_file.getframerate() != 24000
            or duration <= 0
        ):
            raise SystemExit("Kokoro generated an invalid WAV format or duration.")

    print(
        "Kokoro live TTS: PASS "
        f"({output_path}, {duration:.2f}s, 24 kHz mono PCM-16)"
    )


if __name__ == "__main__":
    asyncio.run(main())

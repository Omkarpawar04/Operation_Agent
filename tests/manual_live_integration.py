"""Opt-in live smoke test for configured Groq, Deepgram, and Kokoro.

Run manually with an optional raw 16 kHz mono signed PCM recording:
    python tests/manual_live_integration.py --audio-pcm answer.pcm
No audio is saved by this script.
"""

import argparse
import asyncio
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.evaluator import InterviewEvaluator
from agents.interviewer import InterviewerAgent
from agents.planner import InterviewPlanner
from audio.fallback_pipeline import FallbackVoicePipeline
from config import settings


async def main(audio_path: str | None) -> None:
    if not settings.groq_key:
        raise SystemExit("GROQ_API_KEY is required for the live test.")

    planner = InterviewPlanner()
    plan = await planner.generate_plan(
        "Backend engineer with three years of Python, SQL, and API experience. "
        "Built a service that reduced request latency by 30%.",
        "Hire a backend engineer to build reliable Python APIs, improve database "
        "performance, and collaborate across product and engineering.",
    )
    print(f"Groq planner: PASS ({plan.interview_plan.total_questions} questions)")

    interviewer = InterviewerAgent()
    pipeline = FallbackVoicePipeline(interviewer=interviewer)
    try:
        question = plan.interview_plan.questions[0]
        if settings.deepgram_key and audio_path:
            audio = Path(audio_path).read_bytes()
            transcript = await pipeline.transcribe_audio(audio, sample_rate=16000)
            print(f"Deepgram STT: PASS ({transcript[:100]!r})")
        else:
            transcript = (
                "I profiled the slow endpoint, found repeated database lookups, "
                "added a suitable index, and measured the result with load tests."
            )
            if not settings.deepgram_key:
                print("Deepgram STT: SKIP (DEEPGRAM_API_KEY missing)")
            else:
                print("Deepgram STT: SKIP (pass --audio-pcm with 16 kHz mono PCM)")

        reply = await interviewer.generate_response(
            candidate_message=transcript,
            interview_plan=plan.interview_plan.model_dump(mode="json"),
            conversation_history=[
                {"role": "assistant", "turn_type": "question", "content": question.question},
                {"role": "user", "turn_type": "answer", "content": transcript},
            ],
            current_question=question.model_dump(mode="json"),
        )
        print(f"Groq interviewer: PASS ({reply.action})")

        evaluation = await InterviewEvaluator().evaluate_interview(
            conversation_history=[
                {"role": "assistant", "turn_type": "question", "content": question.question},
                {"role": "user", "turn_type": "answer", "content": transcript},
                {"role": "assistant", "turn_type": "response", "content": reply.text},
            ],
            interview_plan=plan.interview_plan.model_dump(mode="json"),
            candidate_profile=plan.candidate_profile.model_dump(mode="json"),
            job_profile=plan.job_profile.model_dump(mode="json"),
        )
        print(f"Groq evaluator: PASS (score {evaluation.overall_score})")

        total = 0
        async for chunk in pipeline.stream_speech(reply.text):
            total += len(chunk)
        if not total:
            raise RuntimeError("Kokoro returned no audio.")
        print(f"Kokoro local TTS: PASS ({total} PCM bytes)")
    finally:
        await pipeline.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audio-pcm", help="Raw mono PCM s16le audio at 16 kHz")
    args = parser.parse_args()
    asyncio.run(main(args.audio_pcm))

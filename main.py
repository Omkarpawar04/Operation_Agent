
"""
Main application entry point.

Manages:
- FastAPI application lifecycle
- Database initialization
- HTTP health endpoints
- Text-based WebSocket interviews
- Binary WebSocket audio streaming
- Voice activity detection
- Deepgram speech transcription
- AI interviewer responses
- Kokoro local speech generation
- Conversation persistence
"""

import asyncio
import hashlib
import importlib.util
import json
import logging
import time
import uuid
import io
import zipfile
import xml.etree.ElementTree as ET
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from config import settings

from storage.db import database, DatabaseError, ActiveSessionLimitError

from agents.planner import (
    InterviewPlanner,
    PlannerError,
    PlannerRateLimitError,
)
from agents.interviewer import interviewer, InterviewerError
from agents.evaluator import evaluator, EvaluatorError
from agents.groq_client import close_groq_client

from audio.websocket_audio import (
    WebSocketAudioProcessor,
    WebSocketAudioError,
)

from audio.fallback_pipeline import (
    FallbackVoicePipeline,
    FallbackPipelineError,
)
from audio.kokoro_tts import (
    DEFAULT_KOKORO_VOICE,
    KokoroTTSError,
    kokoro_tts_service,
)


# --------------------------------------------------
# LOGGING
# --------------------------------------------------

logging.basicConfig(
    level=getattr(
        logging,
        settings.log_level.upper(),
        logging.INFO,
    ),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger(__name__)


# --------------------------------------------------
# APPLICATION LIFECYCLE
# --------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):

    logger.info("Starting %s...", settings.app_name)

    await database.initialize()

    logger.info("Database initialized successfully.")

    async def warm_local_voice():
        warmup_started = time.perf_counter()
        try:
            await kokoro_tts_service.warmup()
        except Exception as exc:
            logger.warning(
                "Kokoro startup warm-up failed (%s); it will retry on first speech.",
                type(exc).__name__,
            )
        else:
            logger.info(
                "Kokoro model, voice, and first audio warmed in %.2fs.",
                time.perf_counter() - warmup_started,
            )

    # Load the model while the app starts so the first question does not pay
    # model initialization and voice-loading costs.
    warmup_task = asyncio.create_task(warm_local_voice())

    logger.info("Application startup complete.")

    yield

    logger.info("Shutting down application...")
    if not warmup_task.done():
        warmup_task.cancel()
        await asyncio.gather(warmup_task, return_exceptions=True)
    await close_groq_client()
    logger.info("Application shutdown complete.")


# --------------------------------------------------
# FASTAPI APPLICATION
# --------------------------------------------------

app = FastAPI(
    title=settings.app_name,
    description=(
        "An AI-powered voice interview agent "
        "for natural and professional interviews."
    ),
    version="1.0.0",
    debug=settings.debug,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------
# STATIC FRONTEND
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIST_DIR = BASE_DIR / "frontend" / "dist"
FRONTEND_ASSET_DIR = FRONTEND_DIST_DIR / "assets"

if FRONTEND_ASSET_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=FRONTEND_ASSET_DIR), name="frontend-assets")

# --------------------------------------------------
# HTTP ENDPOINTS
# --------------------------------------------------

@app.get("/")
async def root():
    index_file = FRONTEND_DIST_DIR / "index.html"
    if not index_file.is_file():
        raise HTTPException(503, "React frontend build is missing. Run `npm --prefix frontend run build`.")
    return FileResponse(index_file)


@app.get("/health")
async def health_check():

    missing = voice_services_missing()

    return {
        "success": True,
        "status": "healthy",
        "application": settings.app_name,
        "voice_available": not missing,
        "voice_missing": missing,
        "tts_provider": "kokoro-local",
        "tts_status": kokoro_tts_service.status,
    }


@app.get("/api/tts/voices")
async def get_tts_voices():
    """List English voices supported by this Kokoro model."""
    return {
        "default_voice": DEFAULT_KOKORO_VOICE,
        "voices": kokoro_tts_service.voice_catalog(),
    }


@app.post("/api/tts/preview")
async def preview_tts_voice(payload: dict):
    """Generate a short local Kokoro preview for a supported voice."""
    voice = kokoro_tts_service.resolve_voice(payload.get("voice_id"))
    try:
        audio = await kokoro_tts_service.synthesize_wav(
            "Hello, thank you for joining the interview. I look forward to our conversation.",
            voice=voice,
        )
    except KokoroTTSError as exc:
        raise HTTPException(503, "Kokoro could not generate the voice preview.") from exc
    return Response(
        content=audio,
        media_type="audio/wav",
        headers={"Cache-Control": "no-store", "X-Kokoro-Voice": voice},
    )


def voice_services_missing() -> list[str]:
    missing = []
    if not settings.deepgram_key:
        missing.append("DEEPGRAM_API_KEY")
    if not settings.kokoro_enabled:
        missing.append("KOKORO_ENABLED=true")
    elif importlib.util.find_spec("kokoro") is None:
        missing.append("Kokoro is not installed; run the app with venv-kokoro")
    return missing


MAX_DOCUMENT_BYTES = 5 * 1024 * 1024


async def extract_document(upload: UploadFile) -> str:
    """Extract plain text from a bounded TXT, PDF, or DOCX upload."""
    name = (upload.filename or "").lower()
    content = await upload.read(MAX_DOCUMENT_BYTES + 1)
    if not content or len(content) > MAX_DOCUMENT_BYTES:
        raise HTTPException(413, "Document must be non-empty and at most 5 MB.")
    try:
        if name.endswith(".txt"):
            text = content.decode("utf-8-sig")
        elif name.endswith(".pdf"):
            if not content.startswith(b"%PDF"):
                raise ValueError("Invalid PDF file")
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(content), strict=True)
            if len(reader.pages) > 100:
                raise HTTPException(413, "PDF exceeds the 100 page limit.")
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        elif name.endswith(".docx"):
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                if "word/document.xml" not in archive.namelist():
                    raise ValueError("Invalid DOCX file")
                document = archive.getinfo("word/document.xml")
                if document.file_size > MAX_DOCUMENT_BYTES:
                    raise HTTPException(413, "DOCX document content is too large.")
                root = ET.fromstring(archive.read(document))
                text = " ".join(node.text or "" for node in root.iter()
                                if node.tag.endswith("}t"))
        else:
            raise HTTPException(415, "Supported formats are TXT, PDF, and DOCX.")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(400, "Could not read the uploaded document.") from exc
    text = text.strip()
    if not text:
        raise HTTPException(400, "The uploaded document contains no extractable text.")
    return text[:100_000]


@app.post("/api/extract")
async def extract_uploaded_document(file: UploadFile = File(...)):
    return {"text": await extract_document(file)}


@app.get("/api/interviews")
async def interview_history(limit: int = 50):
    return {"interviews": await database.list_sessions(limit)}


@app.get("/api/interviews/{session_id}")
async def get_interview(session_id: str):
    session = await database.get_session(session_id)
    if session is None:
        raise HTTPException(404, "Interview not found.")
    session.pop("client_ip", None)
    session["turns"] = await database.get_turns(session_id)
    return session


@app.get("/api/interviews/{session_id}/report")
async def get_evaluation_report(session_id: str):
    session = await database.get_session(session_id)
    if session is None:
        raise HTTPException(404, "Interview not found.")
    if not session.get("evaluation_report"):
        raise HTTPException(404, "Evaluation report is not available yet.")
    return session["evaluation_report"]


async def evaluate_completed_session(session_id: str) -> dict:
    session = await database.get_session(session_id)
    if not session:
        raise DatabaseError("Interview session was not found.")
    turns = await database.get_turns(session_id)
    result = await evaluator.evaluate_interview(
        conversation_history=turns,
        interview_plan=session.get("interview_plan") or {},
        candidate_profile=session.get("candidate_profile") or {},
        job_profile=session.get("job_profile") or {},
    )
    report = result.model_dump(mode="json")
    report["overall_score"] = evaluator.calculate_overall_score(result)
    await database.update_session(session_id, evaluation_report=report)
    return report


@app.post("/api/interviews/{session_id}/evaluate")
async def retry_evaluation(session_id: str):
    session = await database.get_session(session_id)
    if session is None:
        raise HTTPException(404, "Interview not found.")
    if session["status"] != "completed":
        raise HTTPException(409, "Only completed interviews can be evaluated.")
    try:
        return await evaluate_completed_session(session_id)
    except EvaluatorError as exc:
        raise HTTPException(503, str(exc)) from exc


# --------------------------------------------------
# WEBSOCKET HELPERS
# --------------------------------------------------

async def send_error(
    websocket: WebSocket,
    message: str,
    code: str = "INTERVIEW_ERROR",
):
    """Send a consistent error response."""

    await websocket.send_json({
        "event": "interview_error",
        "success": False,
        "code": code,
        "message": message,
    })


def find_question(
    interview_plan: dict,
    question_id: str | None,
):
    """Find a planned question by its ID."""

    if question_id is None:
        return None

    return next(
        (
            question
            for question in interview_plan.get("questions", [])
            if str(question["id"]) == str(question_id)
        ),
        None,
    )


# --------------------------------------------------
# WEBSOCKET INTERVIEW ENDPOINT
# --------------------------------------------------

@app.websocket("/ws/interview")
async def interview_websocket(websocket: WebSocket):

    await websocket.accept()

    logger.info("New interview WebSocket connection.")

    session_id = None
    interview_plan = None
    current_question = None
    followup_counts: dict[str, int] = {}

    audio_processor = None
    voice_pipeline = None
    selected_voice = DEFAULT_KOKORO_VOICE
    audio_enabled = False
    recording_consent_accepted = False
    recording_active = False
    interview_paused = False
    initial_speech_text = None
    tts_task: asyncio.Task | None = None
    processed_audio_hashes: set[str] = set()
    live_transcription_task: asyncio.Task | None = None
    live_transcription_metadata: dict[str, int] | None = None
    live_transcription_sequence = 0
    live_transcription_turn_id = 0
    live_transcription_last_end_bytes = 0
    live_transcription_error_sent = False
    live_transcription_disabled = False

    async def flush_live_transcription():
        nonlocal live_transcription_task
        nonlocal live_transcription_metadata
        nonlocal live_transcription_error_sent
        nonlocal live_transcription_disabled

        task = live_transcription_task
        if task is None or not task.done():
            return

        metadata = live_transcription_metadata
        live_transcription_task = None
        live_transcription_metadata = None

        try:
            text = task.result()
        except asyncio.CancelledError:
            return
        except Exception as error:
            logger.warning(
                "Live transcription request failed (%s).",
                type(error).__name__,
            )
            live_transcription_disabled = True
            if not live_transcription_error_sent:
                await websocket.send_json({
                    "event": "live_transcription_error",
                    "success": False,
                    "message": "Live captions are temporarily unavailable.",
                })
                live_transcription_error_sent = True
            return

        if text and metadata and not live_transcription_disabled:
            await websocket.send_json({
                "event": "live_transcription",
                "success": True,
                "text": text,
                **metadata,
            })

    def cancel_live_transcription():
        if live_transcription_task is not None and not live_transcription_task.done():
            live_transcription_task.cancel()

    async def deliver_speech(
        text: str,
        voice_turn_started_at: float | None = None,
    ):
        if not voice_pipeline or not text.strip():
            return
        try:
            synthesis_started = time.perf_counter()
            logger.info("Kokoro speech requested (%d characters).", len(text))
            await websocket.send_json({
                "event": "audio_generating", "success": True,
                "provider": "kokoro-local",
                "message": "Preparing the local interviewer voice.",
            })
            chunks = voice_pipeline.stream_speech(text).__aiter__()
            first_chunk = await anext(chunks, None)
            if not first_chunk:
                raise FallbackPipelineError("Kokoro returned no audio.")

            logger.info(
                "Kokoro first audio ready in %.2fs.",
                time.perf_counter() - synthesis_started,
            )
            if voice_turn_started_at is not None:
                logger.info(
                    "Voice answer VAD-end-to-first-audio: %.2fs.",
                    time.perf_counter() - voice_turn_started_at,
                )

            await websocket.send_json({
                "event": "audio_started", "success": True,
                "sample_rate": settings.kokoro_sample_rate,
                "format": "pcm_s16le", "channels": 1,
            })
            await websocket.send_bytes(first_chunk)
            async for chunk in chunks:
                await websocket.send_bytes(chunk)
            await websocket.send_json({"event": "audio_completed", "success": True})
            logger.info(
                "Kokoro speech delivered in %.2fs.",
                time.perf_counter() - synthesis_started,
            )
            if voice_turn_started_at is not None:
                logger.info(
                    "Voice answer VAD-end-to-audio-complete: %.2fs.",
                    time.perf_counter() - voice_turn_started_at,
                )
        except asyncio.CancelledError:
            raise
        except FallbackPipelineError:
            logger.exception("Local Kokoro TTS failed for an interview turn.")
            try:
                await websocket.send_json({
                    "event": "audio_error", "success": False,
                    "message": (
                        "Local Kokoro speech could not be generated. Check the "
                        "venv-kokoro installation and model files, then retry."
                    ),
                })
            except Exception:
                pass

    def queue_speech(
        text: str,
        voice_turn_started_at: float | None = None,
    ):
        nonlocal tts_task
        if tts_task and not tts_task.done():
            tts_task.cancel()
        tts_task = asyncio.create_task(
            deliver_speech(text, voice_turn_started_at)
        )

    await websocket.send_json({
        "event": "connection_ready",
        "success": True,
        "message": "Connected to the AI interview agent.",
    })

    # --------------------------------------------------
    # PROCESS A CANDIDATE ANSWER
    # --------------------------------------------------

    async def process_candidate_answer(
        candidate_message: str,
        source: str = "text",
        generate_audio: bool = False,
        voice_turn_started_at: float | None = None,
    ):

        nonlocal session_id
        nonlocal interview_plan
        nonlocal current_question

        if session_id is None or interview_plan is None:

            await send_error(
                websocket,
                "Start an interview before submitting answers.",
                "NO_ACTIVE_SESSION",
            )

            return

        if interview_paused or not recording_consent_accepted or not recording_active:
            await send_error(
                websocket,
                "The interview is paused until recording consent and recording are restored.",
                "RECORDING_REQUIRED",
            )
            return

        if not isinstance(candidate_message, str) or not candidate_message.strip():

            await send_error(
                websocket,
                "Candidate answer cannot be empty.",
                "EMPTY_ANSWER",
            )

            return

        if len(candidate_message) > 10_000:
            await send_error(websocket, "Answer must be 10,000 characters or fewer.", "ANSWER_TOO_LONG")
            return

        active_session_id = session_id

        try:

            # ------------------------------------------
            # SAVE CANDIDATE ANSWER
            # ------------------------------------------

            await database.save_turn(
                session_id=active_session_id,
                role="user",
                content=candidate_message.strip(),
                turn_type="answer",
                metadata={
                    "question_id": (
                        current_question.get("id")
                        if current_question
                        else None
                    ),
                    "source": source,
                },
            )

            # ------------------------------------------
            # GET CONVERSATION HISTORY
            # ------------------------------------------

            conversation_history = await database.get_turns(
                active_session_id
            )

            # ------------------------------------------
            # GENERATE AI RESPONSE
            # ------------------------------------------

            response_started = time.perf_counter()
            reply = await interviewer.generate_response(
                candidate_message=candidate_message.strip(),
                interview_plan=interview_plan,
                conversation_history=conversation_history,
                current_question=current_question,
            )
            logger.info(
                "Groq interviewer response ready in %.2fs (%d characters).",
                time.perf_counter() - response_started,
                len(reply.text),
            )

            if current_question is not None and str(reply.question_id) == str(current_question.get("id")):
                key = str(current_question.get("id"))
                followup_counts[key] = followup_counts.get(key, 0) + 1
                if followup_counts[key] > 2:
                    questions = interview_plan.get("questions", [])
                    position = next((i for i, item in enumerate(questions)
                                     if str(item.get("id")) == key), -1)
                    if position + 1 < len(questions):
                        next_item = questions[position + 1]
                        reply.text = "Thank you. Let's move on. " + next_item.get("question", "")
                        reply.question_id = str(next_item.get("id"))

            # ------------------------------------------
            # SAVE AI RESPONSE
            # ------------------------------------------

            await database.save_turn(
                session_id=active_session_id,
                role="assistant",
                content=reply.text,
                turn_type="response",
                metadata={
                    "action": reply.action,
                    "question_id": reply.question_id,
                },
            )

            # ------------------------------------------
            # UPDATE CURRENT QUESTION
            # ------------------------------------------

            next_question = find_question(
                interview_plan,
                reply.question_id,
            )

            if next_question is not None:
                current_question = next_question
                question_index = next((index for index, question in enumerate(interview_plan.get("questions", []))
                                       if str(question.get("id")) == str(current_question.get("id"))), 0)
                await database.update_session(
                    session_id=active_session_id,
                    current_question_index=question_index,
                )

            # ------------------------------------------
            # CHECK INTERVIEW COMPLETION
            # ------------------------------------------

            completed = (
                reply.interview_complete
                or reply.action == "finish"
            )

            if completed:

                await database.update_session(
                    session_id=active_session_id,
                    status="completed",
                )

            # ------------------------------------------
            # SEND TEXT RESPONSE
            # ------------------------------------------

            await websocket.send_json({
                "event": "interviewer_response",
                "success": True,
                "session_id": active_session_id,
                "text": reply.text,
                "action": (
                    "finish" if completed else reply.action
                ),
                "question_id": reply.question_id,
                "question_index": (question_index + 1) if next_question is not None else None,
                "interview_complete": completed,
                "source": source,
            })

            # ------------------------------------------
            # GENERATE INTERVIEWER AUDIO
            # ------------------------------------------

            if generate_audio and voice_pipeline is not None:
                queue_speech(reply.text, voice_turn_started_at)

            if completed and tts_task:
                try:
                    await tts_task
                except asyncio.CancelledError:
                    pass

            # ------------------------------------------
            # COMPLETE INTERVIEW
            # ------------------------------------------

            if completed:

                await websocket.send_json({
                    "event": "interview_completed",
                    "success": True,
                    "session_id": active_session_id,
                    "message": (
                        "Your interview has been completed."
                    ),
                })

                try:
                    report = await evaluate_completed_session(active_session_id)
                    await websocket.send_json({
                        "event": "evaluation_result",
                        "success": True,
                        "session_id": active_session_id,
                        "report": report,
                    })
                except Exception as exc:
                    # The completed transcript remains available for the HTTP retry endpoint.
                    logger.warning("Evaluation unavailable for session %s (%s)", active_session_id, type(exc).__name__)
                    await websocket.send_json({
                        "event": "evaluation_error",
                        "success": False,
                        "session_id": active_session_id,
                        "message": "Your interview is saved. The report could not be generated yet; you can retry it from interview history.",
                    })

                session_id = None
                interview_plan = None
                current_question = None

        except (InterviewerError, DatabaseError):

            logger.exception(
                "Could not process candidate answer."
            )

            await send_error(
                websocket,
                "Unable to process your answer. Please try again.",
                "ANSWER_PROCESSING_FAILED",
            )

        except Exception:

            logger.exception(
                "Unexpected error while processing answer."
            )

            await send_error(
                websocket,
                "An unexpected error occurred while processing your answer.",
                "INTERNAL_ERROR",
            )

    # --------------------------------------------------
    # MAIN WEBSOCKET RECEIVE LOOP
    # --------------------------------------------------

    try:

        while True:

            try:

                incoming = await asyncio.wait_for(
                    websocket.receive(),
                    timeout=settings.session_idle_timeout_seconds,
                )

            except asyncio.TimeoutError:

                if session_id is not None:
                    await database.update_session(session_id, status="expired")

                await send_error(
                    websocket,
                    "Interview connection timed out due to inactivity.",
                    "SESSION_TIMEOUT",
                )

                await websocket.close(
                    code=1001,
                    reason="Session idle timeout",
                )

                break

            # ------------------------------------------
            # HANDLE DISCONNECTION
            # ------------------------------------------

            if incoming["type"] == "websocket.disconnect":
                break

            # ------------------------------------------
            # HANDLE BINARY AUDIO
            # ------------------------------------------

            if incoming.get("bytes") is not None:

                audio_chunk = incoming["bytes"]

                if len(audio_chunk) > 256 * 1024:
                    await send_error(websocket, "Audio frame exceeds 256 KB.", "AUDIO_TOO_LARGE")
                    continue

                if not audio_enabled or audio_processor is None or interview_paused:

                    await send_error(
                        websocket,
                        "Start audio before sending microphone data.",
                        "AUDIO_NOT_STARTED",
                    )

                    continue

                if session_id is None:

                    await send_error(
                        websocket,
                        "Start an interview before sending microphone data.",
                        "NO_ACTIVE_SESSION",
                    )

                    continue

                try:

                    result = audio_processor.process_audio(
                        audio_chunk
                    )
                    await flush_live_transcription()

                    if result.speech_started:
                        if live_transcription_task is not None:
                            cancel_live_transcription()
                        live_transcription_turn_id += 1
                        live_transcription_sequence = 0
                        live_transcription_last_end_bytes = 0
                        live_transcription_error_sent = False
                        live_transcription_disabled = False

                    # ----------------------------------
                    # SPEECH STARTED
                    # ----------------------------------

                    if result.speech_started:

                        await websocket.send_json({
                            "event": "speech_started",
                            "success": True,
                        })

                    # ----------------------------------
                    # SPEECH COMPLETED
                    # ----------------------------------

                    if result.speech_ended:

                        completed_utterances = (
                            result.completed_utterances
                        )

                        await websocket.send_json({
                            "event": "speech_ended",
                            "success": True,
                            "audio_duration_ms": (
                                result.audio_duration_ms
                            ),
                            "completed_utterances": len(
                                completed_utterances
                            ),
                        })
                        cancel_live_transcription()

                        # Process every completed utterance.
                        for utterance_index, completed_audio in enumerate(completed_utterances):

                            if not completed_audio:
                                continue

                            audio_hash = hashlib.sha256(completed_audio).hexdigest()
                            if audio_hash in processed_audio_hashes:
                                await websocket.send_json({"event": "duplicate_audio_ignored", "success": True})
                                continue
                            processed_audio_hashes.add(audio_hash)

                            # Stop if the interview has finished.
                            if session_id is None:
                                break

                            if voice_pipeline is None:
                                await send_error(
                                    websocket,
                                    "Voice pipeline is not initialized.",
                                    "VOICE_PIPELINE_NOT_READY",
                                )
                                break

                            await websocket.send_json({
                                "event": "transcription_started",
                                "success": True,
                            })

                            try:

                                # Transcribe completed speech.
                                transcription_started = time.perf_counter()
                                voice_turn_started_at = transcription_started
                                keyterm_builder = getattr(
                                    voice_pipeline, "interview_keyterms", None
                                )
                                keyterms = (
                                    keyterm_builder(interview_plan, current_question)
                                    if keyterm_builder
                                    else None
                                )
                                transcript = (
                                    await voice_pipeline.transcribe_audio(
                                        audio=completed_audio,
                                        sample_rate=(
                                            audio_processor.sample_rate
                                        ),
                                        keyterms=keyterms,
                                    )
                                )
                                logger.info(
                                    "Deepgram transcription ready in %.2fs for %.1fs of audio.",
                                    time.perf_counter() - transcription_started,
                                    len(completed_audio) / (audio_processor.sample_rate * 2),
                                )

                                if not transcript or not transcript.strip():
                                    repeat_prompt = "I did not catch that. Please repeat your answer when you are ready."
                                    await database.save_turn(
                                        session_id, "assistant", repeat_prompt,
                                        "transcription_retry",
                                    )
                                    await websocket.send_json({
                                        "event": "transcription_unclear",
                                        "success": True,
                                        "message": repeat_prompt,
                                    })
                                    queue_speech(repeat_prompt)
                                    continue

                                await websocket.send_json({
                                    "event": "transcript_received",
                                    "success": True,
                                    "text": transcript,
                                })

                                # Process transcript as an answer.
                                await process_candidate_answer(
                                    candidate_message=transcript,
                                    source="voice",
                                    generate_audio=True,
                                    voice_turn_started_at=voice_turn_started_at,
                                )

                                # Preserve turn order if a network frame contains
                                # multiple finished utterances: finish speaking
                                # before processing the next buffered answer.
                                if utterance_index + 1 < len(completed_utterances) and tts_task:
                                    try:
                                        await tts_task
                                    except asyncio.CancelledError:
                                        pass

                            except FallbackPipelineError as error:
                                if "could not detect" in str(error).lower():
                                    repeat_prompt = "I did not catch that. Please repeat your answer when you are ready."
                                    await database.save_turn(session_id, "assistant", repeat_prompt, "transcription_retry")
                                    await websocket.send_json({"event": "transcription_unclear", "success": True,
                                                               "message": repeat_prompt})
                                    queue_speech(repeat_prompt)
                                else:
                                    logger.warning("Speech transcription provider failed.")
                                    await send_error(websocket,
                                                     "Speech transcription failed. Check Deepgram configuration and try again.",
                                                     "TRANSCRIPTION_FAILED")

                    elif (
                        getattr(audio_processor, "is_speaking", False)
                        and voice_pipeline is not None
                        and not live_transcription_disabled
                        and live_transcription_task is None
                    ):
                        snapshot = audio_processor.get_utterance_snapshot()
                        sample_rate = audio_processor.sample_rate
                        bytes_per_second = sample_rate * 2
                        interval_bytes = bytes_per_second * 3
                        end_bytes = len(snapshot)
                        if (
                            end_bytes >= interval_bytes
                            and end_bytes - live_transcription_last_end_bytes >= interval_bytes
                        ):
                            overlap_bytes = int(bytes_per_second * 0.8)
                            start_bytes = max(
                                0,
                                live_transcription_last_end_bytes - overlap_bytes,
                            )
                            live_chunk = snapshot[start_bytes:end_bytes]
                            live_transcription_sequence += 1
                            live_transcription_last_end_bytes = end_bytes
                            keyterm_builder = getattr(
                                voice_pipeline,
                                "interview_keyterms",
                                None,
                            )
                            keyterms = (
                                keyterm_builder(interview_plan, current_question)
                                if keyterm_builder
                                else None
                            )
                            live_transcription_metadata = {
                                "turn_id": live_transcription_turn_id,
                                "sequence": live_transcription_sequence,
                                "start_ms": round(start_bytes * 1000 / bytes_per_second),
                                "end_ms": round(end_bytes * 1000 / bytes_per_second),
                            }
                            live_transcription_task = asyncio.create_task(
                                voice_pipeline.transcribe_audio(
                                    audio=live_chunk,
                                    sample_rate=sample_rate,
                                    keyterms=keyterms,
                                )
                            )

                except WebSocketAudioError as error:

                    logger.warning(
                        "Audio processing failed: %s (buffered %.1fs; limit %ds).",
                        error,
                        audio_processor.get_buffer_duration_ms() / 1000,
                        audio_processor.max_buffer_seconds,
                    )

                    cancel_live_transcription()
                    audio_processor.reset()

                    await send_error(
                        websocket,
                        f"Your recording exceeded the {audio_processor.max_buffer_seconds}-second answer limit. Please pause between thoughts and try again."
                        if "buffer limit" in str(error).lower()
                        else "Invalid or unsupported audio data.",
                        "AUDIO_PROCESSING_FAILED",
                    )

                continue

            # ------------------------------------------
            # HANDLE JSON TEXT MESSAGES
            # ------------------------------------------

            raw_message = incoming.get("text")

            if raw_message is None:
                continue

            try:

                message = json.loads(raw_message)

            except (json.JSONDecodeError, TypeError):

                await send_error(
                    websocket,
                    "Invalid JSON message.",
                    "INVALID_JSON",
                )

                continue

            if not isinstance(message, dict):

                await send_error(
                    websocket,
                    "Expected a JSON object.",
                    "INVALID_MESSAGE",
                )

                continue

            event = message.get("event")

            if event == "recording_consent":
                accepted = message.get("accepted") is True
                recording_consent_accepted = accepted
                if not accepted:
                    recording_active = False
                    if session_id is not None:
                        interview_paused = True
                        audio_enabled = False
                        if audio_processor is not None:
                            cancel_live_transcription()
                            audio_processor.reset()
                        if tts_task and not tts_task.done():
                            tts_task.cancel()
                    await websocket.send_json({
                        "event": "interview_paused" if session_id is not None else "recording_consent_status",
                        "success": True,
                        "accepted": False,
                        "reason": "consent_withdrawn" if session_id is not None else None,
                        "message": "Recording consent was withdrawn. The interview is paused.",
                    })
                else:
                    await websocket.send_json({
                        "event": "recording_consent_status",
                        "success": True,
                        "accepted": True,
                    })
                continue

            if event == "recording_status":
                active = message.get("active") is True
                if active and not recording_consent_accepted:
                    await send_error(websocket, "Recording consent is required.", "RECORDING_CONSENT_REQUIRED")
                    continue
                recording_active = active
                if not active and session_id is not None:
                    interview_paused = True
                    audio_enabled = False
                    if audio_processor is not None:
                        cancel_live_transcription()
                        audio_processor.reset()
                    if tts_task and not tts_task.done():
                        tts_task.cancel()
                    await websocket.send_json({
                        "event": "interview_paused",
                        "success": True,
                        "reason": "recording_stopped",
                        "message": "Recording stopped. Restore your camera and recording to continue.",
                    })
                else:
                    await websocket.send_json({
                        "event": "recording_status",
                        "success": True,
                        "active": recording_active,
                    })
                continue

            # Resume only an in-progress session and restore its conversation state.
            if event == "resume_session":
                if not recording_consent_accepted or not recording_active:
                    await send_error(websocket, "Accept recording consent and restore recording before resuming.", "RECORDING_REQUIRED")
                    continue
                requested_id = message.get("session_id")
                if not isinstance(requested_id, str) or not requested_id:
                    await send_error(websocket, "A valid session_id is required.", "INVALID_SESSION")
                    continue
                await database.expire_idle_sessions(settings.session_idle_timeout_seconds)
                restored = await database.get_session(requested_id)
                if not restored or restored.get("status") != "in_progress":
                    await send_error(websocket, "This interview cannot be resumed.", "SESSION_NOT_RESUMABLE")
                    continue
                if (restored.get("client_ip") and websocket.client
                        and restored["client_ip"] != websocket.client.host):
                    await send_error(websocket, "This interview belongs to a different client.", "SESSION_ACCESS_DENIED")
                    continue
                session_id = requested_id
                interview_paused = True
                selected_voice = kokoro_tts_service.resolve_voice(
                    restored.get("tts_voice")
                )
                interview_plan = restored.get("interview_plan")
                history = await database.get_turns(session_id)
                last_question_id = next((
                    (turn.get("metadata") or {}).get("question_id")
                    for turn in reversed(history)
                    if turn.get("role") == "assistant"
                    and (turn.get("metadata") or {}).get("question_id") is not None
                ), None)
                current_question = find_question(interview_plan or {}, str(last_question_id))
                if current_question is None:
                    current_question = (interview_plan or {}).get("questions", [None])[0]
                await websocket.send_json({
                    "event": "interview_started", "success": True,
                    "session_id": session_id,
                    "tts_voice": selected_voice,
                    "candidate_profile": restored.get("candidate_profile"),
                    "job_profile": restored.get("job_profile"),
                    "total_questions": (interview_plan or {}).get("total_questions", 0),
                    "question": ({"id": current_question.get("id"),
                                  "text": current_question.get("question")}
                                 if current_question else None),
                    "resumed": True,
                })
                continue

            # ==========================================
            # START INTERVIEW
            # ==========================================

            if event == "start_interview":

                if (message.get("recording_consent") is not True
                        or not recording_consent_accepted
                        or not recording_active):
                    await send_error(
                        websocket,
                        "Explicit recording consent and an active recording are required before the interview can start.",
                        "RECORDING_CONSENT_REQUIRED",
                    )
                    continue

                selected_voice = kokoro_tts_service.resolve_voice(
                    message.get("voice_id")
                )

                missing_voice = voice_services_missing()
                if missing_voice:
                    await send_error(
                        websocket,
                        "Voice interview is not configured. Add " + ", ".join(missing_voice) + " and restart the server.",
                        "VOICE_CONFIGURATION_MISSING",
                    )
                    continue

                await database.expire_idle_sessions(settings.session_idle_timeout_seconds)

                if session_id is not None:

                    await send_error(
                        websocket,
                        "An interview is already active.",
                        "SESSION_ALREADY_STARTED",
                    )

                    continue

                resume_text = message.get("resume_text", "")
                job_description = message.get(
                    "job_description",
                    "",
                )

                candidate_name = message.get("candidate_name")

                if (
                    not isinstance(resume_text, str)
                    or not resume_text.strip()
                    or len(resume_text) > 100_000
                ):

                    await send_error(
                        websocket,
                        "A valid candidate resume is required.",
                        "INVALID_RESUME",
                    )

                    continue

                if (
                    not isinstance(job_description, str)
                    or not job_description.strip()
                    or len(job_description) > 100_000
                ):

                    await send_error(
                        websocket,
                        "A valid job description is required.",
                        "INVALID_JOB_DESCRIPTION",
                    )

                    continue

                try:

                    await websocket.send_json({
                        "event": "planning_started",
                        "message": (
                            "Preparing your personalized interview."
                        ),
                    })

                    planner = InterviewPlanner()

                    planning_started = time.perf_counter()
                    plan_response = await planner.generate_plan(
                        resume_text=resume_text,
                        job_description=job_description,
                    )
                    logger.info(
                        "Interview plan ready in %.2fs.",
                        time.perf_counter() - planning_started,
                    )

                    candidate_profile = (
                        plan_response.candidate_profile.model_dump(
                            mode="json"
                        )
                    )

                    job_profile = (
                        plan_response.job_profile.model_dump(
                            mode="json"
                        )
                    )

                    interview_plan = (
                        plan_response.interview_plan.model_dump(
                            mode="json"
                        )
                    )

                    processed_audio_hashes.clear()

                    session_id = str(uuid.uuid4())

                    session = await database.create_session(
                        session_id=session_id,
                        candidate_name=(
                            candidate_name
                            or candidate_profile.get("name")
                        ),
                        job_title=job_profile.get("job_title"),
                        job_description=job_description,
                        candidate_profile=candidate_profile,
                        job_profile=job_profile,
                        interview_plan=interview_plan,
                        tts_voice=selected_voice,
                        client_ip=(websocket.client.host if websocket.client else None),
                        max_active_per_ip=settings.max_concurrent_sessions_per_ip,
                    )

                    if session is None:

                        raise DatabaseError(
                            "Could not create interview session."
                        )

                    await database.update_session(
                        session_id=session_id,
                        status="in_progress",
                    )

                    current_question = (
                        interview_plan["questions"][0]
                    )

                    first_question = current_question["question"]

                    greeting = (
                        f"Hello {candidate_name or candidate_profile.get('name') or 'there'}, "
                        f"welcome to your interview for {job_profile.get('job_title') or 'this role'}. "
                        "I am your AI interviewer. I will ask questions based on your experience and the role. "
                        "Please answer naturally. Let us get started."
                    )
                    initial_speech_text = f"{greeting} {first_question}"

                    await database.save_turn(
                        session_id=session_id,
                        role="assistant",
                        content=greeting,
                        turn_type="greeting",
                    )

                    await database.save_turn(
                        session_id=session_id,
                        role="assistant",
                        content=first_question,
                        turn_type="question",
                        metadata={
                            "question_id": current_question["id"],
                            "category": current_question["category"],
                        },
                    )

                    logger.info(
                        "Interview started: %s",
                        session_id,
                    )

                    await websocket.send_json({
                        "event": "interview_started",
                        "success": True,
                        "session_id": session_id,
                        "tts_voice": selected_voice,
                        "candidate_profile": candidate_profile,
                        "job_profile": job_profile,
                        "total_questions": (
                            interview_plan["total_questions"]
                        ),
                        "question": {
                            "id": current_question["id"],
                            "category": current_question["category"],
                            "difficulty": current_question["difficulty"],
                            "text": first_question,
                        },
                        "greeting": greeting,
                        "question_index": 1,
                        "message": "Your interview has started.",
                    })


                except ActiveSessionLimitError:
                    await send_error(
                        websocket,
                        "You already have the maximum number of active interviews. Resume or complete one before starting another.",
                        "CONCURRENT_SESSION_LIMIT",
                    )
                    session_id = None
                    interview_plan = None
                    current_question = None

                except PlannerRateLimitError as error:

                    logger.exception(
                        "Groq rate-limited interview planning."
                    )

                    await send_error(
                        websocket,
                        str(error),
                        "GROQ_RATE_LIMITED",
                    )

                    session_id = None
                    interview_plan = None
                    current_question = None

                except (PlannerError, DatabaseError):

                    logger.exception(
                        "Interview initialization failed."
                    )

                    await send_error(
                        websocket,
                        "Unable to initialize the interview.",
                        "INTERVIEW_INITIALIZATION_FAILED",
                    )

                    if session_id is not None:

                        try:
                            await database.update_session(
                                session_id=session_id,
                                status="failed",
                            )
                        except DatabaseError:
                            logger.exception(
                                "Could not mark failed session."
                            )

                    session_id = None
                    interview_plan = None
                    current_question = None

                except Exception:

                    logger.exception(
                        "Unexpected interview initialization error."
                    )

                    await send_error(
                        websocket,
                        "Unable to start the interview. Please try again.",
                        "INTERNAL_ERROR",
                    )

                    if session_id is not None:

                        try:
                            await database.update_session(
                                session_id=session_id,
                                status="failed",
                            )
                        except DatabaseError:
                            logger.exception(
                                "Could not mark failed session."
                            )

                    session_id = None
                    interview_plan = None
                    current_question = None

                continue

            # ==========================================
            # START AUDIO
            # ==========================================

            elif event == "start_audio":

                if session_id is None:

                    await send_error(
                        websocket,
                        "Start an interview before enabling audio.",
                        "NO_ACTIVE_SESSION",
                    )

                    continue

                if not recording_consent_accepted or not recording_active:
                    interview_paused = True
                    await send_error(websocket, "Recording must be restored before audio can resume.", "RECORDING_REQUIRED")
                    continue

                if audio_enabled:

                    await send_error(
                        websocket,
                        "Audio processing is already enabled.",
                        "AUDIO_ALREADY_STARTED",
                    )

                    continue

                try:

                    audio_processor = WebSocketAudioProcessor()

                    if voice_pipeline is None:

                        voice_pipeline = FallbackVoicePipeline(
                            interviewer=interviewer,
                            tts_voice=selected_voice,
                        )

                    audio_enabled = True

                    await websocket.send_json({
                        "event": "audio_ready",
                        "success": True,
                        "input_sample_rate": (
                            settings.audio_input_sample_rate
                        ),
                        "output_sample_rate": settings.kokoro_sample_rate,
                        "format": "pcm_s16le",
                        "channels": 1,
                    })

                    logger.info(
                        "Audio enabled for session %s",
                        session_id,
                    )

                except Exception:

                    logger.exception(
                        "Could not initialize audio processing."
                    )

                    if audio_processor is not None:
                        cancel_live_transcription()
                        audio_processor.reset()

                    audio_processor = None
                    audio_enabled = False

                    await send_error(
                        websocket,
                        "Could not initialize audio processing.",
                        "AUDIO_INITIALIZATION_FAILED",
                    )

                continue

            # ==========================================
            # STOP AUDIO
            # ==========================================

            elif event == "stop_audio":

                if session_id is not None:
                    interview_paused = True

                if audio_processor is not None:
                    cancel_live_transcription()
                    audio_processor.reset()

                audio_enabled = False

                await websocket.send_json({
                    "event": "audio_stopped",
                    "success": True,
                })

                if session_id is not None:
                    await websocket.send_json({
                        "event": "interview_paused",
                        "success": True,
                        "reason": "audio_stopped",
                        "message": "Interview paused. Restore recording and audio to continue.",
                    })

                continue

            elif event == "audio_client_ready":
                if session_id is None or current_question is None or voice_pipeline is None:
                    await send_error(websocket, "Voice session is not ready.", "VOICE_PIPELINE_NOT_READY")
                    continue
                if not recording_consent_accepted or not recording_active:
                    interview_paused = True
                    await send_error(websocket, "Recording must be restored before the interview can continue.", "RECORDING_REQUIRED")
                    continue
                interview_paused = False
                try:
                    queue_speech(initial_speech_text or current_question.get("question", ""))
                    initial_speech_text = None
                except Exception:
                    await websocket.send_json({"event": "audio_error", "success": False,
                                               "message": "Could not start interviewer speech."})
                continue

            elif event == "interrupt":
                logger.info(
                    "Interviewer speech interrupted (%s).",
                    message.get("reason", "client request"),
                )
                if tts_task and not tts_task.done():
                    tts_task.cancel()
                    try:
                        await tts_task
                    except asyncio.CancelledError:
                        pass
                await websocket.send_json({"event": "audio_interrupted", "success": True})
                continue

            # ==========================================
            # SUBMIT TEXT ANSWER
            # ==========================================

            elif event == "submit_answer":

                candidate_message = message.get("text", "")

                if (
                    not isinstance(candidate_message, str)
                    or not candidate_message.strip()
                ):

                    await send_error(
                        websocket,
                        "Candidate answer cannot be empty.",
                        "EMPTY_ANSWER",
                    )

                    continue

                await process_candidate_answer(
                    candidate_message=candidate_message,
                    source="text",
                    generate_audio=False,
                )

                continue

            elif event in {"candidate_action", "repeat_question"}:
                action = "repeat" if event == "repeat_question" else message.get("action")
                if session_id is None or interview_plan is None or current_question is None:
                    await send_error(websocket, "There is no active question.", "NO_ACTIVE_SESSION")
                    continue
                if interview_paused or not recording_consent_accepted or not recording_active:
                    await send_error(websocket, "The interview is paused until recording is restored.", "RECORDING_REQUIRED")
                    continue
                if action == "repeat":
                    text = current_question.get("question", "")
                    await database.save_turn(session_id, "assistant", text, "question", {
                        "question_id": current_question.get("id"), "repeat": True,
                    })
                    await websocket.send_json({
                        "event": "interviewer_response", "success": True,
                        "session_id": session_id, "text": text,
                        "action": "repeat", "question_id": current_question.get("id"),
                    })
                    queue_speech(text)
                elif action == "clarify":
                    history = await database.get_turns(session_id)
                    try:
                        clarification = await interviewer.generate_response(
                            candidate_message="Please clarify the current interview question in simpler terms.",
                            interview_plan=interview_plan,
                            conversation_history=history,
                            current_question=current_question,
                        )
                        await database.save_turn(
                            session_id, "assistant", clarification.text,
                            "clarification", {"question_id": current_question.get("id")},
                        )
                        await websocket.send_json({
                            "event": "interviewer_response", "success": True,
                            "session_id": session_id, "text": clarification.text,
                            "action": "clarify", "question_id": current_question.get("id"),
                        })
                        queue_speech(clarification.text)
                    except InterviewerError:
                        await send_error(websocket, "Could not clarify the question. Please try again.", "CLARIFICATION_FAILED")
                elif action == "skip":
                    questions = interview_plan.get("questions", [])
                    current_index = next((i for i, q in enumerate(questions)
                                          if str(q.get("id")) == str(current_question.get("id"))), -1)
                    if current_index + 1 < len(questions):
                        current_question = questions[current_index + 1]
                        await database.update_session(
                            session_id=session_id,
                            current_question_index=current_index + 1,
                        )
                        text = current_question.get("question", "")
                        await database.save_turn(session_id, "assistant", text, "question", {
                            "question_id": current_question.get("id"), "category": current_question.get("category"),
                        })
                        await websocket.send_json({
                            "event": "interviewer_response", "success": True,
                            "session_id": session_id, "text": text,
                            "action": "skip", "question_id": current_question.get("id"),
                        })
                        queue_speech(text)
                    else:
                        await websocket.send_json({
                            "event": "interviewer_response", "success": True,
                            "session_id": session_id,
                            "text": interview_plan.get("closing_prompt", "Thank you. The interview is complete."),
                            "action": "finish", "interview_complete": True,
                        })
                        await database.update_session(session_id, status="completed")
                        await websocket.send_json({
                            "event": "interview_completed", "success": True,
                            "session_id": session_id, "message": "Your interview has been completed.",
                        })
                        try:
                            report = await evaluate_completed_session(session_id)
                            await websocket.send_json({"event": "evaluation_result", "success": True,
                                                       "session_id": session_id, "report": report})
                        except Exception:
                            await websocket.send_json({"event": "evaluation_error", "success": False,
                                                       "session_id": session_id,
                                                       "message": "Interview saved; report generation can be retried from history."})
                        session_id = None
                        interview_plan = None
                        current_question = None
                else:
                    await send_error(websocket, "Action must be repeat, clarify, or skip.", "INVALID_ACTION")
                continue

            # ==========================================
            # END INTERVIEW
            # ==========================================

            elif event in {"end_interview", "finish_interview"}:

                if session_id is None:

                    await send_error(
                        websocket,
                        "There is no active interview to end.",
                        "NO_ACTIVE_SESSION",
                    )

                    continue

                ended_session_id = session_id

                await database.update_session(
                    session_id=ended_session_id,
                    status="completed",
                )

                if audio_processor is not None:
                    cancel_live_transcription()
                    audio_processor.reset()

                audio_enabled = False

                await websocket.send_json({
                    "event": "interview_completed",
                    "success": True,
                    "session_id": ended_session_id,
                    "message": "Interview ended successfully.",
                })

                try:
                    report = await evaluate_completed_session(ended_session_id)
                    await websocket.send_json({
                        "event": "evaluation_result", "success": True,
                        "session_id": ended_session_id, "report": report,
                    })
                except Exception as exc:
                    logger.warning("Evaluation unavailable for session %s (%s)", ended_session_id, type(exc).__name__)
                    await websocket.send_json({
                        "event": "evaluation_error", "success": False,
                        "session_id": ended_session_id,
                        "message": "Your interview is saved. The report could not be generated yet; you can retry it from interview history.",
                    })

                logger.info(
                    "Interview ended: %s",
                    ended_session_id,
                )

                session_id = None
                interview_plan = None
                current_question = None

                continue

            # ==========================================
            # UNKNOWN EVENT
            # ==========================================

            else:

                await send_error(
                    websocket,
                    f"Unknown event: {event}",
                    "UNKNOWN_EVENT",
                )

    except WebSocketDisconnect:

        logger.info(
            "WebSocket disconnected. Session: %s",
            session_id,
        )

    except Exception:

        logger.exception(
            "Unexpected WebSocket connection error."
        )

        try:
            await websocket.close(code=1011)

        except Exception:
            pass

    finally:

        if live_transcription_task is not None:
            if not live_transcription_task.done():
                live_transcription_task.cancel()
            await asyncio.gather(
                live_transcription_task,
                return_exceptions=True,
            )

        if tts_task and not tts_task.done():
            tts_task.cancel()
            await asyncio.gather(tts_task, return_exceptions=True)

        # Release the per-connection HTTP client.
        if voice_pipeline is not None:

            try:
                await voice_pipeline.close()

            except Exception:

                logger.exception(
                    "Could not close voice pipeline."
                )


@app.get("/{frontend_path:path}")
async def serve_react_routes(frontend_path: str):
    """Serve the React entry point for browser routes in the production build."""
    if frontend_path.startswith(("api/", "assets/", "static/")):
        raise HTTPException(404, "Not found.")
    index_file = FRONTEND_DIST_DIR / "index.html"
    if not index_file.is_file():
        raise HTTPException(503, "React frontend build is missing. Run `npm --prefix frontend run build`.")
    return FileResponse(index_file)


# --------------------------------------------------
# APPLICATION ENTRY POINT
# --------------------------------------------------

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )

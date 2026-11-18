
"""
Main application entry point.

Starts the FastAPI server and manages:
- Database initialization
- HTTP health endpoints
- WebSocket interview sessions
- AI interview planning
- AI interviewer communication
- Conversation persistence
"""

import asyncio
import json
import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from storage.db import database, DatabaseError
from agents.planner import InterviewPlanner, PlannerError
from agents.interviewer import interviewer, InterviewerError


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
    logger.info("Application startup complete.")

    yield

    logger.info("Shutting down application...")
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
# HTTP ENDPOINTS
# --------------------------------------------------

@app.get("/")
async def root():

    return {
        "success": True,
        "message": "AI Voice Interview Agent is running.",
        "application": settings.app_name,
    }


@app.get("/health")
async def health_check():

    return {
        "success": True,
        "status": "healthy",
        "application": settings.app_name,
    }


# --------------------------------------------------
# WEBSOCKET HELPERS
# --------------------------------------------------

async def send_error(
    websocket: WebSocket,
    message: str,
    code: str = "INTERVIEW_ERROR",
):
    """Send a consistent error response to the client."""

    await websocket.send_json({
        "event": "interview_error",
        "success": False,
        "code": code,
        "message": message,
    })


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

    await websocket.send_json({
        "event": "connection_ready",
        "success": True,
        "message": "Connected to the AI interview agent.",
    })

    try:

        while True:

            try:
                message = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=settings.session_idle_timeout_seconds,
                )

            except asyncio.TimeoutError:

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

            if not isinstance(message, dict):

                await send_error(
                    websocket,
                    "Invalid message. Expected a JSON object.",
                    "INVALID_MESSAGE",
                )

                continue

            event = message.get("event")

            # --------------------------------------------------
            # START INTERVIEW
            # --------------------------------------------------

            if event == "start_interview":

                if session_id is not None:

                    await send_error(
                        websocket,
                        "An interview is already active on this connection.",
                        "SESSION_ALREADY_STARTED",
                    )

                    continue

                resume_text = message.get("resume_text", "")
                job_description = message.get(
                    "job_description",
                    "",
                )

                candidate_name = message.get("candidate_name")

                if not isinstance(resume_text, str) or not resume_text.strip():

                    await send_error(
                        websocket,
                        "A valid candidate resume is required.",
                        "INVALID_RESUME",
                    )

                    continue

                if not isinstance(job_description, str) or not job_description.strip():

                    await send_error(
                        websocket,
                        "A valid job description is required.",
                        "INVALID_JOB_DESCRIPTION",
                    )

                    continue

                try:

                    await websocket.send_json({
                        "event": "planning_started",
                        "message": "Preparing your personalized interview.",
                    })

                    # Generate personalized interview plan.
                    planner = InterviewPlanner()

                    plan_response = await planner.generate_plan(
                        resume_text=resume_text,
                        job_description=job_description,
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

                    # Create a unique interview session.
                    session_id = str(uuid.uuid4())

                    session = await database.create_session(
                        session_id=session_id,
                        candidate_name=(
                            candidate_name
                            or candidate_profile.get("name")
                        ),
                        job_title=job_profile.get("job_title"),
                        candidate_profile=candidate_profile,
                        job_profile=job_profile,
                        interview_plan=interview_plan,
                    )

                    if session is None:
                        raise DatabaseError(
                            "Could not create interview session."
                        )

                    await database.update_session(
                        session_id=session_id,
                        status="in_progress",
                    )

                    # Select the first planned question.
                    current_question = (
                        interview_plan["questions"][0]
                    )

                    first_question = current_question["question"]

                    # Save the first interviewer message.
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
                        "Interview session started: %s",
                        session_id,
                    )

                    await websocket.send_json({
                        "event": "interview_started",
                        "success": True,
                        "session_id": session_id,
                        "candidate_profile": candidate_profile,
                        "job_profile": job_profile,
                        "total_questions": interview_plan["total_questions"],
                        "question": {
                            "id": current_question["id"],
                            "category": current_question["category"],
                            "difficulty": current_question["difficulty"],
                            "text": first_question,
                        },
                        "message": "Your interview has started.",
                    })

                except (PlannerError, DatabaseError) as exc:

                    logger.exception("Interview initialization failed.")

                    await send_error(
                        websocket,
                        str(exc),
                        "INTERVIEW_INITIALIZATION_FAILED",
                    )

                    # Do not reuse a partially initialized session.
                    if session_id is not None:
                        await database.update_session(
                            session_id=session_id,
                            status="failed",
                        )

                    session_id = None
                    interview_plan = None
                    current_question = None

                except Exception as exc:

                    logger.exception(
                        "Unexpected interview initialization error."
                    )

                    await send_error(
                        websocket,
                        "Unable to start the interview. Please try again.",
                        "INTERNAL_ERROR",
                    )

                    if session_id is not None:
                        await database.update_session(
                            session_id=session_id,
                            status="failed",
                        )

                    session_id = None
                    interview_plan = None
                    current_question = None

                continue

            # --------------------------------------------------
            # SUBMIT CANDIDATE ANSWER
            # --------------------------------------------------

            elif event == "submit_answer":

                if session_id is None or interview_plan is None:

                    await send_error(
                        websocket,
                        "Start an interview before submitting answers.",
                        "NO_ACTIVE_SESSION",
                    )

                    continue

                candidate_message = message.get("text", "")

                if not isinstance(candidate_message, str) or not candidate_message.strip():

                    await send_error(
                        websocket,
                        "Candidate answer cannot be empty.",
                        "EMPTY_ANSWER",
                    )

                    continue

                try:

                    # Persist candidate answer.
                    await database.save_turn(
                        session_id=session_id,
                        role="user",
                        content=candidate_message.strip(),
                        turn_type="answer",
                        metadata={
                            "question_id": (
                                current_question.get("id")
                                if current_question
                                else None
                            ),
                        },
                    )

                    # Retrieve complete conversation history.
                    conversation_history = await database.get_turns(
                        session_id
                    )

                    # Generate contextual interviewer response.
                    reply = await interviewer.generate_response(
                        candidate_message=candidate_message.strip(),
                        interview_plan=interview_plan,
                        conversation_history=conversation_history,
                        current_question=current_question,
                    )

                    # Persist interviewer response.
                    await database.save_turn(
                        session_id=session_id,
                        role="assistant",
                        content=reply.text,
                        turn_type="response",
                        metadata={
                            "action": reply.action,
                            "question_id": reply.question_id,
                        },
                    )

                    # Update current question when the AI identifies one.
                    if reply.question_id is not None:

                        next_question = next(
                            (
                                question
                                for question in interview_plan["questions"]
                                if str(question["id"]) == reply.question_id
                            ),
                            None,
                        )

                        if next_question is not None:
                            current_question = next_question

                    # Handle interview completion.
                    if reply.interview_complete or reply.action == "finish":

                        await database.update_session(
                            session_id=session_id,
                            status="completed",
                        )

                        await websocket.send_json({
                            "event": "interviewer_response",
                            "success": True,
                            "session_id": session_id,
                            "text": reply.text,
                            "action": "finish",
                            "question_id": reply.question_id,
                            "interview_complete": True,
                        })

                        await websocket.send_json({
                            "event": "interview_completed",
                            "success": True,
                            "session_id": session_id,
                            "message": "Your interview has been completed.",
                        })

                        session_id = None
                        interview_plan = None
                        current_question = None

                        continue

                    # Send normal interviewer response.
                    await websocket.send_json({
                        "event": "interviewer_response",
                        "success": True,
                        "session_id": session_id,
                        "text": reply.text,
                        "action": reply.action,
                        "question_id": reply.question_id,
                        "interview_complete": False,
                    })

                except (InterviewerError, DatabaseError) as exc:

                    logger.exception(
                        "Could not process candidate answer."
                    )

                    await send_error(
                        websocket,
                        str(exc),
                        "ANSWER_PROCESSING_FAILED",
                    )

                except Exception:

                    logger.exception(
                        "Unexpected error while processing answer."
                    )

                    await send_error(
                        websocket,
                        "Unable to process your answer. Please try again.",
                        "INTERNAL_ERROR",
                    )

                continue

            # --------------------------------------------------
            # END INTERVIEW
            # --------------------------------------------------

            elif event == "end_interview":

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

                await websocket.send_json({
                    "event": "interview_completed",
                    "success": True,
                    "session_id": ended_session_id,
                    "message": "Interview ended successfully.",
                })

                logger.info(
                    "Interview ended: %s",
                    ended_session_id,
                )

                session_id = None
                interview_plan = None
                current_question = None

                continue

            # --------------------------------------------------
            # UNKNOWN EVENT
            # --------------------------------------------------

            else:

                await send_error(
                    websocket,
                    f"Unknown event: {event}",
                    "UNKNOWN_EVENT",
                )

    except WebSocketDisconnect:

        logger.info(
            "Interview WebSocket disconnected. Session: %s",
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

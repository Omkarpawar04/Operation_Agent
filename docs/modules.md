# Module catalog

This catalog describes active source modules and calls out source files that
are present but not currently part of the runtime path.

## Backend

| Module | Responsibility |
| --- | --- |
| [`main.py`](../main.py) | FastAPI application lifecycle, HTTP routes, WebSocket interview protocol, consent checks, orchestration of planning/audio/answers, report completion, and serving the built React app. Run this module with Uvicorn. |
| [`config.py`](../config.py) | Pydantic settings model; reads environment variables and `.env`, validates settings, and exposes the cached shared `settings` object. |
| [`storage/db.py`](../storage/db.py) | Async SQLite persistence for session records and ordered interview turns; initializes/upgrades tables, expires idle sessions, and enforces active-session limits. |
| [`main_backup.py`](../main_backup.py) | Older backend copy. It is not the active ASGI entry point; use `main:app`. |
| [`test_config.py`](../test_config.py) | Small configuration diagnostic script, not part of the application request path. |

## AI agents (`agents/`)

| Module | Responsibility |
| --- | --- |
| [`agents/groq_client.py`](../agents/groq_client.py) | Lazily creates and reuses the shared asynchronous Groq client, then closes it during application shutdown. |
| [`agents/planner.py`](../agents/planner.py) | Validates candidate/job profiles and an 8–10 question interview plan; calls Groq and retries one invalid structured response. |
| [`agents/interviewer.py`](../agents/interviewer.py) | Builds bounded conversation context, keeps the candidate answer verbatim, requests the next interviewer decision from Groq, and validates response actions. |
| [`agents/evaluator.py`](../agents/evaluator.py) | Produces a validated final score/report, including evidence for four dimensions, strengths, concerns, recommendation, and summary. |
| [`agents/__init__.py`](../agents/__init__.py) | Python package marker. |

## Audio (`audio/`)

| Module | Responsibility |
| --- | --- |
| [`audio/fallback_pipeline.py`](../audio/fallback_pipeline.py) | Connects Deepgram full-turn STT, interviewer response generation, and Kokoro PCM speech streaming; supplies interview-specific keyterms. |
| [`audio/kokoro_tts.py`](../audio/kokoro_tts.py) | Loads/caches Kokoro voices, warms the model, synthesizes WAV previews, and streams sentence-sized PCM without writing temporary audio files. |
| [`audio/vad.py`](../audio/vad.py) | Wraps WebRTC VAD, validates PCM frame format, and reports speech-start, speech, silence, and speech-end states. |
| [`audio/websocket_audio.py`](../audio/websocket_audio.py) | Buffers WebSocket PCM frames into VAD frames and complete utterances; retains pre-roll, enforces an answer buffer limit, and exposes a non-mutating snapshot for live captions. |
| [`audio/stream.py`](../audio/stream.py) | Standalone PCM buffer utility. It is not referenced by the active `main.py` audio path, which uses `WebSocketAudioProcessor`. |
| [`audio/__init__.py`](../audio/__init__.py) | Python package marker. |

## Prompts (`prompts/`)

| File | Responsibility |
| --- | --- |
| [`planner_system.txt`](../prompts/planner_system.txt) | Instructions and output requirements for resume/job analysis and question-plan generation. |
| [`interviewer_system.txt`](../prompts/interviewer_system.txt) | Instructions for candidate response handling, follow-ups, question progression, and response action selection. |
| [`evaluator_system.txt`](../prompts/evaluator_system.txt) | Instructions for evidence-based post-interview scoring and report generation. |

## Frontend (`frontend/src/`)

| Module | Responsibility |
| --- | --- |
| [`main.jsx`](../frontend/src/main.jsx) | React DOM entry point; mounts `App` in Strict Mode. |
| [`App.jsx`](../frontend/src/App.jsx) | Browser routes, application shell, header/footer, and shared `InterviewProvider`. |
| [`hooks/InterviewContext.jsx`](../frontend/src/hooks/InterviewContext.jsx) | Central interview/session state and existing WebSocket/audio orchestration. Owns microphone PCM transport, playback, answer state, captions, and additive live-transcription event state. |
| [`hooks/useMonitoring.js`](../frontend/src/hooks/useMonitoring.js) | Camera/screen stream handling, local `MediaRecorder`, event timeline, and consent-gated local snapshots/recording. |
| [`services/api.js`](../frontend/src/services/api.js) | Fetch wrapper and HTTP helpers for health, history, reports, document extraction, and voice preview. |
| [`services/socket.js`](../frontend/src/services/socket.js) | Creates the interview WebSocket and serializes JSON control events. |
| [`pages/InterviewSetup.jsx`](../frontend/src/pages/InterviewSetup.jsx) | Consent and recording setup, resume/job input, voice selection, interview start, and session history. |
| [`pages/InterviewRoom.jsx`](../frontend/src/pages/InterviewRoom.jsx) | Active interview layout, question, orb, camera preview, live transcription, captions, recovery, and controls. |
| [`pages/InterviewReport.jsx`](../frontend/src/pages/InterviewReport.jsx) | Completed report view, retry action, and start-another-interview action. |
| [`components/AIOrb.jsx`](../frontend/src/components/AIOrb.jsx) | UI-only orb presentation driven by the existing activity state and audio level. |
| [`components/AppHeader.jsx`](../frontend/src/components/AppHeader.jsx) | Brand navigation and backend connection indicator. |
| [`components/InterviewControls.jsx`](../frontend/src/components/InterviewControls.jsx) | Repeat, listening toggle, next-question, and end-interview button bindings. |
| [`components/LiveTranscription.jsx`](../frontend/src/components/LiveTranscription.jsx) | Isolated live/interim transcript display, overlap merging, cursor, status, and local scrolling. |
| [`components/MonitoringPanel.jsx`](../frontend/src/components/MonitoringPanel.jsx) | Candidate-controlled monitoring UI for snapshots, recording, and timeline. The component currently has no import in the active app tree. |
| [`components/ReportSummary.jsx`](../frontend/src/components/ReportSummary.jsx) | Renders overall and dimension scores, evidence, strengths, concerns, recommendation, and summary. |
| [`components/TranscriptPanel.jsx`](../frontend/src/components/TranscriptPanel.jsx) | Read-only conversation captions/history. |
| [`components/VoicePicker.jsx`](../frontend/src/components/VoicePicker.jsx) | Voice selection and asynchronous preview playback. |
| [`components/WebcamPreview.jsx`](../frontend/src/components/WebcamPreview.jsx) | Attaches the provided camera stream to the preview video element and exposes camera controls. |
| [`styles/theme.css`](../frontend/src/styles/theme.css) | Shared CSS variables and design tokens. |
| [`styles/global.css`](../frontend/src/styles/global.css) | Global page, typography, and shared component styling. |
| [`styles/interview.css`](../frontend/src/styles/interview.css) | Setup, interview, camera, transcript, controls, report, and responsive styles. |

`frontend/vite.config.js` configures the React plugin, development proxies, and
production output directory.

## Tests and supporting assets

| Path | Scope |
| --- | --- |
| [`tests/test_api_completion.py`](../tests/test_api_completion.py) | HTTP upload/extraction, history, voice catalog, and report behavior. |
| [`tests/test_database.py`](../tests/test_database.py) | SQLite schema, session/turn persistence, limits, and expiry. |
| [`tests/test_audio.py`](../tests/test_audio.py) | VAD detection and frame validation. |
| [`tests/test_websocket_audio.py`](../tests/test_websocket_audio.py) | PCM buffering, pre-roll, complete utterances, snapshots, and limits. |
| [`tests/test_voice_flow.py`](../tests/test_voice_flow.py) | Mocked end-to-end voice turns, live caption event, interviewer response, and TTS ordering. |
| [`tests/test_ws_flow.py`](../tests/test_ws_flow.py) | WebSocket lifecycle, consent, session, and question-flow behavior. |
| [`tests/test_fallback_stt.py`](../tests/test_fallback_stt.py) | Deepgram request options and keyterm construction. |
| [`tests/test_groq_client.py`](../tests/test_groq_client.py) | Shared Groq client lifecycle. |
| [`tests/test_planner.py`](../tests/test_planner.py) | Plan generation, schema validation, retry, and rate-limit errors. |
| [`tests/test_interviewer_streaming.py`](../tests/test_interviewer_streaming.py) | Interviewer streaming response/context behavior. |
| [`tests/test_evaluator.py`](../tests/test_evaluator.py) | Evaluation schema and weighted scoring. |
| [`tests/test_kokoro_tts.py`](../tests/test_kokoro_tts.py) | Mocked Kokoro loading, voice selection, chunking, and WAV/PCM behavior. |
| [`tests/test_kokoro_live.py`](../tests/test_kokoro_live.py) | Optional live local-model smoke test; requires Kokoro assets. |
| [`tests/manual_live_integration.py`](../tests/manual_live_integration.py) | Optional manual provider integration check. |
| [`tests/benchmark_voice_latency.py`](../tests/benchmark_voice_latency.py) | Optional provider/audio latency benchmark. |

The root `static/` directory contains older standalone client assets; the
current backend serves the Vite build from `frontend/dist`.

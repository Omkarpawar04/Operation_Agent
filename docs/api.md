# HTTP and WebSocket API

The canonical implementations are the route handlers and event loop in
[`main.py`](../main.py). Vite proxies `/api`, `/health`, and `/ws` during
development.

## HTTP routes

| Method and path | Purpose |
| --- | --- |
| `GET /` | Serves the built React entry point. Returns 503 if `frontend/dist/index.html` is missing. |
| `GET /health` | Reports application health and missing voice-service configuration/Kokoro status. |
| `GET /api/tts/voices` | Returns the supported Kokoro voice catalog and default voice. |
| `POST /api/tts/preview` | Accepts JSON `{ "voice_id": "..." }`; returns a short WAV preview. |
| `POST /api/extract` | Accepts multipart field `file` (TXT, PDF, DOCX; max 5 MB) and returns `{ "text": "..." }`. |
| `GET /api/interviews?limit=50` | Lists recent interview sessions. |
| `GET /api/interviews/{session_id}` | Returns the session and ordered turns; omits the client IP. |
| `GET /api/interviews/{session_id}/report` | Returns a saved evaluation or 404 if unavailable. |
| `POST /api/interviews/{session_id}/evaluate` | Retries evaluation for a completed session. |

The catch-all browser route serves the React entry point for client-side
navigation. API errors use FastAPI HTTP errors with a `detail` message.

## Interview WebSocket

Connect to `/ws/interview`. JSON control messages use an `event` field. The
client sends binary microphone frames between control messages.

### Typical client flow

1. `start_interview` with candidate name, resume text, job description, and
   selected voice.
2. Confirm recording with `recording_consent` (`accepted: true`) and
   `recording_status` (`active: true`).
3. Start `start_audio`, then acknowledge `audio_client_ready`.
4. Send mono PCM16 microphone frames. Use `submit_answer` for text input or
   `candidate_action` for actions such as `skip`; `repeat_question` is also
   supported.
5. Use `interrupt` to interrupt speech, `stop_audio` to pause audio, and
   `finish_interview`/`end_interview` to finish.
6. Use `resume_session` to restore an existing session when permitted.

The server validates session and recording consent before accepting answer
progression. Exact message handling and validation live in `main.py`.

### Audio formats

- **Browser to server:** signed 16-bit little-endian PCM, mono, normally 16 kHz.
- **Server to browser:** Kokoro audio is binary mono PCM16 at 24 kHz, preceded
  by JSON audio status messages.
- **Speech detection:** VAD emits speech-start and speech-end notifications.
  `VAD_SILENCE_DURATION_MS` controls endpointing.

### Important server events

| Event | Meaning |
| --- | --- |
| `connection_ready` | WebSocket connection is available. |
| `interview_started` | Planning succeeded and session/question data is ready. |
| `audio_ready` / `audio_stopped` | Audio processing started or stopped. |
| `speech_started` / `speech_ended` | VAD detected candidate speech boundaries. |
| `live_transcription` | Additive interim caption with `text`, `turn_id`, `sequence`, `start_ms`, and `end_ms`. |
| `live_transcription_error` | Live captions failed; it does not replace or cancel final-turn transcription. |
| `transcription_started` / `transcript_received` | Canonical full-turn STT has started/completed. `transcript_received.text` is submitted as the answer. |
| `interviewer_response` | Groq-generated interviewer response and question/action metadata. |
| `audio_generating`, `audio_started`, `audio_completed` | TTS synthesis/playback lifecycle. Binary frames between start/completed events carry audio. |
| `audio_interrupted` | Current interviewer speech was interrupted. |
| `interview_paused` | Required recording consent/status was lost; answer progression is blocked until recovery. |
| `interview_completed`, `evaluation_result` | Interview ended and a report is available. |
| `interview_error`, `audio_error`, `evaluation_error` | A workflow/service error, with a message and usually a code. |

`live_transcription` and `live_transcription_error` are additive events. They do
not change the payload contract or answer semantics of `transcript_received`.
Live segments are short, overlapping Deepgram REST requests; the final answer
always comes from the existing complete-utterance transcription call.

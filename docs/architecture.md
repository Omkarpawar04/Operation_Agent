# Architecture and data flow

## Runtime overview

```text
React/Vite browser
  ├─ HTTP ───────────────> FastAPI routes
  └─ WebSocket + PCM ────> FastAPI interview handler
                               ├─ SQLite session and turn storage
                               ├─ WebRTC VAD and audio buffering
                               ├─ Deepgram speech transcription
                               ├─ Groq planning, responses, evaluation
                               └─ Local Kokoro text-to-speech
```

In development, Vite serves the React client and proxies `/api`, `/health`, and
`/ws` to FastAPI. In production, FastAPI serves `frontend/dist` and its assets.
`main.py` is the active backend entry point.

## Interview lifecycle

1. **Setup:** The browser collects the candidate name, resume, job description,
   and selected interviewer voice. TXT, PDF, and DOCX uploads are extracted by
   `/api/extract`; the resulting text is sent to the backend for planning.
2. **Consent and media:** The browser asks for recording consent and camera and
   microphone access. One media stream is used by the local `MediaRecorder`,
   camera preview, and Web Audio microphone capture. Interview audio frames are
   sent as mono signed 16-bit PCM over the interview WebSocket.
3. **Planning:** `InterviewPlanner` asks Groq for a validated candidate profile,
   job profile, and plan of 8–10 unique questions. The plan and session are
   stored in SQLite.
4. **Spoken answer:** `WebSocketAudioProcessor` uses WebRTC VAD to detect speech
   turns and buffer complete utterances. While speech is active, the server can
   request short, overlapping Deepgram transcriptions for live captions. These
   are preview-only; after VAD ends a turn, the full utterance is transcribed
   again and that canonical result is saved and submitted for evaluation.
5. **Response:** `InterviewerAgent` sends the candidate's final transcript and
   bounded recent conversation context to Groq. The response and question
   progress are saved; `KokoroTTSService` produces local 24 kHz PCM for browser
   playback.
6. **Completion:** The stored turns are evaluated by Groq. The validated report
   is saved with the session and displayed in the report route. A completed
   session can retry report evaluation if needed.

## Audio formats and providers

| Purpose | Current implementation |
| --- | --- |
| Candidate microphone transport | Browser Web Audio to WebSocket as mono PCM16, normally 16 kHz |
| Speech detection | `webrtcvad` through `VoiceActivityDetector`; silence endpoint is configurable |
| Live candidate captions | Throttled Deepgram requests using copies of the active utterance buffer |
| Final candidate transcript | Deepgram Nova-3 full-turn request; this remains authoritative |
| Planning, interviewer decisions, evaluation | Groq through one shared asynchronous OpenAI-compatible client |
| Interviewer speech | Local Kokoro model, mono PCM16 at 24 kHz |

The browser does not open a second microphone for captions. Live caption
requests do not replace the completed-turn transcription or change the answer
passed to the interviewer.

## Persistence and media handling

- SQLite stores interview sessions, profiles/plans, conversation turns, and
  completed evaluation reports. The database path is controlled by
  `DATABASE_PATH`.
- The browser's `MediaRecorder` builds a local recording Blob; it is not posted
  to the FastAPI interview routes. The user can download it in the monitoring
  UI when that component is mounted.
- Camera snapshots are canvas JPEG Blobs held in `useMonitoring` React state.
  Camera snapshot consent is enabled as part of the existing recording consent
  path. The default periodic interval is 60 seconds; eligible monitoring events
  can also trigger a snapshot. No snapshot upload or backend persistence route
  exists.
- `MonitoringPanel.jsx` defines the snapshot counter and privacy controls but
  is not currently mounted by the active route tree. `screenConsent` defaults
  to false, and the setup notice says screen sharing is not enabled.
- Session completion or `clearData` clears local monitoring state. Interview
  text and transcripts, in contrast, are stored in the backend database.

## Failure boundaries

- Recording consent, recording status, and media recovery gate interview
  progression. If required recording access is lost, the backend pauses the
  session.
- Live transcription is auxiliary. A live-caption error is surfaced in the
  panel but does not stop recording or change the canonical full-turn answer
  path.
- Provider errors are surfaced through HTTP errors or WebSocket error events;
  Kokoro initialization is warmed in the background and can retry when speech
  is first requested.

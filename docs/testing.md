# Testing and verification

## Automated suite

Run tests in the application virtual environment so WebRTC VAD, FastAPI, and
the other backend dependencies are available:

```powershell
.\venv-kokoro\Scripts\Activate.ps1
python -m pytest -q
```

The tests mock external Groq, Deepgram, and Kokoro services where appropriate.
Relevant groups:

- `test_planner.py`, `test_interviewer_streaming.py`,
  `test_groq_client.py`, and `test_evaluator.py`: LLM client and agents.
- `test_audio.py`, `test_websocket_audio.py`, and `test_fallback_stt.py`: VAD,
  PCM buffering, live snapshots, and transcription request construction.
- `test_voice_flow.py` and `test_ws_flow.py`: consent, WebSocket lifecycle,
  completed voice turns, live transcription events, and response ordering.
- `test_database.py` and `test_api_completion.py`: SQLite persistence and HTTP
  routes.
- `test_kokoro_tts.py`: mocked local voice model behavior.

Build the frontend separately:

```powershell
npm --prefix frontend run build
```

## Optional live checks

These require real local model assets and/or provider credentials:

```powershell
.\venv-kokoro\Scripts\python.exe tests\test_kokoro_live.py
.\venv-kokoro\Scripts\python.exe tests\manual_live_integration.py
.\venv-kokoro\Scripts\python.exe tests\benchmark_voice_latency.py
```

The Kokoro live test generates a local WAV file. The manual integration and
latency scripts can contact configured services and should be treated as
networked checks, not offline unit tests.

## Manual browser verification

1. Start FastAPI and Vite (or build the frontend and use FastAPI alone).
2. Check `/health` and confirm Groq, Deepgram, and Kokoro readiness.
3. Grant the required camera/microphone/recording consent and start an
   interview.
4. Confirm the greeting and question audio, then speak for several seconds.
5. Verify live segments appear, the LIVE indicator follows VAD, and the final
   caption matches the completed-turn transcript.
6. Confirm a live-caption error does not stop recording or prevent final
   transcription/evaluation.
7. Test repeat, next, interruption, recovery after permissions are withdrawn,
   and interview completion/report generation.

Automated mocks cannot verify real microphone devices, browser permissions,
network jitter, provider credentials, or physical speaker playback; use the
manual flow for those checks.

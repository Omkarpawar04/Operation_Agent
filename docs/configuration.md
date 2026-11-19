# Configuration and local development

## Environment variables

Copy `.env.example` to `.env` and set credentials locally. Never commit `.env`
or paste credential values into documentation.

| Variable | Default/behavior |
| --- | --- |
| `APP_NAME` | `AI Voice Interview Agent` |
| `APP_ENV` | `development` |
| `DEBUG` | `true`; also accepts common `dev`/`prod` names. |
| `HOST`, `PORT` | `127.0.0.1`, `8000`; used by the direct Uvicorn entry point. |
| `LOG_LEVEL` | `INFO` |
| `GROQ_API_KEY` | Required for plan generation, interviewer turns, and evaluation. |
| `GROQ_BASE_URL` | OpenAI-compatible Groq API base URL. |
| `GROQ_TEXT_MODEL` | `openai/gpt-oss-120b` |
| `DEEPGRAM_API_KEY` | Required for voice-answer transcription. |
| `DEEPGRAM_LANGUAGE` | `en`; may be set to another supported language. |
| `KOKORO_ENABLED` | `true`; health/readiness uses this setting. |
| `KOKORO_VOICE` | `af_heart`; user can choose another supported voice in setup. |
| `KOKORO_SPEED` | `1.0` |
| `KOKORO_SAMPLE_RATE` | Fixed to 24000 Hz by the settings model. |
| `KOKORO_DEVICE` | `cpu`; supported values are `cpu`, `cuda`, `mps`. |
| `DATABASE_PATH` | `./data/interviews.db` |
| `SESSION_IDLE_TIMEOUT_SECONDS` | `900` |
| `MAX_CONCURRENT_SESSIONS_PER_IP` | `3` |
| `VAD_SILENCE_DURATION_MS` | `450`; longer pauses may end a turn sooner than expected. |
| `AUDIO_INPUT_SAMPLE_RATE` | `16000` |
| `CORS_ORIGINS` | Comma-separated local origins. |
| `OPENAI_API_KEY`, `OPENAI_REALTIME_MODEL`, `REALTIME_ENABLED` | Reserved for future realtime integration; current interview agents use Groq. |
| `REDIS_URL`, `MAX_SESSION_COST_USD` | Present in settings, but not currently wired into the runtime path. |

Settings are defined in [`config.py`](../config.py). The shared settings object
is loaded once; changing `.env` requires restarting the backend.

## Windows development setup

Kokoro 0.9.4 supports Python 3.10–3.12. The repository's documented Windows
setup uses Python 3.12 and a dedicated environment:

```powershell
py -3.12 -m venv venv-kokoro
.\venv-kokoro\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements-kokoro.txt
if (!(Test-Path .env)) { Copy-Item .env.example .env }
```

Set `GROQ_API_KEY` and `DEEPGRAM_API_KEY` in `.env`, then run the backend from
the repository root:

```powershell
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

For frontend development, use a second terminal:

```powershell
Set-Location frontend
npm ci
npm run dev
```

Open <http://127.0.0.1:5173>. Vite proxies requests to the backend on port 8000.

## Production-style local run

Build the frontend before starting FastAPI:

```powershell
npm --prefix frontend ci
npm --prefix frontend run build
.\venv-kokoro\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

The first Kokoro startup downloads/caches model and voice assets if needed.
TTS runs locally; Groq and Deepgram calls require configured credentials and
network access.

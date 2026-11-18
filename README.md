# AI Voice Interview Agent

FastAPI serves the browser client, WebSocket interview, and SQLite history. Groq handles interview planning, conversational turns, and evaluation. Deepgram transcribes spoken candidate answers. Kokoro generates interviewer speech locally. Candidates answer by voice; captions are read-only.

## Windows setup

The published Kokoro 0.9.4 package supports Python 3.10–3.12. Keep the existing environment and use a separate Python 3.12 environment for the app with local TTS. Python 3.12.10 is the last 3.12 release with a Windows installer.

```powershell
# Install the official Python 3.12.10 build if Python 3.12 is not already installed.
winget install --id Python.Python.3.12 --exact --version 3.12.10 --scope user

py -3.12 -m venv venv-kokoro
.\venv-kokoro\Scripts\Activate.ps1
python -m pip install --upgrade pip

# CPU-only PyTorch; no NVIDIA GPU is required.
python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements-kokoro.txt

if (!(Test-Path .env)) { Copy-Item .env.example .env }
notepad .env
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Set `GROQ_API_KEY` and `DEEPGRAM_API_KEY` in `.env`. No hosted TTS key or voice ID is used. Keep `KOKORO_ENABLED=true`; `KOKORO_VOICE=am_michael`, `KOKORO_SPEED=1.0`, and `KOKORO_DEVICE=cpu` are the local voice defaults. Kokoro-82M does not provide an Indian-English voice; `am_michael` is its highest-graded male English option, but it speaks American English. Set `KOKORO_VOICE` to another compatible voice ID if desired. Kokoro emits mono audio at 24 kHz. First use downloads the model, voice, and English pronunciation assets; after they are cached, speech generation runs locally. The app loads the model and generates a short throwaway phrase in a background startup task, warming both model and first-inference paths before the first question when startup finishes in time. Run the live smoke test once while online to download and warm the assets.

Kokoro's American English pipeline can run without eSpeak NG; eSpeak NG adds pronunciation fallback for out-of-dictionary words. If you need that fallback, download and install the Windows MSI from the [official eSpeak NG releases](https://github.com/espeak-ng/espeak-ng/releases).

Open <http://127.0.0.1:8000>. Upload TXT, PDF, or DOCX resumes up to 5 MB, or paste resume and job details in setup.

## API

- `GET /health` reports configuration readiness and whether the local Kokoro model has loaded.
- `POST /api/extract` accepts a multipart `file` and extracts TXT, PDF, or DOCX text.
- `GET /api/interviews` lists recent interview history.
- `GET /api/interviews/{id}` returns a session and transcript.
- `GET /api/interviews/{id}/report` returns a saved evaluation.
- `POST /api/interviews/{id}/evaluate` retries evaluation for a completed interview.

## WebSocket audio contract

Connect to `/ws/interview`. The client starts with `start_interview`, then sends `start_audio` and `audio_client_ready`. Browser microphone frames are mono signed 16-bit little-endian PCM at 16 kHz. Browser echo cancellation and noise suppression remain enabled. The backend uses WebRTC VAD with a short pre-roll and a configurable 900 ms silence endpoint, then sends the completed utterance to Deepgram Nova-3 with interview-specific technical keyterms. The returned transcript is preserved as recognized; the application does not replace candidate words. `DEEPGRAM_LANGUAGE=en` is the broad English default; set a supported regional language such as `en-IN` in `.env` when that best matches the speakers.

For each interviewer turn the server sends `audio_generating` while Kokoro synthesizes the first sentence, then `audio_started`, binary mono PCM at 24 kHz as sentence audio becomes ready, and `audio_completed`. The existing model and voice stay loaded in memory. `audio_interrupted` cancels delivery when the candidate interrupts. Spoken answers can be up to 120 seconds. The existing browser PCM decoder and playback queue remain in use with a smaller microphone callback buffer. Text captions are read-only.

The interviewer uses one shared async Groq client and streams response events, while waiting for the complete JSON decision before speaking it. Its prompt sends the latest candidate transcript verbatim and only a bounded recent history. This keeps action/question decisions intact while reducing repeated context.

## Tests and live voice setup

Use `venv-kokoro` for the full application and Kokoro tests:

```powershell
.\venv-kokoro\Scripts\Activate.ps1
python -m pytest -v
python tests/test_kokoro_live.py
```

The offline suite mocks Kokoro so it does not load model weights. The live script uses the real local model, writes `tests/output/kokoro_live.wav`, and checks the WAV header and duration. The model and voice files are stored in the Hugging Face cache, not in the repository.

After configuring Groq and Deepgram and granting browser microphone access, verify the complete flow manually:

1. Open the page and confirm `/health` shows voice configuration ready.
2. Start an interview and grant microphone access.
3. Confirm the greeting and first question play automatically.
4. Answer aloud and check the caption, follow-up response, and spoken next question.
5. Try interrupting and repeating a question.
6. Finish the interview and inspect the evidence-based evaluation report.

The live Kokoro WAV script proves local audio generation. It does not by itself verify a physical microphone, browser playback, or live Deepgram/Groq credentials. Run the manual flow above for those checks.

To measure real provider latency using one locally generated technical-speech sample, run:

```powershell
.\venv-kokoro\Scripts\python.exe tests\benchmark_voice_latency.py
```

The report includes Deepgram, Groq (including first text delta), Kokoro first-audio and completion times, word error rate, technical-term recall, and end-to-end time after local VAD endpointing. It writes no audio files. The input is clean Kokoro-generated speech, so it does not measure microphone quality, room noise, or natural human accents.

The default silence endpoint is 450 ms, half the previous 900 ms setting. This saves about 450 ms after the candidate stops, but pauses longer than 450 ms inside an answer can split it into separate turns. Increase `VAD_SILENCE_DURATION_MS` (for example, to 650 or 800) if candidates commonly pause while speaking.

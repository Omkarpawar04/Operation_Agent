# Controlled deployment guide

## Current release status

Milestone 5 (Backend Closure and Production Readiness) is implemented. The core backend text orchestrator, progression policies, lease recovery workers, PostgreSQL persistence, rate limiting, and database backup verification are fully operational and verified by automated tests.

The backend is **staging-ready** with deterministic providers, and **production-ready pending external platform integration** (production JWT/OIDC configuration from the existing FINXL platform, approved transcript retention duration, and production Gemini API credentials).

## Required Identity Provider Information

Before production authentication can be marked fully integrated, the following configuration parameters must be obtained from the existing FINXL platform and injected into the runtime environment:

1. **`JWT_JWKS_URL`** or **`JWT_PUBLIC_KEY`**: The JSON Web Key Set endpoint (e.g., `https://auth.finxl.com/.well-known/jwks.json`) or static RSA/EC PEM public key used to verify asymmetric token signatures.
2. **`JWT_ISSUER`**: The trusted token issuer URI (`iss` claim), e.g., `https://auth.finxl.com/`.
3. **`JWT_AUDIENCE`**: The expected audience identifier (`aud` claim), e.g., `https://api.finxl.com`.
4. **`JWT_ALGORITHMS`**: The allowed signing algorithms (defaults to `["RS256"]`).
5. **`JWT_USER_ID_CLAIM`**: The claim in the token containing the student user ID (defaults to `sub`).
6. **`JWT_ROLE_CLAIM`**: The claim containing student/staff roles (defaults to `role`).
7. **`JWT_LEEWAY_SECONDS`**: Allowed clock skew for expiration and not-before checks (defaults to `60` seconds).

If real platform JWT settings are not configured, production requests to protected student endpoints fail closed with HTTP 401. Development identity (`X-Dev-User-ID`) is strictly isolated to `development` and `test` environments and is permanently disabled in production.

## Configuration

Inject configuration through the deployment secret manager. Never copy `.env` into the image. Production startup requires:
- PostgreSQL (`DATABASE_URL`).
- `LLM_PROVIDER=gemini` and a valid `GEMINI_API_KEY`.
- Explicit, non-wildcard `CORS_ALLOWED_ORIGINS` (e.g., `["https://app.finxl.com"]`).
- Explicit, non-wildcard `TRUSTED_HOSTS` (e.g., `["api.finxl.com"]`).
- Explicit `TRUSTED_PROXIES` if operating behind a load balancer or ingress.
- An approved `TRANSCRIPT_RETENTION_DAYS`.
- Production JWT configuration (`JWT_JWKS_URL` or `JWT_PUBLIC_KEY`, `JWT_ISSUER`, `JWT_AUDIENCE`).

`TRANSCRIPT_RETENTION_DAYS` has no default. Product/legal must approve the duration and retained assessment fields before setting it.

## Transcript Retention and Privacy Policy

### Data Stored
- Student answers (`AnswerRow.transcript`).
- Generated questions (`QuestionRow.text`).
- AI evaluation observations (`EvaluationRow.evidence_json` and `AssessmentResultRow.evidence_json`).
- Assessment attempt history, overall numerical scores, and pass/fail decisions.
- Progression milestones.
- Deletion audit rows (`TranscriptDeletionAuditRow`: student UUID and timestamp only).

### Data Deleted on Deletion / Expiry
- All answer text is replaced with `"[deleted]"`.
- Generated question text is replaced with `"[deleted]"`.
- Evaluation evidence JSON lists are cleared to `[]`.
- In-progress sessions and attempts are transitioned to `abandoned`.
- Deletion executes atomically in a single database transaction. If any part of the operation fails, the transaction rolls back, preventing partially deleted records.

### Retained Assessment Data
- Numerical scores, pass/fail state, and attempt records remain intact to preserve student progression eligibility across interview tracks.
- Deletion audit row records only the student ID and deletion timestamp, without containing any transcript content.

### Audio and Voice Policy
- Audio payloads are strictly ephemeral in client browser memory. No audio bytes, file paths, URLs, object store keys, or provider audio payloads are ever uploaded, recorded, or persisted to database rows, logs, traces, or disk.
- Microphone access is requested only when the student explicitly initiates voice input.
- Privacy limitation: Browser Web Speech recognition may stream audio to vendor recognition servers (e.g., Google or Apple speech services depending on browser implementation). It is not guaranteed to operate offline or end-to-end within the customer perimeter. If strict on-premises data residency is required, migrate to self-hosted Whisper.

## Browser Compatibility & Graceful Degradation

| Browser | Speech Recognition (STT) | Speech Synthesis (TTS) | Graceful Degradation Behavior |
|---|---|---|---|
| **Chrome / Chromium** | Supported (`webkitSpeechRecognition`) | Supported (`speechSynthesis`) | Full voice interview experience. |
| **Microsoft Edge** | Supported (`SpeechRecognition`) | Supported (`speechSynthesis`) | Full voice interview experience. |
| **Safari (macOS / iOS)** | Supported (`webkitSpeechRecognition`) | Supported (`speechSynthesis`) | Full voice interview experience (requires user gesture for audio). |
| **Mozilla Firefox** | Not enabled by default | Supported (`speechSynthesis`) | Displays explanatory notice and automatically enables typed answer fallback. Questions remain spoken. |
| **Headless / Mobile webview** | Variable | Variable | If STT unsupported: typed answer fallback. If TTS unsupported: silent visual interview. |

## Future Hybrid Speech Migration Guide

The frontend architecture implements decoupled ports (`SpeechInput` and `SpeechOutput`). Future cloud or self-hosted speech providers can be introduced without modifying the interview state machine:

1. **Cloud STT (Google Cloud Speech-to-Text / Azure Speech / AWS Transcribe):**
   - Create a class `CloudSpeechInput implements SpeechInput`.
   - In `start()`, capture microphone stream via `navigator.mediaDevices.getUserMedia`, stream chunks or submit short ephemeral audio to a private backend gateway, and resolve with the final transcript string.
   - Inject `speechInput: new CloudSpeechInput(...)` into `VoiceInterviewLifecycle`. No changes to interview orchestration or answer evaluation.

2. **Local / Self-Hosted Whisper STT:**
   - Create a class `WhisperSpeechInput implements SpeechInput`.
   - Submit ephemeral audio recording to a local Whisper inference endpoint (e.g., ONNX in WebWorker or self-hosted FastAPI sidecar) and return the recognized text.

3. **Cloud TTS (Google Cloud Text-to-Speech / Azure Neural TTS / ElevenLabs):**
   - Create a class `CloudSpeechOutput implements SpeechOutput`.
   - In `speak()`, fetch synthesized audio stream/data URL and play via HTML5 `Audio()`.
   - Inject `speechOutput: new CloudSpeechOutput(...)` into `VoiceInterviewLifecycle`.


### Open Product/Legal Decisions
- Approval of the scheduled retention period (`TRANSCRIPT_RETENTION_DAYS`). Scheduled retention remains disabled until this value is formally configured.
- Formal sign-off on the retention split (scrubbing transcript content while preserving progression scores).

## TLS, Proxy, and Reverse-Proxy Security

1. **TLS Termination:** Terminate TLS at a managed ingress or cloud load balancer and allow plaintext only on the private VPC network.
2. **Reverse Proxy Trust (`TRUSTED_PROXIES`):**
   - The application does not blindly trust `X-Forwarded-For` or related headers.
   - Forwarded headers are only inspected if the direct ASGI connection peer matches a configured trusted proxy IP or CIDR block (e.g., `["10.0.0.0/8"]`).
   - The client IP resolver walks from right to left (closest trusted proxy backwards) to determine the rightmost untrusted hop as the genuine client IP, discarding untrusted client-supplied header values.
   - Direct connections from untrusted peers ignore forwarded headers and use the direct peer IP address.
   - If `TRUSTED_PROXIES` is empty, all forwarded headers are ignored.

## Database Backup and Restore Verification

Encrypted database backups and point-in-time recovery (PITR) must be enabled per deployment RPO/RTO objectives.

### Backup Procedure
Execute standard PostgreSQL dump using custom archive format:
```bash
pg_dump -h <DB_HOST> -p <DB_PORT> -U <DB_USER> -d <DB_NAME> -Fc -f /backup/finxl_$(date +%Y%m%d_%H%M%S).dump
```

### Restore Verification Procedure (Non-Destructive Drill)
Never restore over a running database. Always test into an isolated disposable test database:
```bash
# 1. Create a disposable target database
createdb -h <DB_HOST> -p <DB_PORT> -U <DB_USER> finxl_restore_verify_disposable

# 2. Restore the backup archive
pg_restore -h <DB_HOST> -p <DB_PORT> -U <DB_USER> -d finxl_restore_verify_disposable /backup/finxl_test.dump

# 3. Verify schema, table count (13 tables), and latest Alembic revision
psql -h <DB_HOST> -p <DB_PORT> -U <DB_USER> -d finxl_restore_verify_disposable -c "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';"
psql -h <DB_HOST> -p <DB_PORT> -U <DB_USER> -d finxl_restore_verify_disposable -c "SELECT version_num FROM alembic_version;"

# 4. Tear down the disposable test database
dropdb -h <DB_HOST> -p <DB_PORT> -U <DB_USER> finxl_restore_verify_disposable
```

## Operations & Health Checks

- `GET /api/v1/health`: Process liveness; no database dependency.
- `GET /api/v1/ready`: Dependency readiness; verifies PostgreSQL connectivity.
- `GET /api/v1/worker-health`: Background lease-recovery and transcript-retention worker status.
- `GET /api/v1/provider-health`: Reports configured provider name without leaking credentials.
- Rate limits use shared PostgreSQL counters with `Retry-After` response headers.

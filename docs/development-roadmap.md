# FINXL AI Interviewer â€” Development Roadmap

This roadmap follows [the backend architecture](backend-architecture.md). Defaults are implementation mechanics only; unresolved product behavior remains deferred.

## Milestone 1 â€” Foundation (implemented)

- Python/FastAPI app factory, typed configuration, correlation IDs, structured logs, readiness and health.
- Domain state machine, deterministic decision policy, evidence/rubric scoring and attempt lifecycle.
- SQLAlchemy models, Alembic initial migration, repositories/Unit of Work, development-only auth port/adapter.
- Thin API contracts, owner checks, progression derived from attempts, tests/fakes and local run instructions.
- No speech, frontend, permanent audio, or assumed transcript retention duration.

## Milestone 2 â€” Text orchestration and Gemini adapter (implemented)

- Provider-neutral structured LLM port, deterministic fake, and Google `google-genai` adapter with schema validation, timeout, bounded transient retries, safe errors, and token-count logs.
- Text question/answer/follow-up lifecycle, pinned technical course revision/rubric validation, bounded answer history, evidence-based Python scoring, and deterministic decision transitions.
- Idempotent answer handling, expected-version state transitions, active-scope uniqueness migration, and concurrency integration coverage.
- Synthetic development fixtures are explicitly labelled and do not represent approved FINXL content. Live Gemini smoke tests require both `RUN_GEMINI_SMOKE=1` and `GEMINI_API_KEY` and are excluded by default.
- PostgreSQL integration claims remain unverified until the dedicated database run completes; processing reservations also need restart recovery before production use.

## Milestone 2a â€” Resolve operational and product contracts

- Choose identity provider/claims and staff roles; course/enrollment/content source and revision approval flow.
- Decide whether soft-skill stages are global or course-specific, base question counts, clarification rules, and retake policy.
- Validate rubric dimensions, weights, score precision, review/appeal behavior, transcript/result retention and deletion/export.
- Select deployment region, PostgreSQL service, audio privacy/consent requirements, and operational objectives.
- Record decisions as short ADRs and update API schemas/migrations only after approval.

## Milestone 3 — Application architecture refactor and reliability (implemented; production operations remain)

- Extract interview start, answer submission, read, assessment, abandonment, progression, user and readiness operations into application use cases. Keep routers limited to HTTP translation and dependency injection.
- Define application ports for interview queries, course configuration, answer workflow persistence and readiness; implement SQLAlchemy adapters outside the application layer.
- Keep reservation, provider execution and finalization in separate phases. No transaction spans a provider request. Final persistence is optimistic-version checked and atomic.
- Serialize eligible starts and completed progression per student with PostgreSQL row locks, with partial unique indexes and command idempotency constraints as backstops.
- Verify concurrency through PostgreSQL HTTP integration tests, including same-key starts, duplicate answer submission, failure recovery and late provider completion.
- At the Milestone 3 checkpoint, lease recovery was request-driven; Milestone 4 adds managed periodic recovery. No durable provider-command/outbox is used by the current synchronous provider workflow.
- Production authentication, real approved catalogue integration, rate limiting, transcript policy and deployment operations remain out of scope.
## Milestone 4 â€” LLM adapter

- Add provider-neutral LLM schemas and one Gemini infrastructure adapter.
- Set timeout, retry, cost, redaction, bounded-context, schema-validation, and fallback policies.
- Validate output quality and fairness before enabling candidate-facing generation. The model cannot change state or final assessment.

## Milestone 5 â€” Voice capabilities

- Select STT/TTS only after language, latency, cost, consent, data residency, and retention review.
- Implement independent ports/adapters, bounded temporary audio processing, upload validation and deletion guarantees.
- Verify transcripts flow through the same text engine; TTS failure never blocks text access or scoring.

## Milestone 6 â€” Production hardening and controlled rollout

- Add deployment automation, secret management, backups, migration runbooks, monitoring/alerts, rate/cost controls, retention/deletion workflows, support/audit tools.
- Perform security, privacy, load, disaster-recovery, accessibility, rubric validation, and disparate outcome reviews.
- Run a limited non-production and then controlled pilot; expand only against agreed operational and assessment-quality criteria.

## Exit criteria per milestone

Each milestone needs reviewed product/architecture decisions, tests appropriate to its failure modes, backward-compatible API/migration notes, operational ownership, and a truthful list of known limitations. Passing tests alone does not establish production readiness.

## Local backend setup

From the repository root, copy `.env.example` to `.env`, then start the local database with `docker-compose -f compose.db.yml up -d --wait`. The Compose project creates only the `finxl_test` database and a project-scoped persistent volume. From `backend/`, create a virtual environment, install `pip install -e ".[dev]"`, apply migrations with `python -m alembic upgrade head`, and run `python -m uvicorn app.main:app --reload`. Stop PostgreSQL with `docker-compose -f compose.db.yml down`; this preserves the test volume. Do not use `down -v` unless intentionally deleting that test volume. The development adapter requires `X-Dev-User-ID`; it is disabled unless `APP_ENV` is `development` or `test`. Production authentication is not yet implemented and fails closed.

## Milestone 5 — Backend Closure and Production Readiness (implemented)

### Implementation & Verification Status

- **Implemented:**
  - Standard JWT/OIDC production authentication adapter (`JwtIdentityAdapter`) supporting asymmetric signatures, JWKS key retrieval and automatic rotation, algorithm allowlists, issuer/audience/expiry/nbf validation, and safe subject claim mapping.
  - Development authentication remains strictly isolated to `development` and `test` environments. Production requests fail closed when unconfigured.
  - Reverse proxy client IP resolution and header spoofing defense (`get_client_ip` and `TRUSTED_PROXIES`), walking right-to-left through trusted hops.
  - Documented and tested non-destructive PostgreSQL backup and restore verification procedure against disposable databases.
  - Complete 11-step end-to-end interview workflow acceptance test suite.
- **Automated-test verified:**
  - 119 automated tests in the Pytest suite (100% passing).
  - 19 PostgreSQL integration tests covering migrations, lease recovery concurrency with `SKIP LOCKED`, atomic shared rate limiters, transactional transcript erasure, and serializable stage progression.
  - Unit and boundary tests for JWT signature, expiration, leeway, invalid claims, algorithm allowlists, unsigned tokens, and JWKS key rotation.
  - Unit and integration tests for reverse proxy trusted CIDRs, header spoofing prevention, and shared rate limiting.
  - End-to-end multi-stage progression acceptance test covering Soft Skills 1 completion, scoring, eligibility derivation, starting next stage, and rejecting locked/ineligible stages.
- **Live-integration verified:**
  - Live local PostgreSQL 16 container (`postgres:16-alpine`), Alembic migrations at `0005_rate_limit_counters` with zero schema drift.
  - Non-destructive backup and restore drill executed using `pg_dump` and `pg_restore` into a disposable database, verifying 13 public tables.
- **Requires product decision:**
  - Selection and parameters of the existing FINXL identity provider (`JWT_JWKS_URL` or `JWT_PUBLIC_KEY`, `JWT_ISSUER`, `JWT_AUDIENCE`, `JWT_USER_ID_CLAIM`, `JWT_ROLE_CLAIM`).
  - Formal approval of `TRANSCRIPT_RETENTION_DAYS` for automated background erasure.
  - Formal product/legal sign-off on transcript erasure vs. progression retention split.
  - Production Gemini API credentials and budget approval.
  - Approved technical course catalog and rubric revisions.
- **Not implemented:**
  - Voice interview capabilities (STT/TTS adapters and ephemeral audio handling) — deferred to voice milestone.
  - Candidate and reviewer frontend modules.

## Milestone 6 — Browser-Native Voice Architecture (implemented)

### Implementation & Verification Status

- **Implemented:**
  - Independent speech input port (`SpeechInput`) and browser Web Speech API adapter (`BrowserSpeechInput`) using `SpeechRecognition` / `webkitSpeechRecognition`.
  - Independent speech output port (`SpeechOutput`) and browser synthesis adapter (`BrowserSpeechOutput`) using `window.speechSynthesis`.
  - Browser voice interview lifecycle orchestrator (`VoiceInterviewLifecycle`) coordinating question fetching, text-to-speech playback, microphone recognition, final transcript validation, answer submission, follow-up progression, error handling, and safe retry.
  - Browser DOM view component (`VoiceInterviewUI`) displaying active questions, spoken indicator, real-time recognition feedback, transcript preview, processing state, retry actions, and typed answer fallback.
  - Full decoupling: speech ports depend on generic interfaces, keeping the interview orchestrator agnostic of whether speech is browser-native, cloud-hosted (Azure/Google Cloud/AWS), or local (Whisper).
  - Reused the existing backend `POST /api/v1/interviews/{session_id}/answers` endpoint: recognized text is submitted as an ordinary answer, ensuring full server-side enforcement of student ownership, versioning, idempotency, scoring, and progression.
  - Zero audio persistence: audio exists ephemerally in browser memory only during active recognition. No audio files or payloads are uploaded, logged, or stored in PostgreSQL or object storage.
- **Automated-test verified:**
  - 46 Vitest frontend unit and integration tests (100% passing across 5 test suites):
    - `tests/browser-speech-input.test.ts`: 13 tests covering support detection, final transcript capture, interim filtering, empty transcript rejection, permission denial, no-speech, network, audio-capture, cancellation, unexpected termination, and session isolation.
    - `tests/browser-speech-output.test.ts`: 9 tests covering support detection, speech execution, language/voice selection, fallback voices, speech cancellation, and overlap prevention.
    - `tests/interview-api-client.test.ts`: 8 tests covering authentication headers, route paths, idempotency keys, and error mappings (401, 403, 404, 409, 429 with `Retry-After`, 503).
    - `tests/voice-interview-lifecycle.test.ts`: 9 integration tests covering complete lifecycle: question display/speech, listening start/stop, transcript submission, follow-up display/speech, completion, retry on transient failure, typed fallback, and resource cleanup.
    - `tests/voice-interview-ui.test.ts`: 7 tests covering DOM state rendering, spoken indicator, live transcripts, button interactions, permission denial alerts, and completed result cards.
  - 136 backend Pytest tests (100% passing), including 19 PostgreSQL integration tests and zero schema drift (`alembic check`).
- **Browser Compatibility & Graceful Degradation:**
  - Tested against Chrome/Chromium (`webkitSpeechRecognition`), Edge (`SpeechRecognition`), and Safari.
  - Graceful fallback: when speech recognition is unsupported (e.g. Firefox default) or microphone access is denied, microphone controls are disabled with clear instructional messaging, and the typed text fallback is enabled.
  - When speech synthesis is unsupported, questions remain visible as text, and the interview proceeds silently.
- **Privacy & Security:**
  - Microphone access is requested only when the student explicitly clicks "Start Voice Answer".
  - Documentation notes that browser Web Speech APIs may route speech through browser vendor cloud services (e.g., Google or Apple speech servers) depending on browser implementation, which is not guaranteed to be strictly offline.
  - Audio payloads never reach the FINXL backend or database.
- **Requires product decision:**
  - Review of browser vendor speech recognition data handling vs. self-hosted Whisper / cloud STT requirements.
  - Selection of default voice accents and multilingual language support beyond `en-IN`.
  - Integration into candidate portal shell and single-sign-on JWT authentication.

Required configuration: `DATABASE_URL` (PostgreSQL SQLAlchemy URL). `FINXL_TEST_POSTGRES_URL` must point to local `finxl_test`; tests reject other database names and non-local hosts. Foundation tuning: `APP_ENV`, `LOG_LEVEL`, `PASSING_THRESHOLD`, `MAX_BASE_QUESTIONS`, `MAX_FOLLOW_UPS_PER_QUESTION`, `MAX_CLARIFICATIONS_PER_QUESTION`, optional `MAX_ATTEMPTS_PER_STAGE`, and `RETAKE_COOLDOWN_SECONDS`. Run integration checks with `python -m pytest -m postgres` from `backend/`.

## M8.2 assessment-content governance foundation

Infrastructure supports versioned competencies, rubrics, question-bank entries, approval lifecycle states, and question-generation provenance. No FINXL assessment content is populated or declared approved. Production stages remain unavailable until content owners provide and approve competency definitions, rubrics, and question entries; the proposed soft_1 example remains development-only. This work does not start M9.


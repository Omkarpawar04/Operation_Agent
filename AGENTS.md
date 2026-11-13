# Engineering rules for FINXL AI Interviewer

## Architecture boundaries

- Keep a modular monolith; do not create microservices without a concrete operational need.
- Domain code must not import FastAPI, SQLAlchemy, Gemini, or speech-provider SDKs.
- Application use cases coordinate domain policies through ports. API routers validate/authorize/map HTTP and stay thin. Adapters implement ports.
- `app/api/dependencies.py` is the composition root. Route modules must not import ORM models, SQLAlchemy sessions or provider adapters; database readiness should use an application port.
- Application use cases depend on protocols and domain/application types only. SQLAlchemy and provider SDK imports belong in adapters.
- Keep the orchestrator as a coordinator. Put state, progression, decision, scoring, ownership and attempt rules in focused policies/use cases.
- Provider recommendations are untrusted data. Only deterministic Python policy controls interview state, marks, pass/fail, and stage access.

## Python conventions

- Target Python 3.11+. Use type annotations on public functions, methods, and data structures. Prefer explicit domain types/enums and immutable value objects where practical.
- Use `snake_case` for modules/functions, `PascalCase` for types, and clear names. Avoid `Any` unless isolating an external boundary and immediately validate it.
- Keep configuration in typed settings; secrets must come from environment/secret injection, never source control.
- Add dependencies only when they have a clear use and maintainability benefit.

## Errors and API

- Raise typed domain/application errors for expected failures. Do not use broad exception swallowing or return success-shaped defaults after failure.
- Map application errors centrally to stable HTTP error codes; do not leak SQL, prompts, credentials, transcripts, or provider internals.
- Obtain user identity from the auth dependency, never a body-supplied student ID. Check ownership on every student resource.
- Never expose endpoints that directly set score, pass/fail, state, or unlock status.

## Persistence and transactions

- Domain entities are independent of ORM models. Keep repositories behind ports and use a Unit of Work/explicit transaction boundary.
- Use UUID keys, UTC-aware timestamps, foreign keys, constraints, and indexes. Preserve assessment/rubric and course-content revision versions.
- Never hold a database transaction open over a slow network/provider call.
- Use idempotency for state-changing commands and optimistic version checks or PostgreSQL row locking for concurrent writes. Commit related answer/evidence/state/result changes atomically.
- Assessment results are immutable. Infrastructure failures must not consume or fail an assessment attempt.

## Providers and privacy

- LLM, STT and TTS are independent ports. Do not import SDKs into domain/application policy. Validate provider output against typed schemas.
- Do not integrate providers without an explicit task. Never make real provider calls in normal tests.
- Never persist audio bytes, paths, URLs, object keys, or raw provider audio payloads. Keep audio temporary and out of logs/traces/database.
- Do not invent transcript retention periods; follow an approved policy. Redact personal content and secrets from logs.
- Do not evaluate accent, gender, vocal pitch, disability, or inferred personality.

## Testing and quality

- Add meaningful pytest coverage for business rules, failure behavior, ownership, idempotency, and boundaries. No placeholder assertions.
- Domain/application tests use fakes. PostgreSQL is required for persistence/migration/concurrency integration claims; SQLite is not a replacement.
- Run pytest, Ruff, and the configured type checker after changes. Report commands and actual outcomes; do not claim production readiness based only on passing tests.
- Avoid unrelated formatting churn and destructive Git operations. Update architecture/roadmap when a material boundary changes.
- Transcript retention is disabled until `TRANSCRIPT_RETENTION_DAYS` is explicitly approved and set. Student deletion erases answers, question text, and evidence while retaining result scores/pass records for derived progression; this policy requires product/legal review before rollout.
- Development identity is a local testing adapter only. It accepts `X-Dev-User-ID` and does not provide production identity assurance; production protected requests fail closed pending an approved OIDC/JWT integration.
- Rate limits use PostgreSQL shared counters. Run Alembic migrations before enabling the API; production origins and trusted hosts must be explicit.
- The lifespan worker recovers expired answer reservations using bounded `SKIP LOCKED` batches and optionally enforces transcript retention when configured.

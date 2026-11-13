# FINXL AI Interviewer backend architecture

**Status:** Text interview orchestration and Milestone 3 application-boundary refactor implemented. Product and production operations called out below remain deferred.

## System shape

FINXL is a modular monolith: a FastAPI process, PostgreSQL persistence, and one deployable backend with enforced package boundaries. No microservices are needed for the current scope. Use cases coordinate domain policies through ports; adapters implement database, identity, and future AI/audio integrations.

```text
FastAPI routers / Pydantic HTTP DTOs / auth / error mapping
                     â†“
Application use cases and orchestrator (workflow coordination only)
                     â†“
Domain entities + state/progression/decision/evaluation policies
                     â†‘ ports (repositories, UoW, LLM, STT, TTS, identity)
                     â†‘
Infrastructure adapters: SQLAlchemy/PostgreSQL, development identity,
future Gemini/STT/TTS provider clients
```

Dependency direction is inward. Domain packages must not import FastAPI, SQLAlchemy, or provider SDKs. Application code must not depend on concrete adapters. The LLM may recommend a question or evidence observations via validated structured output; deterministic Python policies decide state, score, pass/fail, and progression.

## Interview orchestration and component contracts

The orchestrator coordinates a use case; it does not implement all rules. Each collaborator should have a narrow input/output contract:

| Component | Input â†’ output | Responsibility |
|---|---|---|
| Session Manager | authenticated `StudentId`, `StartInterview` â†’ owned session and initial question | Checks eligibility, enrollment, course revision, idempotency; creates/resumes a session. |
| Interview State Manager | session state, command, expected version â†’ new state or typed conflict | Validates legal transitions and concurrency; never accepts a client-selected state. |
| Question Engine | stage, course revision, sequence, prior context â†’ validated `Question` | Uses the LLM port for a candidate, validates it against stage/course scope and question history, and enforces the configured count. |
| Context Manager | session/question/history â†’ bounded, redacted `InterviewContext` | Controls what the analyzer sees and excludes irrelevant or unsafe context. |
| Answer Analyzer | normalized text + context + rubric â†’ `AnalysisRecommendation` | Returns structured evidence, uncertainty, and optional follow-up/clarification recommendation. It does not score, pass, or mutate a session. |
| Follow-up Engine | recommendation + active question + budget â†’ validated follow-up candidate or none | Checks relevance and policy limits; only proposes a follow-up to the decision policy. |
| Interview Decision Policy | session counters/state + answer quality + validated candidates â†’ `FOLLOW_UP`, `CLARIFICATION`, `NEXT_QUESTION`, or `COMPLETE` | Pure deterministic policy. Enforces limits and question order; may treat analyzer output as input, never authority. |
| Evaluation Engine | rubric + validated evidence across answers â†’ immutable `AssessmentResult` | Deterministically applies configured weights and threshold; returns dimension breakdown and pass/fail. |
| Assessment Manager | completed session + result + attempt key â†’ persisted attempt/result | Owns attempt lifecycle and immutable completion record; infrastructure failures do not create failed assessment attempts. |
| Progression Engine | stage sequence + completed passing results + course scope â†’ `ProgressionStatus` | Derives the next unlocked stage. No write endpoint can directly unlock a stage. |

Orchestrator use case order: reserve/idempotency check in short transaction; load and validate session; assemble context; analyze outside transaction; validate evidence/candidates; obtain deterministic decision; commit answer, evidence, question/state, and (if complete) result/attempt atomically with expected version. Transactions are never held open during external provider calls. If future provider work becomes asynchronous, use durable command records and expiring leases.

## State machine and decisions

States: `CREATED`, `AWAITING_ANSWER`, `ANSWER_PROCESSING`, `AWAITING_FOLLOW_UP_ANSWER`, `COMPLETED`, `ABANDONED`, `FAILED`.

```text
CREATED â†’ AWAITING_ANSWER
AWAITING_ANSWER â†’ ANSWER_PROCESSING
AWAITING_FOLLOW_UP_ANSWER â†’ ANSWER_PROCESSING
ANSWER_PROCESSING â†’ AWAITING_FOLLOW_UP_ANSWER | AWAITING_ANSWER | COMPLETED
CREATED | AWAITING_ANSWER | AWAITING_FOLLOW_UP_ANSWER â†’ ABANDONED
any non-terminal state â†’ FAILED (only terminal operational failure)
```

The state manager checks a transition table, expected `version`, and current active question. Every successful transition increments version. Commands include an idempotency key; repeats return the recorded result. Same-question duplicate answers cannot create a second answer. Concurrent stale writes return conflict. A provider outage is retryable and must leave the assessment attempt unconsumed; it may leave an operational command record, but not a failed assessment.

The decision policy uses configurable `max_base_questions`, `max_follow_ups_per_question`, and `max_clarifications_per_question` (initial configuration is non-product default, not a claim about FINXL requirements). Precedence: enforce hard question/session limits; accept a valid relevant follow-up only when budget remains; request clarification only for a configured answer-quality condition and remaining clarification budget; issue the next question in sequence; otherwise complete. Exhausting a follow-up budget does not block progress. No candidate score enters the decision policy.

## Assessment evidence and scoring

Each evidence item contains rubric dimension id, supporting observation(s), missing evidence, insufficient-evidence flag, and confidence/uncertainty metadata. Evidence is linked to an answer and rubric version. Empty/insufficient evidence is represented explicitly; it is not silently converted to a confident negative observation. Rubric dimensions have non-negative weights summing to 1.0 and a version identifier. Python computes the weighted percentage from validated dimension scores under a versioned policy; pass is `score >= configured_threshold` (default 50%). The initial rubric is an assessment framework for validation, not a scientifically validated instrument. Assessment must not use accent, gender, vocal pitch, disability, or inferred personality. Do not score audio characteristics; the core evaluator consumes normalized text and structured evidence only.

## Attempts and progression

An `AssessmentAttempt` begins only once an eligible session is created. It terminates as `PASSED` or `FAILED` only when a result is committed. Retakes create a distinct attempt linked to the same student/stage/course scope. Operational/provider failure is a command/session failure or retryable condition, never a failed assessment attempt. Attempts/results are immutable after completion. A unique idempotency key prevents duplicate creation. `RetakePolicy` supports configurable limits/cooldown; final retake policy remains a product decision.

Stages are ordered: three shared soft-skills mocks followed by three course-specific technical mocks. Eligibility is derived from completed results in that track/course scope: the first stage is eligible per account policy; each later stage requires a passing immediately preceding attempt. Technical sessions pin the enrolled course and approved content revision. Whether soft-skill progression is global or course-scoped must be resolved before launch; technical course scope is always explicit.

## Voice and provider boundaries

LLM, STT, and TTS are independent ports. LLM methods accept typed context and return schema-validated recommendations. Gemini is implemented behind the LLM port; audio providers remain future work. The engine and tests operate entirely on normalized text. Audio bytes may exist only in bounded request memory or a controlled temporary buffer and are deleted promptly; no audio object, path, URL, or raw payload enters database rows, logs, traces, or permanent application storage.

## Persistence and reliability

Use UUID IDs, timezone-aware UTC timestamps, foreign keys, uniqueness/check constraints, and explicit indexes. Domain entities are independent of ORM models. Persist assessment rubric/version and course content revision snapshots. Derive progression instead of duplicating it. Keep transactions short; commit state, answer, analysis evidence, attempt, and result together. Use optimistic `version` checks and unique idempotency constraints; row locks may supplement them on PostgreSQL. Do not hold a database transaction over slow provider calls. Use typed errors and a uniform HTTP error envelope with a request correlation id. Provider output is untrusted and schema validated.

Core tables: users, courses, enrollments, course content revisions, interview sessions, questions, answers, assessment attempts, evaluations/evidence, and assessment results. Transcript/question retention duration is deliberately unset; establish a policy before production, without implying that a duration is approved. No raw audio/audio reference column exists.

## Initial API contracts

All routes use `/api/v1`, validated DTOs, authenticated identity from a dependency, and ownership checks on every student resource. `X-Request-ID` is accepted only after validation or generated server-side and returned in responses.

| Route | Contract |
|---|---|
| `GET /health` | Process liveness; no database dependency. |
| `GET /ready` | Dependency readiness; verifies database connectivity. |
| `GET /me` | Current authenticated user profile. |
| `GET /progression` | Derived stage statuses, scoped to the student's course where applicable. |
| `POST /interviews` | Start/resume with stage, optional technical course, idempotency key; validates enrollment and preceding pass. |
| `GET /interviews/{session_id}` | Owned session state, active question, version and progress. |
| `POST /interviews/{session_id}/answers` | Text answer initially; question id, expected version, idempotency key. Audio transport may later use an ephemeral multipart path. |
| `POST /interviews/{session_id}/abandon` | Explicit idempotent command with expected version. |
| `GET /interviews/{session_id}/assessment` | Owned immutable result once complete; conflict/not-ready before completion. |

No public pass/fail or unlock mutation endpoint is provided. Authentication includes a development-only adapter that is impossible to select in production configuration; production without configured authentication fails closed. Error responses avoid leaking resource existence or internal provider details.

## Foundation and application boundaries

The text workflow creates an initial question, analyzes owned text answers through the LLM port, chooses a deterministic follow-up/clarification/next/completion outcome, and persists answer evidence and final deterministic results. The `google-genai` adapter uses backend-only credentials, configurable model/timeouts and bounded retries. Technical interviews pin approved course content and rubric revisions. Synthetic fixtures remain visibly labelled. Development identity is limited to development/test; production authentication remains deferred.

API dependencies are the composition root. Interview start and answer submission use application use cases; read, abandonment, assessment, progression, user-profile and readiness routes use application-facing ports and use cases. SQLAlchemy implementations are under `app.adapters.persistence`. Domain packages do not import frameworks or infrastructure. Route modules under `api/v1` do not import SQLAlchemy, database models or provider ports.

The answer workflow uses three separate database transactions: reserve the processing state and expected version; release a still-owned reservation after provider/output failure; or persist answer, evidence, question/state transition and optional immutable result atomically. The provider call runs after reservation commit and before finalization begins. Finalization checks session version/state and uses a student-row lock to serialize progression completion against eligible starts. Starting revalidates eligibility while holding the same student lock, and active-scope unique indexes remain a second line of defense. Unique answer/session idempotency constraints and SQLAlchemy optimistic versioning protect duplicate and stale writes. PostgreSQL HTTP integration tests exercise concurrent idempotent starts, concurrent answer submissions, retry/replay behavior, lease recovery and late provider completion.

Answer idempotency is scoped to a session. A repeated key with the same question and exact answer text replays the current state; reuse with different content conflicts. An unsuccessful provider command stores no answer/evaluation and does not consume the key. The session version advances once for reservation and once for release. A processing lease is recovered on a later answer request; the recovering request receives a conflict and must reload. A provider result that arrives after lease recovery fails the reservation version/state check and cannot write.

The SQLAlchemy engine and session factory are created and disposed by the FastAPI lifespan. The UoW commits/rolls back session creation; answer-workflow adapter methods own the short reservation/release/finalization transaction boundaries and do not hold transactions across provider calls. Query adapters return immutable application DTOs rather than ORM entities.

## Assessment content governance (M8.2 foundation)

Assessment content is versioned independently from orchestration. The `assessment_competencies`, `assessment_rubrics`, and `assessment_question_bank` tables carry stage, stable IDs, content versions, source, lifecycle status, and creation/approval metadata. `AssessmentContentPort` exposes approved, stage/competency/rubric-aligned records only. No FINXL content is seeded by the infrastructure migration. Consequently, production interview start fails closed until approved competency, rubric, and question rows exist for that stage. Production follow-ups use Gemini as a selector over approved same-competency question-bank candidates; generated novel wording is rejected. Development-provider questions retain `development_only` provenance.

The nullable `questions.provenance_json` field records provider/model, generation type, prompt/schema version, generation time, origin, approval state, and bank references for new questions. Existing question rows are left null and remain historically unattributed; migrations do not infer their provider or approval state. The active assessment rubric is pinned through each question's rubric version reference. Deterministic scoring and the existing pass threshold remain in Python. Content-authoring/approval UI and approved FINXL competency/rubric/question records remain outside this infrastructure change.

Remaining operational limitations at the Milestone 3 checkpoint were production identity, background recovery, rate limiting, transcript policy, and deployment operations. Current Milestone 4 progress and open blockers are described in the security and operations section below.
## Security, reliability, and test strategy

Risks include IDOR, stage/course bypass, duplicate/concurrent commands, provider timeout/malformed output, unsafe course/student prompt content, media decoder abuse, cost abuse, transcript privacy leakage, credential leakage, scoring bias, and inconsistent migrations. Mitigations include owner checks, server-side progression, idempotency/version constraints, bounded provider calls, schema validation, strict context boundaries, request quotas/size limits, redacted structured logs, secret injection, immutable rubric versions, and audited privileged access. Audio is never persisted. Retention/export/deletion and third-party processing consent require product/legal decisions.

Tests: domain transition matrix and invalid transitions; version/idempotency; deterministic decision limits; score threshold and invalid weights; insufficient evidence; infrastructure failure attempt accounting; progression/course enrollment/ownership; immutable result; API auth/error contracts; SQL constraints and rollback; PostgreSQL Alembic migration from empty DB; concurrent updates. Unit/application/API tests run locally with fakes and no provider credentials. Persistence integration tests must use PostgreSQL; SQLite is limited to explicitly compatible lightweight tests and cannot substitute for the PostgreSQL migration/concurrency check.

## Deferred decisions

Authentication vendor/claims and staff roles; course/enrollment/content source and approval process; soft skill scope (global/per course); base question counts and interview duration; clarification semantics; retake limit/cooldown/best-vs-latest rule; rubric dimensions and validation process; STT/TTS vendors, languages, consent, and provider retention; transcript/result retention and deletion/export; deployment region, concurrency, and availability objectives; administrative review/override policy. Technical defaults remain configuration only until product owners decide.

## Milestone 6 browser-native voice architecture status

The initial voice capability is implemented via browser-native Speech-to-Text (Web Speech API `SpeechRecognition` / `webkitSpeechRecognition`) and Text-to-Speech (`window.speechSynthesis`), isolated behind replaceable frontend ports:

1. **`SpeechInput` Port & `BrowserSpeechInput` Adapter:**
   - Detects browser support (`SpeechRecognition` / `webkitSpeechRecognition`).
   - Distinguishes interim transcripts from final transcripts; never submits partial/interim utterances.
   - Rejects empty transcripts; handles microphone permission denial (`not-allowed`), no-speech, network, and audio capture errors.
   - Prevents multiple concurrent sessions and cleans up resources on unmount or cancellation.
   - Default language: `en-IN` with English dialect fallbacks.

2. **`SpeechOutput` Port & `BrowserSpeechOutput` Adapter:**
   - Speaks interview questions and follow-up questions using `window.speechSynthesis`.
   - Prevents overlapping speech by canceling prior utterances before speaking a new question.
   - Selects language-matched voices (`en-IN` -> `en-GB` -> `en-US` -> system default) and handles async voice list loading (`onvoiceschanged`).
   - Stops cleanly on unmount, question advancement, or navigation.

3. **Backend Integration & Zero Audio Storage:**
   - Recognized transcripts are submitted through the existing `POST /api/v1/interviews/{session_id}/answers` endpoint as ordinary text answers.
   - The backend enforces authenticated identity, student ownership, session state, expected version, and answer validation.
   - Scores and progression remain completely controlled by deterministic Python domain policies.
   - Audio is strictly ephemeral in browser memory during live recognition; no audio files, payloads, or recordings are uploaded, logged, or persisted to PostgreSQL or disk.
   - Graceful degradation provides typed answer fallback whenever speech recognition is unsupported or permissions are denied.



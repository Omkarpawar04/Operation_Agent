# M8.2 content import and development use

The M8.2 pack is draft review content. Importing it does not approve it or make it
eligible for production selection. The local development opt-in below deliberately
allows these draft records to be used for engineering verification only.

## Validate and import

Run the following from `D:\finxl-ai-interviewer\backend` in the project virtual
environment. The importer reads the JSON pack by default and uses the configured
`DATABASE_URL`.

```powershell
python -m scripts.validate_assessment_content
python -m alembic upgrade head
python -m scripts.import_assessment_content --dry-run
python -m scripts.import_assessment_content --apply
```

The dry run validates all pack references and checks database conflicts without
writing. Apply inserts question, competency, rubric, and follow-up rows in one
transaction. Repeating apply is idempotent. Conflicting existing records stop the
import without overwriting them. Existing lifecycle states are preserved. This
M8.2 pack imports as `draft`; it has no FINXL approver or approval timestamp.

The importer retains source status, source references (PDF file, page, section,
and review notes), curriculum links, expected-answer evidence, rubric levels,
proposed competency stage mappings, and follow-up parent links in the existing
assessment tables' metadata fields and relationships. `development_eligible` marks
only the imported pack questions as available to the explicit development selector.
The approval status remains draft.

## Enable question-bank selection locally

Keep `APP_ENV=development` and set these variables in the backend process before
starting the server. No `.env` secrets or Gemini settings need to change.

```powershell
$env:DEV_ASSESSMENT_CONTENT_MODE = "question_bank"
$env:DEV_ASSESSMENT_ALLOW_DRAFT = "true"
python -m uvicorn app.main:app --reload
```

Both flags are needed for this draft-only pack. Bank mode without the second flag
can select approved, development-eligible records only and will fail clearly when
none exist. The defaults are `fixture` and `false`, preserving prior development
behavior. Bank mode does not call `FakeLLMProvider.generate_question` for the
initial question and does not fall back to a fixture when no eligible bank item is
available. The development adapter still checks stage membership, competency,
rubric, version, eligibility, and follow-up parent relationships.

The frontend resumes an existing active interview for the signed-in development
identity. Finish or abandon an older fixture interview before starting a fresh
bank-mode interview if that active interview is still in progress. Resuming a bank
interview displays its persisted question.

## Verify persisted provenance

Start a fresh interview and inspect the current question through the read-only API:

```powershell
Invoke-RestMethod -Method Get `
  -Uri "http://localhost:8000/api/v1/interviews/<session-id>/question" `
  -Headers @{ "X-Dev-User-ID" = "<development-user-id>" }
```

For a development bank question the response includes `stage_id`,
`content_origin=development_assessment_bank`,
`content_approval_status=draft`, `bank_question_id`, `competency_id`,
`rubric_version_id`, `content_version`, `parent_question_id` when applicable,
and `development_only=true`. The question row stores the same provenance JSON.
Do not use the development identity header outside local development.

Switch back to fixtures by restarting the backend with:

```powershell
$env:DEV_ASSESSMENT_CONTENT_MODE = "fixture"
$env:DEV_ASSESSMENT_ALLOW_DRAFT = "false"
```

## Production and FINXL review

Production rejects development content settings. Its existing adapter continues to
require an approved question, approved competency, approved rubric, and a matching
stage mapping. Draft or development-eligible records are never a production
fallback. The development import does not perform FINXL approval; approval must
come through a separately controlled review process with real reviewer identity
and timestamp.

Before production approval, FINXL reviewers must confirm question wording, answer
evidence, competency definitions, stage mappings, rubric dimensions and weights,
and source accuracy. The pack does not establish official competencies or rubrics.
In particular, neither supplied source supports LBO curriculum for
`technical_3`; that gap remains unresolved and requires FINXL content-owner review.

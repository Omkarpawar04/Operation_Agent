# FINXL Resume Analysis & Optimization Engine

A database-free FastAPI prototype for parsing PDF/DOCX resumes, analyzing a local job description, showing transparent requirement matches with evidence, reporting resume-quality checks, preparing structured resume content, and generating DOCX/PDF versions in two styles.

**No external AI provider is integrated in this phase.** The preparation service only reorders already-present supported skills; it does not rewrite claims or insert missing job requirements.

## Run locally

Requires Python 3.10 or newer.

```powershell
cd D:\finxl
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn backend.app.main:app --reload
```

Open <http://127.0.0.1:8000>. Run the tests with `python -m unittest discover -s tests -v`.

## Architecture

```text
backend/app/main.py                    FastAPI endpoints and orchestration
backend/app/services/resume_parser.py  PDF/DOCX text extraction and structured parsing
backend/app/services/jobs.py           local job source abstraction
backend/app/services/jd_analyzer.py    requirement records and JD sections
backend/app/services/keyword_extractor.py controlled terms, aliases, phrase candidates
backend/app/services/matcher.py        exact/alias/related match and source evidence
backend/app/services/quality_analyzer.py transparent rule-based quality findings
backend/app/services/ai_optimizer.py  provider-free preparation seam for future AI
backend/app/services/resume_generator.py shared structured renderer with two themes
backend/data/                           demo job JSON
backend/uploads/                        temporary uploads, deleted after successful generation
backend/outputs/                        persistent generated documents
frontend/                               single-page FINXL workflow
tests/                                  deterministic parsing, analysis, matching, rendering, API tests
```

The pipeline separates resume content from presentation. Sessions are in memory, jobs are stored in JSON, uploads are temporary files, and generated documents stay on disk. No database is used.

## Structured resume model

The parser returns `personal_info`, a summary, structured experience and internship entries, education entries, projects, categorized skills (`technical`, `tools`, `soft_skills`, `domain`, `other`), certifications, achievements, languages, publications, interests, and an `other` collection for unclassified content. Each job/project entry retains source-supported details such as organization/name, role, location, dates, bullets, technologies, and unclassified lines where detected. `source_lines` are retained for evidence and rule-based checks; generated documents consume the structured fields rather than dumping raw text.

Section matching is case-insensitive and accepts common heading variants such as Work Experience, Professional Experience, Internship Experience, Academic Projects, and Technical Skills. Dates and bullets are inferred from text patterns, independent of original bold/italic styles. Parsing is heuristic, so ambiguous source text is preserved where possible instead of being silently promoted to a factual field.

## JD analysis and matching

`get_job_description(job_id)` still reads the local JSON and is the seam for a future FINXL API. The analyzer returns typed requirement objects with a display name, normalized name, type, category, importance, source, and source evidence. Types include tools, technical/domain/soft skills, qualifications, education, certifications, experience, responsibilities, and other.

Extraction layers:

1. Controlled vocabulary (`TERMS`) for deterministic known phrases.
2. Alias normalization (`MS Excel` and `Microsoft Excel` normalize to Excel; modelling/analytics variants normalize consistently).
3. Small cue-based phrase extraction for uncatalogued phrases after wording such as “experience with” or “preferred”. This is lightweight Python regex, not a downloaded NLP model.
4. Requirement classification, required/preferred/optional/unknown cues, and normalized deduplication.

The matcher reports `matched`, `related`, and `missing`/`not_detected`, plus per-requirement evidence lines and the match type. It uses exact normalized phrase matches, aliases, and a small explicit related-term map. It does not infer that Excel dashboards mean Power BI. Missing JD requirements are never added to the candidate’s resume. No opaque ATS score is produced.

## Resume quality analysis

The analysis response includes `quality_analysis.issues`, structural completeness, and JD-alignment counts. Rules flag missing contact/summary/education, incomplete work entries, missing bullets/project descriptions, long lines, inconsistent date/bullet styles, repeated headings, excessive blank spacing, and unclassified content where detected. Findings are explainable checks, not a ranking or ATS score.

## Templates and generated documents

Both themes render the same structured content through shared generation logic:

- **Professional:** centered name, modern Arial/Helvetica typography, teal section hierarchy, airier spacing.
- **Corporate:** left-aligned name, Times typography, navy rules/headings, more compact formal spacing.

The frontend uses the uploaded candidate’s structured resume to show visibly different live previews of both themes. The final preview uses the selected theme and generated structured payload. DOCX uses python-docx with bold organization/role hierarchy and real list bullets. PDF uses ReportLab with the same section order and content. Layout is kept single-column without decorative graphics or complex tables.

## AI integration preparation

`ai_optimizer.optimize_resume(resume, job, requirements, matching, quality)` is the future provider seam. It currently makes a deep copy and only reorders existing supported skills by match relevance. No network request, provider SDK, API key, or AI dependency is used. A future provider must receive the structured match/evidence and quality results and preserve source facts, contact details, education, dates, experience, projects, certifications, and metrics. It must never add a missing JD item as a candidate skill. Formatting remains the renderer’s responsibility.

## API endpoints

- `GET /api/health`
- `GET /api/jobs`, `GET /api/jobs/{job_id}`
- `GET /api/templates`
- `POST /api/optimize-resume` — multipart `file`, `job_id`; upload, parse, JD analysis, match, quality checks
- `POST /api/resumes/{resume_id}/optimize` — provider-free content preparation
- `POST /api/resumes/{resume_id}/generate` — form `template_id`; write and verify DOCX/PDF, then delete only the temporary upload
- `GET /api/generated-resumes/{resume_id}/{docx|pdf}`

The response retains the original `resume_analysis`, `job_analysis`, `match`, and `templates` fields and adds `quality_analysis`. The job analysis retains `required_skills` and other legacy lists alongside the new structured `requirements`. The match retains its `matched`, `related`, `missing`, and `counts` compatibility fields and adds evidence-bearing `items`.

## File lifecycle and security

`backend/uploads/` holds a unique UUID-prefixed, sanitized PDF/DOCX during analysis and optimization. After the generate endpoint confirms both output files exist and are non-empty, it deletes only that source upload. Any analysis, optimization, or generation error is logged and retains the upload for debugging. `backend/outputs/` is persistent for download. Filenames with spaces are supported; route IDs are validated before output paths are built. Files are limited to 8 MB and extension-checked. Production deployment would also need authentication, retention controls, and stronger file-content inspection.

## Tests

```powershell
python -m unittest discover -s tests -v
```

Tests cover PDF/DOCX parsing, section and internship structure, education/projects/skills extraction, keyword and alias behavior, candidate phrases and requirement importance, matching evidence and missing skills, quality checks, both template outputs, upload cleanup, failure retention, and the API workflow.

## Limitations

- Parser and candidate extraction are heuristic; scanned PDFs need OCR and unusual layouts may require manual correction.
- Phrase extraction is cue-based and uses a small vocabulary/alias/related map; it can miss domain language and needs evaluation data to expand safely.
- Some classifications and required/preferred cues may remain `unknown` when the JD is ambiguous.
- In-memory sessions expire on server restart; output files remain local.
- Provider-free preparation does not rewrite wording. External AI integration is deliberately deferred to a separate phase.

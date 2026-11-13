# FINXL Content Coverage Report — V1

## Source documents processed

| Source file | Pages | Processing | Limitations |
|---|---:|---|---|
| `Financial Modeling & Equity Reasearch (FM&ER).pdf` | 12 | pypdf extraction; pages 6–9 visually rendered and checked | Custom font text extraction is corrupted. Curriculum on pages 6–9 was checked against rendered pages. |
| `Financial Statements & Ratios.pdf` | 27 | pypdf extraction, page-tagged question and answer capture | Text is readable. Extracted boundaries and technical accuracy still need reviewer confirmation. |

The FM&ER filename supplied in the repository is misspelled “Reasearch”; it is preserved exactly in references. Page numbering in this pack is 1-based PDF page numbering.

## Curriculum modules and topics

The brochure contains seven numbered modules. Modules 1–5 appear together on PDF page 6; ratio and valuation topics continue on page 7; module 6 is on page 7; module 7 is on page 8. PDF page 9 gives business-professional contexts such as shaping, running, expanding, or divesting a business. That page is cross-referenced in relevant scenario content but is not assigned an eighth formal module.

| Module | Title | Topic entries | Source page |
|---|---|---:|---:|
| M1 | MS Excel Expert | 25 | 6 |
| M2 | Data Collection and Modeling | 18 | 6 |
| M3 | Finance Fundamentals | 32 | 6 |
| M4 | Sector/Industry Research | 7 | 6 |
| M5 | Financial Modeling & Valuations | 39 | 6 |
| M6 | Equity Research Report | 9 | 7 |
| M7 | Real Case Studies, Mock Interviews, Soft Skills Training | 9 | 8 |

Brochure taxonomy entries: **139** across seven numbered modules. Supplemental Q&A taxonomy entries: **73**. Combined topic records: **212**. Overlap is retained where the brochure repeats a topic in more than one module context. Supplemental Q&A topics are explicitly not treated as an eighth course module.

## Proposed application-stage mapping

| Stage ID | Proposed title | Competencies | Questions | Basic / Intermediate / Advanced |
|---|---|---:|---:|
| `soft_1` | Communication & Behavioral Foundations | 1 | 2 | 1 / 1 / 0 |
| `soft_2` | Problem Framing & Structured Thinking | 4 | 9 | 0 / 5 / 4 |
| `soft_3` | Executive Presence & Stakeholder Influence | 4 | 2 | 0 / 0 / 2 |
| `technical_1` | Accounting Fundamentals & 3-Statement Mechanics | 4 | 14 | 6 / 2 / 6 |
| `technical_2` | Valuation Methodologies (DCF & Comps) | 4 | 18 | 8 / 1 / 9 |
| `technical_3` | LBO Modeling & M&A Mechanics | 7 | 7 | 2 / 2 / 3 |

Stage IDs and titles follow the existing application sequence and supplied M8.2 definitions. The curriculum modules are not treated as equivalent to stages. Soft-stage competencies and all course-to-stage mappings are proposals inferred from course descriptions; they require FINXL approval.

## Pack counts

- Competencies: **16**; each is a proposed catalogue entry.
- Supplemental Q&A topic records: **73**, grouped by source sections/pages and kept separate from the seven numbered brochure modules.
- Questions: **52** total: **35 source-derived** question stems extracted from the Q&A PDF and **17 newly written source-based drafts** grounded in brochure topics.
- Expected-answer evidence records: **52**; source answers are preserved as excerpts/answer text for source-derived questions, while draft criteria are labeled as inferred.
- Rubrics: **16** draft rubric records across **16** competencies. Each uses 0–4 levels and weights totaling 1.00; weights and levels are inferred and unapproved.
- Follow-up candidates: **52** source-based draft candidates linked to parent questions and their competency/stage. None is approved.
- Approval: **0** approved records. All records are draft or pending review and remain outside production.

## Source-derived versus drafted material

Source-derived items are the question stems and answer content present in the supplied Financial Statements & Ratios PDF, and the faithfully transcribed curriculum topics/modules from the FM&ER brochure. Source-based draft questions extend documented topics where direct interview questions were absent. Competency definitions/mappings, question-specific evidence framing, rubrics, scoring weights, performance-level indicators, and follow-up wording are proposals, not FINXL-approved assessment standards.

## Coverage gaps and review requirements

| Area | Finding | Recommended action |
|---|---|---|
| LBO | The supplied FM&ER brochure and Financial Statements & Ratios Q&A do not identify LBO modeling or LBO mechanics as course content. The technical_3 application title mentions LBO, but that is not evidence of curriculum coverage. | FINXL content owner to provide explicit LBO curriculum or confirm that technical_3 should assess only documented financial modeling and transaction topics. |
| Soft-skill definitions | The brochure names communication/interpersonal skills, mock interviews, interview scripting, positive attitude, and emotional intelligence; it does not define the six-stage soft competencies or formal rubrics. | Approve or revise each soft-stage competency and its boundaries. |
| Scoring | Neither source defines rubric dimensions, weights, or performance levels. The rubric pack proposes these solely for review. | Validate criteria and weights with assessment/content owners before import or use. |
| Excel questions | The brochure provides a detailed Excel topic list but no formal Excel interview questions or answers. | Review the source-based draft prompts and add approved practical tasks if required. |
| Corporate action treatments | The brochure lists actions and related ownership concepts but does not describe their accounting or valuation treatments. | Obtain FINXL lesson material or content-owner-approved treatment notes before assessing detailed treatment. |
| FM&ER text extraction | The brochure's embedded/custom font produces corrupted text extraction. Curriculum pages 6-9 were visually rendered and checked; several pages are promotional or irrelevant to assessment content. | Use the rendered brochure pages as source verification; provide a text-accessible original for future automated extraction if exact transcription is needed. |
| Source wording requiring SME check | The brochure prints 'YEARFRACE' (PDF p. 6), and the Q&A answer includes 'Gain Associated with the Juice Transaction' (PDF p. 5). Both strings are retained as supplied; their intended meaning has not been inferred or corrected. | Ask the FINXL content owner/SME to confirm whether these are source typos, specialized terms, or intended wording before retaining them in approved content. |

### LBO coverage

**No explicit LBO curriculum support was found in either supplied document.** The application’s technical_3 title mentions LBO, but that title is not source evidence. The pack maps documented financial modeling, schedules, forecasting, valuation, and named M&A/transaction topics to the stage only as a proposal. FINXL must provide LBO material or approve a revised technical_3 scope before production content can be authored for LBO.

### Extraction and assessment limitations

- Brochure pages 6–9 were visually checked because custom font mapping corrupts text extraction. The pack avoids using the corrupted extracted text as evidence where visual reading was available.
- The Q&A PDF yielded 35 question stems. Questions have no printed question numbers; section headings and 1-based PDF page references are used instead.
- The Q&A PDF includes detailed answers for its questions. The pack preserves answer text on the source-derived question records; reviewers should verify extracted segmentation and source statements. Source explanations that appear questionable must be flagged rather than silently corrected.
- Course-brochure topic listings do not establish exact assessment scope, required difficulty, or approved question wording.
- The source material does not specify official competency definitions, stage mappings, rubric dimensions, weights, performance levels, follow-up wording, or pass thresholds.

## Recommended next steps

1. FINXL content owner reviews and accepts/rejects each competency and six-stage mapping.
2. Subject-matter reviewers verify each source question, answer boundary, technical statement, and page reference.
3. FINXL approves or revises draft questions, expected evidence, follow-ups, and each 0–4 rubric, including its inferred weights.
4. Obtain explicit decision on technical_3/LBO scope and any required LBO source material.
5. Only after approval, prepare a separate controlled import into the existing assessment-content tables; this pack has not been imported.

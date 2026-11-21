# FINXL Finance Curriculum Addendum — Pack 1.1.0

This addendum extends the existing assessment content pack in place. Application stage IDs, the V1.0 question IDs, and the V1.0 content rows remain unchanged. Version 1.1.0 is draft-only and is imported by the existing idempotent assessment content importer.

## Content counts

Each stage adds eight base questions and eight parent-linked follow-up candidates. The original records remain present at version 1.0.0.

| Stage | New base | New follow-ups | Preserved V1.0 base | Total base in pack |
| --- | ---: | ---: | ---: | ---: |
| `soft_1` | 8 | 8 | 2 | 10 |
| `soft_2` | 8 | 8 | 9 | 17 |
| `soft_3` | 8 | 8 | 2 | 10 |
| `technical_1` | 8 | 8 | 14 | 22 |
| `technical_2` | 8 | 8 | 18 | 26 |
| `technical_3` | 8 | 8 | 7 | 15 |
| **Total** | **48** | **48** | **52** | **100** |

The importer represents base questions and follow-up candidates in the same question-bank table, so the complete pack contains 200 question-bank rows when both categories are counted.

## New competencies and rubrics

| Stage | Competency | Rubric | Focus |
| --- | --- | --- | --- |
| `soft_1` | `FIN_FOUNDATIONS_COMM` | `R_FIN_FOUNDATIONS_COMM_V1_1` | Finance terminology, conceptual accuracy, purpose, accessible explanation |
| `soft_2` | `FIN_CONCEPTUAL_REASONING` | `R_FIN_CONCEPTUAL_REASONING_V1_1` | Ratio interpretation, statement connections, reasoning, context |
| `soft_3` | `FIN_SCENARIO_RECOMMENDATION` | `R_FIN_SCENARIO_RECOMMENDATION_V1_1` | Problem diagnosis, evidence, practical recommendation, stakeholder communication |
| `technical_1` | `FIN_MODEL_FUNDAMENTALS` | `R_FIN_MODEL_FUNDAMENTALS_V1_1` | Model layout, historical data, driver-based forecasts, assumption hygiene |
| `technical_2` | `FIN_STATEMENT_RATIO_ANALYSIS` | `R_FIN_STATEMENT_RATIO_ANALYSIS_V1_1` | Statement interpretation, ratio calculations, trends, comparison |
| `technical_3` | `FIN_MODEL_APPLICATIONS` | `R_FIN_MODEL_APPLICATIONS_V1_1` | Integrated forecast interpretation, scenarios, variances, judgment |

Each rubric uses observable criteria and the existing 0–4 scoring scale. Its indicators value correctness, relevant reasoning, and context; verbosity is not a criterion. The deterministic score calculation and 50% pass threshold are unchanged.

## Provenance

All new question stems, expected-answer evidence, and follow-up wording are newly authored from the curriculum brief. They are labeled `inferred_draft`; they are not represented as quotations or extracted questions from the PDFs. The cited pages support the topic only. Each record remains `draft` and `pending_finxl_review`, with no approval actor or timestamp.

Topic references used for the new records:

| Stage | FINXL source and cited pages | Topics supported |
| --- | --- | --- |
| `soft_1` | `Financial Statements & Ratios.pdf`, pp. 1–5, 8, 14–15 | Statement purpose and structure, basic terminology, working capital, cash-flow context |
| `soft_2` | `Financial Statements & Ratios.pdf`, pp. 9, 14–20, 22–24 | Statement links, cash versus profit, ratio types and interpretation |
| `soft_3` | `Financial Statements & Ratios.pdf`, pp. 2, 8, 14–17, 19, 24–27; `Financial Modeling & Equity Reasearch (FM&ER).pdf`, p. 9 | Profit and expense analysis, working capital and cash scenarios, business decisions |
| `technical_1` | `Financial Modeling & Equity Reasearch (FM&ER).pdf`, pp. 6, 9 | Financial information, modeling and business forecasting topics |
| `technical_2` | `Financial Statements & Ratios.pdf`, pp. 1–2, 5, 8–9, 16–20, 22–24 | Statement interpretation and supported liquidity, profitability, solvency, and efficiency ratios |
| `technical_3` | `Financial Modeling & Equity Reasearch (FM&ER).pdf`, pp. 6–7, 9; `Financial Statements & Ratios.pdf`, pp. 8–9, 14–15 | Integrated statements, modeling scenarios, sensitivity, variance/business application, and the source-listed DCF/comparables topics |

The exact reference metadata is stored with each question/evidence/follow-up record in `finxl_assessment_content_v1.json`. The PDF filenames above are preserved exactly as present in `docs/source-material/`, including the source filename typo.

## Selection and legacy records

The deterministic selector recognizes the `Q_CURR_FIN_11_` versioned curriculum prefix, prefers those records when eligible, then uses stable question ID and content-version ordering. It filters repeated wording against session history. Normal repository queries still enforce stage, category, competency, lifecycle status, and parent question. Production queries remain approved-only. New draft records are available only through the existing explicit development draft opt-in.

Legacy V1.0 records are not deleted, edited, or automatically retired. Stage-specific V1.1 competencies keep interview progression on the revised curriculum once its first question is selected. FINXL reviewers can separately approve or retire legacy and new versions through the existing content governance process.

No database migration is required: the existing schema supports content versions, competency/rubric mappings, question categories, provenance, approval state, and parent-linked follow-ups.

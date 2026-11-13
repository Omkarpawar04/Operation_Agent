"""Validate and import the M8.2 pack without granting production approval."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models import AssessmentRubricRow, CompetencyDefinitionRow, QuestionBankRow
from app.domain.assessments.content import ContentStatus, QuestionCategory
from scripts.validate_assessment_content import validate_content

PACK_PATH = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "assessment-content"
    / "v1"
    / "finxl_assessment_content_v1.json"
)
CONTENT_SOURCE = "FINXL M8.2 assessment content pack"


class ContentImportError(ValueError):
    """Input pack or existing database content cannot be imported safely."""


@dataclass(frozen=True, slots=True)
class ImportSummary:
    inserted_competencies: int
    inserted_rubrics: int
    inserted_questions: int
    unchanged_competencies: int
    unchanged_rubrics: int
    unchanged_questions: int
    dry_run: bool


def _metadata(record: dict[str, Any], pack_version: str, **extra: object) -> dict[str, Any]:
    result = dict(record)
    result["pack_version"] = pack_version
    result.update(extra)
    return result


def build_records(
    content: dict[str, Any],
) -> tuple[list[CompetencyDefinitionRow], list[AssessmentRubricRow], list[QuestionBankRow]]:
    """Map the pack into existing tables after the caller validates the full pack."""
    pack_version = content["pack_version"]
    evidence_by_id = {row["evidence_id"]: row for row in content["expected_answer_evidence"]}
    competencies = []
    for item in content["competencies"]:
        stages = item["stage_ids"]
        if not stages:
            raise ContentImportError(f"Competency {item['competency_id']} has no stage mapping")
        competencies.append(
            CompetencyDefinitionRow(
                competency_id=item["competency_id"],
                stage_id=stages[0],
                stage_ids_json=list(stages),
                title=item["name"],
                definition=item["description"],
                content_version=pack_version,
                approval_status=item["approval_status"],
                content_source=CONTENT_SOURCE,
                created_by=None,
                approved_at=None,
                approved_by=None,
                content_metadata_json=_metadata(item, pack_version),
            )
        )

    rubrics = [
        AssessmentRubricRow(
            rubric_version_id=item["rubric_version_id"],
            rubric_id=item["rubric_id"],
            competency_id=item["competency_id"],
            dimensions_json=item["dimensions"],
            scoring_scale_json=item["scoring_scale"],
            evidence_requirements_json=item["evidence_requirements"],
            insufficient_evidence_json=item["insufficient_evidence_criteria"],
            content_version=pack_version,
            approval_status=item["approval_status"],
            content_source=CONTENT_SOURCE,
            created_by=None,
            approved_at=None,
            approved_by=None,
            content_metadata_json=_metadata(item, pack_version),
        )
        for item in content["rubrics"]
    ]

    questions: list[QuestionBankRow] = []
    for item in content["questions"]:
        evidence = evidence_by_id[item["expected_answer_evidence_id"]]
        answer_characteristics = [
            *[f"Essential: {value}" for value in evidence["essential_concepts"]],
            f"Supporting explanation: {evidence['supporting_explanation']}",
            f"Application/reasoning: {evidence['application_or_reasoning']}",
            *[f"Example/calculation: {value}" for value in evidence["examples_or_calculations"]],
            *[
                f"Incomplete evidence: {value}"
                for value in evidence["incomplete_or_missing_evidence"]
            ],
        ]
        if item.get("source_answer_text"):
            answer_characteristics.append(f"Source answer: {item['source_answer_text']}")
        questions.append(
            QuestionBankRow(
                question_id=item["question_id"],
                stage_id=item["stage_id"],
                competency_id=item["competency_id"],
                text=item["text"],
                category=QuestionCategory.BASE.value,
                difficulty=item["difficulty"],
                expected_answer_json=answer_characteristics,
                rubric_version_id=item["rubric_id"],
                content_version=pack_version,
                approval_status=item["approval_status"],
                content_source=CONTENT_SOURCE,
                parent_question_id=None,
                parent_content_version=None,
                development_eligible=item["approval_status"] == ContentStatus.DRAFT.value,
                created_by=None,
                approved_at=None,
                approved_by=None,
                content_metadata_json=_metadata(
                    item,
                    pack_version,
                    expected_answer_evidence=evidence,
                    development_eligible=item["approval_status"] == ContentStatus.DRAFT.value,
                ),
            )
        )

    for item in content["follow_up_candidates"]:
        parent_id = item["parent_question_id"]
        questions.append(
            QuestionBankRow(
                question_id=item["follow_up_id"],
                stage_id=item["stage_id"],
                competency_id=item["competency_id"],
                text=item["text"],
                category=QuestionCategory.FOLLOW_UP.value,
                difficulty="not_assigned",
                expected_answer_json=[item["intended_evidence_gap"]],
                rubric_version_id=next(
                    question["rubric_id"]
                    for question in content["questions"]
                    if question["question_id"] == parent_id
                ),
                content_version=pack_version,
                approval_status=item["approval_status"],
                content_source=CONTENT_SOURCE,
                parent_question_id=parent_id,
                parent_content_version=pack_version,
                development_eligible=item["approval_status"] == ContentStatus.DRAFT.value,
                created_by=None,
                approved_at=None,
                approved_by=None,
                content_metadata_json=_metadata(
                    item,
                    pack_version,
                    question_category="follow_up_candidate",
                    development_eligible=item["approval_status"] == ContentStatus.DRAFT.value,
                ),
            )
        )

    _validate_duplicate_records(questions)
    return competencies, rubrics, questions


def _validate_duplicate_records(questions: list[QuestionBankRow]) -> None:
    seen: set[tuple[str, str, str]] = set()
    for question in questions:
        normalized = " ".join(question.text.casefold().split())
        key = (question.stage_id, question.category, normalized)
        if key in seen:
            raise ContentImportError(
                f"Duplicate question text in stage/category {question.stage_id}/{question.category}"
            )
        seen.add(key)


def _same_content(existing: object, incoming: object, fields: tuple[str, ...]) -> bool:
    return all(getattr(existing, field) == getattr(incoming, field) for field in fields)


def import_content(session: Session, content: dict[str, Any], *, apply: bool) -> ImportSummary:
    """Validate, conflict-check, then insert all new content in one transaction."""
    errors = validate_content(content)
    if errors:
        raise ContentImportError("Assessment content validation failed:\n- " + "\n- ".join(errors))
    if content.get("governance", {}).get("production_approved") is not False:
        raise ContentImportError("Assessment content must remain unapproved")
    if not all(
        item.get("approval_status") == ContentStatus.DRAFT.value
        for collection in ("competencies", "rubrics", "questions", "follow_up_candidates")
        for item in content[collection]
    ):
        raise ContentImportError("This importer accepts draft pack content only")

    competencies, rubrics, questions = build_records(content)
    plan: tuple[tuple[type[object], list[object], tuple[str, ...], str], ...] = (
        (
            CompetencyDefinitionRow,
            list(competencies),
            ("competency_id",),
            "competencies",
        ),
        (AssessmentRubricRow, list(rubrics), ("rubric_version_id",), "rubrics"),
        (
            QuestionBankRow,
            list(questions),
            ("question_id", "content_version"),
            "questions",
        ),
    )
    insertions: dict[str, list[object]] = {name: [] for *_, name in plan}
    unchanged: dict[str, int] = {name: 0 for *_, name in plan}
    fields = {
        "competencies": (
            "stage_id",
            "stage_ids_json",
            "title",
            "definition",
            "content_version",
            "content_source",
            "content_metadata_json",
        ),
        "rubrics": (
            "rubric_id",
            "competency_id",
            "dimensions_json",
            "scoring_scale_json",
            "evidence_requirements_json",
            "insufficient_evidence_json",
            "content_version",
            "content_source",
            "content_metadata_json",
        ),
        "questions": (
            "stage_id",
            "competency_id",
            "text",
            "category",
            "difficulty",
            "expected_answer_json",
            "rubric_version_id",
            "content_version",
            "content_source",
            "parent_question_id",
            "parent_content_version",
            "development_eligible",
            "content_metadata_json",
        ),
    }
    conflicts: list[str] = []
    try:
        for model, incoming_rows, key_fields, name in plan:
            for incoming in incoming_rows:
                key = tuple(getattr(incoming, field) for field in key_fields)
                existing = session.get(model, key[0] if len(key) == 1 else key)
                if existing is None:
                    insertions[name].append(incoming)
                elif _same_content(existing, incoming, fields[name]):
                    unchanged[name] += 1
                else:
                    conflicts.append(f"{name} {key!r} differs from existing content")
        if conflicts:
            raise ContentImportError(
                "Import conflicts detected; no rows written:\n- " + "\n- ".join(conflicts)
            )
        if apply:
            session.add_all(insertions["competencies"])
            session.flush()
            session.add_all(insertions["rubrics"])
            session.flush()
            question_rows = cast(list[QuestionBankRow], insertions["questions"])
            base_rows = [row for row in question_rows if row.parent_question_id is None]
            follow_up_rows = [row for row in question_rows if row.parent_question_id is not None]
            session.add_all(base_rows)
            session.flush()
            session.add_all(follow_up_rows)
            session.flush()
            session.commit()
        else:
            session.rollback()
    except Exception:
        session.rollback()
        raise

    return ImportSummary(
        inserted_competencies=len(insertions["competencies"]),
        inserted_rubrics=len(insertions["rubrics"]),
        inserted_questions=len(insertions["questions"]),
        unchanged_competencies=unchanged["competencies"],
        unchanged_rubrics=unchanged["rubrics"],
        unchanged_questions=unchanged["questions"],
        dry_run=not apply,
    )


def _read_pack(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContentImportError(f"Unable to read assessment content pack: {exc}") from exc
    if not isinstance(value, dict):
        raise ContentImportError("Assessment content pack root must be an object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--dry-run", action="store_true")
    modes.add_argument("--apply", action="store_true")
    parser.add_argument("--content-json", type=Path, default=PACK_PATH)
    args = parser.parse_args()
    try:
        content = _read_pack(args.content_json)
        settings = Settings()
        engine = create_engine(settings.database_url, pool_pre_ping=True)
        try:
            with Session(engine) as session:
                result = import_content(session, content, apply=args.apply)
        finally:
            engine.dispose()
    except (ContentImportError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except SQLAlchemyError:
        print("Database import failed; the transaction was rolled back.", file=sys.stderr)
        return 2
    action = "Applied" if args.apply else "Dry-run passed"
    print(
        f"{action}: competencies +{result.inserted_competencies} "
        f"({result.unchanged_competencies} unchanged), rubrics +{result.inserted_rubrics} "
        f"({result.unchanged_rubrics} unchanged), questions +{result.inserted_questions} "
        f"({result.unchanged_questions} unchanged). All imported approvals remain draft."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

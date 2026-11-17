"""Validate the review-only V1 FINXL assessment content JSON."""

from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

STAGES = {"soft_1", "soft_2", "soft_3", "technical_1", "technical_2", "technical_3"}
DIFFICULTIES = {"basic", "intermediate", "advanced"}
QUESTION_CATEGORIES = {"conceptual", "practical", "scenario_based", "analytical", "communication"}
SOURCE_STATUSES = {"source_derived", "source_based_draft", "inferred_draft", "needs_finxl_review"}
APPROVAL_STATUSES = {"draft", "review", "approved", "retired"}
REVIEW_STATUSES = {"pending_finxl_review", "accepted", "rejected"}
COLLECTIONS = {
    "curriculum_modules": "module_id",
    "curriculum_topics": "topic_id",
    "supplemental_source_topics": "source_topic_id",
    "stages": "stage_id",
    "competencies": "competency_id",
    "questions": "question_id",
    "expected_answer_evidence": "evidence_id",
    "rubrics": "rubric_id",
    "follow_up_candidates": "follow_up_id",
    "source_documents": "source_id",
}
REQUIRED_TOP_LEVEL = {
    "schema_version",
    "pack_version",
    "governance",
    "source_documents",
    "curriculum_modules",
    "curriculum_topics",
    "stages",
    "competencies",
    "supplemental_source_topics",
    "questions",
    "expected_answer_evidence",
    "rubrics",
    "follow_up_candidates",
    "coverage_and_gaps",
    "review_approval_register",
}


def validate_content(content: dict[str, Any]) -> list[str]:
    """Return all structural errors without changing or approving content."""
    errors: list[str] = []
    missing = REQUIRED_TOP_LEVEL - content.keys()
    errors.extend(f"missing top-level field: {field}" for field in sorted(missing))
    if content.get("schema_version") != "finxl_assessment_content.v1":
        errors.append("schema_version must be finxl_assessment_content.v1")
    governance = content.get("governance", {})
    if not isinstance(governance, dict):
        errors.append("governance must be an object")
        governance = {}
    if governance.get("production_approved") is not False:
        errors.append("V1 content pack must remain not production-approved")
    if governance.get("approval_status") not in APPROVAL_STATUSES:
        errors.append("invalid governance approval_status")

    rows: dict[str, list[dict[str, Any]]] = {}
    by_id: dict[str, dict[str, dict[str, Any]]] = {}
    for collection, id_field in COLLECTIONS.items():
        value = content.get(collection, [])
        if not isinstance(value, list):
            errors.append(f"{collection} must be an array")
            value = []
        rows[collection] = [item for item in value if isinstance(item, dict)]
        by_id[collection] = {}
        for index, item in enumerate(rows[collection]):
            item_id = item.get(id_field)
            label = f"{collection}[{index}]"
            if not isinstance(item_id, str) or not item_id.strip():
                errors.append(f"{label} missing required {id_field}")
                continue
            if item_id in by_id[collection]:
                errors.append(f"duplicate {id_field}: {item_id}")
            by_id[collection][item_id] = item
            for field in ("source_status", "approval_status", "review_status"):
                if field not in item and collection != "source_documents":
                    errors.append(f"{label} missing required {field}")
            if item.get("source_status") not in SOURCE_STATUSES:
                errors.append(f"{label} has invalid source_status")
            if item.get("approval_status") not in APPROVAL_STATUSES:
                errors.append(f"{label} has invalid approval_status")
            if item.get("approval_status") == "approved":
                errors.append(f"{label} must not be approved in this content-preparation pack")
            if item.get("review_status") not in REVIEW_STATUSES:
                errors.append(f"{label} has invalid review_status")
            if collection != "source_documents" and (
                not isinstance(item.get("source_references"), list) or not item["source_references"]
            ):
                errors.append(f"{label} missing source traceability")

    module_ids = set(by_id["curriculum_modules"])
    curriculum_topic_ids = set(by_id["curriculum_topics"])
    source_topic_ids = set(by_id["supplemental_source_topics"])
    stage_ids = set(by_id["stages"])
    competency_ids = set(by_id["competencies"])
    question_ids = set(by_id["questions"])
    evidence_ids = set(by_id["expected_answer_evidence"])
    rubric_ids = set(by_id["rubrics"])
    source_ids = set(by_id["source_documents"])
    if stage_ids != STAGES:
        errors.append("stages must contain exactly the six existing application stage IDs")

    def check_refs(item: dict[str, Any], label: str) -> None:
        for source in item.get("source_references", []):
            if not isinstance(source, dict):
                errors.append(f"{label} has malformed source reference")
                continue
            if not source.get("source_document") or not source.get("pdf_pages"):
                errors.append(f"{label} source reference requires document and PDF page")
            elif any(not isinstance(page, int) or page < 1 for page in source["pdf_pages"]):
                errors.append(f"{label} source reference has invalid PDF page")
            if source.get("source_status") not in SOURCE_STATUSES:
                errors.append(f"{label} source reference has invalid source_status")
            if not source.get("review_notes"):
                errors.append(f"{label} source reference requires review_notes")
            if source.get("source_document") and not any(
                source["source_document"] == doc.get("file_name")
                for doc in rows["source_documents"]
            ):
                errors.append(
                    f"{label} references unknown source document {source['source_document']}"
                )

    for topic in rows["curriculum_topics"]:
        if topic.get("module_id") not in module_ids:
            errors.append(f"topic {topic.get('topic_id')} references unknown module")
        check_refs(topic, f"topic {topic.get('topic_id')}")
    for topic in rows["supplemental_source_topics"]:
        if topic.get("source_id") not in source_ids:
            errors.append(
                f"supplemental topic {topic.get('source_topic_id')} references unknown source"
            )
        if not topic.get("topic_group") or not topic.get("topic"):
            errors.append(
                f"supplemental topic {topic.get('source_topic_id')} missing group or topic"
            )
        check_refs(topic, f"supplemental topic {topic.get('source_topic_id')}")
    for stage in rows["stages"]:
        for cid in stage.get("competency_ids", []):
            if cid not in competency_ids:
                errors.append(f"stage {stage.get('stage_id')} references unknown competency {cid}")
        for mid in stage.get("curriculum_module_ids", []):
            if mid not in module_ids:
                errors.append(f"stage {stage.get('stage_id')} references unknown module {mid}")
        check_refs(stage, f"stage {stage.get('stage_id')}")
    for competency in rows["competencies"]:
        cid = competency.get("competency_id")
        if not isinstance(competency.get("name"), str) or not competency["name"].strip():
            errors.append(f"competency {cid} missing name")
        for stage_id in competency.get("stage_ids", []):
            if stage_id not in STAGES:
                errors.append(f"competency {cid} has invalid stage {stage_id}")
        for module_id in competency.get("curriculum_module_ids", []):
            if module_id not in module_ids:
                errors.append(f"competency {cid} references unknown module {module_id}")
        for topic_id in competency.get("curriculum_topic_ids", []):
            if topic_id not in curriculum_topic_ids:
                errors.append(f"competency {cid} references unknown curriculum topic {topic_id}")
            elif by_id["curriculum_topics"][topic_id].get("module_id") not in competency.get(
                "curriculum_module_ids", []
            ):
                errors.append(f"competency {cid} topic is outside its mapped curriculum modules")
        for topic_id in competency.get("source_topic_ids", []):
            if topic_id not in source_topic_ids:
                errors.append(f"competency {cid} references unknown supplemental topic {topic_id}")
        check_refs(competency, f"competency {cid}")

    evidence_by_question: dict[str, dict[str, Any]] = {}
    for evidence in rows["expected_answer_evidence"]:
        qid = evidence.get("question_id")
        if qid not in question_ids:
            errors.append(
                f"evidence {evidence.get('evidence_id')} references unknown question {qid}"
            )
        if qid in evidence_by_question:
            errors.append(f"multiple evidence records reference question {qid}")
        if isinstance(qid, str):
            evidence_by_question[qid] = evidence
        if evidence.get("competency_id") not in competency_ids:
            errors.append(f"evidence {evidence.get('evidence_id')} references unknown competency")
        check_refs(evidence, f"evidence {evidence.get('evidence_id')}")

    rubric_by_id = by_id["rubrics"]
    for rubric in rows["rubrics"]:
        rid = rubric.get("rubric_id")
        cid = rubric.get("competency_id")
        if cid not in competency_ids:
            errors.append(f"rubric {rid} references unknown competency {cid}")
        if rubric.get("rubric_version_id") != rid:
            errors.append(f"rubric {rid} rubric_version_id must match stable rubric ID in V1")
        dimensions = rubric.get("dimensions", [])
        keys: set[str] = set()
        weight_total = Decimal(0)
        if not dimensions:
            errors.append(f"rubric {rid} has no dimensions")
        for dim in dimensions:
            key = dim.get("key")
            if not isinstance(key, str) or not key or key in keys:
                errors.append(f"rubric {rid} has missing or duplicate dimension key")
            keys.add(key)
            try:
                weight = Decimal(str(dim.get("weight")))
            except (InvalidOperation, TypeError):
                errors.append(f"rubric {rid} has invalid dimension weight")
                continue
            if not Decimal(0) <= weight <= Decimal(1):
                errors.append(f"rubric {rid} dimension weight must be in [0,1]")
            weight_total += weight
            if not dim.get("performance_indicators"):
                errors.append(f"rubric {rid} dimension {key} has no performance indicators")
        if dimensions and weight_total != Decimal(1):
            errors.append(f"rubric {rid} weights total {weight_total}, expected 1.0")
        scores = [row.get("score") for row in rubric.get("scoring_scale", [])]
        if set(scores) != {0, 1, 2, 3, 4} or len(scores) != 5:
            errors.append(f"rubric {rid} scoring scale must contain scores 0-4 exactly once")
        level_scores = [row.get("score") for row in rubric.get("performance_levels", [])]
        if set(level_scores) != {0, 1, 2, 3, 4} or len(level_scores) != 5:
            errors.append(f"rubric {rid} performance_levels must contain scores 0-4 exactly once")
        for qid in rubric.get("applicable_question_ids", []):
            candidate = by_id["questions"].get(qid) if isinstance(qid, str) else None
            if candidate is None:
                errors.append(f"rubric {rid} references unknown question {qid}")
            elif candidate.get("competency_id") != cid or candidate.get("rubric_id") != rid:
                errors.append(f"rubric {rid} has cross-competency question mapping for {qid}")
        check_refs(rubric, f"rubric {rid}")

    for question_item in rows["questions"]:
        qid = question_item.get("question_id")
        cid = question_item.get("competency_id")
        stage_id = question_item.get("stage_id")
        mapped_competency = by_id["competencies"].get(cid) if isinstance(cid, str) else None
        if not isinstance(question_item.get("text"), str) or not question_item["text"].strip():
            errors.append(f"question {qid} missing text")
        if stage_id not in STAGES:
            errors.append(f"question {qid} has invalid stage {stage_id}")
        if cid not in competency_ids:
            errors.append(f"question {qid} references unknown competency {cid}")
        elif mapped_competency and stage_id not in mapped_competency.get("stage_ids", []):
            errors.append(f"question {qid} stage is not mapped to competency {cid}")
        if question_item.get("difficulty") not in DIFFICULTIES:
            errors.append(f"question_item {qid} has invalid difficulty")
        if question_item.get("question_category") not in QUESTION_CATEGORIES:
            errors.append(f"question_item {qid} has invalid question_item_category")
        if question_item.get("curriculum_module_ids") and any(
            mid not in module_ids for mid in question_item["curriculum_module_ids"]
        ):
            errors.append(f"question {qid} references unknown curriculum module")
        for topic_id in question_item.get("curriculum_topic_ids", []):
            if topic_id not in curriculum_topic_ids:
                errors.append(f"question {qid} references unknown curriculum topic {topic_id}")
            elif by_id["curriculum_topics"][topic_id].get("module_id") not in question_item.get(
                "curriculum_module_ids", []
            ):
                errors.append(f"question {qid} topic is outside its mapped curriculum modules")
        for topic_id in question_item.get("source_topic_ids", []):
            if topic_id not in source_topic_ids:
                errors.append(f"question {qid} references unknown supplemental topic {topic_id}")
        if question_item.get("rubric_id") not in rubric_ids:
            errors.append(f"question {qid} references unknown rubric")
        elif (
            isinstance(question_item.get("rubric_id"), str)
            and rubric_by_id[question_item["rubric_id"]].get("competency_id") != cid
        ):
            errors.append(f"question {qid} competency does not match rubric competency")
        evidence_id = question_item.get("expected_answer_evidence_id")
        if evidence_id not in evidence_ids:
            errors.append(f"question_item {qid} references unknown expected answer evidence")
        elif (
            not isinstance(qid, str)
            or evidence_by_question.get(qid, {}).get("evidence_id") != evidence_id
        ):
            errors.append(f"question_item {qid} evidence relationship is inconsistent")
        if (
            not isinstance(question_item.get("key_concepts_expected"), list)
            or not question_item["key_concepts_expected"]
        ):
            errors.append(f"question {qid} requires key concepts expected")
        check_refs(question_item, f"question {qid}")
    followup_texts: set[str] = set()
    for followup in rows["follow_up_candidates"]:
        fid = followup.get("follow_up_id")
        parent_id = followup.get("parent_question_id")
        parent = by_id["questions"].get(parent_id) if isinstance(parent_id, str) else None
        if parent is None:
            errors.append(f"follow-up {fid} references missing parent question {parent_id}")
        elif followup.get("competency_id") != parent.get("competency_id") or followup.get(
            "stage_id"
        ) != parent.get("stage_id"):
            errors.append(f"follow-up {fid} crosses parent competency or stage")
        if not isinstance(followup.get("text"), str) or not followup["text"].strip():
            errors.append(f"follow-up {fid} missing text")
        elif followup["text"].strip().casefold() in followup_texts:
            errors.append(f"follow-up {fid} duplicates another candidate wording")
        else:
            followup_texts.add(followup["text"].strip().casefold())
        if not followup.get("intended_evidence_gap"):
            errors.append(f"follow-up {fid} missing intended evidence gap")
        check_refs(followup, f"follow-up {fid}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    default_path = (
        Path(__file__).resolve().parents[2]
        / "docs"
        / "assessment-content"
        / "v1"
        / "finxl_assessment_content_v1.json"
    )
    parser.add_argument("content_json", nargs="?", type=Path, default=default_path)
    args = parser.parse_args()
    try:
        data = json.loads(args.content_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Unable to read content JSON: {exc}", file=sys.stderr)
        return 2
    errors = validate_content(data)
    if errors:
        print("Assessment content validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Assessment content validation passed.")
    print(
        f"Stages: {len(data['stages'])}; competencies: {len(data['competencies'])}; questions: {len(data['questions'])}; rubrics: {len(data['rubrics'])}; follow-ups: {len(data['follow_up_candidates'])}."
    )
    print("All records remain draft/pending review; production_approved=false.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

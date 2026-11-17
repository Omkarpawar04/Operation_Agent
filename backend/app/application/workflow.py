from decimal import Decimal
from uuid import UUID

from app.domain.assessments.models import (
    AssessmentResult,
    EvaluationEvidence,
    Rubric,
    RubricDimension,
    calculate_result,
)
from app.ports.llm import AnswerAnalysis, InterviewPrompt


def is_development_placeholder_question(text: str) -> bool:
    lowered = text.casefold()
    return any(
        marker in lowered   
        for marker in (
            "synthetic development question",
            "synthetic-development-fixture",
            "development question placeholder",
            "fixture question",
        )
    )


def rubric_for(
    passing_threshold: float,
    metadata: dict[str, object] | None = None,
    *,
    required: bool = False,
) -> Rubric:
    # This development rubric is explicitly synthetic and is not a validated instrument.
    dimensions: tuple[RubricDimension, ...] = (RubricDimension("communication", Decimal("1")),)
    source_value = metadata.get("rubric") if metadata else None
    if isinstance(source_value, dict):
        source: dict[str, object] = source_value
        dimensions_source = source.get("dimensions")
        if not isinstance(dimensions_source, list):
            raise ValueError("Approved rubric dimensions are not configured")
        dimensions = tuple(
            RubricDimension(str(item["key"]), Decimal(str(item["weight"])))
            for item in dimensions_source
            if isinstance(item, dict) and "key" in item and "weight" in item
        )
        if len(dimensions) != len(dimensions_source):
            raise ValueError("Approved rubric dimensions are malformed")
        version = source.get("version")
        if not isinstance(version, str) or not version:
            raise ValueError("Approved rubric version is not configured")
        return Rubric(
            version,
            dimensions,
            Decimal(str(source.get("passing_threshold", passing_threshold))),
        )
    if required:
        raise ValueError("Approved course rubric is not configured")
    return Rubric("synthetic-development-v1", dimensions, Decimal(str(passing_threshold)))


def prompt_for_question(
    stage: str, sequence: int, course_context: dict[str, object]
) -> InterviewPrompt:
    return InterviewPrompt(
        "Generate one appropriate interview question. Do not claim synthetic topics are approved.",
        {"stage": stage, "sequence": sequence, **course_context},
    )


def analysis_to_evidence(
    analysis: AnswerAnalysis, rubric: Rubric
) -> tuple[EvaluationEvidence, ...]:
    by_key = {item.dimension_key: item for item in analysis.findings}
    if len(by_key) != len(analysis.findings) or set(by_key) != {
        dimension.key for dimension in rubric.dimensions
    }:
        raise ValueError("Provider evidence did not match the configured rubric")
    evidence: list[EvaluationEvidence] = []
    for dimension in rubric.dimensions:
        finding = by_key[dimension.key]
        score = (
            Decimal(finding.relevance + finding.correctness + finding.completeness)
            * Decimal("100")
            / Decimal("12")
        )
        evidence.append(
            EvaluationEvidence(
                dimension_key=dimension.key,
                supporting_evidence=tuple(finding.evidence),
                missing_evidence=tuple(finding.missing_evidence),
                insufficient_evidence=finding.insufficient_evidence,
                confidence=Decimal(str(finding.confidence)),
                score=None if finding.insufficient_evidence else score,
                explanation=finding.explanation,
                relevance=finding.relevance,
                correctness=finding.correctness,
                completeness=finding.completeness,
            )
        )
    return tuple(evidence)


def evaluate(
    attempt_id: UUID, rubric: Rubric, evidence: tuple[EvaluationEvidence, ...]
) -> AssessmentResult:
    return calculate_result(attempt_id, rubric, evidence)


def repeated_question(candidate: str, earlier: tuple[str, ...]) -> bool:
    normalized = set(candidate.casefold().split())
    if not normalized:
        return True
    for previous in earlier:
        prior = set(previous.casefold().split())
        union = normalized | prior
        if normalized == prior or (union and len(normalized & prior) / len(union) >= 0.8):
            return True
    return False


def rubric_prompt(rubric: Rubric, metadata: dict[str, object]) -> dict[str, object]:
    source = metadata.get("rubric")
    definitions = source.get("dimensions", []) if isinstance(source, dict) else []
    by_key = (
        {
            str(item.get("key")): item
            for item in definitions
            if isinstance(item, dict) and isinstance(item.get("key"), str)
        }
        if isinstance(definitions, list)
        else {}
    )
    return {
        "version": rubric.version,
        "passing_threshold": str(rubric.passing_threshold),
        "dimensions": [
            {
                "key": dimension.key,
                "weight": str(dimension.weight),
                "criteria": str(
                    by_key.get(dimension.key, {}).get(
                        "criteria", "Assess relevance, correctness, completeness, and evidence."
                    )
                )[:500],
            }
            for dimension in rubric.dimensions
        ],
    }

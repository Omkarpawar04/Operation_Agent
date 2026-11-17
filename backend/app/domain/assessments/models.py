from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4


class AttemptStatus(StrEnum):
    IN_PROGRESS = "in_progress"
    PASSED = "passed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class RubricDimension:
    key: str
    weight: Decimal

    def __post_init__(self) -> None:
        if not self.key.strip() or not Decimal("0") <= self.weight <= Decimal("1"):
            raise ValueError("Rubric dimension key and weight in [0,1] are required")


@dataclass(frozen=True, slots=True)
class Rubric:
    version: str
    dimensions: tuple[RubricDimension, ...]
    passing_threshold: Decimal = Decimal("50")

    def __post_init__(self) -> None:
        if not self.version or not self.dimensions or len(self.dimensions) > 12:
            raise ValueError("Rubric version and dimensions are required")
        if len({dimension.key for dimension in self.dimensions}) != len(self.dimensions):
            raise ValueError("Rubric dimension keys must be unique")
        if sum((dimension.weight for dimension in self.dimensions), Decimal("0")) != Decimal("1"):
            raise ValueError("Rubric weights must sum exactly to 1")
        if not Decimal("0") <= self.passing_threshold <= Decimal("100"):
            raise ValueError("Passing threshold must be in [0,100]")


@dataclass(frozen=True, slots=True)
class EvaluationEvidence:
    dimension_key: str
    supporting_evidence: tuple[str, ...]
    missing_evidence: tuple[str, ...]
    insufficient_evidence: bool
    confidence: Decimal
    score: Decimal | None
    explanation: str = ""
    relevance: int | None = None
    correctness: int | None = None
    completeness: int | None = None
    root_question_id: UUID | None = None
    dimension_weight: Decimal | None = None

    def __post_init__(self) -> None:
        if not Decimal("0") <= self.confidence <= Decimal("1"):
            raise ValueError("Confidence must be in [0,1]")
        if self.insufficient_evidence and self.score is not None:
            raise ValueError("Insufficient evidence must remain unscored")
        if not self.insufficient_evidence and self.score is None:
            raise ValueError("Sufficient evidence requires a dimension score")
        if self.score is not None and not Decimal("0") <= self.score <= Decimal("100"):
            raise ValueError("Dimension score must be in [0,100]")
        if any(
            value is not None and not 0 <= value <= 4
            for value in (self.relevance, self.correctness, self.completeness)
        ):
            raise ValueError("Evidence ratings must be in [0,4]")
        if len(self.explanation) > 500:
            raise ValueError("Evidence explanation is too long")
        if self.dimension_weight is not None and not (
            Decimal("0") <= self.dimension_weight <= Decimal("1")
        ):
            raise ValueError("Evidence dimension weight must be in [0,1]")


@dataclass(frozen=True, slots=True)
class AssessmentResult:
    attempt_id: UUID
    rubric_version: str
    score: Decimal
    passed: bool
    evidence: tuple[EvaluationEvidence, ...]
    id: UUID = field(default_factory=uuid4)
    completed_at: datetime = field(default_factory=lambda: datetime.now(UTC))


def calculate_result(
    attempt_id: UUID, rubric: Rubric, evidence: tuple[EvaluationEvidence, ...]
) -> AssessmentResult:
    by_key = {item.dimension_key: item for item in evidence}
    keys = {dimension.key for dimension in rubric.dimensions}
    if len(by_key) != len(evidence) or set(by_key) != keys:
        raise ValueError("Evidence must contain exactly one item for every rubric dimension")
    if any(item.insufficient_evidence for item in evidence):
        raise ValueError("Insufficient evidence cannot produce a final assessment result")
    score = Decimal("0")
    for dimension in rubric.dimensions:
        dimension_score = by_key[dimension.key].score
        if dimension_score is None:
            raise ValueError("Insufficient evidence cannot produce a final assessment result")
        score += dimension.weight * dimension_score
    return AssessmentResult(
        attempt_id, rubric.version, score, score >= rubric.passing_threshold, evidence
    )


def calculate_correctness_result(
    attempt_id: UUID,
    rubric: Rubric,
    question_evidence: tuple[tuple[UUID, tuple[EvaluationEvidence, ...]], ...],
) -> AssessmentResult:
    """Score one correctness result per main question; follow-ups share its denominator slot."""
    if not question_evidence or len({question_id for question_id, _ in question_evidence}) != len(
        question_evidence
    ):
        raise ValueError("Every main question must be represented exactly once")
    weighted_points = Decimal("0")
    denominator = Decimal(len(question_evidence) * 4)
    evidence: list[EvaluationEvidence] = [
        item for _, findings in question_evidence for item in findings
    ]
    for _question_id, findings in question_evidence:
        if not findings:
            raise ValueError("Main question has no correctness evidence")
        by_key: dict[str, list[EvaluationEvidence]] = {}
        for finding in findings:
            if finding.correctness is None:
                raise ValueError("Rubric evaluation omitted correctness rating")
            by_key.setdefault(finding.dimension_key, []).append(finding)
        question_points = Decimal("0")
        used_weights = Decimal("0")
        for _dimension_key, items in by_key.items():
            dimension_weight = items[0].dimension_weight
            if dimension_weight is None or any(
                item.dimension_weight != dimension_weight for item in items
            ):
                raise ValueError("Correctness evidence is missing its rubric dimension weight")
            rating = sum(item.correctness or 0 for item in items) / Decimal(len(items))
            question_points += dimension_weight * rating
            used_weights += dimension_weight
        if used_weights != Decimal("1"):
            raise ValueError("Question rubric weights must sum to one")
        weighted_points += question_points
    score = weighted_points * Decimal("100") / denominator
    return AssessmentResult(
        attempt_id,
        rubric.version,
        score,
        score >= rubric.passing_threshold,
        tuple(evidence),
    )

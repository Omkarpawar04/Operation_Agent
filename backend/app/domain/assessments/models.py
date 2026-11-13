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

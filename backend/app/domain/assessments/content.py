from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from app.domain.assessments.models import Rubric, RubricDimension
from app.domain.interviews.models import InterviewStage


class ContentStatus(StrEnum):
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    RETIRED = "retired"


class QuestionCategory(StrEnum):
    BASE = "base"
    FOLLOW_UP = "follow_up"
    CLARIFICATION = "clarification"


@dataclass(frozen=True, slots=True)
class QuestionProvenance:
    provider_name: str | None
    model_identifier: str | None
    generation_type: str
    prompt_schema_version: str
    generated_at: datetime | None
    origin: str
    approval_status: str
    bank_question_id: str | None = None
    competency_id: str | None = None
    rubric_version_id: str | None = None
    content_version: str | None = None
    parent_question_id: str | None = None

    def __post_init__(self) -> None:
        if not self.generation_type or not self.prompt_schema_version or not self.origin:
            raise ValueError("Question provenance requires generation and origin metadata")
        if self.generated_at is not None and self.generated_at.tzinfo is None:
            raise ValueError("Question provenance timestamps must be timezone-aware")

    def to_json(self) -> dict[str, str | None]:
        return {
            "provider_name": self.provider_name,
            "model_identifier": self.model_identifier,
            "generation_type": self.generation_type,
            "prompt_schema_version": self.prompt_schema_version,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
            "origin": self.origin,
            "approval_status": self.approval_status,
            "bank_question_id": self.bank_question_id,
            "competency_id": self.competency_id,
            "rubric_version_id": self.rubric_version_id,
            "content_version": self.content_version,
            "parent_question_id": self.parent_question_id,
        }

    @classmethod
    def from_json(cls, value: dict[str, object] | None) -> QuestionProvenance | None:
        if value is None:
            return None
        required = ("generation_type", "prompt_schema_version", "origin", "approval_status")
        if any(not isinstance(value.get(key), str) or not value[key] for key in required):
            raise ValueError("Stored question provenance is malformed")
        generated = value.get("generated_at")
        if generated is not None and not isinstance(generated, str):
            raise ValueError("Stored question provenance timestamp is malformed")
        optional = (
            "provider_name",
            "model_identifier",
            "bank_question_id",
            "competency_id",
            "rubric_version_id",
            "content_version",
            "parent_question_id",
        )
        if any(
            value.get(key) is not None and not isinstance(value.get(key), str) for key in optional
        ):
            raise ValueError("Stored question provenance fields are malformed")
        return cls(
            provider_name=(
                str(value["provider_name"]) if value.get("provider_name") is not None else None
            ),
            model_identifier=(
                str(value["model_identifier"])
                if value.get("model_identifier") is not None
                else None
            ),
            generation_type=str(value["generation_type"]),
            prompt_schema_version=str(value["prompt_schema_version"]),
            generated_at=datetime.fromisoformat(generated) if generated else None,
            origin=str(value["origin"]),
            approval_status=str(value["approval_status"]),
            bank_question_id=(
                str(value["bank_question_id"])
                if value.get("bank_question_id") is not None
                else None
            ),
            competency_id=(
                str(value["competency_id"]) if value.get("competency_id") is not None else None
            ),
            rubric_version_id=(
                str(value["rubric_version_id"])
                if value.get("rubric_version_id") is not None
                else None
            ),
            content_version=(
                str(value["content_version"]) if value.get("content_version") is not None else None
            ),
            parent_question_id=(
                str(value["parent_question_id"])
                if value.get("parent_question_id") is not None
                else None
            ),
        )


@dataclass(frozen=True, slots=True)
class CompetencyDefinition:
    competency_id: str
    stage: InterviewStage
    title: str
    definition: str
    content_version: str
    status: ContentStatus
    content_source: str
    created_at: datetime
    created_by: str | None = None
    approved_at: datetime | None = None
    approved_by: str | None = None
    stage_ids: tuple[InterviewStage, ...] = ()

    def __post_init__(self) -> None:
        if not all((self.competency_id.strip(), self.title.strip(), self.definition.strip())):
            raise ValueError("Competency ID, title and definition are required")
        if not self.content_version.strip() or not self.content_source.strip():
            raise ValueError("Competency version and source are required")
        if self.status is ContentStatus.APPROVED and (
            self.approved_at is None or not self.approved_by
        ):
            raise ValueError("Approved competency requires approval metadata")


@dataclass(frozen=True, slots=True)
class RubricDefinition:
    rubric_version_id: str
    rubric_id: str
    competency_id: str
    dimensions: tuple[tuple[str, Decimal, tuple[str, ...]], ...]
    scoring_scale: tuple[tuple[int, str], ...]
    evidence_requirements: tuple[str, ...]
    insufficient_evidence_criteria: tuple[str, ...]
    content_version: str
    status: ContentStatus
    content_source: str
    created_at: datetime
    created_by: str | None = None
    approved_at: datetime | None = None
    approved_by: str | None = None

    def __post_init__(self) -> None:
        if not all((self.rubric_version_id, self.rubric_id, self.competency_id)):
            raise ValueError("Rubric and competency references are required")
        if not self.dimensions or sum((item[1] for item in self.dimensions), Decimal(0)) != Decimal(
            1
        ):
            raise ValueError("Rubric dimension weights must be configured and sum to one")
        scale_scores = tuple(score for score, _ in self.scoring_scale)
        if set(scale_scores) != {0, 1, 2, 3, 4} or len(scale_scores) != 5:
            raise ValueError("Rubric scoring scale must match the configured 0–4 evaluator")
        if any(not indicators for _, _, indicators in self.dimensions):
            raise ValueError("Every rubric dimension requires performance indicators")
        if not self.evidence_requirements:
            raise ValueError("Rubric scoring scale and evidence requirements are required")
        if not self.insufficient_evidence_criteria:
            raise ValueError("Insufficient-evidence criteria are required")
        if self.status is ContentStatus.APPROVED and (
            self.approved_at is None or not self.approved_by
        ):
            raise ValueError("Approved rubric requires approval metadata")

    def to_scoring_rubric(self, threshold: float = 50) -> Rubric:
        return Rubric(
            self.rubric_version_id,
            tuple(RubricDimension(key, weight) for key, weight, _ in self.dimensions),
            Decimal(str(threshold)),
        )


@dataclass(frozen=True, slots=True)
class QuestionBankEntry:
    question_id: str
    stage: InterviewStage
    competency_id: str
    text: str
    category: QuestionCategory
    difficulty: str
    expected_answer_characteristics: tuple[str, ...]
    rubric_version_id: str
    content_version: str
    status: ContentStatus
    content_source: str
    created_at: datetime
    created_by: str | None = None
    approved_at: datetime | None = None
    approved_by: str | None = None
    parent_question_id: str | None = None

    def __post_init__(self) -> None:
        if not self.question_id.strip() or not self.text.strip() or len(self.text) > 1000:
            raise ValueError("Question ID and bounded question text are required")
        if not self.competency_id.strip() or not self.rubric_version_id.strip():
            raise ValueError("Question competency and rubric references are required")
        if not self.difficulty.strip() or not self.expected_answer_characteristics:
            raise ValueError("Question difficulty and expected answer characteristics are required")
        if not self.content_version.strip() or not self.content_source.strip():
            raise ValueError("Question content version and source are required")
        if self.status is ContentStatus.APPROVED and (
            self.approved_at is None or not self.approved_by
        ):
            raise ValueError("Approved question requires approval metadata")

from uuid import UUID

from app.domain.assessments.models import (
    AssessmentResult,
    EvaluationEvidence,
    Rubric,
    calculate_result,
)


class EvaluationEngine:
    """Deterministic Python score calculation from structured rubric evidence."""

    def evaluate(
        self, attempt_id: UUID, rubric: Rubric, evidence: tuple[EvaluationEvidence, ...]
    ) -> AssessmentResult:
        return calculate_result(attempt_id, rubric, evidence)

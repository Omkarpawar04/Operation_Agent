from app.domain.assessments.attempts import AssessmentAttempt, AttemptState
from app.domain.assessments.models import (
    AssessmentResult,
    EvaluationEvidence,
    Rubric,
    calculate_result,
)


class AssessmentManager:
    """Finalizes only evidence-complete attempts; provider errors leave them open."""

    def complete(
        self,
        attempt: AssessmentAttempt,
        rubric: Rubric,
        evidence: tuple[EvaluationEvidence, ...],
    ) -> AssessmentResult:
        if attempt.state is not AttemptState.IN_PROGRESS:
            raise ValueError("Completed assessment attempts are immutable")
        result = calculate_result(attempt.id, rubric, evidence)
        attempt.finish(result.passed)
        return result

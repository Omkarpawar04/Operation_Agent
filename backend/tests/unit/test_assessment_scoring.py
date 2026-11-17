from decimal import Decimal
from uuid import uuid4

from app.domain.assessments.models import (
    EvaluationEvidence,
    Rubric,
    RubricDimension,
    calculate_correctness_result,
)


def _evidence(question_id, dimension: str, correctness: int) -> EvaluationEvidence:
    return EvaluationEvidence(
        dimension_key=dimension,
        supporting_evidence=("evidence",),
        missing_evidence=(),
        insufficient_evidence=False,
        confidence=Decimal("1"),
        score=Decimal(correctness * 25),
        correctness=correctness,
        root_question_id=question_id,
        dimension_weight=Decimal("0.5"),
    )


def test_correctness_score_passes_at_exactly_fifty_percent() -> None:
    question_id = uuid4()
    rubric = Rubric(
        "rubric-v1",
        (
            RubricDimension("accuracy", Decimal("0.5")),
            RubricDimension("reasoning", Decimal("0.5")),
        ),
    )
    result = calculate_correctness_result(
        uuid4(),
        rubric,
        (
            (
                question_id,
                (_evidence(question_id, "accuracy", 2), _evidence(question_id, "reasoning", 2)),
            ),
        ),
    )
    assert result.score == Decimal("50")
    assert result.passed is True


def test_follow_up_evidence_is_averaged_into_parent_and_skip_counts_zero() -> None:
    answered_id = uuid4()
    skipped_id = uuid4()
    rubric = Rubric(
        "rubric-v1",
        (
            RubricDimension("accuracy", Decimal("0.5")),
            RubricDimension("reasoning", Decimal("0.5")),
        ),
    )
    parent_findings = (
        _evidence(answered_id, "accuracy", 1),
        _evidence(answered_id, "reasoning", 1),
        _evidence(answered_id, "accuracy", 3),
        _evidence(answered_id, "reasoning", 3),
    )
    skipped_findings = (
        _evidence(skipped_id, "accuracy", 0),
        _evidence(skipped_id, "reasoning", 0),
    )
    result = calculate_correctness_result(
        uuid4(), rubric, ((answered_id, parent_findings), (skipped_id, skipped_findings))
    )
    assert result.score == Decimal("25")
    assert result.passed is False


def test_duplicate_main_question_in_stage_score_is_rejected() -> None:
    question_id = uuid4()
    rubric = Rubric("rubric-v1", (RubricDimension("accuracy", Decimal("1")),))
    finding = _evidence(question_id, "accuracy", 4)
    try:
        calculate_correctness_result(
            uuid4(), rubric, ((question_id, (finding,)), (question_id, (finding,)))
        )
    except ValueError as error:
        assert "exactly once" in str(error)
    else:
        raise AssertionError("Duplicate question was included in the denominator")

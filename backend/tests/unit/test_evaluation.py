from dataclasses import FrozenInstanceError
from decimal import Decimal as D
from uuid import uuid4

import pytest

from app.domain.assessments.models import (
    EvaluationEvidence,
    Rubric,
    RubricDimension,
    calculate_result,
)


def rubric(threshold: str = "50") -> Rubric:
    return Rubric(
        "v1",
        (RubricDimension("clarity", D("0.5")), RubricDimension("reasoning", D("0.5"))),
        D(threshold),
    )


def evidence(score: str, insufficient: bool = False) -> tuple[EvaluationEvidence, ...]:
    val = D(score)
    if insufficient:
        val = None
    return (
        EvaluationEvidence("clarity", ("example",) if val else (), (), insufficient, D("0.8"), val),
        EvaluationEvidence("reasoning", ("steps",) if val else (), (), insufficient, D("0.7"), val),
    )


@pytest.mark.parametrize("score,passed", [("49.99", False), ("50", True), ("50.01", True)])
def test_pass_threshold_inclusive(score: str, passed: bool) -> None:
    assert calculate_result(uuid4(), rubric(), evidence(score)).passed is passed


@pytest.mark.parametrize("weights", [(D("0.4"), D("0.4")), (D("1.1"), D("-0.1"))])
def test_invalid_rubric_weights_rejected(weights: tuple[D, D]) -> None:
    with pytest.raises(ValueError):
        Rubric("bad", (RubricDimension("a", weights[0]), RubricDimension("b", weights[1])))


def test_insufficient_evidence_cannot_become_a_final_result() -> None:
    with pytest.raises(ValueError, match="Insufficient evidence"):
        calculate_result(uuid4(), rubric(), evidence("0", True))


def test_evidence_must_cover_all_dimensions_once() -> None:
    with pytest.raises(ValueError, match="exactly one"):
        calculate_result(uuid4(), rubric(), evidence("50")[:1])


def test_assessment_result_is_immutable() -> None:
    result = calculate_result(uuid4(), rubric(), evidence("75"))
    with pytest.raises(FrozenInstanceError):
        result.passed = False


def test_duplicate_rubric_dimensions_are_rejected() -> None:
    with pytest.raises(ValueError, match="unique"):
        Rubric(
            "v1",
            (RubricDimension("clarity", D("0.5")), RubricDimension("clarity", D("0.5"))),
        )

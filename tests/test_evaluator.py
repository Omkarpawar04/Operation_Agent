
"""
Tests for the Interview Evaluator Agent.

Uses a fake OpenAI client to avoid real API requests.
"""

import json
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from agents.evaluator import (
    InterviewEvaluator,
    InterviewEvaluation,
    Recommendation,
)


# --------------------------------------------------
# MOCK OPENAI CLIENT
# --------------------------------------------------

class FakeResponses:
    def __init__(self, responses):
        self.responses = responses
        self.call_count = 0

    async def create(self, **kwargs):
        self.call_count += 1
        return SimpleNamespace(
            output_text=self.responses.pop(0)
        )


class FakeOpenAIClient:
    def __init__(self, responses):
        self.responses = FakeResponses(responses)


# --------------------------------------------------
# SAMPLE EVALUATION
# --------------------------------------------------

def create_valid_evaluation():
    return {
        "overall_score": 8.05,
        "technical_depth": {
            "score": 8,
            "evidence": [
                "Explained compound interest correctly."
            ],
        },
        "communication": {
            "score": 7,
            "evidence": [
                "Explained concepts clearly."
            ],
        },
        "problem_solving": {
            "score": 9,
            "evidence": [
                "Demonstrated structured reasoning."
            ],
        },
        "culture_fit": {
            "score": 8,
            "evidence": [
                "Showed willingness to learn and collaborate."
            ],
        },
        "strengths": [
            "Strong financial fundamentals.",
            "Good analytical reasoning.",
            "Willingness to learn.",
        ],
        "concerns": [
            "Could provide more detailed examples.",
            "Needs more practical industry exposure.",
        ],
        "recommendation": "advance",
        "summary": (
        "The candidate demonstrated a solid foundation in financial "
        "concepts and explained compound interest with a generally "
        "correct understanding of principal and accumulated interest. "
        "Their response showed awareness of how interest can grow "
        "over time, although the explanation would be stronger with "
        "a practical numerical example. Communication was "
        "understandable and reasonably focused, but the candidate "
        "could organize answers more clearly and provide additional "
        "context when explaining technical ideas. The available "
        "response offers limited evidence about broader financial "
        "analysis skills, so further questions would be useful before "
        "making a final decision. The candidate showed a promising "
        "ability to understand a core finance concept and communicate "
        "the central idea without introducing major inaccuracies. "
        "Problem-solving ability and collaboration were not fully "
        "demonstrated in this short exchange, and those areas should "
        "be explored in a longer interview. For an entry-level "
        "opportunity, the demonstrated knowledge is encouraging, "
        "while practical application remains an area for development. "
        "Overall, the candidate appears to have a useful starting "
        "foundation and potential to improve with experience, "
        "feedback, and exposure to realistic financial tasks. The "
        "recommendation is to continue the assessment and gather "
        "more evidence across the remaining interview dimensions."
        ),

    }


# --------------------------------------------------
# TEST 1: VALID EVALUATION
# --------------------------------------------------

@pytest.mark.asyncio
async def test_evaluate_interview():

    valid_evaluation = create_valid_evaluation()

    fake_client = FakeOpenAIClient([
        json.dumps(valid_evaluation)
    ])

    evaluator = InterviewEvaluator(
        client=fake_client
    )

    result = await evaluator.evaluate_interview(
        conversation_history=[
            {
                "role": "assistant",
                "content": "What is compound interest?",
            },
            {
                "role": "user",
                "content": (
                    "Interest earned on the principal "
                    "and accumulated interest."
                ),
            },
        ],
        interview_plan={
            "total_questions": 1,
            "questions": [],
        },
    )

    assert isinstance(result, InterviewEvaluation)

    assert result.recommendation == Recommendation.ADVANCE

    assert result.technical_depth.score == 8

    assert fake_client.responses.call_count == 1


# --------------------------------------------------
# TEST 2: WEIGHTED OVERALL SCORE
# --------------------------------------------------

def test_calculate_weighted_overall_score():

    evaluation = InterviewEvaluation.model_validate(
        create_valid_evaluation()
    )

    score = InterviewEvaluator.calculate_overall_score(
        evaluation
    )

    assert score == 8.05


# --------------------------------------------------
# TEST 3: INVALID SUMMARY LENGTH
# --------------------------------------------------

def test_reject_short_summary():

    data = create_valid_evaluation()

    data["summary"] = "This is too short."

    with pytest.raises(ValidationError):
        InterviewEvaluation.model_validate(data)


# --------------------------------------------------
# TEST 4: INVALID RECOMMENDATION
# --------------------------------------------------

def test_reject_invalid_recommendation():

    data = create_valid_evaluation()

    data["recommendation"] = "maybe"

    with pytest.raises(ValidationError):
        InterviewEvaluation.model_validate(data)


# --------------------------------------------------
# TEST 5: INVALID SCORE
# --------------------------------------------------

def test_reject_score_outside_range():

    data = create_valid_evaluation()

    data["technical_depth"]["score"] = 15

    with pytest.raises(ValidationError):
        InterviewEvaluation.model_validate(data)

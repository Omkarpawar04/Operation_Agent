
"""
Tests for the Interview Planner Agent.

These tests use a fake OpenAI client, so they do not
require an API key or make real API requests.
"""

import json
from types import SimpleNamespace

import pytest

from agents.planner import InterviewPlanner, PlannerRateLimitError


# --------------------------------------------------
# MOCK OPENAI CLIENT
# --------------------------------------------------

class FakeResponses:
    """Simulates OpenAI Responses API calls."""

    def __init__(self, responses):
        self.responses = responses
        self.call_count = 0

    async def create(self, **kwargs):
        self.call_count += 1

        output_text = self.responses.pop(0)

        return SimpleNamespace(
            output_text=output_text
        )


class FakeOpenAIClient:
    """Fake OpenAI client for testing."""

    def __init__(self, responses):
        self.responses = FakeResponses(responses)


# --------------------------------------------------
# SAMPLE VALID INTERVIEW PLAN
# --------------------------------------------------

def create_valid_plan():
    """Return a valid eight-question interview plan."""

    questions = [
        {
            "id": 1,
            "category": "warmup",
            "question": "Tell me about yourself and your background.",
            "difficulty": "easy",
            "evaluation_objective": "Understand the candidate's background.",
            "skills_tested": ["Communication"],
            "followup_topics": ["Education"],
            "expected_answer_indicators": ["Clear introduction"],
        },
        {
            "id": 2,
            "category": "technical",
            "question": "Explain the difference between stocks and bonds.",
            "difficulty": "easy",
            "evaluation_objective": "Test financial fundamentals.",
            "skills_tested": ["Financial knowledge"],
            "followup_topics": ["Investment risk"],
            "expected_answer_indicators": ["Ownership versus debt"],
        },
        {
            "id": 3,
            "category": "technical",
            "question": "How does compound interest work?",
            "difficulty": "medium",
            "evaluation_objective": "Test understanding of interest.",
            "skills_tested": ["Financial mathematics"],
            "followup_topics": ["Compounding frequency"],
            "expected_answer_indicators": ["Interest on accumulated interest"],
        },
        {
            "id": 4,
            "category": "project",
            "question": "Describe a project you have completed.",
            "difficulty": "medium",
            "evaluation_objective": "Understand practical experience.",
            "skills_tested": ["Project management"],
            "followup_topics": ["Challenges"],
            "expected_answer_indicators": ["Clear project explanation"],
        },
        {
            "id": 5,
            "category": "behavioral",
            "question": "Tell me about a difficult problem you solved.",
            "difficulty": "medium",
            "evaluation_objective": "Evaluate problem-solving.",
            "skills_tested": ["Problem-solving"],
            "followup_topics": ["Decision-making"],
            "expected_answer_indicators": ["Structured reasoning"],
        },
        {
            "id": 6,
            "category": "situational",
            "question": "How would you handle an approaching deadline?",
            "difficulty": "medium",
            "evaluation_objective": "Evaluate time management.",
            "skills_tested": ["Time management"],
            "followup_topics": ["Prioritization"],
            "expected_answer_indicators": ["Practical action plan"],
        },
        {
            "id": 7,
            "category": "technical",
            "question": "How would you diagnose a slow database query?",
            "difficulty": "hard",
            "evaluation_objective": "Assess technical diagnosis.",
            "skills_tested": ["Database performance"],
            "followup_topics": ["Indexes and query plans"],
            "expected_answer_indicators": ["Evidence-based debugging"],
        },
        {
            "id": 8,
            "category": "behavioral",
            "question": "Describe a time you received difficult feedback.",
            "difficulty": "medium",
            "evaluation_objective": "Assess professional growth.",
            "skills_tested": ["Adaptability"],
            "followup_topics": ["Outcome"],
            "expected_answer_indicators": ["Specific response to feedback"],
        },
    ]

    return {
        "candidate_profile": {
            "name": "Test Candidate",
            "experience_level": "fresher",
            "skills": ["Python", "Finance"],
            "projects": ["Financial Analysis Project"],
            "education": ["Bachelor's Degree"],
        },
        "job_profile": {
            "job_title": "Financial Analyst",
            "must_have_skills": ["Financial analysis"],
            "good_to_have_skills": ["Python"],
            "key_responsibilities": ["Analyze financial data"],
        },
        "interview_plan": {
            "total_questions": 8,
            "questions": questions,
            "closing_prompt": "Do you have any questions for us?",
        },
    }


# --------------------------------------------------
# TEST 1: SUCCESSFUL PLAN GENERATION
# --------------------------------------------------

@pytest.mark.asyncio
async def test_generate_valid_interview_plan():

    valid_plan = create_valid_plan()

    fake_client = FakeOpenAIClient([
        json.dumps(valid_plan)
    ])

    planner = InterviewPlanner(
        client=fake_client
    )

    result = await planner.generate_plan(
        resume_text=(
            "Recent graduate with Python and finance knowledge."
        ),
        job_description=(
            "Looking for a fresher financial analyst."
        ),
    )

    assert result is not None

    assert result.interview_plan.total_questions == 8

    assert len(result.interview_plan.questions) == 8

    question_ids = [
        question.id
        for question in result.interview_plan.questions
    ]

    assert question_ids == list(range(1, 9))

    assert result.job_profile.job_title == "Financial Analyst"

    assert fake_client.responses.call_count == 1


# --------------------------------------------------
# TEST 2: RETRY AFTER INVALID AI RESPONSE
# --------------------------------------------------

@pytest.mark.asyncio
async def test_planner_retries_after_invalid_response():

    valid_plan = create_valid_plan()

    fake_client = FakeOpenAIClient([
        "This is not valid JSON",
        json.dumps(valid_plan),
    ])

    planner = InterviewPlanner(
        client=fake_client
    )

    result = await planner.generate_plan(
        resume_text="Graduate with financial knowledge.",
        job_description="Entry-level financial analyst role.",
    )

    assert result is not None

    assert result.interview_plan.total_questions == 8

    assert fake_client.responses.call_count == 2


@pytest.mark.asyncio
async def test_planner_surfaces_rate_limit_without_retry():
    class RateLimitedResponses:
        call_count = 0

        async def create(self, **kwargs):
            self.call_count += 1
            error = RuntimeError("quota exhausted")
            error.status_code = 429
            raise error

    class RateLimitedClient:
        def __init__(self):
            self.responses = RateLimitedResponses()

    client = RateLimitedClient()
    planner = InterviewPlanner(client=client)

    with pytest.raises(PlannerRateLimitError, match="token quota"):
        await planner.generate_plan(
            resume_text="Python engineer.",
            job_description="Python backend engineer.",
        )

    assert client.responses.call_count == 1


@pytest.mark.asyncio
async def test_planner_reports_groq_retry_delay():
    class RateLimitedResponses:
        async def create(self, **kwargs):
            error = RuntimeError(
                "TPD exhausted. Please try again in 9m1.728s."
            )
            error.status_code = 429
            raise error

    class RateLimitedClient:
        responses = RateLimitedResponses()

    planner = InterviewPlanner(client=RateLimitedClient())

    with pytest.raises(PlannerRateLimitError) as error:
        await planner.generate_plan(
            resume_text="Python engineer.",
            job_description="Python backend engineer.",
        )

    assert "9 minutes and 2 seconds" in str(error.value)

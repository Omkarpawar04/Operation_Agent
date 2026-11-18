
"""
Interview Planner Agent.

Responsibilities:
- Analyse candidate resume and job description.
- Generate personalized interview questions using Groq.
- Validate the generated interview plan.
- Retry once if the AI response is invalid.
"""

import json
import math
import re
from pathlib import Path
from typing import Any, Literal

from pydantic import (
    BaseModel,
    Field,
    ValidationError,
    model_validator,
)

from config import settings
from agents.groq_client import get_groq_client


# --------------------------------------------------
# PROMPT CONFIGURATION
# --------------------------------------------------

PROMPT_PATH = (
    Path(__file__).resolve().parent.parent
    / "prompts"
    / "planner_system.txt"
)


def load_planner_prompt() -> str:
    """Load the planner system prompt."""

    if not PROMPT_PATH.exists():
        raise FileNotFoundError(
            f"Planner prompt not found: {PROMPT_PATH}"
        )

    return PROMPT_PATH.read_text(encoding="utf-8")


# --------------------------------------------------
# PYDANTIC MODELS
# --------------------------------------------------

class CandidateProfile(BaseModel):
    name: str | None = None
    experience_level: str
    skills: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)
    education: list[str] = Field(default_factory=list)


class JobProfile(BaseModel):
    job_title: str
    must_have_skills: list[str] = Field(default_factory=list)
    good_to_have_skills: list[str] = Field(default_factory=list)
    key_responsibilities: list[str] = Field(default_factory=list)


class InterviewQuestion(BaseModel):
    id: int = Field(gt=0)

    category: Literal[
        "warmup",
        "technical",
        "project",
        "behavioral",
        "situational",
    ]

    question: str = Field(min_length=5)

    difficulty: Literal["easy", "medium", "hard"]

    evaluation_objective: str

    skills_tested: list[str] = Field(default_factory=list)
    followup_topics: list[str] = Field(default_factory=list)

    expected_answer_indicators: list[str] = Field(
        default_factory=list
    )


class InterviewPlan(BaseModel):
    total_questions: int = Field(ge=8, le=10)
    questions: list[InterviewQuestion]
    closing_prompt: str

    @model_validator(mode="after")
    def validate_question_count_and_ids(self):

        if len(self.questions) != self.total_questions:
            raise ValueError(
                "total_questions must match the actual number "
                "of questions"
            )

        if not 8 <= len(self.questions) <= 10:
            raise ValueError(
                "Interview plan must contain 8 to 10 questions"
            )

        expected_ids = list(range(1, len(self.questions) + 1))

        actual_ids = [
            question.id for question in self.questions
        ]

        if actual_ids != expected_ids:
            raise ValueError(
                "Question IDs must be sequential starting from 1"
            )

        question_texts = [
            question.question.strip().lower()
            for question in self.questions
        ]

        if len(question_texts) != len(set(question_texts)):
            raise ValueError(
                "Duplicate interview questions detected"
            )

        return self


class PlannerResponse(BaseModel):
    candidate_profile: CandidateProfile
    job_profile: JobProfile
    interview_plan: InterviewPlan


# --------------------------------------------------
# CUSTOM EXCEPTION
# --------------------------------------------------

class PlannerError(Exception):
    """Raised when interview plan generation fails."""


class PlannerRateLimitError(PlannerError):
    """Raised when Groq temporarily rejects planning due to its quota."""


def _retry_delay_seconds(error: Exception) -> int | None:
    """Read the retry delay from Groq headers or its rate-limit message."""
    response = getattr(error, "response", None)
    headers = getattr(response, "headers", {}) or {}

    for header_name in ("retry-after", "x-ratelimit-reset-tokens"):
        value = headers.get(header_name)
        if value:
            try:
                return max(1, math.ceil(float(value)))
            except (TypeError, ValueError):
                duration = re.fullmatch(
                    r"\s*(?:(\d+(?:\.\d+)?)m)?\s*(\d+(?:\.\d+)?)s\s*",
                    str(value),
                    re.IGNORECASE,
                )
                if duration:
                    minutes = float(duration.group(1) or 0)
                    seconds = float(duration.group(2))
                    return max(1, math.ceil(minutes * 60 + seconds))

    match = re.search(
        r"Please try again in\s+(?:(\d+(?:\.\d+)?)m)?\s*(\d+(?:\.\d+)?)s",
        str(error),
        re.IGNORECASE,
    )
    if not match:
        return None

    minutes = float(match.group(1) or 0)
    seconds = float(match.group(2))
    return max(1, math.ceil(minutes * 60 + seconds))


def _format_retry_delay(seconds: int) -> str:
    minutes, remainder = divmod(seconds, 60)
    if minutes and remainder:
        return f"{minutes} minutes and {remainder} seconds"
    if minutes:
        return f"{minutes} minutes"
    return f"{remainder} seconds"


# --------------------------------------------------
# PLANNER AGENT
# --------------------------------------------------

class InterviewPlanner:

    def __init__(self, client: Any | None = None):

        # Optional injected client keeps unit tests independent
        # of the actual Groq API.
        self.client = client

        # Groq is our primary text-generation provider.
        self.model = settings.groq_text_model

        self.system_prompt = load_planner_prompt()

    def _get_client(self) -> Any:
        """Return the injected client or initialize Groq lazily."""

        if self.client is not None:
            return self.client
        try:
            return get_groq_client()
        except RuntimeError as exc:
            raise PlannerError(str(exc)) from exc

    async def generate_plan(
        self,
        resume_text: str,
        job_description: str,
    ) -> PlannerResponse:

        if not resume_text.strip():
            raise ValueError("Resume text cannot be empty")

        if not job_description.strip():
            raise ValueError("Job description cannot be empty")

        # Initialize the Groq client only when needed.
        client = self._get_client()

        user_input = f"""
Analyse the following candidate resume and job description.

CANDIDATE RESUME:
{resume_text}

JOB DESCRIPTION:
{job_description}

Return the personalized interview plan in the exact
JSON structure specified in your instructions.
"""

        validation_feedback = ""

        # Initial attempt + one retry.
        for attempt in range(2):

            current_input = user_input

            if validation_feedback:
                current_input += f"""

IMPORTANT CORRECTION:
Your previous response failed validation.

Validation errors:
{validation_feedback}

Generate a corrected JSON response.
Follow every required field and validation rule.
"""

            try:
                response = await client.responses.create(
                    model=self.model,
                    instructions=self.system_prompt,
                    input=current_input,
                    text={
                        "format": {
                            "type": "json_object"
                        }
                    },
                    max_output_tokens=5000,
                )

                raw_output = response.output_text

                if not raw_output:
                    raise ValueError(
                        "AI returned an empty response"
                    )

                parsed_json = json.loads(raw_output)

                validated_plan = PlannerResponse.model_validate(
                    parsed_json
                )

                return validated_plan

            except (
                json.JSONDecodeError,
                ValidationError,
                ValueError,
            ) as error:

                validation_feedback = str(error)

                if attempt == 0:
                    continue

                raise PlannerError(
                    "Unable to generate a valid interview plan "
                    "after two attempts."
                ) from error

            except Exception as error:

                if getattr(error, "status_code", None) == 429:
                    retry_seconds = _retry_delay_seconds(error)
                    retry_message = (
                        f" Please try again in about {_format_retry_delay(retry_seconds)}."
                        if retry_seconds is not None
                        else " Please try again after the Groq quota resets."
                    )
                    raise PlannerRateLimitError(
                        "Groq's token quota is temporarily exhausted."
                        + retry_message
                    ) from error

                raise PlannerError(
                    f"Interview planning API failed: {error}"
                ) from error

        raise PlannerError(
            "Interview plan generation failed."
        )


# --------------------------------------------------
# CONVENIENCE FUNCTION
# --------------------------------------------------

async def generate_interview_plan(
    resume_text: str,
    job_description: str,
) -> PlannerResponse:

    planner = InterviewPlanner()

    return await planner.generate_plan(
        resume_text=resume_text,
        job_description=job_description,
    )

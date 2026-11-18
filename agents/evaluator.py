
"""
AI Interview Evaluator.

Evaluates completed interviews using Groq.

Provides evidence-based scoring, strengths, concerns,
a hiring recommendation, and a validated summary.
"""

import json
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import (
    BaseModel,
    Field,
    ValidationError,
    field_validator,
)

from config import settings
from agents.groq_client import get_groq_client


# --------------------------------------------------
# CUSTOM EXCEPTION
# --------------------------------------------------

class EvaluatorError(Exception):
    """Raised when interview evaluation fails."""


# --------------------------------------------------
# ENUMS
# --------------------------------------------------

class Recommendation(str, Enum):
    ADVANCE = "advance"
    HOLD = "hold"
    REJECT = "reject"


# --------------------------------------------------
# EVALUATION MODELS
# --------------------------------------------------

class DimensionScore(BaseModel):
    """Score and supporting evidence for one dimension."""

    score: float = Field(ge=0, le=10)
    evidence: list[str] = Field(min_length=1)


class InterviewEvaluation(BaseModel):
    """Complete candidate evaluation report."""

    overall_score: float = Field(ge=0, le=10)

    technical_depth: DimensionScore
    communication: DimensionScore
    problem_solving: DimensionScore
    culture_fit: DimensionScore

    strengths: list[str] = Field(
        min_length=3,
        max_length=5,
    )

    concerns: list[str] = Field(
        min_length=2,
        max_length=4,
    )

    recommendation: Recommendation

    summary: str

    @field_validator("summary")
    @classmethod
    def validate_summary_length(cls, value: str) -> str:
        """Ensure the summary contains 150-200 words."""

        value = value.strip()
        word_count = len(value.split())

        if not 150 <= word_count <= 200:
            raise ValueError(
                f"Evaluation summary contains {word_count} words. "
                "It must contain between 150 and 200 words. "
                "Aim for 170-180 words."
            )

        return value


# --------------------------------------------------
# INTERVIEW EVALUATOR AGENT
# --------------------------------------------------

class InterviewEvaluator:
    """Evaluates completed interviews using Groq."""

    WEIGHTS = {
        "technical_depth": 0.40,
        "communication": 0.20,
        "problem_solving": 0.25,
        "culture_fit": 0.15,
    }

    def __init__(
        self,
        client: Any | None = None,
        model: str | None = None,
    ):
        self.model = model or settings.groq_text_model
        self.client = client

        prompt_path = (
            Path(__file__).resolve().parent.parent
            / "prompts"
            / "evaluator_system.txt"
        )

        try:
            self.system_prompt = prompt_path.read_text(
                encoding="utf-8"
            )
        except OSError as exc:
            raise EvaluatorError(
                f"Could not load evaluator prompt: {exc}"
            ) from exc

    # --------------------------------------------------
    # GROQ CLIENT
    # --------------------------------------------------

    def _get_client(self) -> Any:
        """Return injected client or initialize Groq."""

        if self.client is not None:
            return self.client
        try:
            return get_groq_client()
        except RuntimeError as exc:
            raise EvaluatorError(str(exc)) from exc

    # --------------------------------------------------
    # MAIN EVALUATION
    # --------------------------------------------------

    async def evaluate_interview(
        self,
        conversation_history: list[dict[str, Any]],
        interview_plan: dict[str, Any],
        candidate_profile: dict[str, Any] | None = None,
        job_profile: dict[str, Any] | None = None,
    ) -> InterviewEvaluation:
        """Evaluate the complete interview transcript."""

        if not conversation_history:
            raise ValueError(
                "Conversation history cannot be empty."
            )

        if not interview_plan:
            raise ValueError(
                "Interview plan cannot be empty."
            )

        client = self._get_client()

        context = {
            "candidate_profile": candidate_profile or {},
            "job_profile": job_profile or {},
            "interview_plan": interview_plan,
            "conversation_history": conversation_history,
            "scoring_weights": self.WEIGHTS,
        }

        instructions = self.system_prompt + """

ADDITIONAL EVALUATION RULES:

1. Evaluate only information supported by the transcript.
2. Never invent candidate achievements or experience.
3. Give evidence for every scoring dimension.
4. Use scores between 0 and 10.
5. Consider candidate experience and job requirements.
6. Do not penalize reasonable clarifying questions.
7. Do not confuse speaking fluency with technical competence.
8. Avoid personal or demographic bias.
9. Evaluate problem-solving using demonstrated reasoning.
10. Keep strengths and concerns specific and evidence-based.

SUMMARY REQUIREMENT:

The summary MUST contain between 150 and 200 words.
Aim for 170-180 words.
Count the words before returning the JSON.
Do not shorten the summary to a few sentences.

SCORING WEIGHTS:

Technical depth: 40%
Communication: 20%
Problem-solving: 25%
Culture fit: 15%

Calculate overall_score using these weights.

Return exactly the JSON structure specified in the system prompt.
Return valid JSON only.
"""

        user_input = (
            "Evaluate the following completed interview:\n\n"
            + json.dumps(
                context,
                ensure_ascii=False,
                default=str,
            )
        )

        last_error = None

        # Initial attempt + one correction attempt.
        for attempt in range(2):

            try:
                response = await client.responses.create(
                    model=self.model,
                    instructions=instructions,
                    input=user_input,
                    text={
                        "format": {
                            "type": "json_object"
                        }
                    },
                    max_output_tokens=3000,
                )

                response_text = response.output_text

                if not response_text:
                    raise EvaluatorError(
                        "The AI returned an empty evaluation."
                    )

                evaluation = self._parse_evaluation(
                    response_text
                )

                # Always calculate the authoritative score locally.
                evaluation.overall_score = (
                    self.calculate_overall_score(evaluation)
                )

                return evaluation

            except (
                EvaluatorError,
                ValidationError,
                ValueError,
            ) as exc:

                last_error = exc

                if attempt == 0:
                    instructions += f"""

YOUR PREVIOUS RESPONSE FAILED VALIDATION.

Validation error:
{last_error}

Correct the specific validation error.

IMPORTANT:
- Keep all four evaluation dimensions.
- Every score must be between 0 and 10.
- Keep strengths between 3 and 5 items.
- Keep concerns between 2 and 4 items.
- Summary MUST contain 150-200 words.
- Aim for 170-180 words.
- Count the summary words before returning.
- Do not remove required fields.
- Do not invent candidate information.

Return the complete corrected JSON object only.
"""

        raise EvaluatorError(
            f"Could not generate a valid evaluation: {last_error}"
        ) from last_error

    # --------------------------------------------------
    # JSON PARSING
    # --------------------------------------------------

    @staticmethod
    def _parse_evaluation(
        response_text: str,
    ) -> InterviewEvaluation:
        """Parse and validate the AI-generated JSON."""

        try:
            data = json.loads(response_text)

            return InterviewEvaluation.model_validate(data)

        except (json.JSONDecodeError, ValidationError) as exc:

            raise EvaluatorError(
                f"Invalid evaluation response: {exc}"
            ) from exc

    # --------------------------------------------------
    # WEIGHTED SCORE
    # --------------------------------------------------

    @classmethod
    def calculate_overall_score(
        cls,
        evaluation: InterviewEvaluation,
    ) -> float:
        """Calculate the weighted overall score."""

        score = (
            evaluation.technical_depth.score
            * cls.WEIGHTS["technical_depth"]

            + evaluation.communication.score
            * cls.WEIGHTS["communication"]

            + evaluation.problem_solving.score
            * cls.WEIGHTS["problem_solving"]

            + evaluation.culture_fit.score
            * cls.WEIGHTS["culture_fit"]
        )

        return round(score, 2)


# --------------------------------------------------
# SHARED EVALUATOR INSTANCE
# --------------------------------------------------

evaluator = InterviewEvaluator()

from app.application.workflow import (
    analysis_to_evidence,
    is_development_placeholder_question,
    repeated_question,
)
from app.domain.assessments.content import ContentStatus, QuestionBankEntry
from app.domain.assessments.models import EvaluationEvidence, Rubric
from app.ports.llm import AnswerAnalysis, GeneratedQuestion, InterviewPrompt, LLMProvider


class InvalidProviderOutput(ValueError):
    """Provider output is structurally valid but unsuitable for the current interview."""

    def __init__(self, message: str, category: str = "unsuitable") -> None:
        super().__init__(message)
        self.category = category


class InterviewContextManager:
    """Builds bounded prompts with student content explicitly represented as untrusted data."""

    def build(
        self,
        task: str,
        context: dict[str, object],
        history: tuple[str, ...] = (),
    ) -> InterviewPrompt:
        bounded = {key: value for key, value in context.items() if key != "answer_history"}
        bounded["answer_history"] = [answer[:1000] for answer in history[-8:]]
        return InterviewPrompt(task, bounded)


class QuestionGenerationEngine:
    def generate(
        self,
        provider: LLMProvider,
        prompt: InterviewPrompt,
        history: tuple[str, ...],
        allowed_topics: tuple[str, ...] = (),
    ) -> GeneratedQuestion:
        question = provider.generate_question(prompt)
        if is_development_placeholder_question(question.text):
            raise InvalidProviderOutput("Question provider returned development fixture content")
        if len(question.text.split()) < 5 or repeated_question(question.text, history):
            raise InvalidProviderOutput("Generated question is too short or repetitive")
        if allowed_topics and question.topic not in allowed_topics:
            raise InvalidProviderOutput("Generated question is outside approved course topics")
        return question


class FollowUpGenerationEngine:
    @staticmethod
    def select_development_candidate(
        candidates: tuple[QuestionBankEntry, ...], history: tuple[str, ...]
    ) -> QuestionBankEntry:
        eligible = tuple(item for item in candidates if not repeated_question(item.text, history))
        if not eligible:
            raise InvalidProviderOutput("No unused development question-bank content is available")
        return eligible[0]

    def generate(
        self,
        provider: LLMProvider,
        prompt: InterviewPrompt,
        history: tuple[str, ...],
    ) -> GeneratedQuestion:
        question = provider.generate_follow_up(prompt)
        if is_development_placeholder_question(question.text):
            raise InvalidProviderOutput("Question provider returned development fixture content")
        if len(question.text.split()) < 4:
            raise InvalidProviderOutput(
                "Generated follow-up is too short or repetitive", "too_short"
            )
        if repeated_question(question.text, history):
            raise InvalidProviderOutput(
                "Generated follow-up is too short or repetitive", "repetitive"
            )
        return question

    def select_approved_question(
        self,
        provider: LLMProvider,
        prompt: InterviewPrompt,
        candidates: tuple[QuestionBankEntry, ...],
        competency_id: str,
        history: tuple[str, ...],
    ) -> QuestionBankEntry:
        if not candidates:
            raise InvalidProviderOutput("No approved follow-up questions are configured")
        if any(
            item.status is not ContentStatus.APPROVED or item.competency_id != competency_id
            for item in candidates
        ):
            raise InvalidProviderOutput(
                "Follow-up candidates are outside approved competency content"
            )
        response = provider.generate_follow_up(prompt)
        if response.topic != competency_id:
            raise InvalidProviderOutput("Follow-up competency is outside the approved assessment")
        selected = next(
            (item for item in candidates if item.text.strip() == response.text.strip()), None
        )
        if selected is None:
            raise InvalidProviderOutput("Follow-up did not select approved question-bank content")
        if repeated_question(selected.text, history):
            raise InvalidProviderOutput(
                "Follow-up repeats the current or prior question", "repetitive"
            )
        return selected


class AnswerAnalyzer:
    def analyze(
        self,
        provider: LLMProvider,
        prompt: InterviewPrompt,
        rubric: Rubric,
    ) -> tuple[AnswerAnalysis, tuple[EvaluationEvidence, ...]]:
        analysis = provider.analyze_answer(prompt)
        return analysis, analysis_to_evidence(analysis, rubric)

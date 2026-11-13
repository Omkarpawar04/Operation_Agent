from collections.abc import Iterator
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from app.domain.assessments.models import EvaluationEvidence, Rubric
from app.domain.interviews.models import InterviewSession, Question


@dataclass(frozen=True, slots=True)
class InterviewContext:
    stage_key: str
    question_text: str
    prior_turns: tuple[tuple[str, str], ...]
    course_revision_id: UUID | None


@dataclass(frozen=True, slots=True)
class AnalysisOutput:
    evidence: tuple[EvaluationEvidence, ...]
    follow_up_text: str | None = None
    clarification_text: str | None = None
    answer_needs_clarification: bool = False
    uncertainty: Decimal = Decimal("0")


class ContextManager(Protocol):
    def build(self, session: InterviewSession, question: Question) -> InterviewContext: ...


class QuestionEngine(Protocol):
    def first_question(self, session: InterviewSession) -> Question: ...

    def next_question(self, session: InterviewSession, sequence: int) -> Question: ...


class AnswerAnalyzer(Protocol):
    def analyze(
        self, answer_text: str, context: InterviewContext, rubric: Rubric
    ) -> AnalysisOutput: ...


class FollowUpEngine(Protocol):
    def validate_follow_up(
        self, candidate: str, active_question: Question, context: InterviewContext
    ) -> Question | None: ...

    def validate_clarification(
        self, candidate: str, active_question: Question
    ) -> Question | None: ...


@dataclass(frozen=True, slots=True)
class StructuredTask:
    instruction: str
    context: InterviewContext
    output_schema_name: str


class LLMProvider(Protocol):
    def complete_structured(self, task: StructuredTask) -> AnalysisOutput: ...


@dataclass(frozen=True, slots=True)
class Transcript:
    text: str
    confidence: Decimal | None = None


class SpeechToText(Protocol):
    def transcribe(self, ephemeral_audio: bytes) -> Transcript: ...


class TextToSpeech(Protocol):
    def synthesize(self, text: str) -> Iterator[bytes]: ...

from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field


class GeneratedQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    text: str = Field(min_length=12, max_length=500)
    topic: str = Field(min_length=1, max_length=120)


class DimensionFinding(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    dimension_key: str
    evidence: list[str] = Field(max_length=5)
    missing_evidence: list[str] = Field(max_length=5)
    relevance: int = Field(ge=0, le=4)
    correctness: int = Field(ge=0, le=4)
    completeness: int = Field(ge=0, le=4)
    insufficient_evidence: bool
    confidence: float = Field(ge=0, le=1)
    explanation: str = Field(max_length=500)


class AnswerAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    findings: list[DimensionFinding] = Field(min_length=1, max_length=12)
    follow_up: str | None = Field(default=None, max_length=500)
    clarification: str | None = Field(default=None, max_length=500)
    needs_clarification: bool = False


@dataclass(frozen=True, slots=True)
class InterviewPrompt:
    task: str
    context: dict[str, object]


class LLMProvider(Protocol):
    @property
    def provider_name(self) -> str: ...

    @property
    def model_identifier(self) -> str | None: ...

    @property
    def development_only(self) -> bool: ...

    def generate_question(self, prompt: InterviewPrompt) -> GeneratedQuestion: ...

    def analyze_answer(self, prompt: InterviewPrompt) -> AnswerAnalysis: ...

    def generate_follow_up(self, prompt: InterviewPrompt) -> GeneratedQuestion: ...

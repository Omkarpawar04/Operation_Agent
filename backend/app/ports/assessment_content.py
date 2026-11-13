from typing import Protocol

from app.domain.assessments.content import (
    CompetencyDefinition,
    QuestionBankEntry,
    QuestionCategory,
    RubricDefinition,
)
from app.domain.interviews.models import InterviewStage


class AssessmentContentPort(Protocol):
    """Reads versioned assessment content; only approved rows are returned by default."""

    def approved_questions(
        self,
        stage: InterviewStage,
        category: QuestionCategory,
        competency_id: str | None = None,
        excluded_question_ids: tuple[str, ...] = (),
    ) -> tuple[QuestionBankEntry, ...]: ...

    def approved_competency(self, competency_id: str) -> CompetencyDefinition | None: ...

    def approved_rubric(self, rubric_version_id: str) -> RubricDefinition | None: ...

    def development_questions(
        self,
        stage: InterviewStage,
        category: QuestionCategory,
        *,
        allow_draft: bool,
        competency_id: str | None = None,
        excluded_question_ids: tuple[str, ...] = (),
        parent_question_id: str | None = None,
        question_id: str | None = None,
    ) -> tuple[QuestionBankEntry, ...]: ...

    def development_competency(
        self, competency_id: str, *, allow_draft: bool
    ) -> CompetencyDefinition | None: ...

    def development_rubric(
        self, rubric_version_id: str, *, allow_draft: bool
    ) -> RubricDefinition | None: ...

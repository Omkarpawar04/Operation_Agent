from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AssessmentRubricRow, CompetencyDefinitionRow, QuestionBankRow
from app.domain.assessments.content import (
    CompetencyDefinition,
    ContentStatus,
    QuestionBankEntry,
    QuestionCategory,
    RubricDefinition,
)
from app.domain.interviews.models import InterviewStage
from app.ports.assessment_content import AssessmentContentPort


class SqlAlchemyAssessmentContentAdapter(AssessmentContentPort):
    """Read-only question-bank adapter. Approval is enforced in every query."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def approved_questions(
        self,
        stage: InterviewStage,
        category: QuestionCategory,
        competency_id: str | None = None,
        excluded_question_ids: tuple[str, ...] = (),
    ) -> tuple[QuestionBankEntry, ...]:
        statement = (
            select(QuestionBankRow, CompetencyDefinitionRow)
            .join(
                CompetencyDefinitionRow,
                CompetencyDefinitionRow.competency_id == QuestionBankRow.competency_id,
            )
            .join(
                AssessmentRubricRow,
                AssessmentRubricRow.rubric_version_id == QuestionBankRow.rubric_version_id,
            )
            .where(
                QuestionBankRow.stage_id == stage.value,
                QuestionBankRow.category == category.value,
                QuestionBankRow.approval_status == ContentStatus.APPROVED.value,
                CompetencyDefinitionRow.approval_status == ContentStatus.APPROVED.value,
                AssessmentRubricRow.approval_status == ContentStatus.APPROVED.value,
                QuestionBankRow.competency_id == AssessmentRubricRow.competency_id,
            )
            .order_by(QuestionBankRow.question_id)
        )
        if competency_id is not None:
            statement = statement.where(QuestionBankRow.competency_id == competency_id)
        if excluded_question_ids:
            statement = statement.where(QuestionBankRow.question_id.notin_(excluded_question_ids))
        return tuple(
            self._question(question)
            for question, competency in self._session.execute(statement).all()
            if stage.value in (competency.stage_ids_json or [competency.stage_id])
        )

    def approved_competency(self, competency_id: str) -> CompetencyDefinition | None:
        row = self._session.scalar(
            select(CompetencyDefinitionRow).where(
                CompetencyDefinitionRow.competency_id == competency_id,
                CompetencyDefinitionRow.approval_status == ContentStatus.APPROVED.value,
            )
        )
        return self._competency(row) if row else None

    def approved_rubric(self, rubric_version_id: str) -> RubricDefinition | None:
        row = self._session.scalar(
            select(AssessmentRubricRow)
            .join(
                CompetencyDefinitionRow,
                CompetencyDefinitionRow.competency_id == AssessmentRubricRow.competency_id,
            )
            .where(
                AssessmentRubricRow.rubric_version_id == rubric_version_id,
                AssessmentRubricRow.approval_status == ContentStatus.APPROVED.value,
                CompetencyDefinitionRow.approval_status == ContentStatus.APPROVED.value,
            )
        )
        return self._rubric(row) if row else None

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
    ) -> tuple[QuestionBankEntry, ...]:
        statuses = [ContentStatus.APPROVED.value]
        if allow_draft:
            statuses.append(ContentStatus.DRAFT.value)
        statement = (
            select(QuestionBankRow, CompetencyDefinitionRow)
            .join(
                CompetencyDefinitionRow,
                CompetencyDefinitionRow.competency_id == QuestionBankRow.competency_id,
            )
            .join(
                AssessmentRubricRow,
                AssessmentRubricRow.rubric_version_id == QuestionBankRow.rubric_version_id,
            )
            .where(
                QuestionBankRow.stage_id == stage.value,
                QuestionBankRow.category == category.value,
                QuestionBankRow.development_eligible.is_(True),
                QuestionBankRow.approval_status.in_(statuses),
                CompetencyDefinitionRow.approval_status.in_(statuses),
                AssessmentRubricRow.approval_status.in_(statuses),
                QuestionBankRow.competency_id == AssessmentRubricRow.competency_id,
            )
            .order_by(QuestionBankRow.question_id, QuestionBankRow.content_version)
        )
        if competency_id is not None:
            statement = statement.where(QuestionBankRow.competency_id == competency_id)
        if excluded_question_ids:
            statement = statement.where(QuestionBankRow.question_id.notin_(excluded_question_ids))
        if question_id is not None:
            statement = statement.where(QuestionBankRow.question_id == question_id)
        if parent_question_id is None:
            statement = statement.where(QuestionBankRow.parent_question_id.is_(None))
        else:
            statement = statement.where(QuestionBankRow.parent_question_id == parent_question_id)
        return tuple(
            self._question(question)
            for question, competency in self._session.execute(statement).all()
            if stage.value in (competency.stage_ids_json or [competency.stage_id])
        )

    def development_competency(
        self, competency_id: str, *, allow_draft: bool
    ) -> CompetencyDefinition | None:
        statuses = [ContentStatus.APPROVED.value]
        if allow_draft:
            statuses.append(ContentStatus.DRAFT.value)
        row = self._session.scalar(
            select(CompetencyDefinitionRow).where(
                CompetencyDefinitionRow.competency_id == competency_id,
                CompetencyDefinitionRow.approval_status.in_(statuses),
            )
        )
        return self._competency(row) if row else None

    def development_rubric(
        self, rubric_version_id: str, *, allow_draft: bool
    ) -> RubricDefinition | None:
        statuses = [ContentStatus.APPROVED.value]
        if allow_draft:
            statuses.append(ContentStatus.DRAFT.value)
        row = self._session.scalar(
            select(AssessmentRubricRow)
            .join(
                CompetencyDefinitionRow,
                CompetencyDefinitionRow.competency_id == AssessmentRubricRow.competency_id,
            )
            .where(
                AssessmentRubricRow.rubric_version_id == rubric_version_id,
                AssessmentRubricRow.approval_status.in_(statuses),
                CompetencyDefinitionRow.approval_status.in_(statuses),
            )
        )
        return self._rubric(row) if row else None

    @staticmethod
    def _competency(row: CompetencyDefinitionRow) -> CompetencyDefinition:
        return CompetencyDefinition(
            row.competency_id,
            InterviewStage(row.stage_id),
            row.title,
            row.definition,
            row.content_version,
            ContentStatus(row.approval_status),
            row.content_source,
            row.created_at,
            row.created_by,
            row.approved_at,
            row.approved_by,
            tuple(InterviewStage(value) for value in (row.stage_ids_json or [row.stage_id])),
        )

    @staticmethod
    def _rubric(row: AssessmentRubricRow) -> RubricDefinition:
        dimension_values: list[tuple[str, Decimal, tuple[str, ...]]] = []
        for item in row.dimensions_json:
            key = item.get("key")
            weight = item.get("weight")
            indicators = item.get("performance_indicators")
            if not isinstance(key, str) or not isinstance(indicators, list):
                raise ValueError("Stored rubric dimension is malformed")
            dimension_values.append(
                (
                    key,
                    Decimal(str(weight)),
                    tuple(str(value) for value in indicators),
                )
            )
        dimensions = tuple(dimension_values)
        scale_values: list[tuple[int, str]] = []
        for item in row.scoring_scale_json:
            score = item.get("score")
            label = item.get("label")
            if not isinstance(score, int) or not isinstance(label, str):
                raise ValueError("Stored rubric scoring scale is malformed")
            scale_values.append((score, label))
        scale = tuple(scale_values)
        return RubricDefinition(
            row.rubric_version_id,
            row.rubric_id,
            row.competency_id,
            dimensions,
            scale,
            tuple(str(item) for item in row.evidence_requirements_json),
            tuple(str(item) for item in row.insufficient_evidence_json),
            row.content_version,
            ContentStatus(row.approval_status),
            row.content_source,
            row.created_at,
            row.created_by,
            row.approved_at,
            row.approved_by,
        )

    @staticmethod
    def _question(row: QuestionBankRow) -> QuestionBankEntry:
        return QuestionBankEntry(
            row.question_id,
            InterviewStage(row.stage_id),
            row.competency_id,
            row.text,
            QuestionCategory(row.category),
            row.difficulty,
            tuple(str(item) for item in row.expected_answer_json),
            row.rubric_version_id,
            row.content_version,
            ContentStatus(row.approval_status),
            row.content_source,
            row.created_at,
            row.created_by,
            row.approved_at,
            row.approved_by,
            row.parent_question_id,
        )

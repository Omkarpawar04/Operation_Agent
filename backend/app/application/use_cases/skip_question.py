import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from app.application.orchestrator.engines import (
    FollowUpGenerationEngine,
    InvalidProviderOutput,
    QuestionGenerationEngine,
)
from app.application.workflow import prompt_for_question, rubric_for
from app.core.config import Settings
from app.core.errors import ProviderOutputRejected, ProviderUnavailable
from app.domain.assessments.content import (
    QuestionBankEntry,
    QuestionCategory,
    QuestionProvenance,
    RubricDefinition,
)
from app.domain.assessments.models import (
    EvaluationEvidence,
    calculate_correctness_result,
)
from app.domain.interviews.decision import InterviewAction
from app.domain.interviews.models import QuestionKind
from app.ports.answer_workflow import (
    AnswerCommand,
    AnswerReplay,
    AnswerWorkflowPort,
)
from app.ports.assessment_content import AssessmentContentPort
from app.ports.llm import LLMProvider

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class SkipResult:
    state: str
    version: int
    action: InterviewAction | None
    question_text: str | None
    score: Decimal | None = None


class SkipQuestion:
    """Versioned skip operation that advances or completes without evaluating the learner."""

    def __init__(
        self,
        persistence: AnswerWorkflowPort,
        provider: LLMProvider,
        settings: Settings,
        assessment_content: AssessmentContentPort,
    ) -> None:
        self._persistence = persistence
        self._provider = provider
        self._settings = settings
        self._assessment_content = assessment_content

    def execute(self, command: AnswerCommand) -> SkipResult:
        if not command.is_skip or command.text:
            raise ValueError("Skip command must not contain answer text")
        reservation_or_replay = self._persistence.reserve(
            command, self._settings.provider_operation_lease_seconds
        )
        if isinstance(reservation_or_replay, AnswerReplay):
            return SkipResult(
                reservation_or_replay.state,
                reservation_or_replay.version,
                None,
                reservation_or_replay.question_text,
            )
        reservation = reservation_or_replay
        try:
            stage = reservation.session.stage
            provenance = reservation.active_question.provenance
            production = self._settings.app_env.lower() == "production"
            development_bank = (
                self._settings.app_env.lower() in {"development", "test"}
                and self._settings.dev_assessment_content_mode == "question_bank"
            )
            rubric_definition: RubricDefinition | None = None
            if production:
                if (
                    provenance is None
                    or provenance.origin != "approved_assessment_bank"
                    or provenance.approval_status != "approved"
                    or not provenance.competency_id
                    or not provenance.rubric_version_id
                ):
                    raise ProviderOutputRejected("Active question is not approved for assessment")
                category = QuestionCategory(reservation.active_question.kind.value)
                approved_entries = self._assessment_content.approved_questions(
                    stage, category, provenance.competency_id
                )
                if not any(
                    item.question_id == provenance.bank_question_id
                    and item.content_version == provenance.content_version
                    and item.parent_question_id
                    == (
                        provenance.parent_question_id
                        if category is not QuestionCategory.BASE
                        else None
                    )
                    for item in approved_entries
                ):
                    raise ProviderOutputRejected("Active question is not in approved content")
                competency = self._assessment_content.approved_competency(provenance.competency_id)
                rubric_definition = self._assessment_content.approved_rubric(
                    provenance.rubric_version_id
                )
                if competency is None or stage not in (competency.stage_ids or (competency.stage,)):
                    raise ProviderOutputRejected("Approved question competency is unavailable")
            elif development_bank:
                if (
                    provenance is None
                    or provenance.origin != "development_assessment_bank"
                    or not provenance.competency_id
                    or not provenance.rubric_version_id
                ):
                    raise ProviderOutputRejected(
                        "Active question is not eligible development content"
                    )
                category = QuestionCategory(reservation.active_question.kind.value)
                development_entries = self._assessment_content.development_questions(
                    stage,
                    category,
                    allow_draft=self._settings.dev_assessment_allow_draft,
                    competency_id=provenance.competency_id,
                    parent_question_id=(
                        provenance.parent_question_id
                        if category is not QuestionCategory.BASE
                        else None
                    ),
                    question_id=provenance.bank_question_id,
                )
                if not any(
                    item.question_id == provenance.bank_question_id
                    and item.content_version == provenance.content_version
                    for item in development_entries
                ):
                    raise ProviderOutputRejected(
                        "Active question is not eligible development content"
                    )
                competency = self._assessment_content.development_competency(
                    provenance.competency_id,
                    allow_draft=self._settings.dev_assessment_allow_draft,
                )
                rubric_definition = self._assessment_content.development_rubric(
                    provenance.rubric_version_id,
                    allow_draft=self._settings.dev_assessment_allow_draft,
                )
                if competency is None or stage not in (competency.stage_ids or (competency.stage,)):
                    raise ProviderOutputRejected("Development question competency is unavailable")
            elif provenance and provenance.origin in {
                "approved_assessment_bank",
                "development_assessment_bank",
            }:
                raise ProviderOutputRejected(
                    "Active assessment content is unavailable in this mode"
                )
            if (production or development_bank) and rubric_definition is None:
                raise ProviderOutputRejected("Question rubric is unavailable")
            rubric = (
                rubric_definition.to_scoring_rubric(self._settings.passing_threshold)
                if rubric_definition
                else rubric_for(
                    self._settings.passing_threshold,
                    reservation.course_metadata,
                    required=stage.technical,
                )
            )
            question_evidence: tuple[EvaluationEvidence, ...] = ()
            root_question_id = reservation.root_question_id or reservation.active_question.id
            if reservation.active_question.kind is QuestionKind.BASE:
                question_evidence = tuple(
                    EvaluationEvidence(
                        dimension_key=dimension.key,
                        supporting_evidence=(),
                        missing_evidence=("Main question was skipped",),
                        insufficient_evidence=False,
                        confidence=Decimal("1"),
                        score=Decimal("0"),
                        explanation="Skipped main question; zero correctness points.",
                        relevance=0,
                        correctness=0,
                        completeness=0,
                        root_question_id=root_question_id,
                        dimension_weight=dimension.weight,
                    )
                    for dimension in rubric.dimensions
                )

            next_text: str | None = None
            next_provenance: QuestionProvenance | None = None
            can_ask_more = (
                reservation.session.base_question_count
                < self._settings.max_base_questions
            )
            if can_ask_more and (production or development_bank):
                if provenance is None or not provenance.competency_id:
                    raise ProviderOutputRejected("Question competency provenance is unavailable")
                if production:
                    candidates = self._assessment_content.approved_questions(
                        stage, QuestionCategory.BASE, provenance.competency_id
                    )
                else:
                    candidates = self._assessment_content.development_questions(
                        stage,
                        QuestionCategory.BASE,
                        allow_draft=self._settings.dev_assessment_allow_draft,
                        competency_id=provenance.competency_id,
                    )
                selected = self._select_next(candidates, reservation.previous_questions)
                if selected is not None:
                    next_text = selected.text
                    next_provenance = self._bank_provenance(selected, production)
            elif can_ask_more:
                try:
                    generated = QuestionGenerationEngine().generate(
                        self._provider,
                        prompt_for_question(
                            stage.value,
                            reservation.session.base_question_count + 1,
                            {"previous_question": reservation.active_question.text},
                        ),
                        reservation.previous_questions,
                    )
                    next_text = generated.text
                    development_only = bool(getattr(self._provider, "development_only", False))
                    next_provenance = QuestionProvenance(
                        provider_name=getattr(self._provider, "provider_name", "unknown"),
                        model_identifier=getattr(self._provider, "model_identifier", None),
                        generation_type="base_question",
                        prompt_schema_version="initial_question.v1",
                        generated_at=datetime.now(UTC),
                        origin="development_fixture" if development_only else "model_generated",
                        approval_status="development_only" if development_only else "review",
                    )
                except InvalidProviderOutput as exc:
                    raise ProviderOutputRejected(
                        "Question source returned unsuitable output", exc.category
                    ) from exc

            action = InterviewAction.NEXT_QUESTION if next_text else InterviewAction.COMPLETE
            result = None
            if action is InterviewAction.COMPLETE:
                all_evidence = reservation.previous_evidence + question_evidence
                grouped: dict[UUID, list[EvaluationEvidence]] = {}
                for item in all_evidence:
                    if item.root_question_id is None:
                        raise ValueError("Assessment evidence is missing its parent main question")
                    grouped.setdefault(item.root_question_id, []).append(item)
                result = calculate_correctness_result(
                    reservation.attempt_id,
                    rubric,
                    tuple(
                        (question_id, tuple(grouped[question_id]))
                        for question_id in sorted(grouped, key=str)
                    ),
                )
            completion = self._persistence.complete(
                command,
                reservation,
                question_evidence,
                rubric.version,
                action,
                next_text,
                result,
                next_provenance,
            )
            return SkipResult(
                completion.state,
                completion.version,
                completion.action,
                completion.question_text,
                completion.score,
            )
        except ProviderUnavailable:
            self._persistence.release(reservation)
            raise
        except TimeoutError as exc:
            self._persistence.release(reservation)
            raise ProviderUnavailable("Interview provider is temporarily unavailable") from exc
        except Exception:
            self._persistence.release(reservation)
            raise

    @staticmethod
    def _select_next(
        candidates: tuple[QuestionBankEntry, ...], history: tuple[str, ...]
    ) -> QuestionBankEntry | None:
        try:
            return FollowUpGenerationEngine.select_development_candidate(candidates, history)
        except InvalidProviderOutput:
            return None

    @staticmethod
    def _bank_provenance(
        question: QuestionBankEntry, production: bool
    ) -> QuestionProvenance:
        return QuestionProvenance(
            provider_name="question_bank",
            model_identifier=None,
            generation_type="approved_bank_selection"
            if production
            else "development_bank_selection",
            prompt_schema_version="assessment_question.v1",
            generated_at=None,
            origin="approved_assessment_bank" if production else "development_assessment_bank",
            approval_status=question.status.value,
            bank_question_id=question.question_id,
            competency_id=question.competency_id,
            rubric_version_id=question.rubric_version_id,
            content_version=question.content_version,
        )

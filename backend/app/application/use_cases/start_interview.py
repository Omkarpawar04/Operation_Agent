from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from app.application.orchestrator.engines import (
    FollowUpGenerationEngine,
    InvalidProviderOutput,
    QuestionGenerationEngine,
)
from app.application.sessions.manager import SessionManager
from app.application.workflow import (
    is_development_placeholder_question,
    prompt_for_question,
    rubric_for,
)
from app.core.config import Settings
from app.core.errors import (
    Conflict,
    EnrollmentRequired,
    ProviderOutputRejected,
    ProviderUnavailable,
)
from app.domain.assessments.content import (
    QuestionCategory,
    QuestionProvenance,
)
from app.domain.assessments.models import Rubric
from app.ports.assessment_content import AssessmentContentPort
from app.ports.interview_queries import CourseContentPort, InterviewQueryPort
from app.ports.llm import LLMProvider
from app.ports.sessions import SessionRecord, StartSessionCommand


@dataclass(frozen=True, slots=True)
class StartedInterview:
    record: SessionRecord
    question_text: str


class StartInterview:
    """Validates start policy, obtains a candidate question, then persists a session."""

    def __init__(
        self,
        sessions: SessionManager,
        content: CourseContentPort,
        interviews: InterviewQueryPort,
        provider: LLMProvider,
        settings: Settings,
        assessment_content: AssessmentContentPort | None = None,
    ) -> None:
        self._sessions = sessions
        self._content = content
        self._interviews = interviews
        self._provider = provider
        self._settings = settings
        self._assessment_content = assessment_content

    def execute(self, command: StartSessionCommand) -> StartedInterview:
        course_context: dict[str, object] = {"content_source": "synthetic development fixture"}
        topics: tuple[str, ...] = ()
        revision_id: UUID | None = None
        start_rubric: Rubric | None = None
        if command.stage.technical:
            if command.course_id is None or not self._sessions.has_active_enrollment(
                command.student_id, command.course_id
            ):
                raise EnrollmentRequired("Active course enrollment required")
            approved = self._content.approved_configuration(command.course_id)
            if approved is None:
                raise Conflict("Approved course content is not configured")
            topics_value = approved.metadata.get("topics")
            if not isinstance(topics_value, list):
                raise Conflict("Approved course topics are not configured")
            topics = tuple(topic[:120] for topic in topics_value if isinstance(topic, str))[:50]
            if not topics:
                raise Conflict("Approved course topics are not configured")
            revision_id = approved.revision_id
            metadata = approved.metadata
            skills_value = metadata.get("skills", [])
            skills = (
                [skill[:120] for skill in skills_value if isinstance(skill, str)][:30]
                if isinstance(skills_value, list)
                else []
            )
            try:
                start_rubric = rubric_for(self._settings.passing_threshold, metadata, required=True)
            except ValueError as exc:
                raise Conflict("Approved course rubric is not configured") from exc
            course_context = {
                "content_source": "approved course content",
                "topics": list(topics),
                "skills": skills,
                "evaluation_dimensions": [dimension.key for dimension in start_rubric.dimensions],
                "content_revision_id": str(revision_id),
            }
            command = StartSessionCommand(
                command.student_id,
                command.stage,
                command.idempotency_key,
                command.course_id,
                command.initial_question_text,
                revision_id,
            )
        else:
            if self._settings.app_env.lower() != "production":
                start_rubric = rubric_for(self._settings.passing_threshold)

        existing = self._sessions.find_existing(command)
        if existing is not None:
            question = self._interviews.get_active_question(existing.id, command.student_id)
            if question is None:
                raise Conflict("Interview start is awaiting recovery")
            if is_development_placeholder_question(question.text):
                raise Conflict(
                    "This interview contains a development question. Start a fresh interview."
                )
            if self._settings.app_env.lower() == "production" and (
                question.provenance is None
                or question.provenance.origin != "approved_assessment_bank"
                or question.provenance.approval_status != "approved"
            ):
                raise Conflict("This interview does not contain approved assessment content")
            return StartedInterview(existing, question.text)

        validated_revision_id = self._sessions.validate_start(command)
        if command.stage.technical and validated_revision_id != revision_id:
            raise Conflict("Approved course content changed; retry the interview start")
        self._sessions.release_read_transaction()
        course_context.update(
            {
                "interview_type": "technical" if command.stage.technical else "behavioral",
                "difficulty": command.stage.value,
                "evaluation_dimensions": [dimension.key for dimension in start_rubric.dimensions]
                if start_rubric
                else [],
                "question_limit": self._settings.max_base_questions,
                "previous_questions": (),
            }
        )
        provenance: QuestionProvenance
        if self._settings.app_env.lower() == "production":
            if self._assessment_content is None:
                raise Conflict("Approved assessment question bank is unavailable")
            approved_questions = self._assessment_content.approved_questions(
                command.stage, QuestionCategory.BASE
            )
            if not approved_questions:
                raise Conflict("Approved assessment questions are not configured for this stage")
            bank_question = FollowUpGenerationEngine.select_bank_candidate(approved_questions, ())
            competency = self._assessment_content.approved_competency(bank_question.competency_id)
            rubric = self._assessment_content.approved_rubric(bank_question.rubric_version_id)
            if (
                competency is None
                or rubric is None
                or command.stage not in (competency.stage_ids or (competency.stage,))
                or rubric.competency_id != competency.competency_id
            ):
                raise Conflict("Approved question competency and rubric are not configured")
            question_text = bank_question.text
            provenance = QuestionProvenance(
                provider_name="question_bank",
                model_identifier=None,
                generation_type="approved_bank_selection",
                prompt_schema_version="assessment_question.v1",
                generated_at=None,
                origin="approved_assessment_bank",
                approval_status="approved",
                bank_question_id=bank_question.question_id,
                competency_id=bank_question.competency_id,
                rubric_version_id=bank_question.rubric_version_id,
                content_version=bank_question.content_version,
            )
        elif self._settings.dev_assessment_content_mode == "question_bank":
            if self._assessment_content is None:
                raise Conflict("Development assessment question bank is unavailable")
            candidates = self._assessment_content.development_questions(
                command.stage,
                QuestionCategory.BASE,
                allow_draft=self._settings.dev_assessment_allow_draft,
            )
            if not candidates:
                raise Conflict(
                    "No eligible development assessment questions are configured for this stage"
                )
            bank_question = FollowUpGenerationEngine.select_bank_candidate(candidates, ())
            competency = self._assessment_content.development_competency(
                bank_question.competency_id,
                allow_draft=self._settings.dev_assessment_allow_draft,
            )
            rubric = self._assessment_content.development_rubric(
                bank_question.rubric_version_id,
                allow_draft=self._settings.dev_assessment_allow_draft,
            )
            competency_stages = (
                competency.stage_ids or (competency.stage,) if competency is not None else ()
            )
            if (
                competency is None
                or rubric is None
                or command.stage not in competency_stages
                or rubric.competency_id != competency.competency_id
                or bank_question.stage is not command.stage
                or bank_question.competency_id != competency.competency_id
                or rubric.rubric_version_id != bank_question.rubric_version_id
            ):
                raise Conflict("Development question competency and rubric are not configured")
            start_rubric = rubric.to_scoring_rubric(self._settings.passing_threshold)
            course_context["evaluation_dimensions"] = [
                dimension.key for dimension in start_rubric.dimensions
            ]
            question_text = bank_question.text
            provenance = QuestionProvenance(
                provider_name="question_bank",
                model_identifier=None,
                generation_type="development_bank_selection",
                prompt_schema_version="assessment_question.v1",
                generated_at=None,
                origin="development_assessment_bank",
                approval_status=bank_question.status.value,
                bank_question_id=bank_question.question_id,
                competency_id=bank_question.competency_id,
                rubric_version_id=bank_question.rubric_version_id,
                content_version=bank_question.content_version,
                parent_question_id=bank_question.parent_question_id,
            )
        else:
            try:
                candidate = QuestionGenerationEngine().generate(
                    self._provider,
                    prompt_for_question(command.stage.value, 1, course_context),
                    (),
                    topics,
                )
            except InvalidProviderOutput as exc:
                raise ProviderOutputRejected(
                    "Question provider returned unsuitable output"
                ) from exc
            except ProviderUnavailable:
                raise
            question_text = candidate.text
            provenance = QuestionProvenance(
                provider_name=getattr(
                    self._provider,
                    "provider_name",
                    type(self._provider).__name__.lower(),
                ),
                model_identifier=getattr(self._provider, "model_identifier", None),
                generation_type="initial_question",
                prompt_schema_version="initial_question.v1",
                generated_at=datetime.now(UTC),
                origin=(
                    "development_fixture"
                    if getattr(self._provider, "development_only", False)
                    else "model_generated"
                ),
                approval_status=(
                    "development_only"
                    if getattr(self._provider, "development_only", False)
                    else "review"
                ),
            )

        record = self._sessions.start(
            StartSessionCommand(
                command.student_id,
                command.stage,
                command.idempotency_key,
                command.course_id,
                question_text,
                validated_revision_id,
                provenance,
            )
        )
        question = self._interviews.get_active_question(record.id, command.student_id)
        if question is None:
            raise Conflict("Interview start is awaiting recovery")
        return StartedInterview(record, question.text)

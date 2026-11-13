from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.adapters.llm.fake import FakeLLMProvider
from app.adapters.persistence.assessment_content import SqlAlchemyAssessmentContentAdapter
from app.application.orchestrator.engines import FollowUpGenerationEngine, InvalidProviderOutput
from app.application.use_cases.start_interview import StartInterview
from app.core.config import Settings
from app.core.errors import Conflict
from app.db.base import Base
from app.db.models import AssessmentRubricRow, CompetencyDefinitionRow, QuestionBankRow
from app.domain.assessments.content import (
    ContentStatus,
    QuestionBankEntry,
    QuestionCategory,
    QuestionProvenance,
)
from app.domain.interviews.models import InterviewStage
from app.ports.llm import GeneratedQuestion, InterviewPrompt
from app.ports.sessions import StartSessionCommand


def _approved_content() -> tuple[CompetencyDefinitionRow, AssessmentRubricRow, QuestionBankRow]:
    now = datetime.now(UTC)
    competency = CompetencyDefinitionRow(
        competency_id="test_competency",
        stage_id="soft_1",
        title="Test competency",
        definition="Test-only competency definition.",
        content_version="test-v1",
        approval_status="approved",
        content_source="unit test fixture",
        created_at=now,
        approved_at=now,
        approved_by="test-reviewer",
    )
    rubric = AssessmentRubricRow(
        rubric_version_id="test_rubric-v1",
        rubric_id="test_rubric",
        competency_id=competency.competency_id,
        dimensions_json=[
            {"key": "reasoning", "weight": "1", "performance_indicators": ["Explains choice"]}
        ],
        scoring_scale_json=[{"score": score, "label": str(score)} for score in range(5)],
        evidence_requirements_json=["Decision evidence"],
        insufficient_evidence_json=["No concrete example"],
        content_version="test-v1",
        approval_status="approved",
        content_source="unit test fixture",
        created_at=now,
        approved_at=now,
        approved_by="test-reviewer",
    )
    question = QuestionBankRow(
        question_id="test_question_1",
        stage_id="soft_1",
        competency_id=competency.competency_id,
        text="Test-only approved question about reasoning through a decision.",
        category="base",
        difficulty="introductory",
        expected_answer_json=["Options considered", "Evidence used"],
        rubric_version_id=rubric.rubric_version_id,
        content_version="test-v1",
        approval_status="approved",
        content_source="unit test fixture",
        created_at=now,
        approved_at=now,
        approved_by="test-reviewer",
    )
    return competency, rubric, question


def test_assessment_content_adapter_returns_only_fully_approved_content() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    competency, rubric, approved = _approved_content()
    review = QuestionBankRow(
        question_id="test_question_review",
        stage_id="soft_1",
        competency_id=competency.competency_id,
        text="A review question that must not be used.",
        category="base",
        difficulty="introductory",
        expected_answer_json=["Not available"],
        rubric_version_id=rubric.rubric_version_id,
        content_version="test-v1",
        approval_status="review",
        content_source="unit test fixture",
        created_at=datetime.now(UTC),
    )
    retired_version = QuestionBankRow(
        question_id="test_question_1",
        stage_id="soft_1",
        competency_id=competency.competency_id,
        text="An earlier preserved version of the approved question.",
        category="base",
        difficulty="introductory",
        expected_answer_json=["Prior version"],
        rubric_version_id=rubric.rubric_version_id,
        content_version="test-v0",
        approval_status="retired",
        content_source="unit test fixture",
        created_at=datetime.now(UTC),
    )
    with Session(engine) as session:
        session.add_all((competency, rubric, approved, review, retired_version))
        session.commit()
        bank = SqlAlchemyAssessmentContentAdapter(session)
        results = bank.approved_questions(InterviewStage.SOFT_1, QuestionCategory.BASE)
        assert tuple(item.question_id for item in results) == ("test_question_1",)
        assert results[0].content_version == "test-v1"
        assert bank.approved_competency("test_competency") is not None
        loaded_rubric = bank.approved_rubric("test_rubric-v1")
        assert loaded_rubric is not None
        assert loaded_rubric.to_scoring_rubric().dimensions[0].key == "reasoning"
    engine.dispose()


def test_provenance_round_trip_and_legacy_null_remains_unknown() -> None:
    provenance = QuestionProvenance(
        provider_name="fake",
        model_identifier=None,
        generation_type="initial_question",
        prompt_schema_version="initial_question.v1",
        generated_at=datetime.now(UTC),
        origin="development_fixture",
        approval_status="development_only",
    )
    assert QuestionProvenance.from_json(provenance.to_json()) == provenance
    assert QuestionProvenance.from_json(None) is None


def test_gemini_follow_up_selection_must_match_approved_question_and_competency() -> None:
    class Selector(FakeLLMProvider):
        def generate_follow_up(self, prompt: InterviewPrompt) -> GeneratedQuestion:
            return GeneratedQuestion(
                text="What evidence supported that decision?", topic="test_competency"
            )

    now = datetime.now(UTC)
    question = QuestionBankEntry(
        question_id="approved_follow_up",
        stage=InterviewStage.SOFT_1,
        competency_id="test_competency",
        text="What evidence supported that decision?",
        category=QuestionCategory.FOLLOW_UP,
        difficulty="intermediate",
        expected_answer_characteristics=("Evidence",),
        rubric_version_id="test_rubric-v1",
        content_version="test-v1",
        status=ContentStatus.APPROVED,
        content_source="test fixture",
        created_at=now,
        approved_at=now,
        approved_by="reviewer",
    )
    selected = FollowUpGenerationEngine().select_approved_question(
        Selector(),
        InterviewPrompt("Select an approved follow-up", {}),
        (question,),
        "test_competency",
        ("Original question",),
    )
    assert selected.question_id == question.question_id

    class UnrelatedSelector(Selector):
        def generate_follow_up(self, prompt: InterviewPrompt) -> GeneratedQuestion:
            return GeneratedQuestion(text="New unsupported wording.", topic="other_competency")

    with pytest.raises(InvalidProviderOutput):
        FollowUpGenerationEngine().select_approved_question(
            UnrelatedSelector(),
            InterviewPrompt("Select an approved follow-up", {}),
            (question,),
            "test_competency",
            ("Original question",),
        )


def test_production_start_fails_closed_without_approved_bank_content() -> None:
    class Sessions:
        def find_existing(self, command):
            return None

        def validate_start(self, command):
            return None

        def release_read_transaction(self):
            return None

    class EmptyBank:
        def approved_questions(self, *args, **kwargs):
            return ()

    class MustNotGenerate(FakeLLMProvider):
        called = False

        def generate_question(self, prompt: InterviewPrompt) -> GeneratedQuestion:
            self.called = True
            return super().generate_question(prompt)

    settings = Settings(
        app_env="production",
        llm_provider="gemini",
        gemini_api_key="test-key-not-used",
        cors_allowed_origins=["https://example.invalid"],
        trusted_hosts=["example.invalid"],
        transcript_retention_days=365,
    )
    provider = MustNotGenerate()
    use_case = StartInterview(Sessions(), object(), object(), provider, settings, EmptyBank())
    command = StartSessionCommand(uuid4(), InterviewStage.SOFT_1, "test-start", None)
    with pytest.raises(Conflict, match="Approved assessment questions"):
        use_case.execute(command)
    assert provider.called is False

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from app.adapters.persistence.assessment_content import SqlAlchemyAssessmentContentAdapter
from app.db.base import Base
from app.db.models import AssessmentRubricRow, CompetencyDefinitionRow, QuestionBankRow
from app.domain.assessments.content import QuestionCategory
from app.domain.interviews.models import InterviewStage
from scripts.import_assessment_content import ContentImportError, import_content

PACK_PATH = (
    Path(__file__).resolve().parents[3]
    / "docs"
    / "assessment-content"
    / "v1"
    / "finxl_assessment_content_v1.json"
)


@pytest.fixture
def pack() -> dict[str, object]:
    return json.loads(PACK_PATH.read_text(encoding="utf-8"))


@pytest.fixture
def database():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


def _counts(session: Session) -> tuple[int, int, int]:
    return tuple(
        session.scalar(select(func.count()).select_from(model)) or 0
        for model in (CompetencyDefinitionRow, AssessmentRubricRow, QuestionBankRow)
    )  # type: ignore[return-value]


def test_dry_run_validates_pack_without_writing(database, pack) -> None:
    with Session(database) as session:
        result = import_content(session, pack, apply=False)
        assert result.dry_run is True
        assert (
            result.inserted_competencies,
            result.inserted_rubrics,
            result.inserted_questions,
        ) == (
            22,
            22,
            200,
        )
        assert _counts(session) == (0, 0, 0)


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda item: item["questions"][0].update(competency_id="missing"), "references"),
        (lambda item: item["questions"][0].pop("rubric_id"), "references unknown rubric"),
        (
            lambda item: next(
                question
                for question in item["questions"][1:]
                if question["stage_id"] == item["questions"][0]["stage_id"]
            ).update(text=item["questions"][0]["text"]),
            "Duplicate question text",
        ),
    ],
)
def test_invalid_or_duplicate_pack_is_rejected_before_database_changes(
    database, pack, mutate, message
) -> None:
    invalid = copy.deepcopy(pack)
    mutate(invalid)
    with Session(database) as session:
        with pytest.raises(ContentImportError, match=message):
            import_content(session, invalid, apply=True)
        assert _counts(session) == (0, 0, 0)


def test_apply_preserves_draft_metadata_and_follow_up_parentage(database, pack) -> None:
    with Session(database) as session:
        result = import_content(session, pack, apply=True)
        assert (
            result.inserted_competencies,
            result.inserted_rubrics,
            result.inserted_questions,
        ) == (
            22,
            22,
            200,
        )
        assert _counts(session) == (22, 22, 200)
        question = session.get(QuestionBankRow, ("Q_DRAFT_SOFT1_01", "1.0.0"))
        assert question is not None
        assert question.approval_status == "draft"
        assert question.approved_at is None
        assert question.approved_by is None
        assert question.development_eligible is True
        assert question.content_metadata_json["source_status"] == "source_based_draft"
        assert question.content_metadata_json["source_references"]
        follow_up = session.get(QuestionBankRow, ("FU_Q_DRAFT_SOFT1_01_01", "1.0.0"))
        assert follow_up is not None
        assert follow_up.parent_question_id == question.question_id
        assert follow_up.category == "follow_up"
        assert follow_up.difficulty == "not_assigned"
        competency = session.get(CompetencyDefinitionRow, "C_FINANCE")
        assert competency is not None
        assert competency.stage_ids_json == ["technical_1", "technical_2"]


def test_revised_curriculum_is_balanced_versioned_and_draft(database, pack) -> None:
    from collections import Counter

    from app.domain.interviews.models import InterviewStage

    with Session(database) as session:
        import_content(session, pack, apply=True)
        base_counts = Counter(item["stage_id"] for item in pack["questions"])
        assert all(base_counts[stage.value] >= 8 for stage in InterviewStage)
        assert all(
            item["approval_status"] == "draft"
            and item["source_status"] == "inferred_draft"
            and item["content_version"] == "1.1.0"
            for item in pack["questions"]
            if item["question_id"].startswith("Q_CURR_FIN_11_")
        )
        bank = SqlAlchemyAssessmentContentAdapter(session)
        for stage in InterviewStage:
            questions = bank.development_questions(stage, QuestionCategory.BASE, allow_draft=True)
            assert sum(item.question_id.startswith("Q_CURR_FIN_11_") for item in questions) == 8
            assert questions[0].question_id.startswith("Q_CURR_FIN_11_")
            assert all(item.stage is stage for item in questions)


def test_development_adapter_requires_explicit_draft_opt_in_and_valid_relationships(
    database, pack
) -> None:
    with Session(database) as session:
        import_content(session, pack, apply=True)
        bank = SqlAlchemyAssessmentContentAdapter(session)
        assert bank.approved_questions(InterviewStage.SOFT_1, QuestionCategory.BASE) == ()
        assert (
            bank.development_questions(
                InterviewStage.SOFT_1,
                QuestionCategory.BASE,
                allow_draft=False,
            )
            == ()
        )
        soft_questions = bank.development_questions(
            InterviewStage.SOFT_1,
            QuestionCategory.BASE,
            allow_draft=True,
        )
        assert soft_questions[0].question_id == "Q_CURR_FIN_11_soft_1_01"
        assert soft_questions[0].competency_id == "FIN_FOUNDATIONS_COMM"
        assert soft_questions[0].status.value == "draft"

        multi_stage_question = next(
            row for row in pack["questions"] if row["competency_id"] == "C_FINANCE"
        )
        mapped_questions = bank.development_questions(
            InterviewStage.TECHNICAL_1,
            QuestionCategory.BASE,
            allow_draft=True,
            question_id=multi_stage_question["question_id"],
        )
        assert tuple(row.question_id for row in mapped_questions) == (
            multi_stage_question["question_id"],
        )
        competency = bank.development_competency("C_FINANCE", allow_draft=True)
        assert competency is not None
        assert InterviewStage.TECHNICAL_1 in competency.stage_ids
        assert InterviewStage.TECHNICAL_2 in competency.stage_ids

        followups = bank.development_questions(
            InterviewStage.SOFT_1,
            QuestionCategory.FOLLOW_UP,
            allow_draft=True,
            competency_id="C_SOFT_COMM",
            parent_question_id="Q_DRAFT_SOFT1_01",
        )
        assert followups[0].question_id == "FU_Q_DRAFT_SOFT1_01_01"
        assert followups[0].parent_question_id == "Q_DRAFT_SOFT1_01"


def test_repeated_apply_is_idempotent_and_does_not_downgrade_existing_approval(
    database, pack
) -> None:
    with Session(database) as session:
        import_content(session, pack, apply=True)
        question = session.get(QuestionBankRow, ("Q_DRAFT_SOFT1_01", "1.0.0"))
        assert question is not None
        question.approval_status = "approved"
        question.approved_by = "existing-reviewer"
        session.commit()

        result = import_content(session, pack, apply=True)
        preserved = session.get(QuestionBankRow, ("Q_DRAFT_SOFT1_01", "1.0.0"))
        assert result.inserted_questions == 0
        assert result.unchanged_questions == 200
        assert preserved is not None
        assert preserved.approval_status == "approved"
        assert preserved.approved_by == "existing-reviewer"
        assert _counts(session) == (22, 22, 200)


def test_conflict_and_failed_flush_roll_back_all_import_rows(database, pack, monkeypatch) -> None:
    with Session(database) as session:
        import_content(session, pack, apply=True)
        existing = session.get(QuestionBankRow, ("Q_DRAFT_SOFT1_01", "1.0.0"))
        assert existing is not None
        existing.text = "Conflicting local edit"
        session.commit()
        with pytest.raises(ContentImportError, match="Import conflicts detected"):
            import_content(session, pack, apply=True)
        assert _counts(session) == (22, 22, 200)

    rollback_engine = create_engine("sqlite://")
    Base.metadata.create_all(rollback_engine)
    fresh = Session(rollback_engine)
    original_flush = fresh.flush

    def fail_flush(*args, **kwargs):
        original_flush(*args, **kwargs)
        raise RuntimeError("forced persistence failure")

    monkeypatch.setattr(fresh, "flush", fail_flush)
    with pytest.raises(RuntimeError, match="forced persistence failure"):
        import_content(fresh, pack, apply=True)
    fresh.close()
    with Session(rollback_engine) as verify:
        assert _counts(verify) == (0, 0, 0)
    rollback_engine.dispose()

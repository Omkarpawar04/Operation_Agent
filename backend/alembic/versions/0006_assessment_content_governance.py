"""Versioned assessment content and question provenance.

Revision ID: 0006_content_governance
Revises: 0005_rate_limit_counters
"""

import sqlalchemy as sa

from alembic import op

revision = "0006_content_governance"
down_revision = "0005_rate_limit_counters"
branch_labels = None
depends_on = None

_STAGES = "'soft_1','soft_2','soft_3','technical_1','technical_2','technical_3'"
_STATUSES = "'draft','review','approved','retired'"


def upgrade() -> None:
    op.add_column("questions", sa.Column("provenance_json", sa.JSON(), nullable=True))
    op.create_table(
        "assessment_competencies",
        sa.Column("competency_id", sa.String(length=120), nullable=False),
        sa.Column("stage_id", sa.String(length=30), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("definition", sa.Text(), nullable=False),
        sa.Column("content_version", sa.String(length=80), nullable=False),
        sa.Column("approval_status", sa.String(length=20), nullable=False),
        sa.Column("content_source", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by", sa.String(length=255), nullable=True),
        sa.CheckConstraint(
            f"stage_id IN ({_STAGES})", name="ck_assessment_competencies_stage_valid"
        ),
        sa.CheckConstraint(
            f"approval_status IN ({_STATUSES})",
            name="ck_assessment_competencies_approval_status_valid",
        ),
        sa.PrimaryKeyConstraint("competency_id", name="pk_assessment_competencies"),
    )
    op.create_index(
        "ix_assessment_competencies_stage_id", "assessment_competencies", ["stage_id"]
    )
    op.create_index(
        "ix_assessment_competencies_approval_status",
        "assessment_competencies",
        ["approval_status"],
    )
    op.create_table(
        "assessment_rubrics",
        sa.Column("rubric_version_id", sa.String(length=160), nullable=False),
        sa.Column("rubric_id", sa.String(length=120), nullable=False),
        sa.Column("competency_id", sa.String(length=120), nullable=False),
        sa.Column("dimensions_json", sa.JSON(), nullable=False),
        sa.Column("scoring_scale_json", sa.JSON(), nullable=False),
        sa.Column("evidence_requirements_json", sa.JSON(), nullable=False),
        sa.Column("insufficient_evidence_json", sa.JSON(), nullable=False),
        sa.Column("content_version", sa.String(length=80), nullable=False),
        sa.Column("approval_status", sa.String(length=20), nullable=False),
        sa.Column("content_source", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by", sa.String(length=255), nullable=True),
        sa.CheckConstraint(
            f"approval_status IN ({_STATUSES})",
            name="ck_assessment_rubrics_approval_status_valid",
        ),
        sa.ForeignKeyConstraint(
            ["competency_id"], ["assessment_competencies.competency_id"],
            name="fk_rubric_competency",
        ),
        sa.PrimaryKeyConstraint("rubric_version_id", name="pk_assessment_rubrics"),
    )
    op.create_index("ix_assessment_rubrics_rubric_id", "assessment_rubrics", ["rubric_id"])
    op.create_index(
        "ix_assessment_rubrics_competency_id", "assessment_rubrics", ["competency_id"]
    )
    op.create_index(
        "ix_assessment_rubrics_approval_status", "assessment_rubrics", ["approval_status"]
    )
    op.create_table(
        "assessment_question_bank",
        sa.Column("question_id", sa.String(length=120), nullable=False),
        sa.Column("stage_id", sa.String(length=30), nullable=False),
        sa.Column("competency_id", sa.String(length=120), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=30), nullable=False),
        sa.Column("difficulty", sa.String(length=40), nullable=False),
        sa.Column("expected_answer_json", sa.JSON(), nullable=False),
        sa.Column("rubric_version_id", sa.String(length=160), nullable=False),
        sa.Column("content_version", sa.String(length=80), nullable=False),
        sa.Column("approval_status", sa.String(length=20), nullable=False),
        sa.Column("content_source", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by", sa.String(length=255), nullable=True),
        sa.CheckConstraint(
            f"stage_id IN ({_STAGES})", name="ck_assessment_question_bank_stage_valid"
        ),
        sa.CheckConstraint(
            "category IN ('base','follow_up','clarification')",
            name="ck_assessment_question_bank_category_valid",
        ),
        sa.CheckConstraint(
            f"approval_status IN ({_STATUSES})",
            name="ck_assessment_question_bank_approval_status_valid",
        ),
        sa.ForeignKeyConstraint(
            ["competency_id"], ["assessment_competencies.competency_id"],
            name="fk_qbank_competency",
        ),
        sa.ForeignKeyConstraint(
            ["rubric_version_id"], ["assessment_rubrics.rubric_version_id"],
            name="fk_qbank_rubric",
        ),
        sa.PrimaryKeyConstraint("question_id", name="pk_assessment_question_bank"),
    )
    for column in ("stage_id", "competency_id", "rubric_version_id", "approval_status"):
        op.create_index(
            f"ix_assessment_question_bank_{column}", "assessment_question_bank", [column]
        )


def downgrade() -> None:
    for column in ("stage_id", "competency_id", "rubric_version_id", "approval_status"):
        op.drop_index(
            f"ix_assessment_question_bank_{column}", table_name="assessment_question_bank"
        )
    op.drop_table("assessment_question_bank")
    op.drop_index("ix_assessment_rubrics_approval_status", table_name="assessment_rubrics")
    op.drop_index("ix_assessment_rubrics_competency_id", table_name="assessment_rubrics")
    op.drop_index("ix_assessment_rubrics_rubric_id", table_name="assessment_rubrics")
    op.drop_table("assessment_rubrics")
    op.drop_index(
        "ix_assessment_competencies_approval_status", table_name="assessment_competencies"
    )
    op.drop_index("ix_assessment_competencies_stage_id", table_name="assessment_competencies")
    op.drop_table("assessment_competencies")
    op.drop_column("questions", "provenance_json")

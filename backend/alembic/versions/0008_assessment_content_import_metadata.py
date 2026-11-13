"""Preserve controlled assessment-pack metadata and follow-up ancestry.

Revision ID: 0008_content_pack_metadata
Revises: 0007_question_content_versions
"""

import sqlalchemy as sa

from alembic import op

revision = "0008_content_pack_metadata"
down_revision = "0007_question_content_versions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "assessment_competencies",
        sa.Column("stage_ids_json", sa.JSON(), nullable=True),
    )
    op.add_column(
        "assessment_competencies",
        sa.Column("content_metadata_json", sa.JSON(), nullable=True),
    )
    op.add_column(
        "assessment_rubrics",
        sa.Column("content_metadata_json", sa.JSON(), nullable=True),
    )
    op.add_column(
        "assessment_question_bank",
        sa.Column("parent_question_id", sa.String(length=120), nullable=True),
    )
    op.add_column(
        "assessment_question_bank",
        sa.Column("parent_content_version", sa.String(length=80), nullable=True),
    )
    op.add_column(
        "assessment_question_bank",
        sa.Column(
            "development_eligible",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "assessment_question_bank",
        sa.Column("content_metadata_json", sa.JSON(), nullable=True),
    )
    op.create_foreign_key(
        "fk_qbank_parent_question",
        "assessment_question_bank",
        "assessment_question_bank",
        ["parent_question_id", "parent_content_version"],
        ["question_id", "content_version"],
    )
    op.create_index(
        "ix_assessment_question_bank_development_eligible",
        "assessment_question_bank",
        ["development_eligible"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_assessment_question_bank_development_eligible",
        table_name="assessment_question_bank",
    )
    op.drop_constraint(
        "fk_qbank_parent_question", "assessment_question_bank", type_="foreignkey"
    )
    for column in (
        "content_metadata_json",
        "development_eligible",
        "parent_content_version",
        "parent_question_id",
    ):
        op.drop_column("assessment_question_bank", column)
    op.drop_column("assessment_rubrics", "content_metadata_json")
    op.drop_column("assessment_competencies", "content_metadata_json")
    op.drop_column("assessment_competencies", "stage_ids_json")

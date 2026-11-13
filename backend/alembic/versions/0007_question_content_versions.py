"""Allow stable question IDs to retain multiple content versions.

Revision ID: 0007_question_content_versions
Revises: 0006_content_governance
"""

import sqlalchemy as sa

from alembic import op

revision = "0007_question_content_versions"
down_revision = "0006_content_governance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "pk_assessment_question_bank", "assessment_question_bank", type_="primary"
    )
    op.create_primary_key(
        "pk_assessment_question_bank",
        "assessment_question_bank",
        ["question_id", "content_version"],
    )
    op.create_index(
        "uq_assessment_question_bank_approved_version",
        "assessment_question_bank",
        ["question_id"],
        unique=True,
        postgresql_where=sa.text("approval_status = 'approved'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_assessment_question_bank_approved_version",
        table_name="assessment_question_bank",
    )
    op.drop_constraint(
        "pk_assessment_question_bank", "assessment_question_bank", type_="primary"
    )
    op.create_primary_key(
        "pk_assessment_question_bank", "assessment_question_bank", ["question_id"]
    )

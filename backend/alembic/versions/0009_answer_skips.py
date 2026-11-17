"""Persist skipped-answer status."""

import sqlalchemy as sa

from alembic import op

revision = "0009_answer_skips"
down_revision = "0008_content_pack_metadata"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "answers",
        sa.Column("is_skipped", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("answers", "is_skipped")

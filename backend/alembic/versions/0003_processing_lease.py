"""Track and recover expired in-flight provider operations.

Revision ID: 0003_processing_lease
Revises: 0002_active_interview_scope
"""

import sqlalchemy as sa

from alembic import op

revision = "0003_processing_lease"
down_revision = "0002_active_interview_scope"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "interview_sessions",
        sa.Column("processing_started_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("interview_sessions", "processing_started_at")

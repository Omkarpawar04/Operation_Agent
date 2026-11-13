"""Record transcript erasure without retaining transcript content.

Revision ID: 0004_transcript_deletion_audit
Revises: 0003_processing_lease
"""

import sqlalchemy as sa

from alembic import op

revision = "0004_transcript_deletion_audit"
down_revision = "0003_processing_lease"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "transcript_deletion_audit",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_transcript_deletion_audit_student_id",
        "transcript_deletion_audit",
        ["student_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_transcript_deletion_audit_student_id", table_name="transcript_deletion_audit")
    op.drop_table("transcript_deletion_audit")

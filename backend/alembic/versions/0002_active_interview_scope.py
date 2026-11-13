"""Enforce one active interview per student and stage/course scope.

Revision ID: 0002_active_interview_scope
Revises: 0001_initial
"""

from alembic import op

revision = "0002_active_interview_scope"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    active = (
        "state IN ('created','awaiting_answer','answer_processing','awaiting_follow_up_answer')"
    )
    op.create_index(
        "uq_active_soft_interview_scope",
        "interview_sessions",
        ["student_id", "stage"],
        unique=True,
        postgresql_where=f"course_id IS NULL AND {active}",
        sqlite_where=f"course_id IS NULL AND {active}",
    )
    op.create_index(
        "uq_active_technical_interview_scope",
        "interview_sessions",
        ["student_id", "stage", "course_id"],
        unique=True,
        postgresql_where=f"course_id IS NOT NULL AND {active}",
        sqlite_where=f"course_id IS NOT NULL AND {active}",
    )


def downgrade() -> None:
    op.drop_index("uq_active_technical_interview_scope", table_name="interview_sessions")
    op.drop_index("uq_active_soft_interview_scope", table_name="interview_sessions")

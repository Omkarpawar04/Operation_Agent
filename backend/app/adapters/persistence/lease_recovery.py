import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import InterviewSessionRow, QuestionRow
from app.domain.interviews.models import InterviewState, QuestionKind
from app.ports.lease_recovery import ExpiredLeaseRecoveryPort

logger = logging.getLogger(__name__)


class SqlAlchemyExpiredLeaseRecovery(ExpiredLeaseRecoveryPort):
    """Claim expired sessions with PostgreSQL SKIP LOCKED and restore retryable state."""

    def __init__(self, session: Session, lease_seconds: int) -> None:
        self._session = session
        self._lease_seconds = lease_seconds

    def recover_expired(self, limit: int) -> int:
        cutoff = datetime.now(UTC) - timedelta(seconds=self._lease_seconds)
        rows = self._session.scalars(
            select(InterviewSessionRow)
            .where(
                InterviewSessionRow.state == InterviewState.ANSWER_PROCESSING.value,
                InterviewSessionRow.processing_started_at.is_not(None),
                InterviewSessionRow.processing_started_at < cutoff,
            )
            .order_by(InterviewSessionRow.processing_started_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        ).all()
        recovered = 0
        for row in rows:
            question = (
                self._session.get(QuestionRow, row.active_question_id)
                if row.active_question_id
                else None
            )
            row.state = (
                InterviewState.AWAITING_ANSWER.value
                if question is None or question.kind == QuestionKind.BASE.value
                else InterviewState.AWAITING_FOLLOW_UP_ANSWER.value
            )
            row.version += 1
            row.processing_started_at = None
            recovered += 1
        self._session.commit()
        if recovered:
            logger.info("expired_answer_leases_recovered count=%s", recovered)
        return recovered

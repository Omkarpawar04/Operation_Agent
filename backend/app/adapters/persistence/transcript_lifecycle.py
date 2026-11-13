from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    AnswerRow,
    AssessmentAttemptRow,
    AssessmentResultRow,
    EvaluationRow,
    InterviewSessionRow,
    QuestionRow,
    TranscriptDeletionAuditRow,
)
from app.ports.transcript_lifecycle import TranscriptLifecyclePort


class SqlAlchemyTranscriptLifecycle(TranscriptLifecyclePort):
    """Erase transcript-bearing fields and audit only student and time in one transaction."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def delete_student_transcripts(self, student_id: UUID) -> int:
        session_ids = list(
            self._session.scalars(
                select(InterviewSessionRow.id).where(InterviewSessionRow.student_id == student_id)
            ).all()
        )
        if not session_ids:
            return 0
        has_unredacted_content = self._session.scalar(
            select(AnswerRow.id)
            .where(
                AnswerRow.session_id.in_(session_ids),
                AnswerRow.transcript != "[deleted]",
            )
            .limit(1)
        ) or self._session.scalar(
            select(QuestionRow.id)
            .where(
                QuestionRow.session_id.in_(session_ids),
                QuestionRow.text != "[deleted]",
            )
            .limit(1)
        )
        if has_unredacted_content is None:
            return 0
        return self._erase(session_ids)

    def delete_expired_transcripts(self, before: datetime, limit: int) -> int:
        session_ids = list(
            self._session.scalars(
                select(InterviewSessionRow.id)
                .where(
                    InterviewSessionRow.created_at < before,
                    InterviewSessionRow.state.in_(("completed", "abandoned", "failed")),
                )
                .order_by(InterviewSessionRow.created_at)
                .limit(limit)
                .with_for_update(skip_locked=True)
            ).all()
        )
        return self._erase(session_ids)

    def _erase(self, session_ids: list[UUID]) -> int:
        if not session_ids:
            return 0
        attempt_ids = list(
            self._session.scalars(
                select(AssessmentAttemptRow.id).where(
                    AssessmentAttemptRow.session_id.in_(session_ids)
                )
            ).all()
        )
        self._session.query(InterviewSessionRow).filter(
            InterviewSessionRow.id.in_(session_ids),
            InterviewSessionRow.state.in_(
                ("created", "awaiting_answer", "answer_processing", "awaiting_follow_up_answer")
            ),
        ).update(
            {
                InterviewSessionRow.state: "abandoned",
                InterviewSessionRow.processing_started_at: None,
                InterviewSessionRow.version: InterviewSessionRow.version + 1,
            },
            synchronize_session=False,
        )
        if attempt_ids:
            self._session.query(AssessmentAttemptRow).filter(
                AssessmentAttemptRow.id.in_(attempt_ids),
                AssessmentAttemptRow.status == "in_progress",
            ).update({AssessmentAttemptRow.status: "abandoned"}, synchronize_session=False)
        answer_ids = list(
            self._session.scalars(
                select(AnswerRow.id).where(AnswerRow.session_id.in_(session_ids))
            ).all()
        )
        fresh_answer_count = (
            self._session.query(AnswerRow)
            .filter(AnswerRow.session_id.in_(session_ids), AnswerRow.transcript != "[deleted]")
            .count()
        )
        if answer_ids:
            self._session.query(EvaluationRow).filter(
                EvaluationRow.answer_id.in_(answer_ids)
            ).update({EvaluationRow.evidence_json: []}, synchronize_session=False)
        if attempt_ids:
            self._session.query(AssessmentResultRow).filter(
                AssessmentResultRow.attempt_id.in_(attempt_ids)
            ).update({AssessmentResultRow.evidence_json: []}, synchronize_session=False)
        self._session.query(AnswerRow).filter(AnswerRow.session_id.in_(session_ids)).update(
            {AnswerRow.transcript: "[deleted]"}, synchronize_session=False
        )
        self._session.query(QuestionRow).filter(QuestionRow.session_id.in_(session_ids)).update(
            {QuestionRow.text: "[deleted]"}, synchronize_session=False
        )
        self._session.add_all(
            TranscriptDeletionAuditRow(id=uuid4(), student_id=owner)
            for owner in self._session.scalars(
                select(InterviewSessionRow.student_id)
                .where(InterviewSessionRow.id.in_(session_ids))
                .distinct()
            ).all()
        )
        self._session.commit()
        return int(fresh_answer_count)

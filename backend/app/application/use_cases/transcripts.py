from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.ports.transcript_lifecycle import TranscriptLifecyclePort


class DeleteStudentTranscripts:
    def __init__(self, lifecycle: TranscriptLifecyclePort) -> None:
        self._lifecycle = lifecycle

    def execute(self, student_id: UUID) -> int:
        return self._lifecycle.delete_student_transcripts(student_id)


class EnforceTranscriptRetention:
    def __init__(
        self,
        lifecycle: TranscriptLifecyclePort,
        retention_days: int,
        batch_size: int = 100,
    ) -> None:
        if retention_days < 1 or batch_size < 1:
            raise ValueError("Retention and batch size must be positive")
        self._lifecycle = lifecycle
        self._retention_days = retention_days
        self._batch_size = batch_size

    def execute(self, now: datetime | None = None) -> int:
        reference = now or datetime.now(UTC)
        if reference.tzinfo is None:
            raise ValueError("Retention clock must be timezone-aware")
        return self._lifecycle.delete_expired_transcripts(
            reference - timedelta(days=self._retention_days), self._batch_size
        )

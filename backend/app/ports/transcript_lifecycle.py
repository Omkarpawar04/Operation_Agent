from datetime import datetime
from typing import Protocol
from uuid import UUID


class TranscriptLifecyclePort(Protocol):
    def delete_student_transcripts(self, student_id: UUID) -> int: ...

    def delete_expired_transcripts(self, before: datetime, limit: int) -> int: ...

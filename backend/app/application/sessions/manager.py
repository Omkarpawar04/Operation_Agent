from uuid import UUID

from app.core.errors import Conflict, EnrollmentRequired, RetakeLimitReached, StageLocked
from app.domain.assessments.attempts import RetakePolicy
from app.domain.interviews.models import InterviewStage
from app.ports.sessions import SessionRecord, SessionStartPort, StartSessionCommand


class SessionManager:
    def __init__(
        self, repository: SessionStartPort, retake_policy: RetakePolicy | None = None
    ) -> None:
        self._repository = repository
        self._retake_policy = retake_policy or RetakePolicy()

    def has_active_enrollment(self, student_id: UUID, course_id: UUID) -> bool:
        return self._repository.enrolled(student_id, course_id)

    def find_existing(self, command: StartSessionCommand) -> SessionRecord | None:
        existing = self._repository.find_existing(command.student_id, command.idempotency_key)
        if existing is not None:
            if existing.stage != command.stage.value or existing.course_id != command.course_id:
                raise Conflict("Idempotency key reused with a different request")
        return existing 

    def validate_start(self, command: StartSessionCommand) -> UUID | None:
        if self.find_existing(command) is not None:
            return None
        return self._validate_eligibility(command)

    def _validate_eligibility(self, command: StartSessionCommand) -> UUID | None:
        revision_id = None
        if command.stage.technical:
            if command.course_id is None or not self._repository.enrolled(
                command.student_id, command.course_id
            ):
                raise EnrollmentRequired("Active course enrollment required")
            revision_id = self._repository.approved_revision(command.course_id)
            if revision_id is None:
                raise Conflict("Approved course content is not configured")
            if (
                command.expected_content_revision_id is not     None
                and revision_id != command.expected_content_revision_id
            ):
                raise Conflict("Approved course content changed; retry with the latest revision")
        elif command.course_id is not None:
            raise Conflict("Soft-skills stages do not accept a course id")
        completed_count, last_completed_at = self._repository.completed_attempt_history(
            command.student_id, command.stage, command.course_id
        )
        if not self._retake_policy.allows_start(completed_count, last_completed_at):
            raise RetakeLimitReached("Attempt limit or cooldown prevents starting this stage")
        previous_stage = (
            list(InterviewStage)[command.stage.order - 1] if command.stage.order else None
        )
        if previous_stage and not self._repository.stage_passed(
            command.student_id,
            previous_stage,
            command.course_id if previous_stage.technical else None,
        ):
            raise StageLocked("This interview stage is locked")
        return revision_id
    
    def start(self, command: StartSessionCommand) -> SessionRecord:
        existing = self.find_existing(command)
        if existing is not None:
            return existing
        return self._repository.create(
            command,
            command.expected_content_revision_id,
            lambda: self._validate_eligibility(command),
        )

    def release_read_transaction(self) -> None:
        """End eligibility reads before an external provider call."""
        self._repository.rollback_read_transaction()

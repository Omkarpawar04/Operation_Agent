from app.core.errors import Conflict
from app.domain.interviews.models import InterviewSession, InterviewState, transition


class InterviewStateManager:
    """Applies deterministic transition and version rules to session commands."""

    def abandon(self, session: InterviewSession, expected_version: int) -> None:
        if session.state is InterviewState.ABANDONED and session.version == expected_version + 1:
            return
        try:
            transition(session, InterviewState.ABANDONED, expected_version)
        except ValueError as exc:
            raise Conflict(str(exc)) from exc

from uuid import UUID

from app.core.config import Settings
from app.ports.services import Principal


class DevelopmentIdentityAdapter:
    """Local-only identity adapter; production authentication fails closed."""

    def __init__(self, settings: Settings) -> None:
        if not settings.development_auth_enabled:
            raise RuntimeError("Development identity adapter cannot run outside development/test")
        self._settings = settings

    def resolve(self, presented_identity: str | None) -> Principal:
        if not presented_identity:
            raise ValueError("A development identity header is required")
        try:
            user_id = UUID(presented_identity)
        except ValueError as exc:
            raise ValueError("Invalid development identity") from exc
        return Principal(user_id)

from typing import Protocol

from app.ports.services import Principal


class IdentityProvider(Protocol):
    def resolve(self, presented_identity: str | None) -> Principal: ...

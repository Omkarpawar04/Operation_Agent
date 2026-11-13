from typing import Protocol


class ExpiredLeaseRecoveryPort(Protocol):
    """Atomically recover a bounded batch of expired answer reservations."""

    def recover_expired(self, limit: int) -> int: ...

from app.ports.lease_recovery import ExpiredLeaseRecoveryPort


class RecoverExpiredLeases:
    """Application boundary for periodic answer-reservation recovery."""

    def __init__(self, recovery: ExpiredLeaseRecoveryPort, batch_size: int = 100) -> None:
        if batch_size < 1:
            raise ValueError("batch_size must be positive")
        self._recovery = recovery
        self._batch_size = batch_size

    def execute(self) -> int:
        return self._recovery.recover_expired(self._batch_size)

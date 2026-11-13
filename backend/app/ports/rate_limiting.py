from datetime import datetime
from typing import Protocol


class RateLimitPort(Protocol):
    def consume(self, scope: str, now: datetime, window_seconds: int) -> int: ...

from typing import Protocol


class ReadinessPort(Protocol):
    def check(self) -> None: ...

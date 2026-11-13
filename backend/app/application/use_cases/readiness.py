from app.ports.readiness import ReadinessPort


class CheckReadiness:
    def __init__(self, readiness: ReadinessPort) -> None:
        self._readiness = readiness

    def execute(self) -> dict[str, str]:
        self._readiness.check()
        return {"status": "ready"}

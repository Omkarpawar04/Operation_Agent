from app.domain.interviews.decision import (
    AnalysisRecommendation,
    DecisionLimits,
    InterviewAction,
    decide,
)
from app.domain.interviews.models import InterviewSession


class InterviewDecisionPolicy:
    """Deterministic policy adapter; never receives a score or pass/fail signal."""

    def __init__(self, limits: DecisionLimits) -> None:
        self._limits = limits

    def choose(
        self, session: InterviewSession, recommendation: AnalysisRecommendation
    ) -> InterviewAction:
        return decide(session, self._limits, recommendation)

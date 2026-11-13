from dataclasses import dataclass

from app.application.orchestrator.policy import InterviewDecisionPolicy
from app.domain.assessments.models import EvaluationEvidence, Rubric
from app.domain.interviews.decision import AnalysisRecommendation, InterviewAction
from app.domain.interviews.models import InterviewSession, Question, QuestionKind
from app.ports.interview_services import (
    AnalysisOutput,
    AnswerAnalyzer,
    ContextManager,
    FollowUpEngine,
    QuestionEngine,
)


@dataclass(frozen=True, slots=True)
class OrchestrationResult:
    action: InterviewAction
    evidence: tuple[EvaluationEvidence, ...]
    next_question: Question | None


class InterviewOrchestrator:
    """Coordinates focused services; state, scoring and progression remain separate."""

    def __init__(
        self,
        context_manager: ContextManager,
        analyzer: AnswerAnalyzer,
        follow_up_engine: FollowUpEngine,
        question_engine: QuestionEngine,
        decision_policy: InterviewDecisionPolicy,
    ) -> None:
        self._context = context_manager
        self._analyzer = analyzer
        self._follow_ups = follow_up_engine
        self._questions = question_engine
        self._decision = decision_policy

    def process_answer(
        self,
        session: InterviewSession,
        active_question: Question,
        answer_text: str,
        rubric: Rubric,
    ) -> OrchestrationResult:
        context = self._context.build(session, active_question)
        analysis: AnalysisOutput = self._analyzer.analyze(answer_text, context, rubric)
        follow_up = None
        clarification = None
        if analysis.follow_up_text:
            candidate = self._follow_ups.validate_follow_up(
                analysis.follow_up_text, active_question, context
            )
            if self._valid_child(candidate, session, active_question, QuestionKind.FOLLOW_UP):
                follow_up = candidate
        if analysis.clarification_text:
            candidate = self._follow_ups.validate_clarification(
                analysis.clarification_text, active_question
            )
            if self._valid_child(candidate, session, active_question, QuestionKind.CLARIFICATION):
                clarification = candidate
        recommendation = AnalysisRecommendation(
            follow_up_text=follow_up.text if follow_up else None,
            clarification_text=clarification.text if clarification else None,
            answer_needs_clarification=analysis.answer_needs_clarification,
        )
        action = self._decision.choose(session, recommendation)
        next_question = None
        if action is InterviewAction.FOLLOW_UP:
            next_question = follow_up
        elif action is InterviewAction.CLARIFICATION:
            next_question = clarification
        elif action is InterviewAction.NEXT_QUESTION:
            next_question = self._questions.next_question(session, session.base_question_count + 1)
            if (
                next_question.session_id != session.id
                or next_question.kind is not QuestionKind.BASE
                or next_question.sequence != session.base_question_count + 1
            ):
                raise ValueError("Question engine returned an invalid next question")
        return OrchestrationResult(action, analysis.evidence, next_question)

    @staticmethod
    def _valid_child(
        candidate: Question | None,
        session: InterviewSession,
        parent: Question,
        expected_kind: QuestionKind,
    ) -> bool:
        return bool(
            candidate
            and candidate.session_id == session.id
            and candidate.parent_question_id == parent.id
            and candidate.kind is expected_kind
        )

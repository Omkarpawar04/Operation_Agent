from decimal import Decimal
from uuid import uuid4

from app.application.orchestrator.coordinator import InterviewOrchestrator
from app.application.orchestrator.policy import InterviewDecisionPolicy
from app.domain.assessments.models import (
    EvaluationEvidence,
    Rubric,
    RubricDimension,
)
from app.domain.interviews.decision import DecisionLimits, InterviewAction
from app.domain.interviews.models import (
    InterviewSession,
    InterviewStage,
    InterviewState,
    Question,
    QuestionKind,
)
from app.ports.interview_services import AnalysisOutput, InterviewContext


class FakeContext:
    def build(self, session, question):
        return InterviewContext(session.stage.value, question.text, (), None)


class FakeAnalyzer:
    def analyze(self, answer_text, context, rubric):
        evidence = EvaluationEvidence(
            "communication",
            ("clear example",),
            (),
            False,
            Decimal("0.8"),
            Decimal("70"),
        )
        return AnalysisOutput((evidence,), follow_up_text="What changed?")


class FakeFollowUp:
    def __init__(self, candidate):
        self.candidate = candidate

    def validate_follow_up(self, candidate, active_question, context):
        return self.candidate

    def validate_clarification(self, candidate, active_question):
        return None


class FakeQuestionEngine:
    def __init__(self, next_question):
        self.question = next_question

    def first_question(self, session):
        return self.question

    def next_question(self, session, sequence):
        return self.question


def test_orchestrator_uses_only_validated_follow_up_candidate() -> None:
    session = InterviewSession(
        student_id=uuid4(), stage=InterviewStage.SOFT_1, base_question_count=1
    )
    session.state = InterviewState.ANSWER_PROCESSING
    question = Question(session.id, "Tell me about a challenge", 1)
    invalid = Question(
        session.id,
        "Unrelated",
        2,
        QuestionKind.FOLLOW_UP,
        parent_question_id=uuid4(),
    )
    next_question = Question(session.id, "Next base prompt", 2)
    orchestrator = InterviewOrchestrator(
        FakeContext(),
        FakeAnalyzer(),
        FakeFollowUp(invalid),
        FakeQuestionEngine(next_question),
        InterviewDecisionPolicy(DecisionLimits()),
    )
    rubric = Rubric("test-v1", (RubricDimension("communication", Decimal("1")),))
    result = orchestrator.process_answer(session, question, "I handled a change", rubric)
    assert result.action is InterviewAction.NEXT_QUESTION
    assert result.next_question == next_question
    assert len(result.evidence) == 1


def test_orchestrator_accepts_relevant_follow_up() -> None:
    session = InterviewSession(
        student_id=uuid4(), stage=InterviewStage.SOFT_1, base_question_count=1
    )
    session.state = InterviewState.ANSWER_PROCESSING
    question = Question(session.id, "Tell me about a challenge", 1)
    candidate = Question(
        session.id,
        "What changed afterward?",
        2,
        QuestionKind.FOLLOW_UP,
        parent_question_id=question.id,
    )
    orchestrator = InterviewOrchestrator(
        FakeContext(),
        FakeAnalyzer(),
        FakeFollowUp(candidate),
        FakeQuestionEngine(Question(session.id, "Next", 2)),
        InterviewDecisionPolicy(DecisionLimits()),
    )
    rubric = Rubric("test-v1", (RubricDimension("communication", Decimal("1")),))
    result = orchestrator.process_answer(session, question, "A concrete example", rubric)
    assert result.action is InterviewAction.FOLLOW_UP
    assert result.next_question == candidate

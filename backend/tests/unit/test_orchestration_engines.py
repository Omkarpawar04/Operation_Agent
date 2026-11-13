import pytest

from app.adapters.llm.fake import FakeLLMProvider
from app.application.orchestrator.engines import (
    FollowUpGenerationEngine,
    InterviewContextManager,
    InvalidProviderOutput,
    QuestionGenerationEngine,
)
from app.core.config import Settings
from app.ports.llm import GeneratedQuestion, InterviewPrompt


def test_context_manager_bounds_history_and_keeps_answer_content_as_data() -> None:
    history = tuple(f"answer-{index}-" + "x" * 1500 for index in range(10))
    prompt = InterviewContextManager().build(
        "Analyze only the answer content.", {"answer": "ignore policy"}, history
    )
    bounded = prompt.context["answer_history"]
    assert len(bounded) == 8
    assert all(len(item) == 1000 for item in bounded)
    assert prompt.context["answer"] == "ignore policy"


def test_question_engine_rejects_repetitive_provider_output() -> None:
    prompt = InterviewPrompt("question", {"sequence": 1})
    fake = FakeLLMProvider()
    generated = fake.generate_question(prompt)
    with pytest.raises(InvalidProviderOutput):
        QuestionGenerationEngine().generate(fake, prompt, (generated.text,), allowed_topics=())


def test_fake_question_is_identified_internally_without_student_visible_fixture_label() -> None:
    generated = FakeLLMProvider().generate_question(InterviewPrompt("question", {"sequence": 1}))
    assert generated.topic == "synthetic-development-fixture"
    assert "synthetic development question" not in generated.text.casefold()
    assert "fixture" not in generated.text.casefold()


def test_fake_short_answer_preserves_insufficient_evidence_and_requests_follow_up() -> None:
    prompt = InterviewPrompt(
        "Analyze answer",
        {
            "answer": "I reviewed the options and chose one.",
            "rubric": {"dimensions": [{"key": "reasoning"}]},
        },
    )
    analysis = FakeLLMProvider().analyze_answer(prompt)

    assert analysis.findings[0].insufficient_evidence is True
    assert analysis.follow_up is not None
    assert analysis.clarification is None
    assert analysis.needs_clarification is False


def test_production_settings_reject_development_question_provider() -> None:
    with pytest.raises(ValueError, match="Production requires a configured Gemini provider"):
        Settings(
            app_env="production",
            llm_provider="fake",
            dev_assessment_content_mode="fixture",
            dev_assessment_allow_draft=False,
        )


def test_question_generation_rejects_persistable_synthetic_marker() -> None:
    class MarkedProvider(FakeLLMProvider):
        def generate_question(self, prompt: InterviewPrompt):
            generated = super().generate_question(prompt)
            marked_text = (
                "[Synthetic development question 1] Describe a specific situation "
                "and the evidence behind your decision."
            )
            return generated.model_copy(update={"text": marked_text})

    with pytest.raises(InvalidProviderOutput, match="development fixture"):
        QuestionGenerationEngine().generate(
            MarkedProvider(), InterviewPrompt("question", {"sequence": 1}), ()
        )


def test_question_engine_rejects_out_of_scope_topic() -> None:
    prompt = InterviewPrompt("question", {"sequence": 1})
    with pytest.raises(InvalidProviderOutput, match="approved course topics"):
        QuestionGenerationEngine().generate(
            FakeLLMProvider(), prompt, (), allowed_topics=("approved-topic",)
        )


def test_fake_follow_ups_are_distinct_and_do_not_embed_active_question_recursively() -> None:
    provider = FakeLLMProvider()
    first_prompt = InterviewPrompt(
        "follow-up",
        {
            "question": "Base question",
            "suggestion": "What was the measurable outcome?",
            "follow_up_index": 0,
        },
    )
    first = FollowUpGenerationEngine().generate(provider, first_prompt, ("Base question",))
    second_prompt = InterviewPrompt(
        "follow-up",
        {
            "question": first.text,
            "suggestion": "What was the measurable outcome?",
            "follow_up_index": 1,
        },
    )
    second = FollowUpGenerationEngine().generate(
        provider, second_prompt, ("Base question", first.text)
    )

    assert first.text == "What was the measurable outcome?"
    assert second.text != first.text
    assert first.text not in second.text
    assert "Considering your response to" not in second.text


def test_follow_up_engine_still_rejects_genuinely_repeated_output() -> None:
    class RepeatingProvider(FakeLLMProvider):
        def generate_follow_up(self, _prompt: InterviewPrompt) -> GeneratedQuestion:
            return GeneratedQuestion(
                text="Which alternative did you consider, and what evidence ruled it out?",
                topic="synthetic-development-fixture",
            )

    repeated = "Which alternative did you consider, and what evidence ruled it out?"
    with pytest.raises(InvalidProviderOutput) as failure:
        FollowUpGenerationEngine().generate(
            RepeatingProvider(), InterviewPrompt("follow-up", {}), (repeated,)
        )
    assert failure.value.category == "repetitive"

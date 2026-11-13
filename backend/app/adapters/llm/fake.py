from app.ports.llm import (
    AnswerAnalysis,
    DimensionFinding,
    GeneratedQuestion,
    InterviewPrompt,
)


class FakeLLMProvider:
    """Deterministic local provider; output is explicitly synthetic development content."""

    provider_name = "fake"
    model_identifier = None
    development_only = True

    def generate_question(self, prompt: InterviewPrompt) -> GeneratedQuestion:
        raw_sequence = prompt.context.get("sequence", 1)
        sequence = raw_sequence if isinstance(raw_sequence, int) else 1
        prompts = (
            "Describe a specific situation and the evidence behind your decision.",
            "Explain how you would compare two options and verify the outcome.",
            "What tradeoffs would you consider before choosing an approach?",
            "Describe how you would improve the result after reviewing feedback.",
            "How would you communicate the outcome to the people affected?",
        )
        return GeneratedQuestion(
            text=prompts[(sequence - 1) % len(prompts)],
            topic="synthetic-development-fixture",
        )

    def analyze_answer(self, prompt: InterviewPrompt) -> AnswerAnalysis:
        text = str(prompt.context.get("answer", ""))
        substantial = len(text.split()) >= 12
        rubric = prompt.context.get("rubric")
        dimensions = rubric.get("dimensions") if isinstance(rubric, dict) else None
        dimension_keys = (
            tuple(
                str(item["key"])
                for item in dimensions
                if isinstance(item, dict) and isinstance(item.get("key"), str)
            )
            if isinstance(dimensions, list)
            else ()
        )
        if not dimension_keys:
            dimension_keys = (str(prompt.context.get("dimension", "communication")),)
        return AnswerAnalysis(
            findings=[
                DimensionFinding(
                    dimension_key=dimension_key,
                    evidence=["Student supplied a concrete text response"] if substantial else [],
                    missing_evidence=[] if substantial else ["A specific example and outcome"],
                    relevance=3 if substantial else 1,
                    correctness=3 if substantial else 1,
                    completeness=3 if substantial else 1,
                    insufficient_evidence=not substantial,
                    confidence=0.8 if substantial else 0.4,
                    explanation="Deterministic synthetic test analysis of answer content only.",
                )
                for dimension_key in dimension_keys
            ],
            # In the deterministic dev provider, insufficient evidence should lead to
            # a rubric follow-up. The question bank may not contain separate
            # clarification-category candidates for every parent question.
            follow_up=(
                "What was the measurable outcome?"
                if substantial
                else "Could you add one specific detail that supports your answer?"
            ),
            clarification=None,
            needs_clarification=False,
        )

    def generate_follow_up(self, prompt: InterviewPrompt) -> GeneratedQuestion:
        suggestion = str(
            prompt.context.get("suggestion", "What evidence supports that conclusion?")
        )
        raw_index = prompt.context.get("follow_up_index", 0)
        index = raw_index if isinstance(raw_index, int) and raw_index >= 0 else 0
        follow_ups = (
            suggestion,
            "Which alternative did you consider, and what evidence ruled it out?",
            "What measurable change showed that your approach worked?",
            "How did feedback from affected people change your next step?",
            "What assumption created the greatest risk, and how did you check it?",
            "Which constraint mattered most, and how did you account for it?",
            "What would you change after reviewing the outcome?",
            "How did you verify the result independently?",
            "What tradeoff did you accept, and why was it reasonable?",
            "Who was affected by the decision, and how did you respond to them?",
            "What evidence would have changed your decision at the time?",
            "How did the result compare with the outcome you expected?",
            "What part of the process took the most effort to validate?",
            "How did you reduce the chance of the same problem returning?",
            "What limitation remained after you completed the work?",
            "Which signal helped you decide that the work was complete?",
        )
        return GeneratedQuestion(
            text=follow_ups[index % len(follow_ups)],
            topic="synthetic-development-fixture",
        )

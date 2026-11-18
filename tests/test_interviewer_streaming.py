"""Groq streaming and compact interviewer input tests."""

import asyncio
import json
from types import SimpleNamespace

from agents.interviewer import InterviewerAgent


class FakeStream:
    def __init__(self, events):
        self.events = events

    def __aiter__(self):
        async def iterate():
            for event in self.events:
                yield event
        return iterate()


class FakeResponses:
    def __init__(self, stream):
        self.stream = stream
        self.options = None

    async def create(self, **kwargs):
        self.options = kwargs
        return self.stream


class FakeClient:
    def __init__(self, stream):
        self.responses = FakeResponses(stream)


def test_interviewer_collects_streamed_json_and_sends_compact_verbatim_context():
    output = json.dumps({
        "text": "Thanks. How did you test the API?",
        "action": "continue",
        "question_id": 2,
        "interview_complete": False,
    })
    client = FakeClient(FakeStream([
        SimpleNamespace(type="response.output_text.delta", delta=output[:20]),
        SimpleNamespace(type="response.output_text.delta", delta=output[20:]),
    ]))
    agent = InterviewerAgent(client=client)
    candidate_answer = "I built a FastAPI service with PostgreSQL."

    reply = asyncio.run(agent.generate_response(
        candidate_message=candidate_answer,
        interview_plan={
            "total_questions": 8,
            "questions": [{
                "id": 2,
                "category": "technical",
                "question": "How did you design the API?",
                "skills_tested": ["FastAPI"],
                "expected_answer_indicators": ["tradeoffs"],
            }],
        },
        conversation_history=[
            {"role": "assistant", "turn_type": "question", "content": "How did you design the API?"},
            {"role": "user", "turn_type": "answer", "content": candidate_answer},
        ],
        current_question={
            "id": 2,
            "category": "technical",
            "question": "How did you design the API?",
            "skills_tested": ["FastAPI"],
            "expected_answer_indicators": ["tradeoffs"],
        },
    ))

    assert reply.text == "Thanks. How did you test the API?"
    assert reply.question_id == "2"
    options = client.responses.options
    assert options["stream"] is True
    assert options["reasoning"] == {"effort": "low"}
    assert options["max_output_tokens"] == 260
    context = json.loads(options["input"])
    assert context["candidate_answer_verbatim"] == candidate_answer
    assert context["asked_question_ids"] == ["2"]
    assert context["recent_turns"] == [{
        "role": "assistant",
        "type": "question",
        "content": "How did you design the API?",
    }]
    assert "expected_answer_indicators" not in options["input"]
    assert agent.last_first_token_seconds is not None

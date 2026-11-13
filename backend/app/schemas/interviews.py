from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.interviews.models import InterviewStage, InterviewState


class StartInterviewRequest(BaseModel):
    stage: InterviewStage
    idempotency_key: str = Field(min_length=8, max_length=120)
    course_id: UUID | None = None


class AnswerRequest(BaseModel):
    question_id: UUID
    expected_version: int = Field(ge=0)
    idempotency_key: str = Field(min_length=8, max_length=120)
    text: str = Field(min_length=1, max_length=20000)

    @field_validator("text")
    @classmethod
    def require_nonblank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Answer text must not be blank")
        return value


class AbandonRequest(BaseModel):
    expected_version: int = Field(ge=0)


class InterviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    stage: InterviewStage
    state: InterviewState
    version: int
    active_question_id: UUID | None


class UserResponse(BaseModel):
    id: UUID
    role: str


class ProgressionItem(BaseModel):
    stage: InterviewStage
    status: str

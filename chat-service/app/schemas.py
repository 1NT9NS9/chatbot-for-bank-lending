from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, description="User question in Russian")
    session_id: str | None = Field(None, description="Optional session identifier")


class AskResponse(BaseModel):
    answer: str
    session_id: str 
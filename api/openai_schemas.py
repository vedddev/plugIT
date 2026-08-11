from pydantic import BaseModel, Field, field_validator
from typing import List, Optional


class OpenAIMessage(BaseModel):
    role: str
    content: str

    @field_validator("role")
    @classmethod
    def valid_role(cls, value: str) -> str:
        if value not in {"system", "user", "assistant"}:
            raise ValueError("Unsupported message role.")
        return value

    @field_validator("content")
    @classmethod
    def valid_content(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Message content must not be empty.")
        return value


class ChatCompletionRequest(BaseModel):
    model: str = "auto"
    messages: List[OpenAIMessage] = Field(min_length=1)
    stream: bool = False


class ChoiceMessage(BaseModel):
    role: str
    content: str


class Choice(BaseModel):
    index: int
    message: ChoiceMessage
    finish_reason: str = "stop"


class UsageModel(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponse(BaseModel):
    id: str
    object: str
    created: int
    model: str
    choices: List[Choice]
    usage: UsageModel

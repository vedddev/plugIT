from pydantic import BaseModel


class ChatRequest(BaseModel):
    prompt: str
    system_prompt: str | None = None


class ChatResponseModel(BaseModel):
    provider: str
    model: str
    content: str

    input_tokens: int
    output_tokens: int
    total_tokens: int

    latency_ms: float
    cost: float
    cached: bool
# providers/groq.py

import time
from typing import List

from openai import OpenAI

from providers.base import (
    BaseProvider,
    ChatMessage,
    ChatResponse,
    Usage,
)


class GroqProvider(BaseProvider):

    def __init__(self, api_key: str):
        super().__init__(api_key)

        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1",
        )

    @property
    def name(self) -> str:
        return "groq"

    def chat(
        self,
        messages: List[ChatMessage],
        model: str = "llama-3.1-8b-instant",
        **kwargs,
    ) -> ChatResponse:

        start = time.perf_counter()

        response = self.client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": m.role,
                    "content": m.content,
                }
                for m in messages
            ],
            **kwargs,
        )

        latency = (time.perf_counter() - start) * 1000

        usage = Usage(
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
            total_tokens=response.usage.total_tokens,
        )

        return ChatResponse(
            content=response.choices[0].message.content,
            provider=self.name,
            model=response.model,
            usage=usage,
            latency_ms=round(latency, 2),
            finish_reason=response.choices[0].finish_reason,
            metadata={
                "id": response.id,
            },
        )
        

    def list_models(self) -> List[str]:
        return [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "qwen/qwen3-32b",
            "deepseek-r1-distill-llama-70b",
        ]

    def health_check(self) -> bool:
        try:
            self.client.models.list()
            return True
        except Exception:
            return False
# providers/openai.py

import time
from typing import List

from openai import OpenAI

from providers.base import (
    BaseProvider,
    ChatMessage,
    ChatResponse,
    Usage,
)


class OpenAIProvider(BaseProvider):
    """
    OpenAI Provider Implementation
    """

    def __init__(self, api_key: str):
        super().__init__(api_key)

        self.client = OpenAI(
            api_key=api_key
        )

    @property
    def name(self) -> str:
        return "openai"

    def chat(
        self,
        messages: List[ChatMessage],
        model: str = "gpt-4.1-mini",
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
        """
        Supported models.

        Later you can fetch these dynamically.
        """

        return [
            "gpt-5",
            "gpt-5-mini",
            "gpt-4.1",
            "gpt-4.1-mini",
            "gpt-4o",
        ]

    def health_check(self) -> bool:
        try:
            self.client.models.list()
            return True
        except Exception:
            return False
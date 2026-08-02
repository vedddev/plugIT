# providers/gemini.py

import time
from typing import List

from google import genai

from providers.base import (
    BaseProvider,
    ChatMessage,
    ChatResponse,
    Usage,
)


class GeminiProvider(BaseProvider):

    def __init__(self, api_key: str):
        super().__init__(api_key)

        self.client = genai.Client(
            api_key=api_key
        )

    @property
    def name(self) -> str:
        return "gemini"

    @property
    def capabilities(self):
        return {
            "chat",
            "vision",
            "reasoning",
            "translation",
            "summarization",
            "coding",
        }

    def chat(
        self,
        messages: List[ChatMessage],
        model: str = "gemini-2.5-flash",
        **kwargs,
    ) -> ChatResponse:

        start = time.perf_counter()

        # Convert messages into one prompt
        prompt = "\n".join(
            f"{m.role}: {m.content}"
            for m in messages
        )

        response = self.client.models.generate_content(
            model=model,
            contents=prompt,
        )

        latency = (time.perf_counter() - start) * 1000

        usage = Usage()

        # Usage metadata (if available)
        if getattr(response, "usage_metadata", None):

            usage.input_tokens = (
                response.usage_metadata.prompt_token_count
            )

            usage.output_tokens = (
                response.usage_metadata.candidates_token_count
            )

            usage.total_tokens = (
                response.usage_metadata.total_token_count
            )

        return ChatResponse(
            content=response.text,
            provider=self.name,
            model=model,
            usage=usage,
            latency_ms=round(latency, 2),
            finish_reason="stop",
            metadata={}
        )

    def list_models(self):

        return [
            "gemini-2.5-flash",
            "gemini-2.5-pro",
        ]

    def health_check(self):

        try:
            self.client.models.list()
            return True
        except Exception:
            return False
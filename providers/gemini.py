# providers/gemini.py

import time
from typing import List

from google import genai

from providers.models import PROVIDER_MODELS

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
        model: str = "gemini-3.6-flash",
        **kwargs,
    ) -> ChatResponse:

        start = time.perf_counter()

        # Convert messages into one prompt
        prompt = "\n".join(
            f"{m.role}: {m.content}"
            for m in messages
        )

        response = self.client.models.generate_content(
            model=model if model.startswith("models/") else f"models/{model}",
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

    def stream_chat(self, messages: List[ChatMessage], model: str, **kwargs):
        prompt = "\n".join(f"{message.role}: {message.content}" for message in messages)
        for chunk in self.client.models.generate_content_stream(model=model if model.startswith("models/") else f"models/{model}", contents=prompt):
            text = getattr(chunk, "text", None)
            if text:
                yield text
    def list_models(self):
        return list(PROVIDER_MODELS[self.name])

    def health_check(self):

        try:
            self.client.models.list()
            return True
        except Exception:
            return False
# router/selector.py
from dataclasses import dataclass

from config import ROUTING_POLICY
from router.classifier import Classification
from providers.registry import ProviderRegistry


@dataclass
class Selection:
    provider: str
    model: str


class ModelSelector:

    def __init__(self, registry: ProviderRegistry):
        self.registry = registry

    def select(self, result: Classification) -> Selection:

        route = ROUTING_POLICY.get(
            result.task,
            ROUTING_POLICY["general"]
        )

        provider = route["provider"]

        # If the provider isn't registered, fall back
        if not self.registry.exists(provider):
            print(
                f"[Router] {provider} not available. "
                f"Falling back to Groq."
            )

            provider = "groq"
            route = ROUTING_POLICY["general"]

        return Selection(
            provider=provider,
            model=route["model"]
        )

    def select_by_model(self, model: str) -> Selection:
        """
        Find the provider that owns the requested model.
        Used by the OpenAI-compatible API when the client
        explicitly sends a model name.
        """

        for provider in self.registry.providers.values():

            models = provider.list_models()

            if model in models:
                return Selection(
                    provider=provider.name,
                    model=model,
                )

        raise ValueError(
            f"Model '{model}' is not available."
        )

    def default_model(self, provider):

        if provider == "groq":
            return "llama-3.3-70b-versatile"

        if provider == "gemini":
            return "gemini-2.5-flash"

        if provider == "openai":
            return "gpt-oss-20b"

        raise ValueError(provider)


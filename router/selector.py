from dataclasses import dataclass
from config import ROUTING_POLICY
from router.classifier import Classification
from providers.registry import ProviderRegistry
from providers.models import DEFAULT_MODELS
from router.exceptions import ModelNotFoundError


@dataclass
class Selection:
    provider: str
    model: str


class ModelSelector:
    def __init__(self, registry: ProviderRegistry):
        self.registry = registry

    def select(self, result: Classification) -> Selection:
        route = ROUTING_POLICY.get(result.task, ROUTING_POLICY["general"])
        provider = route["provider"]
        if not self.registry.exists(provider):
            provider = next(iter(self.registry.list()), None)
            if provider is None:
                raise RuntimeError("No providers are registered.")
            model = self.default_model(provider)
        else:
            model = route["model"]
        if model not in self.registry.get(provider).list_models():
            model = self.default_model(provider)
        return Selection(provider=provider, model=model)

    def select_by_model(self, model: str) -> Selection:
        for provider in self.registry.providers.values():
            if model in provider.list_models():
                return Selection(provider=provider.name, model=model)
        raise ModelNotFoundError(f"Model '{model}' is not available.")

    def default_model(self, provider: str) -> str:
        models = self.registry.get(provider).list_models()
        default = DEFAULT_MODELS.get(provider)
        if default in models:
            return default
        if models:
            return models[0]
        raise ValueError(f"Provider '{provider}' has no registered models.")

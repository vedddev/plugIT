# providers/registry.py

from typing import Dict
from providers.base import BaseProvider


class ProviderRegistry:

    def __init__(self):
        self.providers: Dict[str, BaseProvider] = {}

    def register(self, provider: BaseProvider):
        self.providers[provider.name] = provider

    def get(self, name: str) -> BaseProvider:
        if name not in self.providers:
            raise ValueError(f"Provider '{name}' not registered.")

        return self.providers[name]

    def exists(self, name: str) -> bool:
        return name in self.providers

    def list(self):
        return list(self.providers.keys())
# providers/base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
from typing import Iterator

# Message Structure

@dataclass
class ChatMessage:
    role: str
    content: str


# Usage Information

@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


# Chat Response

@dataclass
class ChatResponse:
    content: str
    provider: str
    model: str
    usage: Usage
    latency_ms: float

    cost: float = 0.0

    finish_reason: str | None = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """
        Convert ChatResponse into a JSON-serializable dictionary.
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict):
        """
        Recreate ChatResponse from a dictionary.
        """
        data = data.copy()
        data["usage"] = Usage(**data["usage"])
        return cls(**data)

# Base Provider

class BaseProvider(ABC):
    """
    Base class that every LLM provider must implement.
    """

    def __init__(self, api_key: str):
        self.api_key = api_key

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Provider name (openai, anthropic, gemini, etc.)
        """
        pass

    @abstractmethod
    def chat(
        self,
        messages: List[ChatMessage],
        model: str,
        **kwargs,
    ) -> ChatResponse:
        """
        Send a chat request to the provider.
        """
        pass
    @abstractmethod
    def stream_chat(
        self,
        messages: List[ChatMessage],
        model: str,
        **kwargs,
    ):
        raise NotImplementedError("Providers must implement provider-native streaming.")
    @abstractmethod
    def list_models(self) -> List[str]:
        """
        Return supported models.
        """
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """
        Check if provider is reachable.
        """
        pass




    
from dataclasses import dataclass
from typing import Iterator

from providers.base import ChatMessage, ChatResponse
from providers.registry import ProviderRegistry
from router.classifier import PromptClassifier
from router.selector import ModelSelector, Selection
from pricing.calculator import PricingCalculator
from analytics.tracker import AnalyticsTracker
from cache.redis_cache import RedisCache
from fallback.retry import RetryExecutor
from fallback.manager import CircuitManager
from fallback.fallback import FallbackExecutor
from router.exceptions import AllProvidersFailedError


def is_auto_model(model: str | None) -> bool:
    return model is None or model.strip().lower() == "auto"


@dataclass
class PreparedStream:
    """A provider stream whose first text delta has already been received."""

    iterator: Iterator[str]
    first_chunk: str
    provider: str
    model: str
    circuit: object
    api_key_id: str = "anonymous"
    user_id: str = "legacy-system"

    def close(self) -> None:
        close = getattr(self.iterator, "close", None)
        if close:
            close()


class SmartLLM:
    def __init__(self, registry: ProviderRegistry):
        self.registry = registry
        self.classifier = PromptClassifier()
        self.selector = ModelSelector(registry)
        self.calculator = PricingCalculator()
        self.tracker = AnalyticsTracker()
        self.cache = RedisCache()
        self.circuit_manager = CircuitManager()
        self.retry = RetryExecutor(retries=3, delay=1, backoff=2)
        self.fallback = FallbackExecutor(registry)

    def _select(self, prompt: str, model: str | None) -> Selection:
        if is_auto_model(model):
            classification = self.classifier.classify(prompt)
            selection = self.selector.select(classification)
            print(f"[Router] Mode: AUTO\n[Router] Task: {classification.task}")
        else:
            selection = self.selector.select_by_model(model)
            print(f"[Router] Mode: EXPLICIT\n[Router] Requested model: {model}")
        print(f"[Router] Selected provider: {selection.provider}\n[Router] Selected model: {selection.model}")
        return selection

    @staticmethod
    def _messages(prompt: str, system_prompt: str | None) -> list[ChatMessage]:
        messages = [ChatMessage(role="user", content=prompt)]
        if system_prompt:
            messages.insert(0, ChatMessage(role="system", content=system_prompt))
        return messages

    def _fallback_providers(self, primary: str) -> list[str]:
        return [name for name in self.registry.list() if name != primary]

    def _call(self, selection: Selection, messages: list[ChatMessage]) -> ChatResponse:
        circuit = self.circuit_manager.get(selection.provider)
        if circuit.allow_request():
            try:
                response = self.retry.run(self.registry.get(selection.provider).chat, messages=messages, model=selection.model)
                circuit.record_success()
                return response
            except Exception:
                circuit.record_failure()
                print(f"[Fallback] Primary failed: {selection.provider}")
        else:
            print(f"[Fallback] Primary skipped: {selection.provider} (circuit OPEN)")
        return self.fallback.execute(providers=self._fallback_providers(selection.provider), messages=messages, model_selector=self.selector.default_model, retry=self.retry, circuit_manager=self.circuit_manager)

    def chat(self, prompt: str, system_prompt: str | None = None, model: str | None = None, api_key_id: str = "anonymous", user_id: str = "legacy-system") -> ChatResponse:
        selection = self._select(prompt, model)
        try:
            cached = self.cache.get(prompt=prompt, model=selection.model, system_prompt=system_prompt)
        except Exception as error:
            # Cache availability must never prevent a provider request.
            print(f"[Cache] operation=get status=failed error={type(error).__name__}")
            cached = None
        if cached:
            print("[Cache] HIT")
            response = ChatResponse.from_dict(cached)
            response.latency_ms = 0.5
            response.metadata["cached"] = True
            self.tracker.log(provider=response.provider, model=response.model, prompt=prompt, input_tokens=response.usage.input_tokens, output_tokens=response.usage.output_tokens, total_tokens=response.usage.total_tokens, latency_ms=response.latency_ms, cost=response.cost, cached=True, success=True, api_key_id=api_key_id, user_id=user_id)
            return response
        print("[Cache] MISS")
        try:
            response = self._call(selection, self._messages(prompt, system_prompt))
            response.cost = self.calculator.calculate(response.provider, response.model, response.usage.input_tokens, response.usage.output_tokens)
            try:
                self.cache.set(prompt=prompt, model=selection.model, system_prompt=system_prompt, response=response.to_dict())
            except Exception as error:
                print(f"[Cache] operation=set status=failed error={type(error).__name__}")
            self.tracker.log(provider=response.provider, model=response.model, prompt=prompt, input_tokens=response.usage.input_tokens, output_tokens=response.usage.output_tokens, total_tokens=response.usage.total_tokens, latency_ms=response.latency_ms, cost=response.cost, success=True, api_key_id=api_key_id, user_id=user_id)
            return response
        except Exception:
            self.tracker.log(provider=selection.provider, model=selection.model, prompt=prompt, input_tokens=0, output_tokens=0, total_tokens=0, latency_ms=0, cost=0, success=False, api_key_id=api_key_id, user_id=user_id)
            raise

    def prepare_stream(self, prompt: str, system_prompt: str | None = None, model: str | None = None, api_key_id: str = "anonymous", user_id: str = "legacy-system") -> PreparedStream:
        """Open a stream and obtain its first delta before any HTTP bytes are sent.

        Only failures at this stage are eligible for retry/fallback.  Switching
        providers after a content delta would mix two completions.
        """
        selection = self._select(prompt, model)
        messages = self._messages(prompt, system_prompt)
        candidates = [selection.provider] + self._fallback_providers(selection.provider)
        failures = {}
        for provider_name in candidates:
            circuit = self.circuit_manager.get(provider_name)
            if not circuit.allow_request():
                failures[provider_name] = RuntimeError("circuit is OPEN")
                continue
            chosen_model = selection.model if provider_name == selection.provider else self.selector.default_model(provider_name)
            provider = self.registry.get(provider_name)
            try:
                print(f"[Stream] Starting provider stream: {provider_name}")
                iterator, first = self.retry.run(lambda: self._open_stream(provider, messages, chosen_model))
                print("[Stream] First chunk received")
                return PreparedStream(iterator, first, provider_name, chosen_model, circuit, api_key_id, user_id)
            except Exception as error:
                circuit.record_failure()
                failures[provider_name] = error
                print(f"[Stream] {provider_name} failed before first chunk")
                print("[Gateway] Switching provider...")
        raise AllProvidersFailedError(failures)

    def finish_stream(self, prepared: PreparedStream, prompt: str, success: bool | None) -> None:
        """Record a completed stream; ``None`` is a client-aborted stream."""
        if success is True:
            prepared.circuit.record_success()
            self.tracker.log(provider=prepared.provider, model=prepared.model, prompt=prompt, input_tokens=0, output_tokens=0, total_tokens=0, latency_ms=0, cost=0, success=True, api_key_id=prepared.api_key_id, user_id=prepared.user_id)
            print("[Stream] Stream completed")
        elif success is False:
            prepared.circuit.record_failure()
            self.tracker.log(provider=prepared.provider, model=prepared.model, prompt=prompt, input_tokens=0, output_tokens=0, total_tokens=0, latency_ms=0, cost=0, success=False, api_key_id=prepared.api_key_id, user_id=prepared.user_id)
            print("[Stream] Stream failed after it started; not falling back")

    def stream(self, prompt: str, system_prompt: str | None = None, model: str | None = None):
        """Backward-compatible text-delta iterator for non-OpenAI callers."""
        prepared = self.prepare_stream(prompt, system_prompt, model)
        return self.consume_prepared_stream(prepared, prompt)

    def consume_prepared_stream(self, prepared: PreparedStream, prompt: str):
        """Yield a preflighted stream and finalize its circuit/analytics state."""
        def generate():
            success = None
            try:
                yield prepared.first_chunk
                yield from prepared.iterator
                success = True
            except Exception:
                success = False
                raise
            finally:
                prepared.close()
                self.finish_stream(prepared, prompt, success)

        return generate()

    @staticmethod
    def _open_stream(provider, messages, model):
        iterator = iter(provider.stream_chat(messages=messages, model=model))
        try:
            return iterator, next(iterator)
        except StopIteration as error:
            close = getattr(iterator, "close", None)
            if close:
                close()
            raise RuntimeError("Provider stream ended before producing content.") from error
        except Exception:
            close = getattr(iterator, "close", None)
            if close:
                close()
            raise

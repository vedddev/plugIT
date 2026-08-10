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

    def chat(self, prompt: str, system_prompt: str | None = None, model: str | None = None) -> ChatResponse:
        selection = self._select(prompt, model)
        cached = self.cache.get(prompt=prompt, model=selection.model, system_prompt=system_prompt)
        if cached:
            print("[Cache] HIT")
            response = ChatResponse.from_dict(cached)
            response.latency_ms = 0.5
            response.metadata["cached"] = True
            self.tracker.log(provider=response.provider, model=response.model, prompt=prompt, input_tokens=response.usage.input_tokens, output_tokens=response.usage.output_tokens, total_tokens=response.usage.total_tokens, latency_ms=0, cost=response.cost, cached=True, success=True)
            return response
        print("[Cache] MISS")
        try:
            response = self._call(selection, self._messages(prompt, system_prompt))
            response.cost = self.calculator.calculate(response.provider, response.model, response.usage.input_tokens, response.usage.output_tokens)
            self.cache.set(prompt=prompt, model=selection.model, system_prompt=system_prompt, response=response.to_dict())
            self.tracker.log(provider=response.provider, model=response.model, prompt=prompt, input_tokens=response.usage.input_tokens, output_tokens=response.usage.output_tokens, total_tokens=response.usage.total_tokens, latency_ms=response.latency_ms, cost=response.cost, success=True)
            return response
        except Exception:
            self.tracker.log(provider=selection.provider, model=selection.model, prompt=prompt, input_tokens=0, output_tokens=0, total_tokens=0, latency_ms=0, cost=0, success=False)
            raise

    def stream(self, prompt: str, system_prompt: str | None = None, model: str | None = None):
        selection = self._select(prompt, model)
        messages = self._messages(prompt, system_prompt)
        candidates = [selection.provider] + self._fallback_providers(selection.provider)
        def generate():
            failures = {}
            for provider_name in candidates:
                circuit = self.circuit_manager.get(provider_name)
                if not circuit.allow_request():
                    failures[provider_name] = RuntimeError("circuit is OPEN")
                    continue
                chosen_model = selection.model if provider_name == selection.provider else self.selector.default_model(provider_name)
                provider = self.registry.get(provider_name)
                try:
                    iterator, first = self.retry.run(lambda: self._open_stream(provider, messages, chosen_model))
                    circuit.record_success()
                    yield first
                    for chunk in iterator:
                        yield chunk
                    return
                except Exception as error:
                    circuit.record_failure()
                    failures[provider_name] = error
                    print(f"[Fallback] {provider_name} failed before streaming started")
            raise AllProvidersFailedError(failures)
        return generate()

    @staticmethod
    def _open_stream(provider, messages, model):
        iterator = iter(provider.stream_chat(messages=messages, model=model))
        return iterator, next(iterator)

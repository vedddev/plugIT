from providers.base import ChatMessage, ChatResponse
from providers.registry import ProviderRegistry
from router.classifier import PromptClassifier
from router.selector import ModelSelector
from pricing.calculator import PricingCalculator
from analytics.tracker import AnalyticsTracker
from cache.redis_cache import RedisCache
from fallback.retry import RetryExecutor
# from fallback.circuit_breaker import CircuitBreaker
from fallback.manager import CircuitManager
from fallback.fallback import FallbackExecutor


 


class SmartLLM:

    def __init__(self, registry: ProviderRegistry):
        self.registry = registry
        self.classifier = PromptClassifier()
        self.selector = ModelSelector(self.registry)
        self.calculator = PricingCalculator()
        self.tracker = AnalyticsTracker()
        self.cache = RedisCache()
        self.circuit_manager = CircuitManager()
        self.retry = RetryExecutor(
                retries=3,
                delay=1,
                backoff=2,
            )
        self.fallback=FallbackExecutor(self.registry)

    def chat(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
    ) -> ChatResponse:

        # Step 1 - Classify
        classification = self.classifier.classify(prompt)

        # Step 2 - Select provider/model
        if model:
            selection = self.selector.select_by_model(model)
        else:
            selection = self.selector.select(classification)
            
        print(f"[Router] Requested model: {model}")
        print(f"[Router] Selected provider: {selection.provider}")
        print(f"[Router] Selected model: {selection.model}")

        cached = self.cache.get(
            prompt=prompt,
            model=selection.model,
        )
        
        # Step 3 - Check Redis Cache
        if cached:
            print("[Cache] HIT")

            response = ChatResponse.from_dict(cached)
            response.latency_ms = 0.5      
            response.metadata["cached"] = True
            
            self.tracker.log(
                provider=response.provider,
                model=response.model,
                prompt=prompt,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                total_tokens=response.usage.total_tokens,
                latency_ms=0,
                cost=response.cost,
                cached=True,
                success=True,
            )

            return response
        print("[Cache] MISS")
        
        # Step 4 - Get provider
        provider = self.registry.get(selection.provider)
        
        circuit = self.circuit_manager.get(selection.provider)

        if not circuit.allow_request():
            raise RuntimeError(
                f"{selection.provider} circuit is OPEN"
            )
        
        # Step 5 - Build messages
        messages = []

        if system_prompt:
            messages.append(
                ChatMessage(
                    role="system",
                    content=system_prompt,
                )
            )

        messages.append(
            ChatMessage(
                role="user",
                content=prompt,
            )
        )


        try:

            # Step 6 - Call Provider
            try:

                response = self.retry.run(
                    provider.chat,
                    messages=messages,
                    model=selection.model,
                )
                
                circuit.record_success()
                
            except Exception:

                print("[Gateway] Switching provider...")

                providers = [
                    p for p in self.registry.list()
                    if p != selection.provider
                ]

                response = self.fallback.execute(
                    providers=providers,
                    messages=messages,
                    model_selector=lambda p:
                        self.selector.default_model(p),
                )
            # Step 7 - Calculate Cost
            response.cost = self.calculator.calculate(
                provider=response.provider,
                model=response.model,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            )

            # Step 8 - Save to Redis
            self.cache.set(
                prompt=prompt,
                model=selection.model,
                response=response.to_dict(),
            )

            # Step 9 - Log Success
            self.tracker.log(
                provider=response.provider,
                model=response.model,
                prompt=prompt,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                total_tokens=response.usage.total_tokens,
                latency_ms=response.latency_ms,
                cost=response.cost,
                cached=False,
                success=True,
            )

            return response

        except Exception:

            # Log Failure
            self.tracker.log(
                provider=selection.provider,
                model=selection.model,
                prompt=prompt,
                input_tokens=0,
                output_tokens=0,
                total_tokens=0,
                latency_ms=0,
                cost=0,
                cached=False,
                success=False,
            )
            circuit.record_failure()

            raise
    def stream(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
    ):
        classification = self.classifier.classify(prompt)
        if model:
            selection = self.selector.select_by_model(model)
        else:
            selection = self.selector.select(classification)

        provider = self.registry.get(selection.provider)

        messages = []

        if system_prompt:
            messages.append(
                ChatMessage(
                    role="system",
                    content=system_prompt,
                )
            )

        messages.append(
            ChatMessage(
                role="user",
                content=prompt,
            )
        )

        return provider.stream_chat(
            messages=messages,
            model=selection.model,
        )
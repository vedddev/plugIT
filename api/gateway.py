from providers.base import ChatMessage, ChatResponse
from providers.registry import ProviderRegistry
from router.classifier import PromptClassifier
from router.selector import ModelSelector
from pricing.calculator import PricingCalculator
from analytics.tracker import AnalyticsTracker
from cache.redis_cache import RedisCache


class SmartLLM:

    def __init__(self, registry: ProviderRegistry):

        self.registry = registry
        self.classifier = PromptClassifier()
        self.selector = ModelSelector(self.registry)
        self.calculator = PricingCalculator()
        self.tracker = AnalyticsTracker()
        self.cache = RedisCache()

    def chat(
        self,
        prompt: str,
        system_prompt: str | None = None,
    ) -> ChatResponse:

        # Step 1 - Classify
        classification = self.classifier.classify(prompt)

        # Step 2 - Select provider/model
        selection = self.selector.select(classification)

        # Step 3 - Get provider
        provider = self.registry.get(selection.provider)

        # Step 4 - Check Redis Cache
        cached = self.cache.get(
            prompt=prompt,
            model=selection.model,
        )

        if cached:
            print("[Cache] HIT")

            response = ChatResponse.from_dict(cached)

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
            response = provider.chat(
                messages=messages,
                model=selection.model,
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

            raise
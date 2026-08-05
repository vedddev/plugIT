from providers.base import ChatResponse


class FallbackExecutor:

    def __init__(self, registry):
        self.registry = registry

    def execute(
        self,
        providers,
        messages,
        model_selector,
    ) -> ChatResponse:

        last_error = None

        for provider_name in providers:

            try:

                provider = self.registry.get(provider_name)

                model = model_selector(provider_name)

                print(f"[Fallback] Trying {provider_name}")

                return provider.chat(
                    messages=messages,
                    model=model,
                )

            except Exception as e:

                print(f"[Fallback] {provider_name} failed")

                last_error = e

        raise last_error
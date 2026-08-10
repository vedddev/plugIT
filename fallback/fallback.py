from providers.base import ChatResponse
from router.exceptions import AllProvidersFailedError


class FallbackExecutor:
    def __init__(self, registry):
        self.registry = registry

    def execute(self, providers, messages, model_selector, retry, circuit_manager) -> ChatResponse:
        failures = {}
        for provider_name in providers:
            circuit = circuit_manager.get(provider_name)
            if not circuit.allow_request():
                print(f"[Fallback] Skipping provider: {provider_name} (circuit OPEN)")
                failures[provider_name] = RuntimeError("circuit is OPEN")
                continue
            try:
                provider = self.registry.get(provider_name)
                model = model_selector(provider_name)
                print(f"[Fallback] Trying provider: {provider_name}")
                print(f"[Fallback] Model: {model}")
                response = retry.run(provider.chat, messages=messages, model=model)
                circuit.record_success()
                print(f"[Fallback] Success: {provider_name}")
                return response
            except Exception as error:
                circuit.record_failure()
                failures[provider_name] = error
                print(f"[Fallback] {provider_name} failed")
        raise AllProvidersFailedError(failures)

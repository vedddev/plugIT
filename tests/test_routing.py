import unittest
from api.gateway import SmartLLM
from providers.base import BaseProvider, ChatResponse, Usage
from providers.registry import ProviderRegistry
from router.exceptions import ModelNotFoundError


class FakeProvider(BaseProvider):
    def __init__(self, name, models, fail=False):
        super().__init__("test")
        self._name, self.models, self.fail, self.calls = name, models, fail, 0
    @property
    def name(self): return self._name
    def list_models(self): return self.models
    def health_check(self): return True
    def chat(self, messages, model, **kwargs):
        self.calls += 1
        if self.fail: raise RuntimeError("forced failure")
        return ChatResponse("ok", self.name, model, Usage(1, 1, 2), 1)
    def stream_chat(self, messages, model, **kwargs): yield "ok"


class MemoryCache:
    def __init__(self): self.values = {}
    def get(self, **kwargs): return self.values.get(repr(kwargs))
    def set(self, response, **kwargs): self.values[repr(kwargs)] = response


class RoutingTests(unittest.TestCase):
    def gateway(self, gemini_fail=False, groq_fail=False):
        registry = ProviderRegistry()
        self.gemini = FakeProvider("gemini", ["gemini-2.5-flash"], gemini_fail)
        self.groq = FakeProvider("groq", ["llama-3.3-70b-versatile"], groq_fail)
        registry.register(self.gemini); registry.register(self.groq)
        gateway = SmartLLM(registry); gateway.cache = MemoryCache(); gateway.retry.retries = 1
        return gateway

    def test_auto_uses_policy_not_auto_as_model(self):
        response = self.gateway().chat("Explain Python", model="auto")
        self.assertEqual(response.model, "llama-3.3-70b-versatile")

    def test_explicit_model_resolves_owner(self):
        response = self.gateway().chat("hello", model="gemini-2.5-flash")
        self.assertEqual(response.provider, "gemini")

    def test_invalid_model_is_rejected_before_provider_call(self):
        gateway = self.gateway()
        with self.assertRaises(ModelNotFoundError):
            gateway.chat("hello", model="does-not-exist")
        self.assertEqual(self.gemini.calls + self.groq.calls, 0)

    def test_failed_primary_uses_provider_owned_fallback_model(self):
        response = self.gateway(gemini_fail=True).chat("hello", model="gemini-2.5-flash")
        self.assertEqual((response.provider, response.model), ("groq", "llama-3.3-70b-versatile"))


if __name__ == "__main__":
    unittest.main()

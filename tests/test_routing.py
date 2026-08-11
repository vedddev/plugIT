import unittest
from api.gateway import SmartLLM
from api import openai_routes
from providers.base import BaseProvider, ChatResponse, Usage
from providers.registry import ProviderRegistry
from router.exceptions import ModelNotFoundError
import asyncio
import json


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


class StreamProvider(FakeProvider):
    def __init__(self, name, models, chunks=(), fail_before=False, fail_after=False):
        super().__init__(name, models)
        self.chunks, self.fail_before, self.fail_after = chunks, fail_before, fail_after
        self.stream_calls = 0

    def stream_chat(self, messages, model, **kwargs):
        self.stream_calls += 1
        if self.fail_before:
            raise RuntimeError("connection failed")
        for chunk in self.chunks:
            yield chunk
        if self.fail_after:
            raise RuntimeError("connection lost")


class MemoryUsageTracker:
    def __init__(self): self.records = []
    def record(self, **kwargs): self.records.append(kwargs)


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

    def test_stream_falls_back_before_first_chunk(self):
        registry = ProviderRegistry()
        primary = StreamProvider("gemini", ["gemini-2.5-flash"], fail_before=True)
        fallback = StreamProvider("groq", ["llama-3.3-70b-versatile"], chunks=("hello", " world"))
        registry.register(primary); registry.register(fallback)
        gateway = SmartLLM(registry); gateway.retry.retries = 1
        prepared = gateway.prepare_stream("hello", model="gemini-2.5-flash")
        self.assertEqual((prepared.provider, prepared.model, prepared.first_chunk), ("groq", "llama-3.3-70b-versatile", "hello"))
        self.assertEqual(list(gateway.consume_prepared_stream(prepared, "hello")), ["hello", " world"])
        self.assertEqual(primary.stream_calls, 1)

    def test_stream_does_not_fallback_after_first_chunk_failure(self):
        registry = ProviderRegistry()
        primary = StreamProvider("gemini", ["gemini-2.5-flash"], chunks=("hello",), fail_after=True)
        fallback = StreamProvider("groq", ["llama-3.3-70b-versatile"], chunks=("replacement",))
        registry.register(primary); registry.register(fallback)
        gateway = SmartLLM(registry); gateway.retry.retries = 1
        with self.assertRaisesRegex(RuntimeError, "connection lost"):
            list(gateway.stream("hello", model="gemini-2.5-flash"))
        self.assertEqual(fallback.stream_calls, 0)

    def test_openai_sse_uses_selected_model_and_done_marker(self):
        registry = ProviderRegistry()
        provider = StreamProvider("groq", ["llama-3.3-70b-versatile"], chunks=("Python", " is useful"))
        registry.register(provider)
        gateway = SmartLLM(registry); gateway.retry.retries = 1
        old_gateway, old_tracker = openai_routes.gateway, openai_routes.usage_tracker
        usage = MemoryUsageTracker()
        openai_routes.gateway, openai_routes.usage_tracker = gateway, usage
        try:
            response = openai_routes._stream_response("Explain Python", None, None, "test-key")
            async def collect():
                return [part async for part in response.body_iterator]
            events = asyncio.run(collect())
        finally:
            openai_routes.gateway, openai_routes.usage_tracker = old_gateway, old_tracker
        self.assertEqual(events[-1], "data: [DONE]\n\n")
        payloads = [json.loads(event[6:]) for event in events[:-1]]
        self.assertEqual(payloads[0]["choices"][0]["delta"], {"role": "assistant", "content": ""})
        self.assertEqual(payloads[1]["model"], "llama-3.3-70b-versatile")
        self.assertEqual({item["id"] for item in payloads}, {payloads[0]["id"]})
        self.assertEqual(payloads[-1]["choices"][0]["finish_reason"], "stop")
        self.assertEqual(usage.records[-1]["success"], True)

    def test_openai_stream_invalid_model_returns_openai_error(self):
        registry = ProviderRegistry()
        registry.register(StreamProvider("groq", ["llama-3.3-70b-versatile"], chunks=("hello",)))
        gateway = SmartLLM(registry)
        old_gateway, old_tracker = openai_routes.gateway, openai_routes.usage_tracker
        usage = MemoryUsageTracker()
        openai_routes.gateway, openai_routes.usage_tracker = gateway, usage
        try:
            response = openai_routes._stream_response("hello", None, "does-not-exist", "test-key")
        finally:
            openai_routes.gateway, openai_routes.usage_tracker = old_gateway, old_tracker
        self.assertEqual(response.status_code, 404)
        self.assertEqual(json.loads(response.body)["error"]["code"], "model_not_found")
        self.assertEqual(usage.records[-1]["success"], False)


if __name__ == "__main__":
    unittest.main()

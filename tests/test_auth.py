import os

from fastapi.testclient import TestClient
from api.gateway import SmartLLM
from api import auth, admin_routes, openai_routes
from key_management.store import APIKeyStore
from providers.base import BaseProvider, ChatResponse, Usage
from providers.registry import ProviderRegistry


class _Provider(BaseProvider):
    def __init__(self):
        super().__init__("test")
    @property
    def name(self): return "test-provider"
    def list_models(self): return ["test-model"]
    def health_check(self): return True
    def chat(self, messages, model, **kwargs): return ChatResponse("ok", self.name, model, Usage(2, 3, 5), 12)
    def stream_chat(self, messages, model, **kwargs): yield "ok"


class _UsageTracker:
    def __init__(self): self.records = []
    def get(self, _key): return {"total_tokens": 0}
    def record(self, **kwargs): self.records.append(kwargs)


class _RateLimiter:
    def check(self, _key): return {"limit": 60, "remaining": 59, "reset": 0}


class _Cache:
    def get(self, **_kwargs): return None
    def set(self, **_kwargs): return None


def test_session_auth_lifecycle_and_password_not_returned(tmp_path, monkeypatch):
    monkeypatch.setenv("SMARTLLM_DB_URL", f"sqlite:///{(tmp_path / 'auth.db').as_posix()}")
    from api.server import app
    with TestClient(app) as client:
        registered = client.post("/auth/register", json={"name": "Test User", "email": "test@example.com", "password": "safe-pass-123"})
        assert registered.status_code == 201
        assert "password" not in registered.json()
        assert client.get("/auth/me").status_code == 200
        assert client.get("/dashboard/stats").status_code == 200
        assert client.post("/auth/logout").status_code == 204
        assert client.get("/auth/me").status_code == 401


def test_invalid_login_and_duplicate_email(tmp_path, monkeypatch):
    monkeypatch.setenv("SMARTLLM_DB_URL", f"sqlite:///{(tmp_path / 'auth2.db').as_posix()}")
    from api.server import app
    with TestClient(app) as client:
        payload = {"email": "dup@example.com", "password": "safe-pass-123"}
        assert client.post("/auth/register", json=payload).status_code == 201
        assert client.post("/auth/register", json=payload).status_code == 409
        client.post("/auth/logout")
        assert client.post("/auth/login", json={"email": payload["email"], "password": "wrong-pass"}).status_code == 401


def test_openai_bearer_key_auth_tracks_the_key_owner(tmp_path, monkeypatch):
    monkeypatch.setenv("SMARTLLM_DB_URL", f"sqlite:///{(tmp_path / 'api.db').as_posix()}")
    store = APIKeyStore(str(tmp_path / "keys.db"), pepper="test-pepper")
    monkeypatch.setattr(auth, "key_store", store)
    monkeypatch.setattr(admin_routes, "key_store", store)
    registry = ProviderRegistry(); registry.register(_Provider())
    gateway = SmartLLM(registry); gateway.cache = _Cache(); gateway.tracker.enable_database()
    usage = _UsageTracker()
    monkeypatch.setattr(openai_routes, "gateway", gateway)
    monkeypatch.setattr(openai_routes, "usage_tracker", usage)
    monkeypatch.setattr(openai_routes, "limiter", _RateLimiter())
    from api.server import app
    with TestClient(app) as user_a, TestClient(app) as user_b:
        registered = user_a.post("/auth/register", json={"name": "User A", "email": "a@key.test", "password": "safe-pass-123"})
        user_b.post("/auth/register", json={"name": "User B", "email": "b@key.test", "password": "safe-pass-123"})
        key_response = user_a.post("/admin/api-keys", json={"name": "integration key"})
        assert key_response.status_code == 200
        key = key_response.json()["key"]
        headers = {"Authorization": f"Bearer {key}"}
        assert user_a.get("/v1/models", headers=headers).status_code == 200
        completion = user_a.post("/v1/chat/completions", headers=headers, json={"model": "test-model", "messages": [{"role": "user", "content": "hello"}]})
        assert completion.status_code == 200
        assert user_a.post("/v1/chat/completions", json={"model": "test-model", "messages": []}).status_code == 401
        assert user_a.get("/v1/models", headers={"Authorization": "Bearer sk-smartllm-invalid"}).status_code == 401
        assert user_a.get("/dashboard/stats?period=all").json()["total_requests"] == 1
        assert len(user_a.get("/dashboard/recent?period=all").json()["data"]) == 1
        assert user_b.get("/dashboard/stats?period=all").json()["total_requests"] == 0

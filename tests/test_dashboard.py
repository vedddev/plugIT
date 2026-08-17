from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.dashboard_routes import router
from api.errors import register_exception_handlers
from analytics.tracker import AnalyticsTracker
from api.gateway import SmartLLM
from providers.base import BaseProvider, ChatResponse, Usage
from providers.registry import ProviderRegistry
from database.dashboard import record_request, stats, usage
from database.initialization import LEGACY_USER_ID
from database.initialization import initialize_database


def _url(tmp_path):
    return f"sqlite:///{(tmp_path / 'dashboard.db').as_posix()}"


def _seed(database_url):
    now = datetime.now(timezone.utc)
    record_request(api_key_id="key-a", user_id=LEGACY_USER_ID, provider="groq", model="llama", input_tokens=10,
                   output_tokens=5, total_tokens=15, latency_ms=100, cost=0.1,
                   cached=False, success=True, database_url=database_url, created_at=now.isoformat())
    record_request(api_key_id="key-b", user_id=LEGACY_USER_ID, provider="gemini", model="flash", input_tokens=4,
                   output_tokens=6, total_tokens=10, latency_ms=50, cost=0.2,
                   cached=True, success=False, database_url=database_url, created_at=now.isoformat())
    record_request(api_key_id="key-c", user_id=LEGACY_USER_ID, provider="groq", model="llama", input_tokens=1,
                   output_tokens=1, total_tokens=2, latency_ms=20, cost=0.01,
                   cached=False, success=True, database_url=database_url,
                   created_at=(now - timedelta(days=31)).isoformat())


def test_dashboard_queries_return_filtered_statistics(tmp_path):
    database_url = _url(tmp_path)
    initialize_database(database_url)
    _seed(database_url)

    today = stats(LEGACY_USER_ID, "today", database_url)
    assert today["total_requests"] == 2
    assert today["requests_today"] == 2
    assert today["successful_requests"] == 1
    assert today["failed_requests"] == 1
    assert today["total_input_tokens"] == 14
    assert today["total_output_tokens"] == 11
    assert today["total_tokens"] == 25
    assert today["total_cost"] == 0.3
    assert today["average_latency"] == 75
    assert (today["cache_hits"], today["cache_misses"], today["cache_hit_rate"]) == (1, 1, 0.5)
    assert stats(LEGACY_USER_ID, "all", database_url)["total_requests"] == 3
    dashboard_usage = usage(LEGACY_USER_ID, "today", database_url)
    assert [item["name"] for item in dashboard_usage["provider_usage"]] == ["gemini", "groq"]
    assert dashboard_usage["time_series"][0]["requests"] == 2


def test_dashboard_endpoints_require_admin_and_use_isolated_database(tmp_path, monkeypatch):
    database_url = _url(tmp_path)
    initialize_database(database_url)
    _seed(database_url)
    monkeypatch.setenv("SMARTLLM_DB_URL", database_url)
    monkeypatch.setenv("SMARTLLM_ADMIN_KEY", "dashboard-secret")
    app = FastAPI()
    app.include_router(router)
    register_exception_handlers(app)

    with TestClient(app) as client:
        assert client.get("/dashboard/stats").status_code == 401
        headers = {"X-Admin-Key": "dashboard-secret"}
        response = client.get("/dashboard/stats?period=today", headers=headers)
        assert response.status_code == 200
        assert response.json()["total_requests"] == 2
        usage_response = client.get("/dashboard/usage?period=today", headers=headers)
        assert usage_response.status_code == 200
        assert usage_response.json()["model_usage"][0]["name"] == "flash"
        recent_response = client.get("/dashboard/recent?period=all&limit=2", headers=headers)
        assert recent_response.status_code == 200
        assert len(recent_response.json()["data"]) == 2


def test_tracker_persists_future_dashboard_events(tmp_path):
    database_url = _url(tmp_path)
    tracker = AnalyticsTracker(log_dir=str(tmp_path / "logs"))
    tracker.enable_database(database_url)
    tracker.log(provider="groq", model="llama", prompt="test", input_tokens=2,
                output_tokens=3, total_tokens=5, latency_ms=25, cost=0.05,
                cached=True, success=True, api_key_id="key-a")
    summary = stats(LEGACY_USER_ID, "all", database_url)
    assert (summary["total_requests"], summary["cache_hits"], summary["total_tokens"]) == (1, 1, 5)


def test_dashboard_isolation_uses_session_owner_not_query_parameters(tmp_path, monkeypatch):
    database_url = _url(tmp_path)
    monkeypatch.setenv("SMARTLLM_DB_URL", database_url)
    from api.server import app
    with TestClient(app) as user_a, TestClient(app) as user_b:
        a = user_a.post("/auth/register", json={"name": "Vedant", "email": "a@example.com", "password": "safe-pass-123"})
        b = user_b.post("/auth/register", json={"name": "User B", "email": "b@example.com", "password": "safe-pass-123"})
        assert a.status_code == b.status_code == 201
        assert a.json()["name"] == "Vedant"
        record_request(api_key_id="key-a", user_id=a.json()["id"], provider="groq", model="llama",
                       input_tokens=4, output_tokens=6, total_tokens=10, latency_ms=20, cost=0.01,
                       cached=False, success=True, database_url=database_url)
        # Account ids supplied by the browser are ignored: B still sees no A data.
        assert user_b.get(f"/dashboard/stats?period=all&account_id={a.json()['id']}").json()["total_requests"] == 0
        assert user_b.get("/dashboard/usage?period=all").json()["time_series"] == []
        assert user_b.get("/dashboard/providers?period=all").json()["metrics"] == []
        assert user_b.get("/dashboard/requests").json()["data"] == []
        assert user_b.get("/dashboard/models?period=all").json()["observed_providers"] == []
        assert user_b.get("/dashboard/filters").json() == {"providers": [], "models": []}
        assert user_a.get("/dashboard/stats?period=all").json()["total_requests"] == 1
        request_id = user_a.get("/dashboard/requests").json()["data"][0]["id"]
        assert user_b.get(f"/dashboard/requests/{request_id}").status_code == 404


class _Provider(BaseProvider):
    def __init__(self):
        super().__init__("test")

    @property
    def name(self):
        return "test-provider"

    def list_models(self):
        return ["test-model"]

    def health_check(self):
        return True

    def chat(self, messages, model, **kwargs):
        return ChatResponse("ok", self.name, model, Usage(3, 4, 7), 12.5)

    def stream_chat(self, messages, model, **kwargs):
        yield "ok"


class _MemoryCache:
    def __init__(self):
        self.values = {}

    def get(self, **kwargs):
        return self.values.get(repr(kwargs))

    def set(self, response, **kwargs):
        self.values[repr(kwargs)] = response


def test_gateway_request_lifecycle_persists_events_and_usage_by_default(tmp_path, monkeypatch):
    database_url = _url(tmp_path)
    monkeypatch.setenv("SMARTLLM_DB_URL", database_url)
    registry = ProviderRegistry()
    registry.register(_Provider())
    gateway = SmartLLM(registry)
    gateway.cache = _MemoryCache()

    first = gateway.chat("one", model="test-model", api_key_id="key-a")
    second = gateway.chat("one", model="test-model", api_key_id="key-a")
    assert (first.metadata.get("cached", False), second.metadata["cached"]) == (False, True)

    from database.connection import connect
    with connect(database_url) as connection:
        events = connection.execute(
            "SELECT provider, model, input_tokens, output_tokens, total_tokens, latency_ms, cached, success "
            "FROM request_events ORDER BY created_at"
        ).fetchall()
        summary = connection.execute("SELECT * FROM usage_summaries WHERE api_key_id = ?", ("key-a",)).fetchone()
    assert len(events) == 2
    assert tuple(events[0]) == ("test-provider", "test-model", 3, 4, 7, 12.5, 0, 1)
    assert tuple(events[1]) == ("test-provider", "test-model", 3, 4, 7, 0.5, 1, 1)
    assert (summary["requests"], summary["successful_requests"], summary["total_tokens"]) == (2, 2, 14)

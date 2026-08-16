import os

from fastapi.testclient import TestClient


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

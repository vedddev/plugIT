"""Authentication primitives for browser sessions and gateway API keys."""

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

import base64
import hashlib
from fastapi import Cookie, Header, HTTPException

from errors.exceptions import AuthenticationError
from database.connection import session
from key_management.store import APIKeyStore

SESSION_COOKIE = "rim_session"
SESSION_TTL_DAYS = 30
key_store = APIKeyStore()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.isoformat()


def normalize_email(email: str) -> str:
    return email.strip().lower()


def validate_password(password: str) -> None:
    if len(password) < 8 or len(password) > 128:
        raise HTTPException(status_code=422, detail="Password must be between 8 and 128 characters.")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return "scrypt$16384$8$1$" + base64.urlsafe_b64encode(salt).decode() + "$" + base64.urlsafe_b64encode(digest).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, n, r, p, salt_text, digest_text = password_hash.split("$", 5)
        if algorithm != "scrypt":
            return False
        salt = base64.urlsafe_b64decode(salt_text.encode())
        expected = base64.urlsafe_b64decode(digest_text.encode())
        actual = hashlib.scrypt(password.encode(), salt=salt, n=int(n), r=int(r), p=int(p))
        return secrets.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def create_user(email: str, password: str, name: str, role: str = "user") -> dict[str, Any]:
    email = normalize_email(email)
    if "@" not in email or len(email) > 320:
        raise HTTPException(status_code=422, detail="Enter a valid email address.")
    validate_password(password)
    now = _iso(_now())
    user = {"id": str(uuid4()), "email": email, "name": name.strip() or email.split("@", 1)[0],
            "role": role, "is_active": True, "created_at": now, "updated_at": now}
    try:
        with session() as connection:
            connection.execute(
                "INSERT INTO users (id,email,password_hash,name,role,is_active,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)",
                (user["id"], email, hash_password(password), user["name"], role, 1, now, now),
            )
    except Exception as error:
        if "UNIQUE constraint failed: users.email" in str(error):
            raise HTTPException(status_code=409, detail="An account with that email already exists.") from error
        raise
    return user


def public_user(row) -> dict[str, Any]:
    return {"id": row["id"], "email": row["email"], "name": row["name"], "role": row["role"]}


def authenticate_user(email: str, password: str):
    with session() as connection:
        row = connection.execute("SELECT * FROM users WHERE email = ?", (normalize_email(email),)).fetchone()
    if not row or not row["is_active"] or not verify_password(password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    return row


def create_session(user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    now = _now()
    with session() as connection:
        connection.execute("INSERT INTO sessions (id,user_id,expires_at,created_at,last_seen_at) VALUES (?,?,?,?,?)",
                           (hashlib.sha256(token.encode()).hexdigest(), user_id,
                            _iso(now + timedelta(days=SESSION_TTL_DAYS)), _iso(now), _iso(now)))
    return token


def get_session_user(token: str | None):
    if not token:
        return None
    now = _iso(_now())
    session_id = hashlib.sha256(token.encode()).hexdigest()
    with session() as connection:
        row = connection.execute(
            "SELECT users.* FROM sessions JOIN users ON users.id=sessions.user_id "
            "WHERE sessions.id=? AND sessions.expires_at>? AND users.is_active=1", (session_id, now)
        ).fetchone()
        if row:
            connection.execute("UPDATE sessions SET last_seen_at=? WHERE id=?", (now, session_id))
    return row


def revoke_session(token: str | None) -> None:
    if token:
        with session() as connection:
            connection.execute("DELETE FROM sessions WHERE id=?", (hashlib.sha256(token.encode()).hexdigest(),))


def current_user(rim_session: str | None = Cookie(default=None)):
    row = get_session_user(rim_session)
    if not row:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return row


def require_role(role: str):
    def dependency(user=__import__("fastapi").Depends(current_user)):
        if user["role"] != role:
            raise HTTPException(status_code=403, detail="You do not have permission for this resource.")
        return user
    return dependency


def require_admin(x_admin_key: str | None = Header(default=None), rim_session: str | None = Cookie(default=None)):
    """Normal access is session-based; the server-only key remains an emergency fallback."""
    user = get_session_user(rim_session)
    if user:
        return user
    expected = os.getenv("SMARTLLM_ADMIN_KEY")
    if expected and x_admin_key and secrets.compare_digest(x_admin_key, expected):
        # Server-admin fallback is only for legacy/server operations. It is not
        # a wildcard tenant and therefore sees only legacy-owned analytics.
        return {"id": "legacy-system", "email": "server", "name": "Server admin", "role": "admin"}
    raise AuthenticationError("Authentication required.")


def require_api_key(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    """Authenticate OpenAI-compatible API calls from a Bearer token only."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authentication required.")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(status_code=401, detail="Invalid Authorization header.")
    return key_store.authenticate(token.strip())


# Kept as an import-compatible name for any non-v1 callers. Unlike the old
# HTTPBearer dependency it is a Header dependency, so FastAPI never exposes a
# `credentials` query parameter.
verify_api_key = require_api_key

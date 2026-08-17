import base64
import hashlib
import hmac
import os
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from errors.exceptions import AuthenticationError

KEY_PREFIX = "sk-smartllm-"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


class APIKeyStore:
    """SQLite storage; plaintext key material is never persisted."""

    def __init__(self, path: str | None = None, pepper: str | None = None):
        self.path = path or os.getenv("SMARTLLM_KEY_DB", "smartllm_keys.db")
        self.pepper = (pepper or os.getenv("SMARTLLM_KEY_PEPPER") or "").encode()
        if not self.pepper:
            # Safe for local development; production explicitly requires a secret.
            if os.getenv("SMARTLLM_ENV", "development").lower() == "production":
                raise RuntimeError("SMARTLLM_KEY_PEPPER must be configured in production.")
            self.pepper = b"smartllm-development-pepper"
        self._initialize()

    def _connection(self):
        return sqlite3.connect(self.path)

    def _initialize(self) -> None:
        Path(self.path).parent.mkdir(parents=True, exist_ok=True) if Path(self.path).parent != Path(".") else None
        with self._connection() as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS api_keys (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, key_prefix TEXT NOT NULL UNIQUE,
                key_hash TEXT NOT NULL, is_active INTEGER NOT NULL DEFAULT 1,
                expires_at TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                last_used_at TEXT, metadata TEXT, user_id TEXT
            )""")
            columns = {row[1] for row in conn.execute("PRAGMA table_info(api_keys)")}
            if "user_id" not in columns:
                conn.execute("ALTER TABLE api_keys ADD COLUMN user_id TEXT")
            conn.execute("CREATE INDEX IF NOT EXISTS ix_api_keys_user_id ON api_keys(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS ix_api_keys_prefix ON api_keys(key_prefix)")

    def _hash(self, key: str) -> str:
        return hmac.new(self.pepper, key.encode(), hashlib.sha256).hexdigest()

    @staticmethod
    def _prefix(key: str) -> str:
        return key[:len(KEY_PREFIX) + 8]

    def create(self, name: str, expires_at: datetime | None = None, metadata: str | None = None, user_id: str | None = None) -> tuple[dict, str]:
        secret = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip("=")
        key = f"{KEY_PREFIX}{secret}"
        now, key_id, prefix = utcnow(), str(uuid4()), self._prefix(key)
        record = {"id": key_id, "name": name, "key_prefix": prefix, "is_active": True,
                  "expires_at": iso(expires_at), "created_at": iso(now), "updated_at": iso(now),
                  "last_used_at": None, "metadata": metadata}
        with self._connection() as conn:
            conn.execute("INSERT INTO api_keys (id,name,key_prefix,key_hash,is_active,expires_at,created_at,updated_at,last_used_at,metadata,user_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                         (key_id, name, prefix, self._hash(key), 1, record["expires_at"], record["created_at"], record["updated_at"], None, metadata, user_id))
        return record, key

    def _safe(self, row) -> dict | None:
        if not row:
            return None
        keys = ("id", "name", "key_prefix", "is_active", "expires_at", "created_at", "updated_at", "last_used_at", "metadata")
        return dict(zip(keys, row))

    def list(self, user_id: str | None = None) -> list[dict]:
        with self._connection() as conn:
            rows = conn.execute("SELECT id,name,key_prefix,is_active,expires_at,created_at,updated_at,last_used_at,metadata FROM api_keys WHERE (? IS NULL OR user_id=?) ORDER BY created_at DESC", (user_id, user_id)).fetchall()
        return [self._safe(row) for row in rows]

    def get(self, key_id: str, user_id: str | None = None) -> dict | None:
        with self._connection() as conn:
            return self._safe(conn.execute("SELECT id,name,key_prefix,is_active,expires_at,created_at,updated_at,last_used_at,metadata FROM api_keys WHERE id=? AND (? IS NULL OR user_id=?)", (key_id, user_id, user_id)).fetchone())

    def revoke(self, key_id: str, user_id: str | None = None) -> dict | None:
        now = iso(utcnow())
        with self._connection() as conn:
            conn.execute("UPDATE api_keys SET is_active=0,updated_at=? WHERE id=? AND (? IS NULL OR user_id=?)", (now, key_id, user_id, user_id))
        return self.get(key_id, user_id)

    def rotate(self, key_id: str, user_id: str | None = None) -> tuple[dict, str] | None:
        old = self.get(key_id, user_id)
        if not old:
            return None
        secret = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip("=")
        key, now, prefix = f"{KEY_PREFIX}{secret}", iso(utcnow()), self._prefix(f"{KEY_PREFIX}{secret}")
        with self._connection() as conn:
            conn.execute("UPDATE api_keys SET key_prefix=?,key_hash=?,is_active=1,updated_at=?,last_used_at=NULL WHERE id=?", (prefix, self._hash(key), now, key_id))
        return self.get(key_id, user_id), key

    def authenticate(self, key: str) -> dict:
        with self._connection() as conn:
            row = conn.execute(
                "SELECT id,name,key_hash,is_active,expires_at,user_id FROM api_keys WHERE key_prefix=?",
                (self._prefix(key),),
            ).fetchone()
            if not row or not hmac.compare_digest(row[2], self._hash(key)):
                raise AuthenticationError("Invalid API key.")
            if not row[3] or (row[4] and utcnow() >= datetime.fromisoformat(row[4])):
                raise AuthenticationError("Invalid API key.")
            conn.execute("UPDATE api_keys SET last_used_at=?,updated_at=? WHERE id=?", (iso(utcnow()), iso(utcnow()), row[0]))
            return {"id": row[0], "name": row[1], "user_id": row[5]}

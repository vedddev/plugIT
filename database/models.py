"""Application-database record types.

The key-management database remains the source of truth for API-key identity.
``api_key_id`` fields are opaque references to that store, never plaintext
keys or key hashes.
"""

from dataclasses import dataclass


# These statements are the schema representation of the record types below.
# ``api_key_id`` is an external reference to key_management.store, so there is
# intentionally no foreign key to the separate API-key SQLite database.
SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        name TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'user',
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_users_email ON users(email)",
    """
    CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        expires_at TEXT NOT NULL,
        created_at TEXT NOT NULL,
        last_seen_at TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_sessions_user_id ON sessions(user_id)",
    "CREATE INDEX IF NOT EXISTS ix_sessions_expires_at ON sessions(expires_at)",
    """
    CREATE TABLE IF NOT EXISTS usage_summaries (
        api_key_id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL DEFAULT 'legacy-system' REFERENCES users(id) ON DELETE RESTRICT,
        requests INTEGER NOT NULL DEFAULT 0 CHECK (requests >= 0),
        successful_requests INTEGER NOT NULL DEFAULT 0 CHECK (successful_requests >= 0),
        failed_requests INTEGER NOT NULL DEFAULT 0 CHECK (failed_requests >= 0),
        input_tokens INTEGER NOT NULL DEFAULT 0 CHECK (input_tokens >= 0),
        output_tokens INTEGER NOT NULL DEFAULT 0 CHECK (output_tokens >= 0),
        total_tokens INTEGER NOT NULL DEFAULT 0 CHECK (total_tokens >= 0),
        cost REAL NOT NULL DEFAULT 0 CHECK (cost >= 0),
        last_request_at TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS request_events (
        id TEXT PRIMARY KEY,
        api_key_id TEXT NOT NULL,
        user_id TEXT NOT NULL DEFAULT 'legacy-system' REFERENCES users(id) ON DELETE RESTRICT,
        input_tokens INTEGER NOT NULL CHECK (input_tokens >= 0),
        output_tokens INTEGER NOT NULL CHECK (output_tokens >= 0),
        total_tokens INTEGER NOT NULL CHECK (total_tokens >= 0),
        cost REAL NOT NULL CHECK (cost >= 0),
        success INTEGER NOT NULL CHECK (success IN (0, 1)),
        created_at TEXT NOT NULL,
        provider TEXT,
        model TEXT,
        latency_ms REAL,
        cached INTEGER CHECK (cached IN (0, 1))
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_request_events_api_key_id ON request_events(api_key_id)",
    "CREATE INDEX IF NOT EXISTS ix_request_events_created_at ON request_events(created_at)",
)


@dataclass(frozen=True)
class UsageSummary:
    api_key_id: str
    requests: int
    successful_requests: int
    failed_requests: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost: float
    last_request_at: str | None


@dataclass(frozen=True)
class RequestEvent:
    id: str
    api_key_id: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost: float
    success: bool
    created_at: str
    provider: str | None = None
    model: str | None = None
    latency_ms: float | None = None
    cached: bool | None = None


def request_event_from_row(row) -> RequestEvent | None:
    """Convert a sqlite row into a ``RequestEvent`` without exposing SQL."""
    if row is None:
        return None
    return RequestEvent(
        id=row["id"],
        api_key_id=row["api_key_id"],
        input_tokens=row["input_tokens"],
        output_tokens=row["output_tokens"],
        total_tokens=row["total_tokens"],
        cost=row["cost"],
        success=bool(row["success"]),
        created_at=row["created_at"],
        provider=row["provider"],
        model=row["model"],
        latency_ms=row["latency_ms"],
        cached=bool(row["cached"]) if row["cached"] is not None else None,
    )

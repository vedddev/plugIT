"""Schema initialization for SmartLLM's application database."""

import sqlite3
from datetime import datetime, timezone

from database.connection import connect
from database.models import SCHEMA_STATEMENTS


REQUEST_EVENT_COLUMNS = {
    "user_id": "TEXT REFERENCES users(id) ON DELETE RESTRICT",
    "provider": "TEXT",
    "model": "TEXT",
    "latency_ms": "REAL",
    "cached": "INTEGER CHECK (cached IN (0, 1))",
}

LEGACY_USER_ID = "legacy-system"


def _ensure_legacy_owner(connection) -> None:
    """Keep pre-ownership records visible only to the dedicated legacy account."""
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    connection.execute(
        """INSERT OR IGNORE INTO users
           (id,email,password_hash,name,role,is_active,created_at,updated_at)
           VALUES (?,?,?,?,?,?,?,?)""",
        (LEGACY_USER_ID, "legacy@rim.invalid", "!disabled-legacy-account!", "Legacy data", "system", 0, now, now),
    )


def initialize_database(database_url: str | None = None) -> None:
    """Create the application tables and indexes if they do not exist.

    This is deliberately idempotent so it is safe to call during every
    application startup.  The API-key database is managed separately by
    ``key_management.store`` and is never opened here.
    """
    connection = connect(database_url)
    try:
        for statement in SCHEMA_STATEMENTS:
            connection.execute(statement)
        _ensure_legacy_owner(connection)
        existing_columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(request_events)")
        }
        for name, definition in REQUEST_EVENT_COLUMNS.items():
            if name not in existing_columns:
                connection.execute(f"ALTER TABLE request_events ADD COLUMN {name} {definition}")
        summary_columns = {row["name"] for row in connection.execute("PRAGMA table_info(usage_summaries)")}
        if "user_id" not in summary_columns:
            connection.execute("ALTER TABLE usage_summaries ADD COLUMN user_id TEXT REFERENCES users(id) ON DELETE RESTRICT")
        # SQLite cannot add a NOT NULL column to populated tables. Backfill once;
        # all new writes supply an owner explicitly.
        connection.execute("UPDATE request_events SET user_id=? WHERE user_id IS NULL", (LEGACY_USER_ID,))
        connection.execute("UPDATE usage_summaries SET user_id=? WHERE user_id IS NULL", (LEGACY_USER_ID,))
        connection.execute("CREATE INDEX IF NOT EXISTS ix_request_events_user_created_at ON request_events(user_id, created_at)")
        connection.execute("CREATE INDEX IF NOT EXISTS ix_usage_summaries_user_id ON usage_summaries(user_id)")
        connection.commit()
    except sqlite3.Error as error:
        connection.rollback()
        raise RuntimeError("Unable to initialize the SmartLLM application database.") from error
    finally:
        connection.close()

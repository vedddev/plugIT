"""Configuration for SmartLLM's application database."""

import os
from pathlib import Path
from urllib.parse import unquote, urlparse


DEFAULT_DATABASE_URL = "sqlite:///smartllm.db"


def database_url() -> str:
    """Return the configured application database URL without logging it."""
    return os.getenv("SMARTLLM_DB_URL", DEFAULT_DATABASE_URL)


def sqlite_database_path(url: str | None = None) -> str:
    """Resolve a SQLite URL to a sqlite3-compatible database path.

    SmartLLM currently supports SQLite, which keeps local development
    dependency-free. The URL setting deliberately follows common database URL
    syntax so a SQLAlchemy/Alembic migration can be introduced later without
    changing application configuration.
    """
    value = url or database_url()
    parsed = urlparse(value)
    if parsed.scheme != "sqlite":
        raise ValueError("SMARTLLM_DB_URL must use the sqlite:// URL scheme.")
    if parsed.netloc not in ("", "localhost"):
        raise ValueError("SQLite database URLs must not include a remote host.")

    path = unquote(parsed.path)
    if path == "/:memory:":
        return ":memory:"
    # sqlite:///relative.db maps to a relative file. sqlite:////absolute.db
    # retains its leading slash, as required by sqlite3 on POSIX hosts.
    if value.startswith("sqlite:///") and not value.startswith("sqlite:////"):
        path = path.lstrip("/")
    if not path:
        raise ValueError("SMARTLLM_DB_URL must include a database path.")
    return str(Path(path))

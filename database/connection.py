"""SQLite connection and transaction helpers."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from database.config import sqlite_database_path


def connect(database_url: str | None = None) -> sqlite3.Connection:
    path = sqlite_database_path(database_url)
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


@contextmanager
def session(database_url: str | None = None) -> Iterator[sqlite3.Connection]:
    """Provide a committed transaction, rolling back on errors."""
    connection = connect(database_url)
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

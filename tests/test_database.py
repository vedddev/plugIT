"""Integration tests for SmartLLM's isolated application database."""

from database.config import sqlite_database_path
from database.connection import connect, session
from database.initialization import initialize_database
from database.models import RequestEvent, UsageSummary, request_event_from_row


def test_database_connection_models_schema_and_request_event_crud(tmp_path):
    database_file = tmp_path / "smartllm-test.db"
    database_url = f"sqlite:///{database_file.as_posix()}"
    assert sqlite_database_path(database_url) == str(database_file)

    connection = connect(database_url)
    try:
        assert connection.execute("SELECT 1").fetchone()[0] == 1
        assert isinstance(UsageSummary("key-1", 0, 0, 0, 0, 0, 0, 0.0, None), UsageSummary)
        assert isinstance(RequestEvent("event-1", "key-1", 1, 2, 3, 0.01, True, "2026-01-01T00:00:00Z"), RequestEvent)
    finally:
        connection.close()

    initialize_database(database_url)
    with session(database_url) as connection:
        tables = {row["name"] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        assert {"usage_summaries", "request_events"} <= tables
        connection.execute(
            """INSERT INTO request_events
               (id, api_key_id, input_tokens, output_tokens, total_tokens, cost, success, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            ("event-1", "key-1", 1, 2, 3, 0.01, 1, "2026-01-01T00:00:00Z"),
        )

    with session(database_url) as connection:
        event = request_event_from_row(connection.execute("SELECT * FROM request_events WHERE id = ?", ("event-1",)).fetchone())
        assert event == RequestEvent("event-1", "key-1", 1, 2, 3, 0.01, True, "2026-01-01T00:00:00Z")
        connection.execute("UPDATE request_events SET success = 0, cost = ? WHERE id = ?", (0.02, "event-1"))

    with session(database_url) as connection:
        updated = request_event_from_row(connection.execute("SELECT * FROM request_events WHERE id = ?", ("event-1",)).fetchone())
        assert updated is not None
        assert (updated.success, updated.cost) == (False, 0.02)
        connection.execute("DELETE FROM request_events WHERE id = ?", ("event-1",))

    with session(database_url) as connection:
        assert connection.execute("SELECT * FROM request_events WHERE id = ?", ("event-1",)).fetchone() is None


def test_initialize_database_is_idempotent(tmp_path):
    database_url = f"sqlite:///{(tmp_path / 'idempotent.db').as_posix()}"
    initialize_database(database_url)
    initialize_database(database_url)
    with connect(database_url) as connection:
        count = connection.execute("SELECT COUNT(*) FROM sqlite_master WHERE type = 'table'").fetchone()[0]
        assert count == 4

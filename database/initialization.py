"""Schema initialization for SmartLLM's application database."""

import sqlite3

from database.connection import connect
from database.models import SCHEMA_STATEMENTS


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
        connection.commit()
    except sqlite3.Error as error:
        connection.rollback()
        raise RuntimeError("Unable to initialize the SmartLLM application database.") from error
    finally:
        connection.close()

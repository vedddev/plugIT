"""Main application database support for SmartLLM.

This database is intentionally separate from ``key_management.store`` and
never contains API-key material or hashes.
"""

from database.initialization import initialize_database

__all__ = ["initialize_database"]

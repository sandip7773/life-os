"""
Life OS · shared/db.py
The single wrapper around the Supabase client. Modules import from here,
never from supabase-py directly (see CLAUDE.md architecture rules).

Needs SUPABASE_URL and SUPABASE_KEY in the environment — entry points
(bot/main.py, scripts) are responsible for loading .env first.
"""

import os

from supabase import Client, create_client

_client = None


def _db() -> Client:
    global _client
    if _client is None:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        if not url or not key:
            raise RuntimeError("SUPABASE_URL / SUPABASE_KEY missing from environment (.env)")
        _client = create_client(url, key)
    return _client


def insert(table: str, row: dict) -> dict:
    """Insert one row; returns it as stored (including generated id/created_at)."""
    result = _db().table(table).insert(row).execute()
    return result.data[0]


def update(table: str, row_id: str, fields: dict) -> dict:
    """Update one row by id; returns the updated row."""
    result = _db().table(table).update(fields).eq("id", row_id).execute()
    return result.data[0]


def delete(table: str, row_id: str) -> None:
    """Delete one row by id."""
    _db().table(table).delete().eq("id", row_id).execute()


def latest(table: str, order_col: str = "created_at") -> dict | None:
    """Newest row in a table by order_col, or None if the table is empty."""
    result = _db().table(table).select("*").order(order_col, desc=True).limit(1).execute()
    return result.data[0] if result.data else None


def list_rows(table: str, order_col: str = "created_at", limit: int = 50) -> list[dict]:
    """Newest-first rows from a table, up to limit."""
    result = _db().table(table).select("*").order(order_col, desc=True).limit(limit).execute()
    return result.data

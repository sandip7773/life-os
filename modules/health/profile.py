"""
Life OS · Health module · profile.py
The training profile: a single jsonb row in the profiles table.
Falls back to DEFAULT_PROFILE until a row exists (first update creates it);
missing keys in a stored row are filled from the default.
"""

import logging
from datetime import datetime, timezone

from shared import db

log = logging.getLogger("life-os.profile")

PROFILES_TABLE = "profiles"

DEFAULT_PROFILE = {
    "goal": "gain muscle mass",
    "experience": "intermediate",
    "days_per_week": 3,
    "session_length_minutes": 60,
    "equipment": "commercial gym (full equipment)",
    "constraints": "none",
    "preferences": "enjoy compound lifts, dislike long cardio sessions",
}

ALLOWED_FIELDS = list(DEFAULT_PROFILE)
_INT_FIELDS = {"days_per_week", "session_length_minutes"}


def get_profile() -> dict:
    try:
        row = db.latest(PROFILES_TABLE, order_col="updated_at")
    except Exception:
        log.warning("Could not read profile from DB; using defaults", exc_info=True)
        return dict(DEFAULT_PROFILE)
    if row is None:
        return dict(DEFAULT_PROFILE)
    return {**DEFAULT_PROFILE, **row["data"]}


def update_field(field: str, value: str) -> dict:
    """Set one profile field (creates the row on first use). Returns the new profile."""
    if field not in ALLOWED_FIELDS:
        raise ValueError(f"Unknown field '{field}'. Fields: {', '.join(ALLOWED_FIELDS)}")
    if field in _INT_FIELDS:
        try:
            value = int(value)
        except ValueError:
            raise ValueError(f"'{field}' needs a whole number, got '{value}'.")

    row = db.latest(PROFILES_TABLE, order_col="updated_at")
    if row is None:
        data = {**DEFAULT_PROFILE, field: value}
        db.insert(PROFILES_TABLE, {"data": data})
        return data

    data = {**DEFAULT_PROFILE, **row["data"], field: value}
    db.update(PROFILES_TABLE, row["id"], {
        "data": data,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })
    return data

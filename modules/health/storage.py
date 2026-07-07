"""
Life OS · Health module · storage.py
Persistence for health-domain data. plan_data (jsonb) is the structured
source of truth for a workout plan; plan_markdown is a human-readable
snapshot rendered from it at save time (see CLAUDE.md schema rules:
generated content stored as blob + metadata).
"""

from shared import db
from modules.health.render import render_plan_markdown

WORKOUT_PLANS_TABLE = "workout_plans"


def save_workout_plan(plan_data: dict, profile: dict, model: str) -> dict:
    """Persist a generated plan; returns the stored row."""
    return db.insert(WORKOUT_PLANS_TABLE, {
        "plan_data": plan_data,
        "plan_markdown": render_plan_markdown(plan_data),
        "profile": profile,
        "model": model,
    })


def update_workout_plan_data(plan_id: str, plan_data: dict) -> dict:
    """Overwrite an existing plan's structured data (dashboard editing)."""
    return db.update(WORKOUT_PLANS_TABLE, plan_id, {
        "plan_data": plan_data,
        "plan_markdown": render_plan_markdown(plan_data),
    })


def get_latest_workout_plan() -> dict | None:
    """Most recently saved plan row, or None if nothing is saved yet."""
    return db.latest(WORKOUT_PLANS_TABLE)


# --- workout logs (logged-entries shape: structured rows, not blobs) -------

WORKOUT_LOGS_TABLE = "workout_logs"


def save_workout_log(raw_text: str, exercises: list[dict]) -> dict:
    """Persist one logged session; returns the stored row (id used for Undo)."""
    return db.insert(WORKOUT_LOGS_TABLE, {
        "raw_text": raw_text,
        "exercises": exercises,
    })


def delete_workout_log(log_id: str) -> None:
    """Remove a logged session (the bot's Undo button)."""
    db.delete(WORKOUT_LOGS_TABLE, log_id)


def get_recent_workout_logs(limit: int = 100) -> list[dict]:
    """Newest-first logged sessions, for history Q&A and charts."""
    return db.list_rows(WORKOUT_LOGS_TABLE, order_col="logged_at", limit=limit)

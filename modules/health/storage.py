"""
Life OS · Health module · storage.py
Persistence for health-domain data. Workout plans are generated content:
stored as a markdown blob + metadata (see CLAUDE.md schema rules).
"""

from shared import db

WORKOUT_PLANS_TABLE = "workout_plans"


def save_workout_plan(plan_markdown: str, profile: dict, model: str) -> dict:
    """Persist a generated plan; returns the stored row."""
    return db.insert(WORKOUT_PLANS_TABLE, {
        "plan_markdown": plan_markdown,
        "profile": profile,
        "model": model,
    })


def get_latest_workout_plan() -> dict | None:
    """Most recently saved plan row, or None if nothing is saved yet."""
    return db.latest(WORKOUT_PLANS_TABLE)

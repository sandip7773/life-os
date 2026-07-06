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

"""
Life OS · Health module · render.py
Turns structured plan_data (see workout_generator.PLAN_SCHEMA) into display
formats. Formatting is built directly from fields — no text parsing, so it
can't drift from what the model actually returned.
"""

import html


def render_plan_html(plan_data: dict) -> str:
    """Telegram-ready: <b>day headers</b>, one line per exercise."""
    lines = [html.escape(plan_data["summary"]), ""]
    for day in plan_data["days"]:
        lines.append(f"<b>{html.escape(day['label'])} — {html.escape(day['weekday'])}</b>")
        for ex in day["exercises"]:
            lines.append(
                f"{html.escape(ex['name'])} — {ex['sets']}×{html.escape(str(ex['reps']))}, "
                f"rest {html.escape(str(ex['rest']))}"
            )
        lines.append("")
    return "\n".join(lines).strip()


def render_plan_markdown(plan_data: dict) -> str:
    """Plain markdown for the dashboard and the plan_markdown snapshot column."""
    lines = [plan_data["summary"], ""]
    for day in plan_data["days"]:
        lines.append(f"**{day['label']} — {day['weekday']}**")
        for ex in day["exercises"]:
            lines.append(f"{ex['name']} — {ex['sets']}×{ex['reps']}, rest {ex['rest']}")
        lines.append("")
    return "\n".join(lines).strip()

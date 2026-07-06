"""
Life OS · Health module · workout_generator.py
Standalone workout plan generator. No bot, no orchestrator (storage is
shared/db.py via modules/health/storage.py once a plan is generated).

Usage (from the repo root, so shared/ resolves):
    1. Profile comes from the DB (edit via /profile in Telegram or the
       dashboard); falls back to profile.DEFAULT_PROFILE without a DB.
    2. Make sure ANTHROPIC_API_KEY is set in the environment / .env
    3. python -m modules.health.workout_generator

    Optional: python -m modules.health.workout_generator --dry-run   (prints the prompt, no API call)

Output: plan printed to terminal + saved as workout_plan_YYYY-MM-DD.md

Since Phase 5, plans are structured data (see PLAN_SCHEMA below), not
prose — this is what lets the dashboard edit individual exercises and lets
the bot answer "what am I doing today" by matching an explicit weekday
field, instead of parsing free text.
"""

import os
import sys
from datetime import date

MODEL = "claude-sonnet-4-6"

PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {
            "type": "string",
            "description": "2-3 sentence explanation of the weekly structure and why it fits the goal",
        },
        "days": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "label": {"type": "string", "description": "e.g. 'Push', 'Legs', 'Full Body'"},
                    "weekday": {
                        "type": "string",
                        "enum": [
                            "Monday", "Tuesday", "Wednesday", "Thursday",
                            "Friday", "Saturday", "Sunday",
                        ],
                    },
                    "exercises": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "sets": {"type": "integer"},
                                "reps": {"type": "string", "description": "e.g. '6-8' or '12'"},
                                "rest": {"type": "string", "description": "e.g. '2-3 min'"},
                            },
                            "required": ["name", "sets", "reps", "rest"],
                        },
                    },
                },
                "required": ["label", "weekday", "exercises"],
            },
        },
    },
    "required": ["summary", "days"],
}


def build_prompt(profile: dict) -> str:
    return f"""You are an experienced strength and conditioning coach.
Create a weekly workout plan for this person:

- Goal: {profile["goal"]}
- Experience level: {profile["experience"]}
- Training days per week: {profile["days_per_week"]}
- Time per session: about {profile["session_length_minutes"]} minutes
- Available equipment: {profile["equipment"]}
- Constraints / injuries: {profile["constraints"]}
- Preferences: {profile["preferences"]}

Assign each training day a specific weekday, spaced sensibly across the
week for recovery given the frequency (e.g. 3 days/week suits
Monday/Wednesday/Friday; more days need closer spacing but still some
recovery between sessions hitting similar muscle groups).

Keep exercise selection practical and specific to the goal and equipment.
No generic filler, no disclaimers.
"""


def generate_plan(prompt: str) -> dict:
    from shared.llm import generate_json  # lazy import so --dry-run works without the anthropic package

    return generate_json(prompt, model=MODEL, schema=PLAN_SCHEMA, max_tokens=3000)


def main() -> None:
    from modules.health.profile import get_profile
    from modules.health.render import render_plan_markdown

    prompt = build_prompt(get_profile())

    if "--dry-run" in sys.argv:
        print(prompt)
        return

    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("Set ANTHROPIC_API_KEY first: export ANTHROPIC_API_KEY=sk-ant-...")

    print(f"Generating your plan with {MODEL} ...\n")
    plan_data = generate_plan(prompt)
    plan_text = render_plan_markdown(plan_data)

    filename = f"workout_plan_{date.today().isoformat()}.md"
    with open(filename, "w") as f:
        f.write(f"# Workout plan — week of {date.today().isoformat()}\n\n{plan_text}\n")

    print(plan_text)
    print(f"\nSaved to {filename}")


if __name__ == "__main__":
    main()

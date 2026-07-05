"""
Life OS · Health module · Day 1
Standalone workout plan generator. No bot, no database, no orchestrator.

Usage (from the repo root, so shared/ resolves):
    1. Profile comes from the DB (edit via /profile in Telegram or the
       dashboard); falls back to profile.DEFAULT_PROFILE without a DB.
    2. Make sure ANTHROPIC_API_KEY is set in the environment / .env
    3. python -m modules.health.workout_generator

    Optional: python -m modules.health.workout_generator --dry-run   (prints the prompt, no API call)

Output: plan printed to terminal + saved as workout_plan_YYYY-MM-DD.md
"""

import os
import sys
from datetime import date

MODEL = "claude-sonnet-4-6"


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

Format the plan as a chat message that will be read on a phone:
1. One short paragraph (2–3 sentences) explaining the weekly structure and why it fits the goal.
2. For each training day: a **bold day header** line, then one line per exercise, like:
   Bench Press — 4×6-8, rest 2-3 min

Bold (**like this**) is the ONLY formatting allowed. No # headings, no tables, no pipes, no bullet markers.
Be terse. Under 1800 characters total. No generic filler, no disclaimers.
"""


def generate_plan(prompt: str) -> str:
    from shared.llm import generate  # lazy import so --dry-run works without the anthropic package

    return generate(prompt, model=MODEL)


def main() -> None:
    from modules.health.profile import get_profile

    prompt = build_prompt(get_profile())

    if "--dry-run" in sys.argv:
        print(prompt)
        return

    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("Set ANTHROPIC_API_KEY first: export ANTHROPIC_API_KEY=sk-ant-...")

    print(f"Generating your plan with {MODEL} ...\n")
    plan = generate_plan(prompt)

    filename = f"workout_plan_{date.today().isoformat()}.md"
    with open(filename, "w") as f:
        f.write(f"# Workout plan — week of {date.today().isoformat()}\n\n{plan}\n")

    print(plan)
    print(f"\nSaved to {filename}")


if __name__ == "__main__":
    main()

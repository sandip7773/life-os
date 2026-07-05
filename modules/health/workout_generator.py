"""
Life OS · Health module · Day 1
Standalone workout plan generator. No bot, no database, no orchestrator.

Usage (from the repo root, so shared/ resolves):
    1. Edit PROFILE below (this IS the interface for now).
    2. Make sure ANTHROPIC_API_KEY is set in the environment / .env
    3. python -m modules.health.workout_generator

    Optional: python -m modules.health.workout_generator --dry-run   (prints the prompt, no API call)

Output: plan printed to terminal + saved as workout_plan_YYYY-MM-DD.md
"""

import os
import sys
from datetime import date

# ---------------------------------------------------------------------------
# YOUR PROFILE — edit these lines, nothing else needs to change
# ---------------------------------------------------------------------------
PROFILE = {
    "goal": "gain muscle mass",       # e.g. strength, muscle, fat loss, endurance
    "experience": "intermediate",                    # beginner / intermediate / advanced
    "days_per_week": 3,
    "session_length_minutes": 60,
    "equipment": "commercial gym (full equipment)",  # or "dumbbells + bands at home", etc.
    "constraints": "none",                           # injuries, movements to avoid, etc.
    "preferences": "enjoy compound lifts, dislike long cardio sessions",
}

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

Format the plan in clean Markdown:
1. One short paragraph explaining the weekly structure and why it fits the goal.
2. A section per training day with a table: exercise, sets, reps, rest, and a one-line form cue.
3. A short "Progression" section: how to add weight/reps week over week.
4. A short "If you miss a day" section with the simplest recovery rule.

Keep it practical and specific. No generic filler, no disclaimers.
"""


def generate_plan(prompt: str) -> str:
    from shared.llm import generate  # lazy import so --dry-run works without the anthropic package

    return generate(prompt, model=MODEL)


def main() -> None:
    prompt = build_prompt(PROFILE)

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

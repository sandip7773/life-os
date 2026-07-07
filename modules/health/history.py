"""
Life OS · Health module · history.py
Answers about training. Two kinds:
- "what am I doing today" — deterministic weekday match against the latest
  plan's days (no LLM call, can't hallucinate).
- history questions — recent workout_logs rows are given to the model with
  the question; it may only answer from that data.
"""

import json
from datetime import datetime

from shared.llm import generate
from modules.health.storage import get_latest_workout_plan, get_recent_workout_logs

QA_MODEL = "claude-haiku-4-5-20251001"


def get_today_session() -> dict:
    """
    Returns {"status": "no_plan" | "rest" | "training",
             "weekday": today's name,
             "day": the matching plan day (training only),
             "training_days": [weekday, ...] (rest only)}.
    """
    weekday = datetime.now().strftime("%A")
    row = get_latest_workout_plan()
    if row is None or not row.get("plan_data"):
        return {"status": "no_plan", "weekday": weekday}
    for day in row["plan_data"]["days"]:
        if day["weekday"] == weekday:
            return {"status": "training", "weekday": weekday, "day": day}
    return {
        "status": "rest",
        "weekday": weekday,
        "training_days": [d["weekday"] for d in row["plan_data"]["days"]],
    }


def answer_history_question(question: str) -> str:
    logs = get_recent_workout_logs(limit=100)
    if not logs:
        return (
            "No workouts logged yet — after a session, just tell me what you "
            "did (e.g. 'did squats 5x5 at 80kg') and I'll start tracking."
        )
    # logged_at is stored in UTC; convert to local dates so "today"/"yesterday"
    # line up with the user's clock.
    entries = [
        {
            "date": datetime.fromisoformat(row["logged_at"]).astimezone().strftime("%Y-%m-%d"),
            "exercises": row["exercises"],
        }
        for row in logs
    ]
    today = datetime.now().strftime("%Y-%m-%d (%A)")
    prompt = f"""You are a fitness assistant. Today is {today}.
Below is the user's workout log history as JSON, newest first. Answer their
question using ONLY this data — if the answer isn't in it, say you don't
have that logged. Be specific with dates, weights and reps, and keep the
answer short (a few lines). Exercise names may vary slightly between logs
("squats" vs "back squat") — treat obvious matches as the same exercise.
Plain text only, no markdown.

Logs: {json.dumps(entries)}

Question: {question}
"""
    return generate(prompt, model=QA_MODEL, max_tokens=500)

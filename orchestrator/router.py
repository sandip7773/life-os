"""
Life OS · orchestrator/router.py
Classifies a free-text message into an intent. Routing only — no domain
logic lives here (see CLAUDE.md: "the orchestrator stays thin").

Today this only knows about the Health module's intents/fields. When a
second domain is added, this will need a small registry instead of a
hardcoded field list — not worth building until that domain exists.
"""

from shared.llm import generate_json
from modules.health.profile import ALLOWED_FIELDS

MODEL = "claude-haiku-4-5-20251001"

INTENTS = (
    "generate_workout",
    "show_last_plan",
    "show_profile",
    "update_profile",
    "log_session",
    "unknown",
)

_SCHEMA = {
    "type": "object",
    "properties": {
        "intent": {"type": "string", "enum": list(INTENTS)},
        "field": {"type": ["string", "null"], "enum": ALLOWED_FIELDS + [None]},
        "value": {"type": ["string", "null"]},
        "exercises": {
            "type": "array",
            "description": "Only for log_session: the exercises they report doing",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "sets": {"type": ["integer", "null"]},
                    "reps": {"type": ["string", "null"], "description": "e.g. '5' or '8-10'"},
                    "weight": {"type": ["number", "null"]},
                    "unit": {"type": ["string", "null"], "enum": ["kg", "lb", None]},
                },
                "required": ["name", "sets", "reps", "weight", "unit"],
            },
        },
    },
    "required": ["intent", "field", "value", "exercises"],
}


_UNKNOWN = {"intent": "unknown", "field": None, "value": None, "exercises": []}


def classify(text: str) -> dict:
    """
    Returns {"intent": ..., "field": ..., "value": ..., "exercises": [...]}.
    field/value only meaningful for update_profile; exercises only for
    log_session.
    """
    prompt = f"""Classify this message from a fitness bot user into exactly one intent:

- generate_workout: they want a NEW workout plan created (e.g. "give me a leg day", "make me a new plan")
- show_last_plan: they want to see their most recently saved plan
- show_profile: they want to see their current training settings
- update_profile: they want to change a training setting. Extract which field
  (one of: {", ".join(ALLOWED_FIELDS)}) and the new value.
- log_session: they are reporting a workout they DID (past tense), e.g.
  "did squats 5x5 at 80kg", "finished bench 3x8 with 60kg and some curls".
  Extract each exercise with sets/reps/weight/unit where stated (null when
  not stated). "5x5 at 80kg" means sets=5, reps="5", weight=80, unit="kg".
- unknown: none of the above fit, or the message is unrelated/unclear

Message: "{text}"
"""
    try:
        result = generate_json(prompt, model=MODEL, schema=_SCHEMA, max_tokens=1000)
    except Exception:
        return dict(_UNKNOWN)

    if result.get("intent") not in INTENTS:
        return dict(_UNKNOWN)
    return {
        "intent": result["intent"],
        "field": result.get("field"),
        "value": result.get("value"),
        "exercises": result.get("exercises") or [],
    }

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

INTENTS = ("generate_workout", "show_last_plan", "show_profile", "update_profile", "unknown")

_SCHEMA = {
    "type": "object",
    "properties": {
        "intent": {"type": "string", "enum": list(INTENTS)},
        "field": {"type": ["string", "null"], "enum": ALLOWED_FIELDS + [None]},
        "value": {"type": ["string", "null"]},
    },
    "required": ["intent", "field", "value"],
}


def classify(text: str) -> dict:
    """
    Returns {"intent": ..., "field": ... or None, "value": ... or None}.
    field/value are only meaningful when intent == "update_profile".
    """
    prompt = f"""Classify this message from a fitness bot user into exactly one intent:

- generate_workout: they want a new workout plan (e.g. "give me a leg day", "make me a new plan")
- show_last_plan: they want to see their most recently saved plan
- show_profile: they want to see their current training settings
- update_profile: they want to change a training setting. Extract which field
  (one of: {", ".join(ALLOWED_FIELDS)}) and the new value.
- unknown: none of the above fit, or the message is unrelated/unclear

Message: "{text}"
"""
    try:
        result = generate_json(prompt, model=MODEL, schema=_SCHEMA)
    except Exception:
        return {"intent": "unknown", "field": None, "value": None}

    if result.get("intent") not in INTENTS:
        return {"intent": "unknown", "field": None, "value": None}
    return {
        "intent": result["intent"],
        "field": result.get("field"),
        "value": result.get("value"),
    }

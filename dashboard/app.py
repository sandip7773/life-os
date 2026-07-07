"""
Life OS · Dashboard · Streamlit v1 (local only)

Run from the repo root:
    streamlit run dashboard/app.py

Health tab is real (workout plans + profile editing); the other domain
tabs are placeholders until those modules are built.

Since Phase 5, the latest workout plan is editable here per-exercise (the
dashboard is the planning surface; the bot is for logging + questions).
Older plans and legacy pre-Phase-5 rows stay read-only.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))  # so shared/ and modules/ resolve

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv(REPO_ROOT / ".env")

from shared import db
from modules.health.profile import ALLOWED_FIELDS, get_profile, update_field
from modules.health.storage import update_workout_plan_data

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

st.set_page_config(page_title="Life OS", layout="wide")
st.title("Life OS")

health, meals, money, career, mentorship = st.tabs(
    ["Health", "Meals", "Money", "Career", "Mentorship"]
)


def _clean_exercises(edited_df: pd.DataFrame) -> list[dict]:
    """Turn a data_editor's dataframe back into plan_data's exercise shape,
    dropping blank rows added via num_rows='dynamic' and coercing types."""
    cleaned = []
    for row in edited_df.to_dict("records"):
        name = str(row.get("name") or "").strip()
        if not name:
            continue
        try:
            sets = int(row.get("sets") or 1)
        except (TypeError, ValueError):
            sets = 1
        cleaned.append({
            "name": name,
            "sets": sets,
            "reps": str(row.get("reps") or ""),
            "rest": str(row.get("rest") or ""),
        })
    return cleaned


with health:
    plans_col, profile_col = st.columns([2, 1])

    with plans_col:
        st.subheader("Workout plans")
        plans = db.list_rows("workout_plans", limit=20)

        if not plans:
            st.info("No plans yet — send /workout to the Telegram bot.")
        else:
            latest = plans[0]
            older = plans[1:]

            if latest.get("plan_data"):
                # Editable: work on a session-held copy so in-progress edits
                # survive Streamlit's rerun-on-every-interaction model, until
                # Save (or a newly generated plan) resets it.
                if st.session_state.get("editing_plan_id") != latest["id"]:
                    st.session_state["editing_plan_id"] = latest["id"]
                    st.session_state["editing_plan_data"] = {
                        "summary": latest["plan_data"]["summary"],
                        "days": [dict(d) for d in latest["plan_data"]["days"]],
                    }
                plan_data = st.session_state["editing_plan_data"]

                st.markdown(f"**Latest plan — {latest['created_at'][:10]}** (editable)")
                plan_data["summary"] = st.text_area("Summary", value=plan_data["summary"])

                remove_day_index = None
                for i, day in enumerate(plan_data["days"]):
                    label_col, weekday_col, remove_col = st.columns([3, 2, 1])
                    day["label"] = label_col.text_input("Day label", value=day["label"], key=f"label_{i}")
                    weekday_idx = WEEKDAYS.index(day["weekday"]) if day["weekday"] in WEEKDAYS else 0
                    day["weekday"] = weekday_col.selectbox(
                        "Weekday", WEEKDAYS, index=weekday_idx, key=f"weekday_{i}"
                    )
                    if remove_col.button("Remove day", key=f"remove_day_{i}"):
                        remove_day_index = i

                    # Explicit column order: Postgres jsonb re-sorts dict keys
                    # alphabetically, so without pinning, columns shift after a
                    # save/reload round-trip.
                    edited_df = st.data_editor(
                        pd.DataFrame(day["exercises"], columns=["name", "sets", "reps", "rest"]),
                        num_rows="dynamic",
                        width="stretch",
                        column_order=("name", "sets", "reps", "rest"),
                        column_config={
                            "name": st.column_config.TextColumn("Exercise", required=True),
                            "sets": st.column_config.NumberColumn("Sets", min_value=1, step=1),
                            "reps": st.column_config.TextColumn("Reps"),
                            "rest": st.column_config.TextColumn("Rest"),
                        },
                        key=f"exercises_{i}",
                    )
                    day["exercises"] = _clean_exercises(edited_df)
                    st.divider()

                if remove_day_index is not None:
                    plan_data["days"].pop(remove_day_index)
                    st.rerun()

                add_col, save_col = st.columns([1, 1])
                if add_col.button("Add day"):
                    plan_data["days"].append({
                        "label": "New Day", "weekday": "Monday",
                        "exercises": [{"name": "", "sets": 1, "reps": "", "rest": ""}],
                    })
                    st.rerun()
                if save_col.button("Save changes", type="primary"):
                    update_workout_plan_data(latest["id"], plan_data)
                    st.session_state.pop("editing_plan_id", None)  # reload fresh from DB next run
                    st.success("Saved.")
                    st.rerun()
            else:
                # legacy row saved before Phase 5's structured plans
                with st.expander(f"Latest plan — {latest['created_at'][:10]}  ·  {latest['model']}", expanded=True):
                    st.markdown(latest["plan_markdown"])

            for plan in older:
                label = f"Plan — {plan['created_at'][:10]}  ·  {plan['model']}"
                with st.expander(label):
                    st.markdown(plan["plan_markdown"])

    with profile_col:
        st.subheader("Training profile")
        profile = get_profile()
        with st.form("profile_form"):
            new_values = {}
            for field in ALLOWED_FIELDS:
                current = profile[field]
                if isinstance(current, int):
                    new_values[field] = st.number_input(field, value=current, min_value=1, step=1)
                else:
                    new_values[field] = st.text_input(field, value=str(current))
            if st.form_submit_button("Save profile"):
                changed = [f for f in ALLOWED_FIELDS if new_values[f] != profile[f]]
                for f in changed:
                    update_field(f, str(new_values[f]))
                if changed:
                    st.success("Saved: " + ", ".join(changed))
                else:
                    st.info("No changes to save.")

for tab, name in (
    (meals, "Meals"),
    (money, "Money"),
    (career, "Career"),
    (mentorship, "Mentorship"),
):
    with tab:
        st.caption(f"{name} — coming later. The layout is ready for it.")

"""
Life OS · Dashboard · Streamlit v1 (local only)

Run from the repo root:
    streamlit run dashboard/app.py

Health tab is real (workout plans + profile editing); the other domain
tabs are placeholders until those modules are built.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))  # so shared/ and modules/ resolve

import streamlit as st
from dotenv import load_dotenv

load_dotenv(REPO_ROOT / ".env")

from shared import db
from modules.health.profile import ALLOWED_FIELDS, get_profile, update_field

st.set_page_config(page_title="Life OS", layout="wide")
st.title("Life OS")

health, meals, money, career, mentorship = st.tabs(
    ["Health", "Meals", "Money", "Career", "Mentorship"]
)

with health:
    plans_col, profile_col = st.columns([2, 1])

    with plans_col:
        st.subheader("Workout plans")
        plans = db.list_rows("workout_plans", limit=20)
        if not plans:
            st.info("No plans yet — send /workout to the Telegram bot.")
        for i, plan in enumerate(plans):
            label = f"Plan — {plan['created_at'][:10]}  ·  {plan['model']}"
            with st.expander(label, expanded=(i == 0)):
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

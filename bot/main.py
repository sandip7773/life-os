"""
Life OS · Telegram bot · Phase 4
Thin dispatch layer. Slash commands (/workout, /lastplan, /profile) and a
free-text path (classified by orchestrator/router.py) both reach the same
handler logic below. Buttons cover the /start menu and profile-edit
confirmation.
"""

import html
import os
import logging
import re
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from modules.health.workout_generator import MODEL, build_prompt, generate_plan
from modules.health.storage import (
    save_workout_plan,
    get_latest_workout_plan,
    save_workout_log,
    delete_workout_log,
)
from modules.health.profile import get_profile, update_field, validate_field, ALLOWED_FIELDS
from modules.health.render import render_plan_html
from orchestrator.router import classify

load_dotenv()  # reads .env into environment variables

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s | %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("life-os")


def md_to_telegram_html(text: str) -> str:
    # Plans use **bold** as their only markup. Escape everything else for
    # Telegram's HTML mode, then turn the bold markers into <b> tags.
    escaped = html.escape(text)
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escaped)


async def reply_chunked(update: Update, text: str) -> None:
    # Telegram messages cap at 4096 chars. Chunk on line boundaries so a
    # <b>…</b> pair (always within one line) never gets split.
    # effective_message works for both regular messages and button presses.
    chunk = ""
    for line in text.split("\n"):
        if len(chunk) + len(line) + 1 > 4000:
            await update.effective_message.reply_text(chunk, parse_mode="HTML")
            chunk = ""
        chunk += line + "\n"
    if chunk.strip():
        await update.effective_message.reply_text(chunk, parse_mode="HTML")


def _menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Generate workout", callback_data="menu_workout"),
            InlineKeyboardButton("Last plan", callback_data="menu_lastplan"),
        ],
        [InlineKeyboardButton("View profile", callback_data="menu_profile")],
    ])


# ---------------------------------------------------------------------------
# Core actions — shared by slash commands, free text, and buttons
# ---------------------------------------------------------------------------

async def _run_workout(update: Update) -> None:
    await update.effective_message.reply_text("Generating your plan, one moment...")
    profile = get_profile()
    plan_data = generate_plan(build_prompt(profile))
    await reply_chunked(update, render_plan_html(plan_data))
    try:
        save_workout_plan(plan_data, profile, MODEL)
        await update.effective_message.reply_text("Saved. /lastplan brings it back any time.")
    except Exception:
        log.exception("Failed to save workout plan")
        await update.effective_message.reply_text(
            "Heads up: the plan above could not be saved to the database."
        )


async def _run_lastplan(update: Update) -> None:
    row = get_latest_workout_plan()
    if row is None:
        await update.effective_message.reply_text("No saved plans yet. /workout generates one.")
        return
    date_str = row["created_at"][:10]
    if row.get("plan_data"):
        text = f"<b>Last plan — saved {date_str}</b>\n\n" + render_plan_html(row["plan_data"])
    else:
        # legacy row saved before Phase 5's structured plans
        text = md_to_telegram_html(f"**Last plan — saved {date_str}**\n\n" + row["plan_markdown"])
    await reply_chunked(update, text)


async def _run_profile_view(update: Update) -> None:
    p = get_profile()
    lines = ["<b>Your profile</b>"]
    lines += [f"{k}: {html.escape(str(v))}" for k, v in p.items()]
    lines.append("\nChange one with: /profile field value — or just tell me in your own words.")
    await update.effective_message.reply_text("\n".join(lines), parse_mode="HTML")


async def _propose_profile_update(
    update: Update, context: ContextTypes.DEFAULT_TYPE, field: str | None, value: str | None
) -> None:
    if field is None or value is None:
        await _send_fallback_menu(update, prefix="I couldn't tell what to change. ")
        return
    try:
        coerced = validate_field(field, value)
    except ValueError as e:
        await update.effective_message.reply_text(str(e))
        return
    context.user_data["pending_profile_update"] = {"field": field, "value": coerced}
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("Yes", callback_data="profile_confirm_yes"),
        InlineKeyboardButton("No", callback_data="profile_confirm_no"),
    ]])
    await update.effective_message.reply_text(f"Set {field} to {coerced}?", reply_markup=keyboard)


def _format_logged_exercise(ex: dict) -> str:
    parts = [ex["name"]]
    if ex.get("sets") and ex.get("reps"):
        parts.append(f"{ex['sets']}×{ex['reps']}")
    elif ex.get("sets"):
        parts.append(f"{ex['sets']} sets")
    if ex.get("weight"):
        parts.append(f"@ {ex['weight']:g}{ex.get('unit') or ''}")
    return " ".join(parts)


async def _log_session(update: Update, raw_text: str, exercises: list) -> None:
    if not exercises:
        await update.effective_message.reply_text(
            "Sounds like a workout log, but I couldn't pick out the exercises — "
            "try something like: did squats 5x5 at 80kg, bench 3x8 at 60kg"
        )
        return
    try:
        row = save_workout_log(raw_text, exercises)
    except Exception:
        log.exception("Failed to save workout log")
        await update.effective_message.reply_text(
            "Couldn't save that log to the database — try again in a moment."
        )
        return
    lines = ["<b>Logged:</b>"] + [html.escape(_format_logged_exercise(ex)) for ex in exercises]
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("Undo", callback_data=f"undo_log:{row['id']}"),
    ]])
    await update.effective_message.reply_text(
        "\n".join(lines), parse_mode="HTML", reply_markup=keyboard
    )


async def _send_fallback_menu(update: Update, prefix: str = "") -> None:
    await update.effective_message.reply_text(
        prefix + "Not sure what you meant — here's what I can do:",
        reply_markup=_menu_keyboard(),
    )


# ---------------------------------------------------------------------------
# Slash commands
# ---------------------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Life OS is up. Tell me what you want in your own words, or use "
        "/workout, /lastplan, /profile.",
        reply_markup=_menu_keyboard(),
    )


async def workout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _run_workout(update)


async def lastplan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _run_lastplan(update)


async def profile_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if not args:
        await _run_profile_view(update)
        return
    if len(args) < 2:
        await update.message.reply_text(
            "Usage: /profile field value\nFields: " + ", ".join(ALLOWED_FIELDS)
        )
        return
    field, value = args[0], " ".join(args[1:])
    try:
        data = update_field(field, value)
    except ValueError as e:
        await update.message.reply_text(str(e))
        return
    await update.message.reply_text(
        f"Updated {field} = {data[field]}. /workout uses this from now on."
    )


# ---------------------------------------------------------------------------
# Free text (classified by the orchestrator) and buttons
# ---------------------------------------------------------------------------

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    result = classify(update.message.text)
    intent = result["intent"]

    if intent == "generate_workout":
        await _run_workout(update)
    elif intent == "show_last_plan":
        await _run_lastplan(update)
    elif intent == "show_profile":
        await _run_profile_view(update)
    elif intent == "update_profile":
        await _propose_profile_update(update, context, result["field"], result["value"])
    elif intent == "log_session":
        await _log_session(update, update.message.text, result["exercises"])
    else:
        await _send_fallback_menu(update)


async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()  # stops the button's loading spinner in Telegram
    data = query.data

    if data == "menu_workout":
        await _run_workout(update)
    elif data == "menu_lastplan":
        await _run_lastplan(update)
    elif data == "menu_profile":
        await _run_profile_view(update)
    elif data == "profile_confirm_yes":
        pending = context.user_data.pop("pending_profile_update", None)
        if pending is None:
            await update.effective_message.reply_text("Nothing pending to confirm.")
            return
        updated = update_field(pending["field"], str(pending["value"]))
        await update.effective_message.reply_text(
            f"Updated {pending['field']} = {updated[pending['field']]}. "
            "/workout uses this from now on."
        )
    elif data == "profile_confirm_no":
        context.user_data.pop("pending_profile_update", None)
        await update.effective_message.reply_text("Cancelled — no changes made.")
    elif data.startswith("undo_log:"):
        log_id = data.split(":", 1)[1]
        try:
            delete_workout_log(log_id)
            await update.effective_message.reply_text("Undone — that session was removed.")
        except Exception:
            log.exception("Failed to undo workout log")
            await update.effective_message.reply_text("Couldn't undo that log — check the dashboard.")


def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("TELEGRAM_BOT_TOKEN missing from .env")

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("workout", workout))
    app.add_handler(CommandHandler("lastplan", lastplan))
    app.add_handler(CommandHandler("profile", profile_cmd))
    app.add_handler(CallbackQueryHandler(handle_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    log.info("Bot starting. Commands, free text, and buttons are all live.")
    app.run_polling()


if __name__ == "__main__":
    main()

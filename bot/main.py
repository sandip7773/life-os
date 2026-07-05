"""
Life OS · Telegram bot · Day 2b
Thin dispatch layer. Commands: /workout (generate + save), /lastplan (retrieve).
"""

import html
import os
import logging
import re
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from modules.health.workout_generator import PROFILE, MODEL, build_prompt, generate_plan
from modules.health.storage import save_workout_plan, get_latest_workout_plan

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
    chunk = ""
    for line in text.split("\n"):
        if len(chunk) + len(line) + 1 > 4000:
            await update.message.reply_text(chunk, parse_mode="HTML")
            chunk = ""
        chunk += line + "\n"
    if chunk.strip():
        await update.message.reply_text(chunk, parse_mode="HTML")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Life OS is up. /workout generates a weekly plan, /lastplan shows the last saved one."
    )


async def workout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Generating your plan, one moment...")
    prompt = build_prompt(PROFILE)
    plan = generate_plan(prompt)
    await reply_chunked(update, md_to_telegram_html(plan))
    try:
        save_workout_plan(plan, PROFILE, MODEL)
        await update.message.reply_text("Saved. /lastplan brings it back any time.")
    except Exception:
        log.exception("Failed to save workout plan")
        await update.message.reply_text(
            "Heads up: the plan above could not be saved to the database."
        )


async def lastplan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    row = get_latest_workout_plan()
    if row is None:
        await update.message.reply_text("No saved plans yet. /workout generates one.")
        return
    header = f"**Last plan — saved {row['created_at'][:10]}**\n\n"
    await reply_chunked(update, md_to_telegram_html(header + row["plan_markdown"]))


def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("TELEGRAM_BOT_TOKEN missing from .env")

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("workout", workout))
    app.add_handler(CommandHandler("lastplan", lastplan))

    log.info("Bot starting. Send /workout or /lastplan in Telegram.")
    app.run_polling()


if __name__ == "__main__":
    main()

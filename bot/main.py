"""
Life OS · Telegram bot · Day 2a
Thin dispatch layer. One command today: /workout.
"""

import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from modules.health.workout_generator import PROFILE, build_prompt, generate_plan

load_dotenv()  # reads .env into environment variables

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s | %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("life-os")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Life OS is up. Try /workout to generate a weekly plan."
    )


async def workout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Generating your plan, one moment...")
    prompt = build_prompt(PROFILE)
    plan = generate_plan(prompt)
    # Telegram messages cap at 4096 chars. Chunk if needed.
    for i in range(0, len(plan), 4000):
        await update.message.reply_text(plan[i:i + 4000])


def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("TELEGRAM_BOT_TOKEN missing from .env")

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("workout", workout))

    log.info("Bot starting. Send /workout in Telegram.")
    app.run_polling()


if __name__ == "__main__":
    main()
# Life OS — CLAUDE.md

Claude Code reads this file automatically. It is the single source of truth for how to work on this project. **Session-by-session build plans live in `PLAN.md` — read it at the start of every session.**

## What this project is

Life OS is a modular AI personal assistant. One Telegram bot is the unified interface for the user (Sandi). A thin Python orchestrator routes each incoming message to a domain module. Supabase (hosted Postgres) is the shared data layer.

Domains (in build order):
1. **Health** — workout plans, meal/macro logging, meal plans (ACTIVE BUILD)
2. **Money** — finance + bill tracking (architecture defined, builds next, follows Health's pattern)
3. **Career Planning**
4. **Mentorship**
5. Dashboard (further out)

## Architecture rules (locked in — do not revisit without asking)

- **Hub-and-spoke**: one Telegram bot → one thin orchestrator → pluggable domain modules.
- **The orchestrator stays thin.** It classifies/routes only. ALL domain logic lives in module handlers (`modules/<domain>/`).
- **`shared/` wraps external clients once.** Modules never call the Anthropic SDK, OpenAI SDK, or Supabase client directly — they import from `shared/llm.py` and `shared/db.py`.
- **Model tiering**: cheap/fast models (GPT-4o-mini, Gemini Flash) for classification/routing; Claude for nuanced generation and reasoning.
- **Two schema shapes, never conflated**:
  - *Generated content* (workout plans, meal plans): stored as JSON/text blobs with metadata.
  - *Logged entries* (meals, macros, transactions): structured rows with typed numeric fields.
- **n8n handles scheduled/triggered automation** — separate from conversational logic. Don't build cron/scheduling into the bot.
- **Garmin integration is parked (v2).** Do not build it, stub it, or design around it.

## Current state

- `modules/health/workout_generator.py` — standalone workout plan generator using the Anthropic SDK. Working, committed. Profile is a hardcoded dict; that's intentional for now.
- `bot/main.py` — Telegram bot (python-telegram-bot) responding to `/workout` with a generated plan. Working, committed.
- Supabase project `personal-assistant` exists in ap-southeast-2, currently **paused** — Sandi will unpause it and provide `SUPABASE_URL` and `SUPABASE_KEY` when needed.
- Git repo initialised, `.gitignore` and `.env` pattern established (`python-dotenv`).

## Roadmap (direction, not decided — plan details WITH Sandi)

The phases and features below are candidate ideas, not a locked plan. At the start of a build, discuss and agree scope with Sandi before writing code. Rough direction:

- **Next up**: wire Supabase into the existing bot (persist workout plans). Details to be planned together.
- **After that (rough order, all open to discussion)**: meal and macro logging (free-text parsed by LLM + quick-pick; structured numeric schema), then a meal plan generator informed by real logged data, then the Money module (a `transactions` table + CSV ingestion is paused pending bank format confirmation from Sandi).
- Dashboard, Career, and Mentorship modules are further out.

Do not invent schemas, commands, or feature scope unilaterally — propose options and let Sandi choose.

## Working style (important)

- **Session flow**: exploratory discussion first to lock in decisions, then guided execution. Plan phases and features collaboratively with Sandi — she wants to design the details in conversation, not receive a finished plan.
- **One visible working output per session.** Never end a session without something demoable and committed. Prefer small vertical slices over broad scaffolding.
- **Clarify before recommending.** Ask targeted questions before proposing solutions when requirements are ambiguous.
- **Push back on complexity.** If something adds friction without proportionate value, say so before building it.
- **Explain at block level, not line level.** Sandi is technically proficient (Python, APIs, n8n/Make/Zapier). For code, give a short summary of what each block/function does — enough to find and fix things later — not line-by-line walkthroughs. Shell commands still explained individually (not chained), with plain alternatives to clever one-liners.
- **Sandi handles manual/external steps**: creating API keys, unpausing Supabase, Telegram BotFather config, dashboard clicks. Tell her exactly what you need and wait; don't guess credentials or invent table names that haven't been created.
- Commit at each working milestone with clear messages.

## Stack

- Python 3.x, virtualenv (`.venv`), `pip`, `python-dotenv`
- python-telegram-bot
- Anthropic SDK (generation), OpenAI/Gemini APIs (classification) — all via `shared/`
- Supabase (`supabase-py`)
- n8n for automation, Git for version control, VS Code

## Environment variables (in `.env`, never committed)

- `ANTHROPIC_API_KEY` — set
- `TELEGRAM_BOT_TOKEN` — set
- `SUPABASE_URL`, `SUPABASE_KEY` — Sandi will provide when Day 2b starts
- `OPENAI_API_KEY` / `GEMINI_API_KEY` — later, when orchestrator classification is built

## Target repo layout

```
life-os/
├── CLAUDE.md
├── PLAN.md
├── .env                  # never committed
├── .gitignore
├── requirements.txt
├── bot/
│   └── main.py           # Telegram entry point, stays thin
├── orchestrator/         # message routing (future — don't build early)
├── shared/
│   ├── llm.py            # wraps Anthropic/OpenAI/Gemini clients
│   └── db.py             # wraps Supabase client
└── modules/
    ├── health/
    │   ├── workout_generator.py   # exists
    │   ├── handlers.py            # bot command/message handlers for health
    │   └── ...
    └── money/                     # future
```

Note: a nested `life-os/life-os/` directory happened once before — watch out for it when scaffolding.

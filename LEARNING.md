# Life OS — Learning Guide

A study companion for this project: every component we use, why it was
chosen, what the alternatives were, how it fails, and how to debug it.
Written to be pasted into Claude chats as context when you want to go
deeper on any piece. Sibling docs: `PROJECT_SPEC.md` (what this is),
`PLAN.md` (build plans), `CLAUDE.md` (Claude's working rules).

---

## The map: how a `/workout` flows through everything

Tracing one command end-to-end is the fastest way to understand the system:

```
You type /workout in Telegram
  → Telegram's servers hold the message
  → bot/main.py (long-polling loop) picks it up, runs the workout() handler
  → handler calls modules/health/profile.py → get_profile()
      → shared/db.py → Supabase REST API → profiles table → your settings
  → handler calls workout_generator.build_prompt(profile) → prompt text
  → generate_plan() → shared/llm.py → Anthropic API → Claude writes the plan
  → bot converts **bold** to Telegram HTML, splits into ≤4000-char chunks, sends
  → modules/health/storage.py → shared/db.py → INSERT into workout_plans
  → "Saved." confirmation sent
```

The dashboard is a second door into the same data: `dashboard/app.py` reads
`workout_plans` and reads/writes `profiles` through the *same* shared/db and
profile.py code — which is why an edit in either place shows up in both.

---

## Component by component

### 1. Python + virtualenv (running under WSL)

**What**: All code is Python. The `.venv` folder holds this project's own
copy of Python packages so they don't clash with other projects.

**The catch discovered in this project**: the `.venv` was created inside
WSL (Ubuntu running on Windows), so it contains *Linux* binaries
(`.venv/bin/`). Windows Python can't use it (Windows venvs have
`.venv/Scripts/` instead). Everything must run through WSL.

**Failure modes & debugging**:
- "command not found" / "No module named X" → you're using the wrong
  Python. Check with `which python` and `pip show <package>`. The reliable
  form here is always `.venv/bin/python -m <module>` from the repo root.
- Imports like `from shared import db` fail → you ran the file from the
  wrong directory. Run from repo root with `-m`
  (e.g. `python -m bot.main`), which puts the root on the import path.

### 2. python-telegram-bot (the chat interface)

**What**: A library that connects to Telegram's Bot API. Ours uses
**long polling**: an infinite loop asking Telegram "any new messages?"
every few seconds. Each `/command` maps to an async handler function in
`bot/main.py`.

**Why polling, not webhooks**: webhooks (Telegram pushes messages to a URL
you host) need a public server + HTTPS. Polling works from any laptop with
no setup. Webhooks become worth it when the bot is deployed 24/7.

**Key facts you'll hit**:
- Messages cap at 4096 chars → we chunk at 4000 (`reply_chunked`).
- Formatting requires a `parse_mode`; plain sends show `**bold**`
  literally. We use HTML mode and convert `**x**` → `<b>x</b>`.
- Telegram queues messages sent while the bot is offline (~24h) and
  delivers them on startup — that's why a dead bot seems to "catch up".

**Failure modes & debugging** (both happened in this project):
- *Bot silent in Telegram* → the process isn't running. It's not "the bot
  is broken" — there is simply nobody polling. Check with `ps aux | grep
  bot.main` in WSL.
- *Two instances running* → they fight over `getUpdates` and both
  misbehave (Telegram error "Conflict"). Only ever run one.
- *HTML parse errors* → if sent text contains stray `<` or `&` without
  escaping, Telegram rejects the message. Our `md_to_telegram_html()`
  escapes first, converts bold second — keep that order.
- Watch the terminal running the bot: every update and API call is logged.

### 3. Anthropic API via `shared/llm.py` (the AI generation)

**What**: `generate(prompt, model, max_tokens)` sends a prompt to Claude
and returns text. The only place the Anthropic SDK is touched.

**Why a wrapper**: when we add retries, another provider, token logging, or
switch models, it's one file — not a hunt through every module. This is the
"`shared/` wraps external clients once" architecture rule in action.

**Alternatives**: calling the SDK directly in each module (we started
there; refactored out — every new call site would multiply future work),
or a framework like LangChain (adds a big dependency for what is, for us,
one function).

**Failure modes & debugging**:
- Missing/invalid `ANTHROPIC_API_KEY` → authentication error on first call.
- Rate limits / overloaded API → 429/529 errors; retry after a pause.
- **Latency variance is normal**: identical prompts took 21s and 75s on
  the same day. Output length is controllable (our prompt says "under 1800
  characters"); API load is not.
- Debug by printing the prompt (`--dry-run` on the generator does exactly
  this — inspect what Claude is actually being asked).

### 4. Supabase via `shared/db.py` (the database)

**What**: Hosted Postgres with a REST API in front of it (called
PostgREST). `supabase-py` translates `db.insert("table", {...})` into HTTP
calls. You never manage a database server.

**Why Supabase**: free tier, zero server admin, a web dashboard (Table
Editor + SQL Editor) for inspecting data, and the REST layer means the
dashboard-and-bot-share-data pattern needs no extra API of ours.
**Alternatives**: SQLite (simpler, but local-file-only — a future hosted
dashboard couldn't reach it), raw Postgres (server admin burden), Airtable
(friendly but weak as a real database).

**Concepts you must know**:
- **Two kinds of API keys** (bit us today): the *publishable* key
  (`sb_publishable_...`) is safe for browsers but subject to Row Level
  Security; the *secret* key (`sb_secret_...`) bypasses RLS and must only
  live server-side (our `.env`).
- **Row Level Security (RLS)**: per-row permission rules. Our tables have
  RLS ON with no policies = the publishable key can do *nothing* (good—
  data is private), while the secret key ignores RLS entirely.
- **Free-tier pausing**: idle projects pause; everything errors until you
  restore it from the dashboard.

**Failure modes & debugging** (all three seen in this project):
- `42501: new row violates row-level security policy` → you're on the
  publishable key. Swap in the secret key.
- `PGRST205: Could not find the table ... in schema cache` → the table
  doesn't exist yet; run the CREATE TABLE in the SQL Editor.
- Scary red logs about `Realtime ... MigrationsFailedToRun` in the
  Supabase dashboard → internal noise from Supabase's Realtime service
  (which we don't use), common right after unpausing. Ignore; our requests
  are the `200`/`201` lines.
- General debugging: the Table Editor shows you exactly what's stored;
  every db call the bot makes is logged as an `httpx` line with the HTTP
  status (`201 Created` = insert worked).

### 5. Streamlit (the dashboard)

**What**: A Python library that turns a script into a web page. No HTML,
CSS, or JavaScript — `st.title("Life OS")` renders a heading,
`st.text_input(...)` renders a form field.

**The one mental model that explains all of Streamlit**: your script
**re-runs top to bottom on every interaction** (button click, field edit).
It's not an app with state that "reacts"; it's a script that replays. This
explains most surprises — e.g. after clicking Save, the whole script runs
again, re-fetching plans and profile from Supabase.

**Why Streamlit**: pure Python (your language), reuses `shared/db.py` and
`modules/health/` directly with zero API layer, and a working page in an
hour. Trade-off: it looks functional rather than designer-polished, and
complex interactivity gets awkward.
**Alternatives considered**: Next.js/React (most polished, but a whole new
JS/TS stack and slower first version), plain HTML + Supabase JS (no server,
but auth/RLS gets fiddly and it grows badly), and cousins like Dash or
Gradio (similar niche; Streamlit has the biggest community).

**Failure modes & debugging**:
- Page won't load → is the process running? Start:
  `.venv/bin/python -m streamlit run dashboard/app.py` from repo root.
  Port busy → something else on 8501 (another Streamlit still running).
- Blank/erroring page → the exception shows in the terminal AND on the
  page itself; Streamlit is unusually good at surfacing errors.
- Slow page → remember the rerun model: every interaction re-fetches from
  Supabase. Fine at our scale; `st.cache_data` exists if it ever isn't.
- Headless testing exists: `streamlit.testing.v1.AppTest` runs the script
  without a browser (how the dashboard was verified today).

### 6. .env + python-dotenv (secrets)

**What**: `.env` holds keys (Anthropic, Telegram token, Supabase URL/key).
`load_dotenv()` reads it into environment variables at startup. `.env` is
git-ignored — secrets never enter version control.

**Failure modes**: forgetting `load_dotenv()` in a new entry point (bot,
dashboard, and scripts each load it themselves); editing `.env` while a
process runs (restart to pick up changes); the classic disaster is
committing `.env` — if a key ever leaks, revoke and reissue it, don't just
delete the commit.

### 7. Git (version control)

**Why the one-commit-per-working-milestone habit**: every commit is a
known-good state you can return to. When something breaks, `git log` +
`git diff HEAD~1` answer "what changed since it last worked?" — the single
most powerful debugging tool in the whole stack.

### 8. n8n (reserved for scheduling — not used yet)

**What**: a visual automation tool (you know it). Reserved role here:
anything time-triggered (e.g. Monday-morning auto-plans) lives in n8n, not
in the bot. **Why**: the bot answers messages; mixing schedulers into it
adds a second responsibility and a second failure mode. Separation means a
broken schedule never takes the bot down.

---

## The architecture rules, as *why*s

- **Hub-and-spoke, thin orchestrator**: one bot, many domain modules. The
  router only routes so that adding Money never means touching Health.
- **`shared/` wraps external services once**: swap a provider or add
  logging in one file. Both bot and dashboard already benefit — they share
  db access for free.
- **Two schema shapes**: AI-written text (workout plans) is stored as one
  blob — you only ever read it back. Facts you log (meals, money) are
  stored as typed numeric rows — you'll want sums and averages, and you
  can't `SUM()` a paragraph. Conflating these is the most expensive
  mistake available this early, which is why it's a locked rule.

---

## Debugging playbook (symptom → first place to look)

| Symptom | First check |
|---|---|
| Bot silent in Telegram | Is the process running? (`ps aux \| grep bot.main` in WSL) |
| Bot replies but "couldn't save" | Bot terminal log → likely a Supabase error (key? paused project?) |
| `42501` RLS violation | Wrong key type — need `sb_secret_...` in `.env` |
| `PGRST205` table not found | Table not created — SQL Editor |
| Dashboard won't load | Is Streamlit running? Right port? Terminal shows the error |
| Dashboard shows stale data | It doesn't — it re-fetches on every interaction; refresh the page |
| Generation feels slow | Normal variance (21–75s observed). Not a bug below ~90s |
| "No module named shared" | Ran from wrong directory — use `-m` from repo root |
| Everything Supabase errors at once | Project paused (free tier) — restore in dashboard |

*A good general habit: read the error message bottom-up (Python tracebacks
put the actual error last), then find which component's boundary it names —
the table above is really just "which boundary broke?"*

# Life OS — Learning Guide

A study companion for this project: every component we use, why it was
chosen, what the alternatives were, how it fails, and how to debug it.
Written to be pasted into Claude chats as context when you want to go
deeper on any piece. Sibling docs: `PROJECT_SPEC.md` (what this is),
`PLAN.md` (build plans), `CLAUDE.md` (Claude's working rules).

> Covers the project through Phase 5. The shape has evolved: the bot began
> as fixed slash commands returning AI-written documents, and is now a
> natural-language assistant that classifies what you mean, keeps structured
> data about your training, and answers questions grounded in it. The
> dashboard is the planning surface; the bot is for logging and asking.

---

## The two maps: how a message flows through everything

Tracing a message end-to-end is the fastest way to understand the system.
There are two entry styles now — a slash command and free text — and they
converge on the same handlers.

**A. "give me a leg day" (free text → new plan)**

```
You type "give me a leg day" in Telegram (no slash)
  → bot/main.py MessageHandler catches it → handle_text()
  → orchestrator/router.py classify() → shared/llm.py generate_json()
        → Anthropic (Haiku) returns {"intent": "generate_workout", ...}
  → handler runs _run_workout():
      → profile.get_profile() → shared/db.py → Supabase → your settings
      → workout_generator.generate_plan() → shared/llm.py generate_json()
            → Anthropic (Sonnet) returns STRUCTURED plan_data (not prose)
      → render.render_plan_html(plan_data) builds the Telegram message
      → storage.save_workout_plan() → Supabase INSERT into workout_plans
        (both plan_data jsonb AND a rendered plan_markdown snapshot)
```

**B. "did squats 5x5 at 80kg" (free text → logged fact)**

```
handle_text() → classify() → {"intent": "log_session",
                              "exercises": [{name, sets, reps, weight, unit}]}
  → _log_session() → storage.save_workout_log() → Supabase workout_logs
  → bot replies "Logged: …" with an Undo button (deletes the row if tapped)
```

Notice the difference from a plan: a plan is *generated content* (one blob
you read back); a logged session is a *structured fact* (numeric fields you
can later sum, chart, and query). That distinction is the spine of the whole
project — see "The two schema shapes" below.

The dashboard is a third door into the same data: `dashboard/app.py` reads
and writes the same Supabase tables through the same `shared/db.py` and
`modules/health/` code — which is why an edit in the dashboard shows up in
Telegram and vice-versa.

---

## Component by component

### 1. Python + virtualenv (running under WSL)

**What**: All code is Python. The `.venv` folder holds this project's own
copy of Python packages so they don't clash with other projects.

**The catch discovered in this project**: the `.venv` was created inside
WSL (Ubuntu running on Windows), so it contains *Linux* binaries
(`.venv/bin/`). Windows Python can't use it (Windows venvs have
`.venv/Scripts/` instead). Everything must run through WSL. To activate:
`source .venv/bin/activate`; or run directly without activating:
`.venv/bin/python -m bot.main`.

**Failure modes & debugging**:
- "command not found" / "No module named X" → wrong Python. Check with
  `which python` and `pip show <package>`. Reliable form is always
  `.venv/bin/python -m <module>` from the repo root.
- Imports like `from shared import db` fail → you ran the file from the
  wrong directory. Run from repo root with `-m` (e.g. `python -m bot.main`),
  which puts the root on the import path.

### 2. python-telegram-bot (the chat interface)

**What**: A library that connects to Telegram's Bot API via **long
polling** (an infinite loop asking Telegram "any new messages?"). Three
kinds of handler now live in `bot/main.py`:
- `CommandHandler` — slash commands (`/workout`, `/lastplan`, `/profile`).
- `MessageHandler(filters.TEXT & ~filters.COMMAND)` → `handle_text` — any
  non-command message; this is the natural-language path.
- `CallbackQueryHandler` → `handle_button` — taps on inline buttons.

**Buttons and confirmation flows** (added Phase 4): inline keyboards
(`InlineKeyboardMarkup`) give tappable buttons. Each button carries a
`callback_data` string; `handle_button` reads it and dispatches. Two uses:
the `/start` menu, and confirm/undo safety steps — a natural-language
profile edit shows "Set days_per_week to 4? Yes/No" before writing, and a
logged session shows an Undo button. State between the message and the
button press is held in `context.user_data` (in-memory; resets if the bot
restarts — fine for a single-user bot).

**Why polling, not webhooks**: webhooks need a public server + HTTPS.
Polling works from any laptop with no setup. Webhooks become worth it when
the bot is deployed 24/7.

**Key facts you'll hit**:
- Messages cap at 4096 chars → we chunk at 4000 (`reply_chunked`), splitting
  on line boundaries so a `<b>…</b>` tag never breaks across messages.
- Formatting requires a `parse_mode`; we use HTML mode. Plans are now
  *rendered from structured fields* into `<b>` headers (see render.py), so
  the bot no longer depends on the model emitting exact `**bold**`.
- Telegram queues messages sent while the bot is offline (~24h) and delivers
  them on startup — that's why a dead bot seems to "catch up".

**Failure modes & debugging**:
- *Bot silent* → the process isn't running. Nobody's polling. Check
  `pgrep -af bot.main` in WSL.
- *Two instances running* → they fight over `getUpdates` and both misbehave
  (Telegram "Conflict" error). Only ever run one.
- *HTML parse errors* → stray `<` or `&` in sent text. Our renderers
  `html.escape()` first, then add tags — keep that order.
- *A message does the wrong thing* → it's a **misclassification**, not a
  handler bug. Watch the bot log to see which intent `classify()` returned.
  See the orchestrator section.

### 3. Anthropic API via `shared/llm.py` (the AI layer)

**What**: the single place the Anthropic SDK is touched. Two functions:
- `generate(prompt, model, max_tokens)` → returns text. Used for prose:
  history Q&A answers.
- `generate_json(prompt, model, schema)` → returns a dict matching `schema`.
  Used everywhere we need *structured* output: plan generation, intent
  classification, log extraction.

**Structured output via "tool use" (the important technique)**: instead of
asking the model for JSON in text and hoping it parses, `generate_json`
gives the model a fake "tool" whose input schema is what we want, and forces
it to call that tool (`tool_choice={"type":"tool","name":"extract"}`). The
model's tool call *is* validated JSON in the shape we asked for. This is why
plans come back as reliable `{summary, days:[…]}` and logs as
`[{name, sets, reps, weight, unit}]` — no fragile text parsing.

**Model tiering** (an architecture rule, now real): cheap/fast **Claude
Haiku** does classification and history Q&A (high volume, simple); capable
**Claude Sonnet** writes workout plans (nuanced, once per request). Note: the
original plan was to use GPT-4o-mini/Gemini for classification; we used Haiku
instead to avoid needing a second API key — a deliberate deviation recorded
in PLAN.md Phase 4. Model IDs live at the top of `router.py`,
`workout_generator.py`, and `history.py`.

**Why a wrapper**: switch models, add retries/logging, or add a provider in
one file. "`shared/` wraps external clients once."

**Failure modes & debugging**:
- Missing/invalid `ANTHROPIC_API_KEY` → auth error on first call.
- Rate limits / overload → 429/529; retry after a pause.
- **Latency variance is normal**: identical prompts took 21s and 75s the
  same day. Output length is controllable; API load is not.
- Structured output wrong/empty → inspect the prompt and the schema. A
  too-strict schema (e.g. a required field the model can't fill) causes
  bad extractions more often than the model "being dumb".

### 4. The orchestrator / intent classifier (`orchestrator/router.py`)

**What**: `classify(text)` decides what a free-text message *means* and
returns a dict like `{"intent": "log_session", "field": None, "value": None,
"exercises": [...]}`. Intents today: `generate_workout`, `show_last_plan`,
`show_profile`, `update_profile`, `log_session`, `whats_today`,
`query_history`, `unknown`. It uses Haiku via `generate_json`.

**The role, and the discipline**: the orchestrator only *routes* — it
classifies and hands back. All the actual doing lives in the bot handlers
and the health module. This is the "thin orchestrator" rule: adding a Money
domain later means adding intents and a field registry here, never business
logic. Right now it only knows Health's fields (`ALLOWED_FIELDS`), which is
deliberate — a general registry isn't worth building until a second domain
exists.

**Why an LLM classifier, not keywords**: "give me a leg day", "make me a
plan", and "I need something for legs" all mean the same thing; keyword
rules can't keep up with phrasing. An LLM reads intent. The cost is that
it's probabilistic — see failure modes.

**Failure modes & debugging**:
- *Misclassification* → the model picked the wrong intent, or extracted a
  field/value wrong. This is the main new failure class. Debug by calling
  `classify("your message")` directly in a script and reading the result;
  fix by sharpening the intent descriptions in the prompt or the schema.
- *Everything comes back `unknown`* → usually an exception inside
  `generate_json` (bad key, network) being swallowed into the safe default.
  Check the bot log for the underlying error.
- Safety nets exist for the fragile cases: profile edits and unknown intents
  both route to a confirm/menu step rather than acting blindly.

### 5. Supabase via `shared/db.py` (the database)

**What**: Hosted Postgres with a REST API (PostgREST) in front. `supabase-py`
turns `db.insert("table", {...})` into HTTP calls. Helpers in `shared/db.py`:
`insert`, `update`, `delete`, `latest`, `list_rows`. You never run a server.

**Two schema shapes, now both real** (this is the concept to internalize):
- `workout_plans` — *generated content*. `plan_data` (jsonb) is the
  structured source of truth; `plan_markdown` is a human-readable snapshot
  rendered from it at save time. You read plans back; you don't do math on
  them.
- `workout_logs` — *logged entries*. Structured numeric rows
  (`exercises` jsonb with sets/reps/weight/unit). You DO aggregate these —
  "heaviest squat over time", "what did I lift last week". You can't `SUM()`
  a paragraph, which is exactly why logs aren't stored as prose.
- `profiles` — a single jsonb settings row (neither content nor a log; just
  current state).

**Concepts you must know**:
- **Two kinds of API keys**: the *publishable* key (`sb_publishable_…`) is
  browser-safe but blocked by Row Level Security; the *secret* key
  (`sb_secret_…`) bypasses RLS and must stay server-side (our `.env`). We
  use the secret key.
- **Row Level Security (RLS)**: per-row permission rules. Our tables have
  RLS ON with no policies = publishable key can do nothing (data private),
  secret key ignores RLS.
- **Free-tier pausing**: idle projects pause; everything errors until you
  restore from the dashboard.
- **jsonb does not preserve key order** — Postgres re-sorts object keys
  alphabetically. Store `{name, sets, reps, rest}` and it comes back
  `{name, reps, rest, sets}`. Harmless for lookups, but it bit us visually
  (dashboard columns shifting after a save/reload); the fix was pinning
  column order in the UI, not trusting dict order.

**Failure modes & debugging**:
- `42501: new row violates row-level security policy` → you're on the
  publishable key. Use the secret key.
- `PGRST205: Could not find the table … in schema cache` → the table doesn't
  exist yet; run the CREATE TABLE in the SQL Editor.
- `column … does not exist` → the code expects a column you haven't added
  yet (e.g. `plan_data` needed an `alter table … add column`). Migrations
  are manual SQL you run in the dashboard.
- Scary red `Realtime … MigrationsFailedToRun` logs in the Supabase
  dashboard → internal noise from a service we don't use, common after
  unpausing. Ignore. Our requests are the `200`/`201` lines.
- Table Editor shows exactly what's stored; every db call is an `httpx` log
  line with its HTTP status (`201 Created` = insert worked).

### 6. Streamlit (the dashboard)

**What**: A Python library that turns a script into a web page — no
HTML/CSS/JS. `st.title(...)`, `st.data_editor(...)`, `st.line_chart(...)`.

**The one mental model that explains all of Streamlit**: the script
**re-runs top to bottom on every interaction**. It's not a reactive app with
persistent state; it's a script that replays. Two consequences you'll meet:
- To keep in-progress edits alive across those reruns, we stash them in
  `st.session_state` (the plan being edited is held there until Save writes
  it back to Supabase and clears it).
- After any click, everything re-fetches from the DB — which is why an edit
  saved in the dashboard is instantly visible to the bot.

**What the dashboard does now**: the Health tab shows the latest plan in
editable tables (`st.data_editor`, one per day — swap exercises, change
sets/reps, add/remove days), a profile form, and a Progress line chart of
your heaviest logged weight per exercise over time. Older plans stay
read-only.

**Why Streamlit**: pure Python, reuses `shared/db.py` and `modules/health/`
directly with zero API layer, working page in an hour. Trade-off: functional
rather than polished, and complex interactivity gets awkward.
**Alternatives**: Next.js/React (polished, but a whole JS/TS stack), plain
HTML + Supabase JS (no server, but auth/RLS fiddly), Dash/Gradio (similar
niche, smaller community).

**Failure modes & debugging**:
- Page won't load → is the process running? `.venv/bin/python -m streamlit
  run dashboard/app.py` from repo root. Port busy → another Streamlit on 8501.
- Blank/erroring page → the exception shows in the terminal AND on the page.
- Widget edits "don't take" when automated → Streamlit widgets sync through
  the browser; scripted DOM edits don't always register before a save.
  Real typing in a real browser is fine — this only affects test automation,
  which is why some dashboard checks need a human click-through.
- Headless testing: `streamlit.testing.v1.AppTest` runs the script without a
  browser (how we smoke-test rendering).

### 7. .env + python-dotenv (secrets)

**What**: `.env` holds keys (Anthropic, Telegram, Supabase). `load_dotenv()`
reads it into environment variables at startup. `.env` is git-ignored —
secrets never enter version control. Each entry point (bot, dashboard,
scripts) calls `load_dotenv()` itself.

**Failure modes**: forgetting `load_dotenv()` in a new entry point; editing
`.env` while a process runs (restart to pick up changes); the classic
disaster is committing `.env` — if a key leaks, revoke and reissue it, don't
just delete the commit.

### 8. Git + GitHub (version control & backup)

**Local habit**: one commit per working milestone. Every commit is a
known-good state; `git log` + `git diff HEAD~1` answer "what changed since it
last worked?" — the most powerful debugging tool in the stack.

**Remote (added when we pushed to GitHub)**:
- A *remote* named `origin` points local git at a GitHub repo
  (`git remote add origin <url>`); `git push -u origin main` uploads and
  links the branch so later pushes are just `git push`.
- **GitHub auth is NOT your password** — password auth was removed in 2021.
  Over HTTPS you authenticate with a **Personal Access Token** (fine-grained,
  scoped to the repo, needs Contents: Read and write). Typing your real
  password gives `403 Permission denied` — that specific error almost always
  means "you used a password, not a token".
- `git config --global credential.helper store` caches the token so you're
  not pasting it every push (stored plain-text in your home dir — fine on a
  personal machine).
- The private repo keeps life data private; `.env` staying git-ignored keeps
  keys off GitHub even in a private repo.

### 9. n8n (reserved for scheduling — not used yet)

**What**: a visual automation tool. Reserved role: anything time-triggered
(e.g. Monday-morning auto-plans) lives in n8n, not the bot. **Why**: the bot
answers messages; mixing schedulers in adds a second responsibility and
failure mode. Separation means a broken schedule never takes the bot down.

---

## Key techniques worth naming

- **Structured output via tool use** (component 3): force the model to
  return schema-shaped JSON by making it "call a tool". Turns the LLM from a
  text generator into a reliable data extractor. Used for plans, intent
  classification, and log parsing.
- **Grounded question answering** (`modules/health/history.py`): to answer
  "what did I lift last week", we fetch recent `workout_logs`, hand them to
  the model *with* the question, and instruct it to answer only from that
  data and admit when something isn't there. This is retrieval-augmented
  answering in miniature — the model reasons over real data instead of
  making things up. Verified by asking about a lift never logged and
  confirming it refuses rather than inventing a number.
- **Deterministic when you can, LLM when you must** (`get_today_session`):
  "what am I doing today" is answered by matching today's weekday against the
  plan — plain Python, no model call, can't hallucinate. Only open-ended
  questions go to the LLM. Reach for code first, the model second.

---

## The architecture rules, as *why*s

- **Hub-and-spoke, thin orchestrator**: one bot, one classifier that only
  routes, many domain modules. Adding Money never means touching Health.
- **`shared/` wraps external services once**: swap a provider or add logging
  in one file. Bot and dashboard share db and LLM access for free.
- **Two schema shapes**: generated content (plans) is stored to read back;
  logged entries (sessions, later meals/money) are structured numeric rows
  you aggregate. Now concrete in `workout_plans` vs `workout_logs`.
  Conflating them is the most expensive early mistake, which is why it's
  locked.
- **Dashboard plans, bot logs/asks**: the dashboard is for creating and
  editing (a screen, a keyboard); the bot is for quick capture and questions
  on the go. Each surface plays to its strengths against shared data.

---

## Debugging playbook (symptom → first place to look)

| Symptom | First check |
|---|---|
| Bot silent in Telegram | Is the process running? (`pgrep -af bot.main` in WSL) |
| A message triggers the wrong action | Misclassification — call `classify("…")` in a script, read the intent |
| Everything classifies as `unknown` | An exception inside `generate_json` swallowed — check bot log |
| Bot replies but "couldn't save" | Bot log → likely a Supabase error (key? paused? missing column?) |
| `42501` RLS violation | Wrong key type — need `sb_secret_…` in `.env` |
| `PGRST205` table not found | Table not created — SQL Editor |
| `column … does not exist` | Missing migration — `alter table … add column …` in SQL Editor |
| Dashboard columns/fields reorder after save | jsonb re-sorts keys; UI must pin order, don't trust dict order |
| Dates look a day off | Logs stored UTC; convert to local before display (`.astimezone()`) |
| Dashboard won't load | Is Streamlit running? Right port? Terminal shows the error |
| Dashboard edit won't save under automation | Streamlit widget quirk — needs a real browser click, not scripted |
| Generation feels slow | Normal variance (21–75s observed). Not a bug below ~90s |
| "No module named shared" | Ran from wrong directory — use `-m` from repo root |
| `git push` → 403 Permission denied | Used a password, not a Personal Access Token |
| Everything Supabase errors at once | Project paused (free tier) — restore in dashboard |

*A good general habit: read the error message bottom-up (Python tracebacks
put the actual error last), then find which component's boundary it names —
the table above is really just "which boundary broke?"*

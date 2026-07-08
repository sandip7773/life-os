# Life OS — What This Is (Plain-Language Overview)

This is a snapshot for human reading. For Claude's operating rules see
`CLAUDE.md`; for the live, evolving build plan see `PLAN.md`.

## What Life OS is

Life OS is a personal assistant you talk to on Telegram. Instead of juggling
separate apps for workouts, finances, career planning, and mentorship,
there's one chat you send messages to, and behind the scenes different
"modules" handle each area of your life. Everything gets saved to one shared
database so nothing is lost between conversations.

## How it's put together

A few concepts come up repeatedly — here's what they mean, briefly:

- **Telegram bot** — the actual chat window you type into. It's the single
  front door; you never talk to a "health bot" and a "money bot" separately.

- **Orchestrator** *(built, Health-only for now)* — a lightweight router
  that reads each free-text message and decides what you *mean* (e.g. "give
  me a leg day" = make a plan; "did squats 5x5" = log a workout; "what did I
  lift last week" = answer from history). It uses a cheap, fast AI model to
  classify intent, then hands off — it doesn't do the actual work itself.
  Today it only knows Health's intents; other domains plug in later.

- **Modules** — each life area (Health, Money, Career, Mentorship) is its
  own self-contained piece of code. A module knows how to do its own job
  (like generating a workout plan) without needing to know anything about
  the other modules.

- **`shared/` wrappers** — anywhere the app needs to talk to an outside
  service (the Claude AI model, the Supabase database), it goes through one
  shared piece of code instead of every module calling that service on its
  own. This means if we ever switch AI providers or change how the database
  connects, it's a one-place fix instead of hunting through every module.

- **Supabase** — the hosted database. In plain terms: the place where things
  get permanently saved so they survive after the chat conversation ends or
  the bot restarts.

- **Dashboard** — a local web page (built with Streamlit) that is the
  *planning* surface. The AI drafts a workout plan, and you edit it there
  exercise-by-exercise; it also shows a progress chart of your lifts. The
  split is deliberate: **the dashboard is for planning and reviewing, the
  bot is for quick logging and asking questions** on the go. Both read and
  write the same database, so an edit in one shows up in the other.

- **Two kinds of saved data** — the project deliberately treats these as
  different, and both now exist:
  - *Generated content*: something the AI made for you — a workout plan.
    Stored as structured data (days, exercises, sets/reps) so you can edit
    individual pieces, plus a readable snapshot. You mainly read it back.
  - *Logged entries*: facts you record — "did squats 5x5 at 80kg" — saved as
    actual numbers in a database row, not a sentence. This matters because
    questions like "what did I lift last week?" or a progress chart need to
    add numbers up and compare them, not re-read paragraphs.

## What's built and working right now (Health)

The Health module is a working personal-training assistant end-to-end:

- **Talk to it naturally** — you don't need to memorize commands. "Give me a
  leg day", "what's my profile", "I want to train 4 days a week", "did squats
  5x5 at 80kg", "what did I lift last week" all just work. (The old slash
  commands `/workout`, `/lastplan`, `/profile` still work too, and a button
  menu appears when it's unsure what you meant.)
- **Workout plans** — the AI drafts a personalized weekly plan from your
  profile (goal, experience, days/week, equipment…), saved to the database.
  Ask for your last plan any time and it comes back instantly.
- **Editable plans in the dashboard** — open the local dashboard and edit the
  latest plan exercise-by-exercise (swap moves, change sets/reps, add or
  remove days). Changes are saved and the bot sees them immediately.
- **Session logging** — tell the bot what you actually did and it's saved as
  structured numbers, with an Undo button in case it misheard.
- **"What am I doing today?"** — it checks today's weekday against your plan
  and tells you today's session (or that it's a rest day).
- **History questions** — ask about past workouts and it answers only from
  what you've actually logged, rather than making things up.
- **Progress chart** — the dashboard charts your heaviest logged weight per
  exercise over time.
- **Editable profile** — change your training settings from either the bot
  (in plain words) or the dashboard.

Under the hood, all of this runs through the shared wrappers (`shared/llm.py`
for the AI, `shared/db.py` for the database) and the thin orchestrator, so
the next domain reuses the same machinery.

## What's next (ideas only — not committed, to be planned in detail first)

The plan is to apply the exact same pattern the Health module now proves —
AI-drafted content you edit in the dashboard, plus natural-language logging
and questions through the bot — to new areas:

- **Meals** — meal plans you can edit, plus logging what you ate (parsed into
  macros) and asking about it. Same shape as workouts.
- **Money module** — tracking transactions and bills.
- **Career and Mentorship** modules, and eventually a hosted (not just local)
  dashboard, are further out.

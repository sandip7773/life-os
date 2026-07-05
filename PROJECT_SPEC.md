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

- **Orchestrator** *(not built yet)* — a lightweight router that will read
  each message and decide which module should handle it (e.g. "log 2 eggs"
  goes to Health, "paid rent" goes to Money). Its only job is deciding where
  a message goes — it doesn't do the actual work itself.

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

- **Two kinds of saved data** — the project deliberately treats these as
  different:
  - *Generated content*: something the AI wrote for you, saved mostly as-is
    — like a full workout plan in Markdown. You don't need to do math on
    this, just read it back later.
  - *Logged entries*: facts you record about yourself, saved as structured,
    calculable data — like "ate 2 eggs, 12g protein, 140 calories" as actual
    numbers in a database row, not just a sentence. This matters because
    later features (like "how much protein did I eat this week?") need to
    add numbers up, not re-read paragraphs.

## What's built and working right now

- **Workout plan generator** — a script that takes your fitness profile
  (goal, experience level, days per week, equipment, etc.) and asks Claude
  to write a personalized weekly workout plan in Markdown.
- **Telegram `/workout` command** — the bot is live and connected; typing
  `/workout` in Telegram triggers the generator above and sends the plan
  back to you in chat, split into pieces if it's too long for one message.
- **Shared AI wrapper** — the code that actually calls Claude now lives in
  one place (`shared/llm.py`) instead of being written directly inside the
  workout generator. This was a small cleanup so that every future feature
  needing AI generation reuses the same wrapper instead of each one calling
  the AI service its own way.

## What's being built right now (Day 2b)

Right now, if you ask for a workout plan, it's only ever in that one
Telegram message — once the chat scrolls away, it's gone unless you saved it
yourself. This next piece fixes that:

- Every plan the bot generates gets **saved to the database** automatically.
- A new command, **`/lastplan`**, lets you ask for your most recently saved
  plan again, instantly — no need to regenerate it (which costs an API call
  and takes ~30 seconds) if you just want to see it again.

This depends on a few manual setup steps (unpausing the database project,
creating the table it saves to, and adding the connection details) that
happen outside of code, in the Supabase dashboard.

## What's next (ideas only — not committed, to be planned in detail first)

- **Meal & macro logging** — describe what you ate in plain text, the AI
  figures out the macros, and it's saved as structured numbers you can
  total up later.
- **Meal plan generator** — like the workout generator, but for meals, and
  informed by what you've actually been logging.
- **Money module** — tracking transactions and bills, following the same
  pattern the Health module established.

Dashboard, Career, and Mentorship modules are further out and not yet
scoped.

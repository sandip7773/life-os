# Kickoff prompt — paste this into Claude Code on first run

(Prerequisite: put `CLAUDE.md` in the repo root and commit it. Claude Code reads it automatically.)

---

Read CLAUDE.md fully before doing anything.

You're taking over the Life OS build. The architecture, goals, and current state in CLAUDE.md are accurate and locked in: Day 1 (workout generator) and Day 2a (Telegram /workout bot) are done and committed.

Important: the detailed plan does NOT exist yet. The roadmap in CLAUDE.md is direction only. I want to design the phases and features WITH you in discussion — don't hand me a finished plan or start building.

Start like this:
1. Confirm your understanding of the repo state — list the file tree and skim bot/main.py and modules/health/workout_generator.py.
2. Give me a one-paragraph read-back of the project so I can check you've got it.
3. Then open a planning discussion for the next build step (wiring Supabase into the bot). Ask me targeted questions, propose options with trade-offs, and let me decide — scope, schema, commands, everything. When we've agreed the details, write them into a PLAN.md (or a section of CLAUDE.md — ask me which) so future sessions have them, then we build.

Ways of working, non-negotiable:
- Plan features collaboratively; never invent scope, schemas, table names, or credentials — propose, ask, wait.
- One working, committed output per build session. Small vertical slices.
- Explain code at block/function level (what each part does, so I can fix it later) — no line-by-line walkthroughs. Shell commands one at a time, no chained one-liners without a plain alternative.
- If anything seems over-complicated, push back before building it.
- I handle manual/external steps (Supabase dashboard, keys, BotFather) — give me precise instructions and wait.
- Stay inside the architecture rules in CLAUDE.md (thin orchestrator, shared/ wrappers, two schema shapes, Garmin parked).

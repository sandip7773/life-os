# Life OS — PLAN.md

Session-by-session build plans agreed with Sandi. CLAUDE.md holds the stable
architecture rules and working style; this file holds what we decided to build
and how. Update it at the end of each planning discussion, before code.

---

## Day 2b — Persist workout plans in Supabase  (DONE)

Agreed with Sandi on 2026-07-05.

### Scope (vertical slice)

1. `/workout` keeps working exactly as today, but after generating a plan it
   saves it to Supabase.
2. New command `/lastplan` fetches the most recent saved plan from Supabase
   and sends it back (reusing the existing 4000-char chunking).
3. `shared/db.py` created — the only place the Supabase client is constructed.
4. `shared/llm.py` created and the direct Anthropic SDK call in
   `modules/health/workout_generator.py` moved behind it (pays down the one
   existing violation of the shared/ rule while there is a single call site).

Out of scope: profile editing, plan history browsing, orchestrator, anything
meal-related.

### Schema — `workout_plans` (generated-content shape: blob + metadata)

```sql
create table workout_plans (
  id            uuid primary key default gen_random_uuid(),
  created_at    timestamptz not null default now(),
  plan_markdown text not null,     -- exactly what Claude returned
  profile       jsonb not null,    -- snapshot of the PROFILE dict that produced it
  model         text not null      -- e.g. claude-sonnet-4-6
);

-- Single-user bot using the service_role key (bypasses RLS).
-- RLS on with no policies = anon/public key can't touch the table.
alter table workout_plans enable row level security;
```

Decision note: a generic `generated_content` table was considered and
rejected as premature — meal plans get their own table when they're planned,
and merging later is cheap at this data volume.

### Commit plan

1. `refactor: move Anthropic call behind shared/llm.py` — pure move, no
   behaviour change, verified before the feature work starts.
2. `Day 2b: /workout persists to Supabase, /lastplan retrieves` — shared/db.py,
   save on generate, new command, `supabase` added to requirements.txt.

### Manual steps (Sandi)

- Unpause Supabase project `personal-assistant` (ap-southeast-2).
- Run the SQL above in the Supabase SQL editor.
- Add `SUPABASE_URL` (Project URL) and `SUPABASE_KEY` (service_role key) to `.env`.

### Done when

- `/workout` generates a plan AND a new row appears in `workout_plans`.
- `/lastplan` returns that plan from the database (no API call, instant).
- Both commits pushed; PLAN.md section marked done.

### Status: COMPLETE
- DB round-trip verified with insert/fetch/delete test (all three passed).
- Telegram end-to-end tested: `/workout` → plan + "Saved" confirmation, `/lastplan` → echoes saved plan.
- Prompt optimized for speed (20–21s generation, down from 30–60s); plan output tightened to 1.4k chars, no loss of quality.

---

## Next candidates (direction only — NOT planned, discuss with Sandi first)

- Meal + macro logging (free-text parsed by LLM + quick-pick; structured
  numeric rows — the second schema shape).
- Meal plan generator informed by real logged data.
- Money module (`transactions` + CSV ingestion — paused pending bank format
  confirmation from Sandi).

# AGENT.md — operating manual for Elmer

> Build-agent instructions. `CLAUDE.md` imports this so Claude Code auto-loads it.
> Start here + `README.md` (what it is / how to run & deploy) + `constitution.md`
> (non-negotiable principles). v1 is built and deployed; this describes how it's put
> together and how to extend it safely.

## What this is
A single-user, self-hosted trainer for the **ISED Basic Amateur Radio Qualification,
targeting Basic with Honours (80%)**. App name **`Elmer`**
(stored once as `config.APP_NAME`; never hardcode it). Visual direction: "instrument
panel" — neutral light/dark base, one phosphor accent, mono for numbers/IDs/formulas,
per-section mastery as a segmented S-meter colored by depth tier. All design tokens live
in `app/static/tokens.css`; every SVG tool themes from them.

## Locked stack (don't change without the user)
- **FastAPI (Python) + SQLite + vanilla JS/SVG**, single Docker container. No
  Next/Svelte, no Postgres, no heavy CSS framework.
- **AI = Anthropic API behind `app/coaching/ai_provider.AIProvider`** (`explain` /
  `diagnose` / `narrate` / `condense`). Key from `ANTHROPIC_API_KEY` (env/`.env`,
  never committed). A `StubProvider` is the offline/over-budget fallback — keep it working.

## The deterministic-vs-AI split (the most important rule)
- **Deterministic engine (`app/engine/*`) — no LLM, no randomness in analysis, idempotent.**
  Same `attempts` ⇒ same output. Owns: mastery + fresh-accuracy (`mastery.py`), ability θ /
  difficulty (`adaptive.py`), spaced repetition (`scheduler.py`, Leitner), depth tiers +
  diagnostic placement (`mastery.depth_tier`, `diagnostic.py`), trend / miss analysis
  (`analysis.py`), the journal's day digest (`day_digest.py`), readiness + coverage
  guarantee (`readiness.py`), and the
  `recommendation.json` the dashboard reads (`recommend.py`). Question *selection* may use
  randomness (it's not analysis); scoring/tier/scheduling/readiness may not.
- **AI layer (`app/coaching/*`) — generative only.** Explanations, misconception
  diagnosis, journal narrative, lesson condensation. Nondeterminism is expected here. It
  **never** feeds the mastery/scheduling/readiness math.

## Key decisions in force
- **Readiness = ≥80% fresh-question accuracy in every section AND every subsection probed.**
  Both required before "book the exam."
- **"Fresh" = COLD RECALL, not first-exposure-only.** An attempt is fresh when it's a
  question's first ever OR it lands ≥`config.FRESH_COOLDOWN_DAYS` (default 3, env
  `HAMSTUDY_FRESH_COOLDOWN_DAYS`) after that question's previous attempt; a section scores
  over each question's **most recent** cold attempt. Defined once in `mastery.cold_sql()`
  — mastery, tiers, readiness coverage, trend and drill selection all read through it, so
  they can't drift. Still deterministic: the cooldown compares two timestamps already in
  the log, never the wall clock. (v1 used first-attempt-only, which froze every number
  permanently once the bank had been seen — Honours became unreachable by construction.)
- **Models:** the one-time explanation **batch ran on Opus** (best quality, cache-first DB
  reads forever). **Live calls route off Opus** (user is credit-limited): Sonnet for all
  four call types — narrate moved off Haiku when the journal switched to reasoning over
  the day digest (miss themes, deltas; ~$0.01/entry). Haiku stays available via
  `HAMSTUDY_MODEL_NARRATE`. All in `config.AI_MODELS`, env-overridable per type.
- **Budget guard:** every live call logs tokens+cost to `usage` and checks month-to-date vs
  `AI_MONTHLY_BUDGET_USD` (default $15); over budget ⇒ stub. Batch is a build step and is
  NOT counted against this — gate batch spend with the Console limit instead.
- **Original text only.** Lessons (`app/content/sections/*.md`) and AI output are original;
  reference docs (RIC-3/RBR-4/RIC-1, in the curated corpus) ground accuracy but are never
  reproduced. Cite freely-usable Gov works (RBR-4 §X) only when present in the grounding.
- **Bank:** parsed from the official ISED PDF (two-column aware parser); `bank_version`
  derived from the PDF title page. English-only.

## How to extend
- **Add a concept tool:** drop `app/static/tools/<id>.js` (calls `Elmer.register("<id>", fn)`,
  themes from tokens), register it in `app/tools.py` (`TOOLS` + `SECTION_TOOLS`).
- **Add/adjust an AI call:** add a method on `AIProvider` + `AnthropicProvider` + `StubProvider`;
  externalize the prompt as `prompts/<type>.md` (Console-tunable, loaded by `prompts.py`);
  route the model in `config.AI_MODELS`; it auto-inherits the budget guard + grounding.
- **Bank update (≈yearly):** `fetch_sources` → `ingest` → `validate`, then re-run the
  explanation batch (`explain_batch.submit/collect`) for the new `bank_version` and
  re-export the seed. Trim the RIC grounding / chunk the batch first to control cost +
  rate limits; prefer Opus only if credits allow.
- Always run `python tests/smoke_test.py` (forces the stub — never spends) before committing.
  Also run `python tests/engine_test.py` — self-contained (synthetic bank in a temp DB, no
  `data/` needed) and it pins the engine invariants the smoke test can't see: fresh accuracy
  recovers after the cooldown but never rewards cramming, drills rotate through a section,
  and the coach's focus matches the weakest dashboard row.

## Conventions
- Spec-driven, small committed steps. Append a dated entry to `LOG.md` each session.
- `attempts` is append-only — never delete/mutate. Re-ingest upserts `questions` by `id`.
- Read paths/secrets from `config.py`/env — no hardcoded keys, hostnames, or ports.

## What NOT to do
- Don't put an LLM in the mastery/trend/scheduling/readiness path.
- Don't drop `attempts` or the `explanations` seed (the seed is the portable batch asset —
  losing it means a paid re-batch).
- Don't reproduce community-course prose; don't add multi-user/auth/public hosting; don't
  expand to Advanced Qualification or Morse before the user asks.

## Deploy & ops (recap; full steps in README)
- `deploy/install.sh` = one-shot LXC install (Docker + DB rebuild from seed + start + systemd
  boot unit). `docker-compose.yml` mounts `data/` (durable) and `app/static|templates|content`
  (live UI). `app/db/backup.py` = WAL-safe NAS backup (cron). UI change → `git pull`
  (+`restart` for templates); Python change → `up -d --build`.

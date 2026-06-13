# AGENT.md — Build-agent operating manual

> **Copy or symlink this file to `CLAUDE.md`** so Claude Code auto-loads it as project
> instructions. It is the same content either way — this project is tool-portable.

## What this project is
A single-user, self-hosted training system to get the user (Chris, Alberta) through the
**ISED Basic Amateur Radio Qualification, targeting Basic with Honours (80%)**. Two parts
that share one SQLite store: an **interactive web app** (the learning surface) and a
**coaching layer folded into that app** (deterministic engine + Anthropic API for
explanation/narrative). Full detail: `ham-radio-training-build-spec.md` (read §0 first).

## Read these before doing anything
1. `ham-radio-training-build-spec.md` — the master brief. **§0 records decisions that
   override any conflicting prose later in the file.**
2. `constitution.md` — non-negotiable principles. When unsure, these decide.
3. `BACKLOG.md` — the phased task list. Work phases in order.
4. `QUESTIONS.md` — what's settled and what's still open. Don't re-litigate settled items;
   don't guess on open ones that block you — ask.

## Where to build what
- **Cowork:** Phase 0 research/ground-truthing, and the optional thin deep-dive skill.
- **Claude Code:** the app build, Phases 1–7 (iterative multi-file code, git, run/test).

## Locked technical decisions (do not change without the user)
- Stack: **FastAPI (Python) + SQLite + vanilla JS / SVG client**, single container.
  HTMX allowed for the app shell. No Next/Svelte, no Postgres.
- AI: **Anthropic API** behind an `AIProvider` interface (`explain` / `diagnose` /
  `narrate`). API key from env/secrets — **never commit a key**. Keep a stub/local impl
  swappable behind the same interface.
- Data: SQLite on NAS-backed volume; LAN/VPN-only; back up to NAS.

## Conventions
- **Spec-driven per phase:** short spec → plan → tasks → implement. Small, committed steps.
- **Append to `LOG.md`** every working session: date, what was done, decisions, next step.
- Data model lives in spec §7. `attempts` is **append-only** — never delete or mutate rows.
- The deterministic engine must be **idempotent**: same `attempts` ⇒ same `recommendation`.
  No LLM calls, no randomness in that path. (LLM is only in the AI layer.)
- Lesson text is **original** — never paste community-course prose. Cite/link sources for
  the user instead.
- Always record and surface `bank_version`. Re-ingest by upsert on `id`.

## What NOT to touch / do
- Don't redistribute or republish community course PDFs inside the app.
- Don't put an LLM in the mastery/trend/scheduling/readiness path.
- Don't drop or rewrite `attempts` history on re-ingest or recompute.
- Don't add multi-user/auth/public-hosting complexity — single-user behind the homelab.
- Don't expand scope to Advanced Qualification or Morse before Basic-with-Honours ships.
- Don't hardcode secrets, hostnames, or the Obsidian path — read from config; open
  deployment specifics are in `QUESTIONS.md`.

## Definition of done (v1)
The user can, locally: pick a syllabus section → learn it with an interactive tool → drill
the real bank questions; run a full 100-question mock (70% and 80% lines shown); have missed
questions resurface via spaced repetition; and see a dashboard "today's session" produced by
the deterministic engine, with on-demand Claude explanations and an auto-written journal.
Readiness fires when fresh-question accuracy holds ≥80% across all 8 sections.

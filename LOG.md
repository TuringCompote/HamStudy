# LOG.md — change log

Append a dated entry each working session (newest at the bottom): what changed,
decisions, next step. History before the v1 ship was condensed into the entry below.

---

## v1 — shipped & deployed (2026-06-13)

Elmer is feature-complete and running on the homelab LXC. Built across the planned
phases (all done):

- **Data:** ISED bank ingested (984 questions, two-column parser, `bank_version`
  from the PDF) + SQLite schema; idempotent re-ingest.
- **Quiz:** per-section drill, 100-Q proportional mock (70/80 lines), review queue;
  server-side grading; `attempts` append-only.
- **Learning:** 8 SVG concept tools + original lessons + Learn→Interact→Drill.
- **Spaced repetition:** Leitner scheduler + review queue + formula trainer.
- **Adaptive engine:** diagnostic placement, depth tiers from fresh accuracy,
  Elo/IRT-lite θ-aware selection, coverage guarantee — all deterministic/idempotent.
- **Loop + AI:** `recommendation.json` + dashboard "Today's session"; `AIProvider`
  (+ stub) with budget guard + `usage` table; **984 batch explanations** (Opus,
  one-time ≈ $24, cache-first, adaptive reveal by tier; portable seed in
  `seed/explanations.jsonl`); live **diagnose()** (Sonnet) + AI **journal** (Haiku).
  Live calls route off Opus (credit-limited); Opus reserved for the batch.
- **UI:** instrument-panel dashboard (readiness, stat cards, inline journal week-strip,
  per-section S-meters), mobile-responsive.
- **Deploy:** Dockerfile + compose (port 80, UI mounts, healthcheck), one-shot
  `deploy/install.sh`, systemd boot unit, WAL-safe NAS backup helper.

**Known follow-ons (see README Roadmap):** trend/decay window, tier-scaled lesson
depth + "tuned for you" condensed-lesson cache, optional Cowork deep-dive skill,
Phase 7 Advanced Qualification.

**Operational reminders:** set the Anthropic Console spend limit before heavy live use;
`data/hamstudy.db` is durable state (back it up); push commits to `origin` so the LXC
can `git pull`.

---

## (append new entries below)

## 2026-06-13 — design: trainer cartridges (generalize the engine)

Wrote `specs/trainer-cartridges.md` — a design-only proposal (no code) to turn
Elmer's engine into a **multi-cartridge** trainer. Insight: the deterministic
engine (mastery/θ/Leitner/readiness) only ever consumes `attempts` + scopes, so
the ham bank is just cartridge #1; new domains slot in beside it without touching
the scoring math (constitution §6).

Decided with the user — four new cartridges: **Morse/CW** (Koch audio decode),
**Language/vocab** (spaced-rep + AI mnemonics/roleplay), **Calibration**
(confidence-tagged answers, deterministic Brier scoring), **Inquiry** (ask-the-
right-question, deterministic info-gain over a hidden hypothesis set; AI is only
the oracle).

Schema plan is **additive/migration-safe**: new `cartridges` + generic `items`
tables (ham keeps `questions`), additive columns on `attempts`
(`cartridge/item_id/scope_path/confidence/extra`) preserving append-only, and
`cartridge` added to the `progress` PK. New AI methods `generate` + `roleplay`
(stub-safe, budget-guarded, prompt-externalized). Build sequence: framework →
calibration → morse → vocab → inquiry, each a small committed step with the stub
smoke test green.

Note: AGENT.md says don't add Morse before the user asks — **the user asked today**.

Next step: user to answer §10 open questions (first vocab deck, calibration host,
switcher placement, Morse speed, naming), then build step 1 (framework) behind a
no-behavior-change commit.


## 2026-07-04 — improvement round 1: verified fixes + iPhone baseline

First session with Claude Fable 5. Ran a multi-agent review of the whole codebase
(7 subsystem readers + synthesis), installed the `frontend-design` plugin for the
upcoming visual redesign, then shipped the two cheapest phases of the plan.

**Verified fixes:**
- Formula trainer never mounted — `formula_trainer.html` lacked
  `data-tool="formulatrainer"`, so the page shipped an empty div since v1.
- Budget guard mispriced Sonnet: `usage.py` PRICING had no `claude-sonnet-4-6`
  row, billing every live Sonnet call at Opus rates (~1.7× early stub cutover).
- **Local-day semantics** (new `app/timeutil.py` + `config.TZ`, env
  `HAMSTUDY_TZ`, default `America/Edmonton`): streaks (`coach.day_streak`), the
  Leitner per-day collapse (`scheduler.compute_schedule`), and journal entry
  dates now use the user's local day instead of UTC — an evening session no
  longer splits/writes tomorrow. `attempts` stays UTC; deterministic (fixed zone
  from config). One-time seam: streak/boxes recompute under local days on
  upgrade. Added `tzdata` to requirements.
- `/api/explain` now pins the cached-explanation read to the question row's
  `bank_version` — a reworded question after a bank update can't serve its stale
  explanation (live fallback covers until a re-batch).
- Smoke test hardened: mastery assertions are delta-based (absolute counts broke
  on any DB with real section-5 drills — including prod), and journal/
  recommendation outputs now redirect to temp instead of leaking into `data/`.

**iPhone baseline (daily driver is iPhone Safari over LAN/VPN HTTP):**
- Home-screen app shell: apple-touch metas + generated S-meter icons
  (`app/static/icons/`, pure-stdlib generator) + `/manifest.webmanifest` route
  (APP_NAME from config). No service worker — plain-HTTP LAN is fine without.
- `color-scheme: light dark` (native widgets follow the theme), safe-area
  insets, 44px tap targets under `@media (pointer: coarse)`, hover rules gated
  behind `@media (hover: hover)`, ≥16px form controls (kills iOS zoom-on-focus),
  `:focus-visible` outline.
- Hover-only info made touchable: readiness blockers are a `<details>`
  disclosure; section page shows fresh counts inline.
- **Quiz session resume** (`quiz.js` + sessionStorage): iOS discarding the tab
  mid-quiz no longer loses the run — Resume/Start-over prompt, exam timer
  restored, finished-but-unviewed runs reopen straight to the results screen.
  Answers were always safe server-side; this recovers the in-flight session.

Findings adversarially verified by refuter agents; the review caught the
finished-run resume edge case before commit.

**Deploy note:** this round changes Python (`config`, `timeutil`, `main`,
engine) — deploy with `git pull && docker compose up -d --build`, not the
UI-only pull+restart path (the bind-mounted `base.html` references the new
`/manifest.webmanifest` route). Optionally set `HAMSTUDY_TZ` in `.env`.

Next: journal/day-digest overhaul (needs the Sonnet pricing row above), then
dig-deeper extensions (post-exam miss review, chosen-distractor-first), then the
instrument-panel visual redesign with the frontend-design plugin.

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

## 2026-07-05 — improvement round 2: journal that knows your day + post-exam miss review

**Journal / day-digest overhaul (the "AI summary is crappy" fix).** Root cause from
the review: `narrate()` never saw the day's work — only the forward-looking plan as
raw JSON, "2-3 sentences" hardcoded, on Haiku. Now:
- New deterministic `app/engine/day_digest.py`: everything that happened on a LOCAL
  day — totals, per-mode results, per-section results with start-of-day → now
  fresh-accuracy deltas (via a new `before=` cutoff on `compute_section_mastery`),
  the actual missed questions (stem, chosen vs correct, repeat count), and the
  fast-wrong signal. Pure over `attempts` + config.TZ.
- `narrate(digest=...)` across the provider interface; `prompts/narrate.md` rewritten
  (voice, 80–150 words, miss-theme naming, no invented numbers — all Console-tunable);
  narrate routed to **Sonnet** (~$0.01/entry; Haiku still via `HAMSTUDY_MODEL_NARRATE`).
- Journal body now: narrative → "## Today" facts → "### Missed today" (question texts,
  chose → correct) → per-section table. The stub fallback writes an honest digest
  summary too, so no-key/over-budget entries are still informative.
- **Auto-write:** finishing any quiz fires a background `/api/journal` rewrite —
  the strip stays current without tapping "Write today's". Write button + diagnose
  button now surface real errors (res.ok checks).
- 2 narrate golden cases added to `docs/ai-evals/cases.jsonl`; README updated
  (narrate now needs Sonnet-grade reasoning — grade for miss themes + no fabrication).

**Post-exam miss review (dig-deeper extension).** The mock exam results screen now
lists every miss — stem, your answer vs correct — each with the full Explain flow.
Previously misses only resurfaced days later via the review queue. And explanations
are now personalized: the distractor *you picked* is promoted to the top of "why the
others are wrong", tagged "you picked this →" (matches batch layers keyed by option
text or bare letter).

Verified: smoke test green (now covers digest determinism + journal body); stub
journal, exam miss review, and the you-picked-this marker all exercised in the
isolated preview. Deploy: Python changed ⇒ `git pull && docker compose up -d --build`.

Next: instrument-panel visual redesign (fresh session so the frontend-design plugin
loads), then tools overhaul / data-safety / bank freshness per the round-1 plan.

## 2026-07-05 — instrument-panel visual redesign (specs/visual-redesign.md executed)

Contract-first order from the handoff spec, with the frontend-design plugin loaded:

**Step 1 — constants consolidated.** New `mastery.ui_config()` is the single source
of the tier→CSS map + pass/honours bars. `base.html` injects it on every page as
`window.ElmerConfig` plus `--bar-pass`/`--bar-honours` CSS props; quiz.js (tierCss,
exam-line chips, verdict thresholds), the dashboard tier legend, and the topbar
tagline all read it — the hardcoded copies are deleted. `/api/sections` now applies
`diagnostic.apply_diagnostic_tiers`, so it agrees with the dashboard for low-data
sections.

**Step 2 — tokens.css filled out.** Type scale (`--fs-*`), elevation (`--elev-1/2`,
`--well`), motion (`--dur-*`, `--ease-out`), `--focus-ring`, phosphor glow
(`--glow`, `--glow-strong`), opaque `--surface-raised`, and the propagation-tool sky
colors tokenized (`--sky-day/night`). Inter (named but never loaded) replaced with
self-hosted woff2 (no CDN on the LAN): **Chakra Petch 500/700** (faceplate display
lettering) + **IBM Plex Mono 400/600** (every readout) — `app/static/fonts/`, OFL,
~50 KB total. The documented one-line accent swap (teal→amber) still works, both themes.

**Step 3 — the reskin.** `style.css` rewritten; every DOM/JS contract and smoke-test
marker preserved. Dark = the shack at night (charcoal faceplate, recessed wells,
phosphor glow); light = the bench manual (warm paper, same instruments in print).
S-meters are now bezeled wells with segment slits, glowing tier-colored fills, a
power-up sweep animation (gated behind prefers-reduced-motion), and **calibration
ticks at the pass/honours bars on every meter** — the mission etched into the
instruments. Readiness/stat values read as phosphor displays; buttons are machined
keys; quiz options got keycap letters. Free telemetry wins (engine outputs that
nothing displayed, zero new math): confident-but-wrong **warning lamp** per dashboard
row, and a section-page telemetry strip with **θ**, **fresh vs review accuracy**, and
a fast-wrong alert chip. Theme-color metas + webmanifest updated to mirror the new
`--bg`. Step 4 (moving recommend.refresh off GET /) not needed — no polling added.

Verified in the isolated preview (scratch DB copy, stub AI, devserver.py wrapper):
375×812 dark+light and desktop; drill + Explain (you-picked-this-first intact), exam
results + miss review, session resume, journal strip/entry + auto-write, diagnostic
CTA, propagation/band-plan tools, webfonts loading; smoke test green.

**Deploy note:** Python changed (`main.py`, `mastery.py`) ⇒
`git pull && docker compose up -d --build` (not the UI-only pull+restart path).

## 2026-10-12 — Phase 7: Advanced Qualification (separate track, same engine)

User passed Basic **with Honours**; asked for Advanced "also available, but separate
and tracked separately, same sources, same format, with the AI content generated in
this session (more, deeper)".

**Architecture — qualification profiles, not a flag.** New `app/quals.py`: one `Qual`
per track (`BASIC`, `ADVANCED`) carrying id prefix (B-/A-), section names (8 / 7),
exam size (100 / 50), honours flag, bank PDF/URL, seed file, lessons dir, tool map,
grounding map, and derived paths. The active profile is a **ContextVar**:
`app/main.py` now builds one `APIRouter`, mounts it twice (`/` Basic, `/advanced`
Advanced) behind a 10-line ASGI wrapper that activates the profile per request.
`connect()` opens `quals.current().db_path`; the engine iterates
`quals.current().sections` instead of `range(1, 9)`; recommend/journal/content/
tools/corpus read their paths and maps from the profile. **No engine math changed**
and nothing branches on the qualification. Two SQLite files
(`data/hamstudy.db`, `data/hamstudy_advanced.db`), two journal folders, two
recommendation.json files — `attempts`/`progress`/`diagnostics`/`explanations`
never mix. The AI budget guard sums both stores (one wallet).

**Data.** The ISED Advanced bank is `amateur_advanced_questions_en.pdf` (effective
2025-02-04, 549 questions, 7 sections, 50-question exam). The existing two-column
parser ingested it unchanged once the id regex took the prefix. `ingest`/`validate`/
`init_db`/`explain_batch` take `--qual advanced`; validate pins the Advanced size in
`meta.expected_total`. `fetch_sources` fetches both banks; `install.sh` builds both
DBs; `backup.py` snapshots both.

**Parse verified exact against ISED's own data.** The user supplied ISED's delimited
bank (`amat_adv_quest.zip` → `amat_adv_quest_delim.txt`; correct answer first). All
549 stems, option sets and answer keys matched; the only diff was a parser artifact —
words hyphenated across a PDF line break came out as "left- hand" (32 Advanced /
34 Basic questions). `ingest._join` now re-joins those; both banks re-ingest clean
and the Advanced parse is a character-for-character match. `validate` gained an
exact cross-check against the delimited file whenever it is present
(`fetch_sources` now pulls both zips). Re-ingesting Basic is cosmetic-only (same
`bank_version`, attempts/explanations untouched).

**Explanations — written in-session, no API spend.** 549 structured explanations
(`seed/explanations_advanced.jsonl`, same schema as the Basic seed plus a new
`worked_example` layer; median ~530 words/question vs ~300 for the Opus batch;
every question has a worked numeric/derivation example, 490 carry edge cases). 16
parallel writers from one brief, each chunk machine-validated (coverage, distractor
letters = exactly the wrong options, link whitelist, no regulatory citations) and
re-validated centrally. quiz.js renders `worked_example`; `DEPTH_LAYERS` reveals it
at deep/unrated.

**UI.** Topbar qualification switcher; `<html data-qual>` flips the accent to amber
on Advanced (deep-tier shifts to rust so it stays distinguishable); the 80% bar is
"Honours" on Basic and "target" on Advanced (`ui_config()` → `ElmerConfig`); exam
verdicts/lines follow. Every link/fetch builds on `BASE`/`ElmerConfig.base`; quiz
resume keys include the qualification. Each track serves its own webmanifest so both
can live on the iPhone home screen. 7 original Advanced lessons
(`app/content/sections_advanced/`), an Advanced formula set for the trainer, and the
existing electronics/antenna tools mapped onto Advanced sections 1/2/7.

**Verified:** smoke test extended with an `advanced()` block (isolation: an Advanced
attempt lands only in the Advanced store, a B- id 404s on `/advanced`, 50-Q mock
distribution, journal/recommendation paths, all 7 section pages + lessons);
screenshots of dashboard/section/drill in the preview.

**Deploy:** Python changed ⇒ `git pull && docker compose up -d --build`; on the LXC
`deploy/install.sh` (re-run is safe) builds `hamstudy_advanced.db` from the bank +
seed. Next: Advanced-specific concept tools (filters/Q, modulation envelope, Smith
chart), and a per-track home-screen icon.

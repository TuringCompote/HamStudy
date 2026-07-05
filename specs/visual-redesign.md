# specs/visual-redesign.md — instrument-panel reskin (phase 5 of improvement plan)

> Handoff spec, written 2026-07-05 at the end of improvement rounds 1–2 (see
> `LOG.md`). Start this work in a **fresh Claude Code session** so the
> `frontend-design` plugin (installed at user scope 2026-07-04) is loaded.
> Design intent is unchanged: **instrument panel** — calm neutral base, ONE
> phosphor accent, mono for numbers/IDs, S-meters — but executed at a level
> that feels like real gear, not a sketch of it. The owner granted full visual
> freedom ("knock my socks off") as long as the mission (Basic with Honours)
> and this intent survive.

## What already happened (don't redo)

- iPhone baseline shipped: home-screen metas + generated S-meter icons
  (`app/static/icons/`, generator was a scratchpad script — regenerate by the
  same pure-stdlib PNG approach if the mark changes), `/manifest.webmanifest`
  route, `color-scheme`, safe-area insets, 44px targets under
  `@media (pointer: coarse)`, hover rules gated behind `@media (hover: hover)`,
  quiz session resume, post-exam miss review, journal day-digest.
- The app icon (needle pushing into the amber zone) is the identity seed — the
  reskin should feel related to it.

## Hard constraints

- iPhone Safari over **plain LAN HTTP** (VPN) + desktop browsers. No service
  worker (needs HTTPS). Keep every touch affordance from the baseline above.
- `tokens.css` stays the single theming source; every SVG tool and page themes
  from it (AGENT.md). Light + dark via `prefers-color-scheme`.
- Vanilla CSS/JS only — no framework, no build step (locked stack).
- Deploy model: `app/static` + `app/templates` are bind-mounted (CSS/JS apply on
  `git pull`; templates need `docker compose restart`). If the redesign touches
  Python (it will — see step 1), tell the owner to `up -d --build`.

## The safe order (contract-first — do NOT start by painting)

**Step 1 — consolidate duplicated constants (small Python + JS).**
The same facts live in four places and will drift the moment the UI is reworked:
tier→CSS map + pass/honours bars are duplicated in `quiz.js` (~tierCss() and the
70/80 lines in the results view), `dashboard.html` (legend + cutoff text),
`app/engine/mastery.py` (`TIER_CUTOFFS`, `_TIER_CSS`), and `coach.py`. Emit them
once — either a tiny `/api/config` or Jinja-injected JSON in `base.html` — and
delete the copies. Also: `GET /api/sections` returns tiers **without**
`diagnostic.apply_diagnostic_tiers`, so it disagrees with the dashboard for
low-data sections — fix if the redesign adds any live-JS dashboard behavior.

**Step 2 — fill the token gaps in `tokens.css`.**
- Type scale (style.css hardcodes ~16 rem sizes today), elevation levels,
  `--focus-ring`, motion/duration tokens.
- Two hardcoded colors escape the token system: the propagation tool's sky
  colors (`.prop-sky.is-day` / `.is-night` in style.css).
- `--font-sans` names Inter but nothing loads it (no CDN allowed on LAN —
  either self-host a woff2 in `app/static/` or drop the name).
- Keep the documented one-line accent swap (teal → amber) working.

**Step 3 — the reskin itself (`style.css`, ~380 lines, full rewrite allowed).**
Instrument chrome: bezeled segmented S-meters with tick marks and glow, panel
surfaces, mono readouts. **Free wins — telemetry the engine already computes
that nothing displays** (pure presentation, zero new math):
- per-section ability θ from `adaptive.compute_ability_difficulty`
- fast-wrong counts from `analysis.wrong_classification` — a
  "confident-but-wrong" warning lamp per section
- fresh-vs-review accuracy split (`analysis.fresh_vs_review`)
- the day digest (`app/engine/day_digest.py`) — could drive a "today" panel.

**Step 4 — only if the redesign adds polling/live updates:** move
`recommend.refresh` off `GET /` (it rewrites `recommendation.json` + maybe a
history row on every dashboard view; `app/main.py` dashboard route) to
attempt-write time or a TTL.

## Contracts that must not break (redesign around these)

- **quiz.html DOM ids** quiz.js binds at load: `#quiz` (+`data-mode/section/
  confidence`), `#loading`, `#card`, `#stem`, `#options`, `#feedback`, `#next`,
  `#results`, `#progress`, `#timer`. quiz.js also *generates* markup using
  classes: `.option`, `.letter`, `.feedback`, `.explain-btn`, `.explain-out`,
  `.exp-layer/.exp-label/.exp-list/.exp-extra`, `.miss-review/.miss-item/
  .miss-stem/.miss-answers/.miss-yours/.miss-right`, `.results`, `.score`,
  `.verdict`, `.exam-lines`, `.card-actions`. Restyle via CSS freely; rename
  only in lockstep with quiz.js.
- **journal strip ids** journal.js binds: `#jr-write`, `#jr-prev`, `#jr-next`,
  `#jr-days`, `#jr-range`, `#jr-entry` (+ generated `.jr-day/.jr-wd/.jr-dn/
  .jr-close/.jr-body`, classes `lit`/`today`/`on`).
- **tier CSS class names** (`tier-testout/light/standard/deep`, `tier-text-*`)
  are consumed by both Jinja templates and quiz.js's `tierCss()` until step 1
  consolidates them.
- **/api/explain response shape** (batch: `source/tier/default_layers/layers`;
  live: `text/degraded`) and the adaptive-reveal behavior — the owner's
  favorite feature; extend, never regress.
- Section-page tool mount contract: `<div data-tool="<id>">` + `Elmer.register`
  (`app/static/tools/registry.js`); `formula_trainer.html` mounts
  `formulatrainer` the same way.
- `attempts` append-only; no LLM in engine paths; smoke test
  (`python tests/smoke_test.py`) must stay green — it asserts dashboard markers
  `readiness-val`, `stat-cards`, `session-card`, `Per-section mastery`,
  `tier-text-deep`, `app-badge` exist in `GET /` — update those assertions
  deliberately if the markup renames.

## Verification workflow (hard-won — see memory + LOG 2026-07-04)

- Never point a dev server at real `data/`. Copy `data/hamstudy.db` into the
  session scratchpad and launch uvicorn through a wrapper that sets
  `HAMSTUDY_DB` / `HAMSTUDY_RECOMMENDATION` / `HAMSTUDY_JOURNAL` /
  `HAMSTUDY_AI_PROVIDER=stub` **inside Python before importing the app**, then
  asserts `config.DB_PATH` actually points at the copy. (Shell-level
  `cmd set X && uvicorn` silently fails to apply env vars — that's how one test
  click once leaked into the local dev DB.)
- Check at 375×812 with dark **and** light schemes, plus desktop. The owner
  uses the app daily on an iPhone.
- Owner's Anthropic credits are limited: prefer inline work + one focused
  review pass over large agent fan-outs.

## Explicitly out of scope for this phase

Tools overhaul (drill harness — separate phase; `specs/trainer-cartridges.md`
is about *new domains*, not this), schema/migration work, bank freshness,
Advanced Qualification, multi-user anything.

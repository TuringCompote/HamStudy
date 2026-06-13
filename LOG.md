# LOG.md — Build progress log

Append-only. Newest entries at the bottom. Each session: date, what was done,
decisions, next step.

---

## 2026-06-13 — Phase 0 finish + Phase 1 (data foundation)

**Done**
- Scaffolded the project: `app/`, `app/db/`, `data/` (git-ignored), `references/`
  (git-ignored), `.gitignore`, `requirements.txt`.
- Downloaded the official ISED Basic question bank PDF into
  `references/amateur_basic_questions_en.pdf` (322 KB, valid PDF) from the
  authoritative `apc-cap.ic.gc.ca` data-file URL (the dated `documents/...` URLs
  in PHASE0 404'd; the lowercase `.pdf` data file is live, per PHASE0's note).
- Stood up the SQLite schema (spec §7) — `app/db/schema.sql` +
  `app/db/init_db.py`. Tables: `questions`, `attempts` (append-only),
  `progress`, `diagnostics`, `usage`, `recommendation`, `journal`, plus a
  `meta` k/v table. `init_db` is idempotent (`CREATE ... IF NOT EXISTS`).
- Built the ingest parser (`app/db/ingest.py`). The bank is a **two-column**
  layout; naive `extract_text()` interleaves columns. Solution: reconstruct each
  page column-by-column, splitting at the empty gutter (x≈257), grouping words
  into lines by `top`. Parsed **984/984 questions, 0 bad, 0 duplicates**, all
  mapping to sections 1–8.
- Wrote `app/db/validate.py`: asserts count==984, id format, section 1–8, 4
  options each, correct_index 0–3, no dupes/empties; reports per-section + answer
  distribution. **All checks pass.**
- Verified idempotent re-ingest: re-running keeps `questions` at 984 and
  **preserves `attempts`** (inserted a probe attempt, re-ran ingest, probe
  survived) — constitution §6 satisfied. Upsert preserves `notes` / `difficulty_b`.

**Decisions**
- **`bank_version = 2025-08-26`, not 2025-07-15.** The live authoritative file's
  title page reads "26 August, 2025", and the foreword states questions are
  "effective the date printed on the title page." Same 984-question count, so
  it's an ISED re-issue of the same pool with a newer effective date. Ingest
  **derives `bank_version` from the PDF title page** rather than hardcoding, so
  this self-corrects on future re-issues. (Flagged to Chris.)
- Parser handles two ID/answer orderings: normal `B-AAA-BBB-CCC (X)` and the
  ~37 cases where x-sorting puts the answer first, `(X) B-AAA-BBB-CCC`. Both
  carry that id's correct answer.
- Wrote our own parser (studied `canadian-ham-exam`'s approach as reference per
  PHASE0) — the column-split + trailing-A/B/C/D-marker logic is specific to this
  PDF and worth owning.
- Per-section counts (this bank): S1=199, S2=99, S3=199, S4=63, S5=142, S6=140,
  S7=87, S8=55.
- Downloaded PDFs/ZIPs are git-ignored (constitution §2/§3 — don't redistribute
  source binaries); the parsed SQLite is the app's data. Re-download is scripted
  in `app/db/fetch_sources.py`.

**Reference material (resolved same session)**
- Found the working URLs (the PHASE0 `documents/...` paths were missing the
  `sites/default/files/` segment). Downloaded into `references/` (git-ignored):
  - **Reference Material ZIP** → auto-extracted to `_extracted/`: the **"Exam"**
    PDF (5 pp, *unlabelled* — exam-legal sheet to train with) and the **"Training"**
    PDF (7 pp, *labelled* study aid). For Phase 4 formula trainer.
  - **RBR-4** (Standards for Operation) → PDF.
  - **RIC-3** and **RIC-1** → HTML-only on ISED (no PDF published), saved as
    faithful server-rendered HTML; clean text extraction deferred to Phase 5 when
    the AI reference layer consumes them.
- `app/db/fetch_sources.py` now re-downloads all five sources reproducibly
  (verified end-to-end; ZIP auto-extracts). `.gitignore` excludes `*.html` too.
- Note: a 2025-07-15-dated bank copy also exists on ised-isde, while the apc-cap
  data file is the 2025-08-26 re-issue — same 984 pool. We use apc-cap (newer).

---

## 2026-06-13 — Phase 2 (quiz engine MVP)

**Done**
- FastAPI app (`app/main.py`): server-rendered dashboard + quiz-runner shell
  (Jinja), with a small JSON API the vanilla-JS runner drives.
- **Data access** (`app/db/queries.py`): question fetch (answer-stripped for
  quizzes), server-side grading + append to `attempts`, section stats, the 8
  section names (original labels, not lesson content).
- **Deterministic mastery** (`app/engine/mastery.py`): per-section mastery % +
  coverage %, overall summary, Honours/pass bars (80/70). Pure arithmetic over
  `attempts` — idempotent (constitution §5).
- **Quiz construction** (`app/quiz.py`): per-section drill (random N) + 100-Q
  mock exam — section-proportional via largest-remainder, spread across
  subsections (round-robin over shuffled buckets). Randomness lives here, NOT in
  the analysis path.
- **Client** (`app/static/quiz.js` + `style.css`, templates): drill gives
  per-question feedback; exam defers to a results screen with the **70% pass and
  80% Honours lines** + per-section breakdown + timer.
- **Smoke test** (`tests/smoke_test.py`) against a throwaway DB copy: health,
  no-answer-leak in drill+exam payloads, 100-Q proportional distribution,
  server-side grading correctness, `attempts` rows written, deterministic mastery
  (1/2 ⇒ 50%), pages render. **All pass.** Verified a real uvicorn boot too.

**Decisions**
- **Correct answers never ship in the quiz payload** — `/api/quiz` strips
  `correct_index`; `/api/attempt` grades server-side and returns correctness.
  Keeps the `attempts` log the sole source of truth and avoids trivially leaking
  the key to the page.
- Mock exam proportionality is at the **section** level for the MVP (matches the
  bank distribution exactly: 20/10/20/6/15/14/9/6). Finer per-subsection
  proportionality + adaptive (θ-aware) selection are deferred to Phase 4.5.
- Mastery v1 = correct/answered all-time per section. Trend, fresh-vs-review, and
  the §6d.4 coverage guarantee come in Phases 4.5/5; the dashboard's "all
  sections Honours" flag is a coarse placeholder, not the terminal readiness
  signal.
- Default drill size 20; mock 100.

**Open / next step**
- **Next: Phase 3** — interactive learning layer (Ohm's law, reactance/resonance,
  dB, SWR/impedance, wavelength↔frequency), original per-section lesson text, and
  the Learn → Interact → Drill flow.

---

## 2026-06-13 — Alignment to updated docs (Elmer + instrument-panel design)

**Context:** planning docs gained spec §0.2b + QUESTIONS #16/#17 — **app name
`Elmer`** and an **"instrument panel"** visual direction. Phase 2 code predated
these, so this is a cleanup pass before Phase 3 builds the SVG tools.

**Done**
- `APP_NAME = "Elmer"` in `config.py` (env-overridable, one-line changeable);
  registered as a Jinja global. Removed all hardcoded "HamStudy" from templates +
  FastAPI title (verified: 0 occurrences served, brand/title now "Elmer").
- `app/static/tokens.css` — single source of design tokens: neutral base with
  **light + dark** (via `prefers-color-scheme`), **one phosphor accent** (teal;
  amber alt documented as a one-line swap), `--font-mono` for numbers/IDs/formula
  values + `--font-sans` body, spacing/radius/border tokens. The Phase-3 SVG tools
  will theme from these.
- Refactored `style.css` to consume tokens throughout; mastery now renders as a
  **segmented S-meter** (`.smeter`) colored by band via `mastery_band()` in the
  engine (`tier-ok/warn/low`) — a placeholder wired to switch to depth-tier color
  once Phase 4.5 computes `tier`.
- Smoke test still green; verified real uvicorn boot + S-meter markup with data.

**Decisions**
- Accent defaults to **teal**; final teal-vs-amber call deferred (open item in
  QUESTIONS) — swappable in one line in `tokens.css`.
- S-meter color is mastery-band for now; the hook (`band` field) is in place so
  Phase 4.5 can recolor by adaptive depth tier without template changes.

**Next:** Phase 3 — concept tools (Ohm/reactance/dB/SWR/wavelength) as SVG+JS
theming from `tokens.css`, original lesson text, Learn → Interact → Drill.

---

## 2026-06-13 — Phase 3 (interactive learning layer — P0 set)

**Done**
- **Learn → Interact → Drill** section flow: `GET /section/{n}` + `section.html`.
  Each page = original lesson (Learn) → the section's concept tools (Interact) →
  a drill button (Drill). Dashboard section names now link to `/section/{n}`.
- **Original lesson text for all 8 sections** (`app/content/sections/section{1..8}.md`,
  rendered by `app/content` via python-markdown). Written fresh, pitched for an
  experienced electronics learner (constitution §3 — no copied course prose).
- **Client tool framework** (`static/tools/registry.js`): tools self-register and
  mount into `<div data-tool="id">`; shared SVG/format helpers; errors are caught
  so one broken tool can't blank the page.
- **Five P0 concept tools** (SVG + vanilla JS, themed from `tokens.css`):
  - `ohms.js` — any two of V/I/R/P → other two + the formula used + a live circuit.
  - `reactance.js` — L/C/f controls; X_L & X_C with a log-log plot crossing at f₀.
  - `decibel.js` — ratio ↔ dB, power(10·log)/voltage(20·log) toggle, S-unit context.
  - `swr.js` — load R+jX & Z₀ → Γ, SWR, reflected %, return loss + delivered/reflected bar.
  - `wavelength.js` — f ↔ λ, ½λ dipole & ¼λ vertical with velocity factor.
- **Tool→section map** (`app/tools.py`): §5 = ohms/reactance/decibel, §6 = swr/wavelength.
- Smoke test extended: all 8 section pages 200, `/section/9` → 404, lesson exists
  for every section, all tool assets + tokens.css serve. **All pass.** JS passes
  `node --check`; tool formulas verified by hand.

**Decisions**
- Lesson content as markdown files (not DB) — easy to edit, version, keep original.
- Tools are pure client-side (no answers/PII leave the browser); they're generic
  widgets that will theme automatically if the accent flips teal↔amber.
- **Not yet done:** the 3 non-P0 tools (series/parallel R&C, band-plan explorer,
  propagation visual) remain in BACKLOG. Headless JS execution wasn't run — the
  interactive behavior should get a quick browser eyeball.

**Next:** remaining Phase 3 non-P0 tools, or proceed to Phase 4 (spaced repetition
+ review queue). Recommend a quick browser check of the tools first.

---

## 2026-06-13 — Series/Parallel tool + dashboard rebuild + AI-content design

**Done**
- **Series/Parallel R&C tool** (`static/tools/seriesparallel.js`, §4): add/remove
  components, series/parallel toggle, live equivalent + schematic. (Committed earlier.)
- **Dashboard rebuilt to match Chris's mockup** (`example dashboard.png`):
  - Header: app badge + **Elmer** + "Basic with honours · target 80%" + **Exam
    readiness** %.
  - Four stat cards: Sections ready (x/8), Day streak, Bank mastered, of 984 %.
  - **"Today's session"** card (provisional deterministic suggestion).
  - Per-section rows: **segmented S-meter colored by depth tier** + % + tier label,
    with a tier legend (test-out / light / standard / deep).
  - New deterministic engine module `app/engine/coach.py`: `dashboard_summary`,
    `day_streak` (attempt-date-derived, no wall-clock), `mastered_count` (distinct
    questions whose latest attempt is correct), `suggest_session`. Tier proxy
    `provisional_tier` + `tier_css` in `mastery.py`. Tier color tokens in `tokens.css`.
  - Short section names for the rows. Section page S-meter now tier-colored too.
- Smoke test extended (dashboard markup + coach aggregates). Empty-DB state renders
  cleanly (0/8, streak 0, "run a drill" prompt). All green.
- **Recorded the AI-content vision in the docs** (Chris's decisions #18/#19):
  - spec **§6d.6** (AI-adapted content from a curated local corpus + RAG; engine
    diagnoses, AI writes original text; generate-on-demand + cache; base lessons as
    fallback) and **§7** `content_cache` table.
  - QUESTIONS #18/#19; BACKLOG Phase 4.5 tasks (corpus/RAG, AI-adapted content,
    content_cache).

**Decisions**
- **Tier coloring is a PROVISIONAL mastery-threshold proxy** (≥80 test-out / ≥70
  light / ≥55 standard / else deep) chosen to match the mockup. Phase 4.5 swaps it
  for the real adaptive tier (diagnostic + performance + trend) — no template change
  needed (templates read `tier`/`tier_css`).
- **"Today's session" is a deterministic placeholder**; Phase 5 replaces it with the
  full engine `recommendation.json` + AI phrasing.
- **AI source = curated LOCAL corpus, not live scraping** (reliable, cheap, local,
  copyright-safe). Original-text-only rule preserved.

**Phase 3 completed (same session)**
- Built the last two tools: **band-plan explorer** (`bandplan.js`, §1 — qualification
  toggle showing which Canadian bands Basic vs Basic-with-Honours unlocks; the
  >30 MHz rule, ranges, primary/secondary) and **propagation visual**
  (`propagation.js`, §7 — day/night + frequency slider; sky-wave ray refracts below
  the MUF, penetrates above, D-layer absorbs low HF by day). Wired §1 and §7.
- **All 8 concept tools** now built; smoke test covers all 9 tool scripts. node --check
  clean. Band-plan freq edges noted as "verify against RBR-4."

**Open / next step**
- Browser eyeball of the dashboard + tools still recommended (no headless JS run here).
- **Phase 3 is done** (8 tools + original lessons + Learn→Interact→Drill). Next: Phase 4
  (deterministic spaced-repetition scheduler + review queue + formula-sheet trainer).

---

## 2026-06-13 — Phase 4 P0 (spaced repetition + review queue)

**Done**
- **Deterministic scheduler** (`app/engine/scheduler.py`): Leitner boxes computed
  purely from `attempts`, collapsed to one review outcome per calendar day (so
  same-session repeats can't inflate a box). correct ⇒ promote (cap box 6), wrong
  ⇒ reset to box 1; box→interval {1:0,2:1,3:3,4:7,5:16,6:35} days; `due_date =
  last_review + interval`. `due_reviews()` (most-overdue/weakest first) and
  `review_due_count()`. "Today" only filters due-ness; box/interval/due are pure
  over the log (constitution §5). Verified: promotion cap, lapse reset, same-day
  collapse, due ordering, determinism.
- **Review mode**: `quiz.build_review()` serves due questions (answer-stripped);
  `/api/quiz` + `/quiz?mode=review`; recorded with `mode=review`; immediate
  per-question feedback (like drill). Empty queue → friendly 404.
- **Dashboard**: real `review_due` count; "Review N due" button in the session
  card; `suggest_session` now cites the real review count.
- Smoke test extended (scheduler determinism, review-due ≥1, review payload has no
  answers, review page renders). All green. The user's dry-run attempts are now in
  the real DB (review showed 11 due from real usage).

**Decisions**
- **Leitner over SM-2** for v1: fully deterministic, no ease-factor tuning, maps
  cleanly to "missed → resurfaces soon." Can swap to SM-2-lite later if desired.
- One-outcome-per-day collapse prevents drill-spam from over-promoting a question.

**Next:** formula-sheet trainer (non-P0, using the unlabelled exam sheet), then
Phase 4.5 (adaptive engine) / Phase 5 (close the loop + AI layer).

**Formula-sheet trainer (same session — Phase 4 complete)**
- `/formula-trainer` + `static/tools/formulatrainer.js`: flashcards over an
  **original curated formula set** (`app/formulas.py`, 21 staples) — two directions
  ("find → formula" / "formula → find"), self-rated, missed cards requeue. Trains
  recognizing the **unlabelled** exam sheet's formulas without reproducing the PDF
  (constitution §3). Linked from the dashboard (+ mock exam + review buttons).
- Smoke test covers the trainer page/asset/data. All green. **Phase 4 done.**

**Git note:** Phase 4 commits are LOCAL — `git push` was denied this session, so
`origin` is behind by the scheduler/review commit + the formula-trainer commit.
Push when ready.

**Next:** Phase 4.5 (adaptive engine: diagnostic placement, real depth tiers,
Elo/IRT-lite θ-aware selection, coverage guarantee) or Phase 5 (close the loop +
Anthropic AI layer + the §6d.6 corpus/RAG content).

---

## 2026-06-13 — Phase 4.5 (adaptive engine — deterministic core)

Built in three committed increments (all deterministic; AI deferred to Phase 5):

**1/3 — Fresh accuracy, real tiers, coverage, readiness**
- Depth tier now from **fresh-question accuracy** (each question's first attempt),
  not all-time — the exam-relevant signal. Per-section fresh_answered/correct/pct.
- `app/engine/readiness.py`: `coverage()` (subsections probed by fresh Qs) +
  `readiness()` → `exam_ready` only when all 8 sections ≥80% fresh AND every
  subsection probed, with plain-language blockers (§6d.4 / constitution §8).
- Dashboard now shows fresh % per section + overall, a "Book the exam" flag, and
  "not ready yet" with blocker tooltip.

**2/3 — Elo/IRT-lite + θ-aware drills**
- `app/engine/adaptive.py`: replay attempts → per-section ability θ + per-question
  difficulty b (fixed K + init ⇒ deterministic; they co-calibrate). `select_drill`
  serves the ~75% productive zone, pulling forward under-probed subsections + unseen
  questions; random only at cold start. `build_drill` routes through it.

**3/3 — Diagnostic placement**
- `app/engine/diagnostic.py` + `/quiz?mode=diagnostic` + `/api/diagnostic` +
  section-page CTA (with cold/rusty/new confidence prior). 8-Q probe across
  subsections, scored → starting tier, recorded in the `diagnostics` table.
  `apply_diagnostic_tiers` seeds a section's tier from the probe until it has
  ≥6 fresh attempts, after which measured performance overrides (§6d.1).
- Added `PRAGMA busy_timeout=5000` to DB connections (WAL robustness).

**Verified:** θ rises with success / wrong questions get higher difficulty;
scheduler + adaptive + readiness all deterministic; diagnostic scoring + tier
seeding (thin-data → diagnostic source, ≥6 fresh → measured). Smoke test extended
to cover readiness, adaptive determinism, and the full diagnostic flow. All green.

**Decisions**
- Tier cutoffs kept at the mockup's 80/70/55 (test-out/light/standard, else deep),
  centralized in `TIER_CUTOFFS`; computed from fresh accuracy now. Spec §6d.2's
  90/75/50 is a one-line alternative if preferred.
- Tier is computed on demand (+ diagnostic-seeded), not persisted to `progress` —
  keeps it idempotent over the log; persistence is a pure optimization if needed.

**Git:** Phase 4.5 commits are LOCAL (push still denied to the agent this session).
Pending push: the 3 Phase-4.5 increments (+ earlier Phase-4 commits if not yet
pushed). 

**Next:** Phase 5 — close the loop (recommendation.json), the `AIProvider` +
Anthropic layer, budget guard, journal, and the §6d.6 curated-corpus content
adaptation; plus the deferred trend/decay + tier-scaled lesson depth/spacing.

---

## 2026-06-13 — Phase 5 (1/3 + 2/3): loop + AI layer + budget guard

**1/3 — deterministic loop close** (committed): `analysis.py` (trend, fresh-vs-
review, most-missed, fast/slow-wrong), `recommend.py` (`recommendation.json` +
history table, dedup by content hash), dashboard reads it; `AIProvider` interface
+ `StubProvider`.

**2/3 — Anthropic AI layer + budget guard** (this step):
- `app/coaching/anthropic_provider.py`: real Claude impl behind `AIProvider`
  (explain/diagnose/narrate/condense). Key from `ANTHROPIC_API_KEY` (.env,
  gitignored) — never hardcoded. **Graceful fallback to the stub** on no-key,
  over-budget, or any API error (the loop never breaks). Opus 4.8 surface
  (no temperature/budget_tokens); grounding passed as a `cache_control` system
  block (corpus wiring lands in 3/3).
- `app/coaching/usage.py`: `usage` table logging (tokens + est cost) + monthly
  budget guard. Pricing per claude-api ref: Opus $5/$25, Haiku $1/$5 per MTok;
  cache read 0.1×, write 1.25×. `within_budget()` checks month-to-date vs the
  configurable ceiling (default $15, `HAMSTUDY_AI_BUDGET`).
- `/api/explain` (on-demand miss explanation + "Explain ▾" button in drill/review),
  `/api/journal` (AI-narrated `data/journal/YYYY-MM-DD.md` + index), `/api/ai-status`.
  `app/coaching/journal.py`.
- config loads `.env`; `AI_PROVIDER` auto = anthropic when a key is present, else
  stub; `AI_MODEL` / `AI_MODEL_CHEAP` configurable.
- Smoke test exercises the AI layer **stub-forced (no spend)**: explain/journal
  degrade cleanly, cost math ($5+$25=$30/MTok), budget guard, ai-status. All green.

**Not yet verified:** a real (paid) Anthropic call — held pending your OK (spends
a fraction of a cent). **Remaining for 3/3:** per-call-type model routing
(Opus explain/diagnose, optional Haiku narrate), externalized prompt files, RIC
prompt-cache corpus, evals/. (Status + plan posted; awaiting OK.)

**How to run**
```
pip install -r requirements.txt
python -m app.db.ingest      # downloads must already be in references/
python -m app.db.validate
```

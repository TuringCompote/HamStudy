# Design: Trainer Cartridges — generalizing Elmer's engine

> Status: **proposed** (design only — no code yet). Author pass: 2026-06-13.
> Read alongside `AGENT.md` (operating manual), `constitution.md` (non-negotiables),
> and `app/db/schema.sql` (the contract this builds on).

## 1. The core idea

Elmer looks like a ham-radio app, but the valuable part is **domain-agnostic**: a
deterministic training engine (mastery, ability θ, Leitner spaced repetition,
readiness, trend/miss analysis) sitting on top of an append-only `attempts` log,
with a generative AI layer bolted on the side. The ISED question bank is just the
**first cartridge** loaded into that engine.

This doc proposes making that explicit: a small **cartridge** abstraction so new
trainers slot in beside the ham bank **without touching the scoring math**
(constitution §6 / AGENT.md "the most important rule"). It then specs four
cartridges chosen with the user:

1. **Morse / CW** — Koch-method audio decoding trainer.
2. **Language / vocab** — spaced-rep vocabulary with AI mnemonics + roleplay.
3. **Calibration** — confidence-tagged answers, Brier-scored over time.
4. **Inquiry** — ask-the-right-question trainer scored on information gain.

### Design tenets (inherited, non-negotiable)
- **Deterministic engine stays deterministic and idempotent.** Same `attempts` ⇒
  same mastery/θ/schedule/readiness. New cartridges feed it events; they never put
  an LLM in that path (constitution §6, AGENT.md §"deterministic-vs-AI split").
- **AI is generative only** — item generation, explanation, roleplay, narrative.
  It never feeds the scoring math.
- **`attempts` is append-only.** Every cartridge emits attempts in one shared shape.
- **Locked stack** — FastAPI + SQLite + vanilla JS/SVG, one container. No new
  frameworks. Audio = Web Audio API in vanilla JS (no libraries).
- **Budget-guarded AI**, original content only, secrets from env (unchanged).

## 2. What "cartridge" means

A cartridge is the minimal description of a training domain. Today the ham bank is
hardcoded as section 1–8 multiple-choice. We generalize to:

```
Cartridge:
  id            "ham" | "morse" | "vocab" | "calib" | "inquiry"
  name          display name (themeable; never hardcoded in UI)
  item_kind     how an item is presented/answered (see §4)
  scopes        the grouping hierarchy for mastery (ham: section>subsection>question;
                morse: charset-stage>character; vocab: deck>word; etc.)
  selection     how the next item is chosen (may use randomness — selection is not analysis)
  scoring       maps a raw response -> a graded attempt (correct 0/1 + optional extras)
  readiness     domain definition of "ready" (ham: ≥80% fresh in every section/subsection)
  ai_hooks      which AIProvider methods apply (explain / generate / roleplay / narrate)
```

The deterministic engine only ever sees **attempts** and **scopes**. It does not
know or care whether an item was a multiple-choice question, a Morse character, or
a vocabulary word. That's the whole trick.

## 3. Schema changes (additive, migration-safe)

The current schema hardwires the ham domain: `questions` has `section`/`subsection`,
`attempts.mode` is a fixed enum, `progress.scope_id` is ham-shaped. We extend
**additively** — existing rows keep working; the ham cartridge is backfilled to
`cartridge='ham'`.

### 3.1 New table: `cartridges`
```sql
CREATE TABLE IF NOT EXISTS cartridges (
    id            TEXT PRIMARY KEY,        -- 'ham','morse','vocab','calib','inquiry'
    name          TEXT NOT NULL,
    item_kind     TEXT NOT NULL,           -- 'mcq'|'audio_decode'|'recall'|'calibrated_mcq'|'inquiry'
    config        TEXT NOT NULL,           -- JSON: scopes, readiness rule, selection params
    content_version TEXT NOT NULL,         -- analog of bank_version (per-cartridge)
    created_at    TEXT NOT NULL
);
```

### 3.2 New generic item table: `items`
The ham `questions` table stays as-is (don't disturb a working ingest + the seeded
explanations keyed on `question_id`). New cartridges write to a generic `items`
table instead:
```sql
CREATE TABLE IF NOT EXISTS items (
    id            TEXT PRIMARY KEY,        -- '<cartridge>:<localid>' e.g. 'vocab:fr-0421'
    cartridge     TEXT NOT NULL REFERENCES cartridges(id),
    scope_path    TEXT NOT NULL,           -- '/' delimited, e.g. 'deck-fr-a1/animals' or 'stage-2/K'
    payload       TEXT NOT NULL,           -- JSON: item_kind-specific (prompt, audio spec, options, answer)
    difficulty_b  REAL,                    -- IRT-lite difficulty; NULL until calibrated
    content_version TEXT NOT NULL,
    generated_by  TEXT                     -- NULL=authored | model id if AI-generated
);
CREATE INDEX IF NOT EXISTS idx_items_cart ON items(cartridge, scope_path);
```
Ham reads from `questions`; everything else from `items`. A thin `bank.py` adapter
presents both behind one `get_item(id)` / `iter_items(cartridge, scope)` interface
so the engine never branches on cartridge.

### 3.3 Extend `attempts` (the one invariant table) — additively
```sql
ALTER TABLE attempts ADD COLUMN cartridge   TEXT NOT NULL DEFAULT 'ham';
ALTER TABLE attempts ADD COLUMN item_id     TEXT;          -- generic; question_id kept for ham
ALTER TABLE attempts ADD COLUMN scope_path  TEXT;          -- generic; section/subsection kept for ham
ALTER TABLE attempts ADD COLUMN confidence  REAL;          -- calibration cartridge (0..1), else NULL
ALTER TABLE attempts ADD COLUMN extra       TEXT;          -- JSON: per-cartridge signals (info_gain, wpm, latency_curve)
```
`mode`'s CHECK constraint is widened (drop+recreate via table rebuild in a
migration) to add `'session'` for free-form cartridges. Existing ham rows are
untouched and remain valid. **Append-only rule still holds** — we only add columns.

### 3.4 `progress` already generalizes
`progress(scope_type, scope_id, …)` is keyed by scope string and is *recomputed
from attempts* — it's safe to rebuild and already domain-neutral. We add
`cartridge` to the PK so two cartridges can't collide on a scope id:
```sql
-- new PK: (cartridge, scope_type, scope_id)
```

### 3.5 `usage` and `explanations` call-type widening
`usage.call_type` and the AI layer learn two new types: `generate` (item/content
generation) and `roleplay` (turn-based tutor). Budget guard applies unchanged.

**Migration:** one `app/db/migrate_002_cartridges.py`, idempotent, run by
`init_db` and `deploy/install.sh`. Backfills `cartridge='ham'`, inserts the `ham`
row into `cartridges`. `validate.py` gains per-cartridge assertions.

## 4. Item kinds (the UI/answer contract)

Each cartridge declares an `item_kind`. The engine doesn't read these; the
**front-end + scoring** do. All run in vanilla JS, themed from `tokens.css`.

| item_kind        | presented as                          | answered by                | graded extras            |
|------------------|----------------------------------------|----------------------------|--------------------------|
| `mcq` (ham)      | stem + 4 options                       | pick index                 | response_ms              |
| `audio_decode`   | Web Audio tones (CW)                   | type the decoded text      | wpm, per-char latency    |
| `recall`         | prompt (word/definition/cloze)         | type / self-grade / pick   | response_ms              |
| `calibrated_mcq` | any item + a confidence slider         | answer **and** set 0–100%  | confidence → Brier       |
| `inquiry`        | scenario; you ask questions, then solve| free-text Q&A then commit  | info_gain per question   |

New item kinds = new client modules under `app/static/trainers/<kind>.js`
registering with the existing `Elmer.register(...)` pattern (same as the concept
tools in `app/static/tools/`). The scoring half lives server-side in
`app/engine/scoring/<kind>.py` and returns a normalized attempt.

## 5. Routing & navigation

Generalize the ham-specific routes without breaking them:
- Keep `/section/{n}`, `/quiz/...` working (they become the `ham` cartridge views).
- Add `/train/{cartridge}` (lobby), `/train/{cartridge}/drill`, and a JSON API
  `POST /api/{cartridge}/attempt` that all cartridges share.
- Dashboard gains a **cartridge switcher**; each cartridge renders its own
  readiness/S-meter strip from `progress`. The instrument-panel aesthetic and
  `tokens.css` are reused verbatim — a new cartridge ships zero new CSS ideally.

## 6. The four cartridges

### 6.1 Morse / CW (`morse`, item_kind `audio_decode`)
- **Scopes:** Koch stages (`stage-1`…`stage-N`) → individual characters. Koch
  introduces 2 characters at full target speed, adds the next only when accuracy
  on the current set clears a threshold — which is exactly a **mastery gate** the
  engine already expresses (tier/`mastery_pct`). Mapping: a character is "mastered"
  at ≥90% fresh copy accuracy; stage unlocks next character via readiness rule.
- **Audio:** Web Audio API oscillator at a configurable tone (600–700 Hz),
  **Farnsworth timing** — character speed fixed high (e.g. 18 wpm) while inter-
  character spacing stretches and tightens as θ rises. All client-side; no audio
  files shipped.
- **Items:** an item is a target string to send. Authored stages for the standard
  Koch order; AI (`generate`) optionally produces themed practice "messages" /
  mock QSOs to decode once the alphabet is unlocked.
- **Attempt:** `correct` = exact (or Levenshtein-threshold) match; `extra` =
  `{wpm, per_char_errors}` so `analysis.py` can surface "you keep missing B/V."
- **Readiness:** all target characters ≥90% fresh copy at target wpm.
- **Constitution check:** AGENT.md says *don't add Morse before the user asks* —
  **the user asked** (2026-06-13). Note it in `LOG.md` when built.

### 6.2 Language / vocab (`vocab`, item_kind `recall`)
- **Scopes:** deck → word. Decks are user-chosen (e.g. `fr-a1`); a deck is a
  content pack in `items`.
- **Spaced repetition:** this is the canonical Leitner use case — `scheduler.py`
  already does ease/interval per question scope; words reuse it unchanged.
- **Items:** front (prompt) / back (answer) + part of speech + example. Authored
  packs *or* AI-`generate`d from a word list. **Self-grade** (again/hard/good/easy)
  maps to the existing ease update; optionally a typed-answer auto-grade.
- **AI hooks:** `explain` → for a word you keep missing, generate a **personalized
  mnemonic** (cache-first in `explanations`-style store, keyed by item+content_version
  so it's a one-time cost like the ham batch). `roleplay` → "use it in a sentence"
  conversational drill (live, budget-guarded, Sonnet/Haiku per `AI_MODELS`).
- **Readiness:** ≥80% fresh recall across the deck (mirrors the ham rule), or a
  user-set "graduated N words" goal.

### 6.3 Calibration (`calib`, item_kind `calibrated_mcq`)
- **The twist:** wraps **any** other cartridge's items. You answer *and* declare a
  confidence (0–100%). Stored in the new `attempts.confidence` column.
- **Deterministic scoring (new engine module `calibration.py`):** purely a
  function of attempts → a **Brier score** and a **calibration curve** (bucket
  confidences into deciles; for each bucket, observed accuracy vs. stated
  confidence). Idempotent, no randomness, no LLM — fits the engine rules perfectly.
- **"Mastery" reinterpreted:** the scope is confidence-band, not topic. Progress
  shows *over/under-confidence* per band ("at 90% stated you're right 64% — drop
  your confidence"). The S-meter becomes a **calibration gauge** (deviation from
  the diagonal), a very on-brand instrument.
- **Selection:** draw from a host cartridge (default `ham`) so it doubles as exam
  prep with a metacognition layer. No new content needed to ship v1.
- **Readiness:** Brier ≤ target (e.g. 0.10) and no band off by >10 points.

### 6.4 Inquiry (`inquiry`, item_kind `inquiry`)
- **The skill:** asking the highest-information question. AI hides a solution
  (a fault to diagnose, a person/object in 20-questions, a differential).
- **Loop:** scenario shown → user asks free-text questions → AI answers in role
  (`roleplay`) → user commits a final answer. Deterministic scorer estimates
  **information gain per question** from the candidate set the scenario declares
  (the scenario ships with a hidden hypothesis set; each answer prunes it; gain =
  entropy reduction). The *AI plays the oracle*; the **scoring of question quality
  is deterministic** over the declared hypothesis set — keeping it out of the LLM
  path.
- **Items:** AI-`generate`d scenarios (scenario text + hidden answer + hypothesis
  set + which questions are "discriminating"), reviewed/cached like the batch so
  scoring is reproducible.
- **Attempt:** `correct` = solved within a question budget; `extra` =
  `{questions_asked, mean_info_gain, wasted_questions}`.
- **Readiness:** solve rate ≥ target at ≤ budget questions, mean info-gain ≥ target.
- **Risk/honesty note:** info-gain scoring is only as good as the scenario's
  declared hypothesis set; v1 keeps scenarios small (≤8 hypotheses) so the math is
  trustworthy. Flagged as the most experimental of the four.

## 7. AIProvider extensions

Add two methods across `AIProvider` / `AnthropicProvider` / `StubProvider`
(the stub must keep working — constitution + AGENT.md):
```python
def generate(self, *, cartridge: str, spec: dict, grounding: str = "") -> AIResult   # items/scenarios/mnemonics
def roleplay(self, *, cartridge: str, context: dict, history: list) -> AIResult       # turn-based tutor/oracle
```
- Prompts externalized as `prompts/generate_<cartridge>.md` and
  `prompts/roleplay_<cartridge>.md` (Console-tunable, loaded by `prompts.py`).
- Models routed in `config.AI_MODELS` (`generate`→Sonnet for build-time packs;
  `roleplay`→Haiku/Sonnet live). Batch-style generation (vocab packs, inquiry
  scenarios) is a **build step** like the ham explanation batch — gate with the
  Console limit, export a portable **seed** so deploy rebuilds free.
- `StubProvider.generate/roleplay` return deterministic placeholders so the app
  runs fully offline.

## 8. What this explicitly does NOT change
- The ham experience and routes — unchanged behavior, just reclassified as the
  `ham` cartridge.
- The deterministic scoring math in `mastery.py` / `adaptive.py` / `scheduler.py`
  / `readiness.py` — unchanged; they consume the same attempt shape.
- `attempts` append-only contract — preserved (additive columns only).
- No new framework, no multi-user/auth, no public hosting, no Advanced bank.

## 9. Build sequence (small committed steps, per AGENT.md)

1. **Framework** — `cartridges`/`items` tables + migration + `bank.py` adapter +
   backfill `ham`; `validate.py` + `smoke_test.py` cover it. *No behavior change.*
2. **Calibration** — cheapest first: no new content (wraps `ham`), one deterministic
   `calibration.py`, one client slider, a calibration gauge. Proves the attempt-shape
   extension end-to-end.
3. **Morse** — first truly new content + the `audio_decode` kind + Web Audio module.
   Self-contained; great demo.
4. **Vocab** — exercises `generate` (packs) + the cache-first mnemonic store +
   `roleplay`; ships a portable seed.
5. **Inquiry** — last (most experimental): `roleplay` oracle + deterministic
   info-gain scorer + small authored/generated scenario set.

Each step: spec-aligned, `python tests/smoke_test.py` (forces stub, never spends)
green before commit, and a dated `LOG.md` entry.

## 10. Open questions for the user
- **Vocab first language/deck?** (drives the first content pack / seed.)
- **Calibration host** — wrap the ham bank (exam prep + metacognition), or make it
  domain-agnostic from day one?
- **Cartridge switcher placement** — top-level nav vs. a dashboard "console select"?
- **Morse target speed** — fixed (e.g. 18/5 wpm Farnsworth) or user-set per stage?
- **Naming** — keep everything under "Elmer," or does the meta-trainer get its own
  identity now that it's no longer ham-only?

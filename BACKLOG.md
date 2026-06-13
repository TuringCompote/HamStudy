# BACKLOG.md — Living task list

Derived from §9 of the build spec, reconciled with the §0 decisions. Work phases in order.
Check items off as completed and mirror narrative progress into `LOG.md`. P0 = must-have
for that phase to be "done".

Legend: `[ ]` todo · `[~]` in progress · `[x]` done

---

## Phase 0 — Research & ground-truthing  *(done 2026-06-13 → see `PHASE0-FINDINGS.md`)*
- [x] (P0) Fetch and verify the URLs in spec §5. Done — official URLs LIVE; corrected the
      data-file URL to lowercase `.pdf` and the `p_level_id=1` = Advanced (not Basic) error.
- [x] (P0) Identify the **current** bank + `bank_version` = **2025-07-15**, **984 questions**.
- [x] (P0) Confirm `B-AAA-BBB-CCC` ID + answer-in-brackets format from the official page.
- [x] (P0) Decide parser approach: official PDF = ground truth; adapt `canadian-ham-exam`
      (v1.0.1, 2025-02-26, UTF-8); cross-check count vs 984 + HamStudy CA_B_2025.
- [x] (P0, do at build start) Download the bank PDF + Reference Material ZIP into
      `references/`. **Done** — bank PDF (apc-cap data file) + Reference Material ZIP
      (labelled "Training" + unlabelled "Exam" formula/diagram sheets, auto-extracted to
      `_extracted/`). Correct ZIP path is `sites/default/files/documents/`. **English-only.**
- [x] Download RIC-3, RBR-4, RIC-1 into `references/` for the AI explanation layer
      (prompt-cache these at runtime). **Done** — RBR-4 as PDF; RIC-3 & RIC-1 are HTML-only
      (no PDF published), saved as faithful HTML for Phase-5 text extraction. All in
      `app/db/fetch_sources.py` (reproducible re-download).

## Phase 1 — Data foundation  *(done 2026-06-13 → see `LOG.md`)*
- [x] (P0) Build the ingest script: official bank → `questions` table (with `bank_version`).
      `app/db/ingest.py` — two-column-aware parser, 984/984 questions.
- [x] (P0) Stand up the SQLite schema (spec §7): `questions`, `attempts`, `progress`,
      `recommendation`, `journal` (+ `diagnostics`, `usage`, `meta`). `app/db/schema.sql`.
- [x] (P0) Validate: count==984, per-section counts, no missing correct answers, every ID
      parses to a valid section 1–8. `app/db/validate.py` — all checks pass.
- [x] Idempotent re-ingest: upsert by `id`, derive `bank_version` from the PDF title page,
      **never drop `attempts`** (verified with a probe attempt).

## Phase 2 — Quiz engine (MVP)  *(done 2026-06-13 → see `LOG.md`)*
- [x] (P0) Per-section drilling. `build_drill` + `/quiz?mode=drill&section=N` (immediate feedback).
- [x] (P0) Full 100-question mock exam: section-proportional sampling (largest-remainder),
      spread across subsections, **70% pass + 80% Honours lines shown**, timer. `build_mock_exam`.
- [x] (P0) Record every answer to `attempts` (server-graded; id, section, sub, chosen, correct,
      ms, mode, ts). Answers never shipped to the client in the quiz payload.
- [x] Deterministic engine v1: per-section mastery % + coverage. `app/engine/mastery.py` (idempotent).
- [x] Minimal dashboard. Per-section mastery bars + coverage + drill/exam entry points.

## Phase 3 — Interactive learning layer  *(DONE 2026-06-13 — all 8 tools + lessons + flow)*
- [x] (P0) Ohm's Law / power triangle solver. `static/tools/ohms.js` (any 2 of V/I/R/P → other 2 + formula + circuit SVG).
- [x] (P0) Reactance & resonance playground (L, C, f; X_L, X_C, f_resonant + log-log plot). `reactance.js`.
- [x] (P0) Decibel converter (ratio ↔ dB, power/voltage toggle, 6 dB/S-unit examples). `decibel.js`.
- [x] (P0) SWR / impedance matching visualizer (R+jX & Z₀ → Γ, SWR, reflected %, return loss, bar). `swr.js`.
- [x] (P0) Wavelength ↔ frequency tool (½λ dipole, ¼λ vertical, velocity factor). `wavelength.js`.
- [x] Series/parallel resistance & capacitance calculator with live schematic. `seriesparallel.js` (§4).
- [x] Band-plan explorer (Canadian bands, privileges by qualification, primary/secondary). `bandplan.js` (§1).
- [x] Propagation visual (ionospheric layers vs day/night, sky/ground/LOS, MUF). `propagation.js` (§7).
- [x] (P0) Write **original** short lesson text per section (no copied course prose).
      `app/content/sections/section{1..8}.md` — all 8 written, rendered via `app/content`.
- [x] (P0) Wire the "Learn → Interact → Drill" flow per section. `GET /section/{n}` +
      `section.html`; tools mounted via `static/tools/registry.js` (data-tool framework).
      *(Browser visual/interaction check still recommended — JS untested headless.)*

## Phase 4 — Spaced repetition + review queue  *(DONE 2026-06-13)*
- [x] (P0) Deterministic scheduler: ease/interval per question (Leitner). `app/engine/scheduler.py`
      — Leitner boxes from `attempts` (one outcome/day), box→interval, due_date; idempotent.
- [x] (P0) Review queue surfacing previously-missed questions. `quiz.build_review` +
      `/quiz?mode=review` + `/api/quiz` review mode; dashboard "N due" button; immediate feedback.
- [x] Formula-sheet trainer using the **unlabelled** ISED aid sheet (exam-legal sheet).
      `/formula-trainer` + `formulatrainer.js` — flashcards over an original curated set
      (`app/formulas.py`), two directions, missed cards requeue. Trains recognizing the
      unlabelled sheet's formulas (no PDF reproduced).

## Phase 4.5 — Adaptive learning engine (§6d)  *(deterministic core DONE 2026-06-13)*
- [x] (P0) Diagnostic placement: per-section probe (8 Q across subsections) + self-declared
      confidence prior; engine scores it → starting **depth tier**. `app/engine/diagnostic.py`,
      `/quiz?mode=diagnostic`, `/api/diagnostic`, section-page CTA.
- [x] (P0) Depth tiers (test-out/light/standard/deep) from **fresh** accuracy, seeded by the
      diagnostic when fresh data is thin (measured overrides). Tier computed on demand +
      shown on dashboard/section. *(Drives drill selection; lesson-depth/spacing scaling by
      tier is the Phase-5 AI + scheduler-tuning follow-on.)*
- [x] (P0) Elo/IRT-lite: per-question `difficulty_b` + per-section ability `θ`, replayed from
      `attempts` (deterministic); drill selector serves the ~75% productive zone. `adaptive.py`.
- [~] (P0) Continuous re-evaluation: tiers recompute from accumulated fresh accuracy each
      load, so they move as performance changes. *(Windowed trend/decay = Phase 5.)*
- [x] (P0) **Coverage guarantee (§6d.4):** per-subsection fresh probing tracked; readiness
      requires ≥80%/section AND every subsection probed. `app/engine/readiness.py`.
      *(Recency-window refinement deferred.)*
- [ ] AI layer: condense lesson text to tier depth; generate Deep-tier worked examples;
      explain individual misses; narrate tier changes. (Anthropic, behind `AIProvider`.) → Phase 5
- [x] `diagnostics` table (append-only) records every probe + resulting tier.
- [ ] **Curated local corpus + RAG (§6d.6):** index `references/` (question bank, RIC-3/1,
      RBR-4, formula sheets + any user-added PDFs) into a lightweight retrieval index;
      English-only; re-indexable when files change.
- [ ] **AI-adapted content (§6d.6):** "Tuned for you" lesson block + per-miss explanations,
      generated from the corpus to fit the engine's tier/miss diagnosis. Original text only
      (cite/link community sources, never reproduce). Base lessons stay as fallback.
- [ ] **`content_cache` table (§7):** cache AI content by (section/sub + tier + miss-profile
      hash + bank_version + prompt-version); regenerate only on key change; budget-guarded.

## Phase 5 — Close the loop (deterministic engine + Anthropic AI layer)  *(DONE 2026-06-13)*
- [x] (P0) Engine computes mastery + **trend** / fresh-vs-review / most-missed / fast-wrong vs
      slow-wrong, idempotent. `app/engine/analysis.py`.
- [x] (P0) Engine writes `recommendation.json` (+ history table, dedup by content hash).
      `app/engine/recommend.py`.
- [x] (P0) Dashboard reads the recommendation and surfaces "today's session" (app→engine→docs→app).
- [x] (P0) `AIProvider` (`explain/diagnose/narrate/condense`) + Anthropic impl + Stub; key from
      `.env`; per-call-type routing (Opus reason/content, Haiku narrate); externalized prompts.
- [x] (P0) **Budget guard:** `usage` table + monthly ceiling (default $15, configurable);
      fall back to stub when exceeded; RIC docs prompt-cached. `app/coaching/usage.py`.
- [x] AI-written narrative `journal/YYYY-MM-DD.md` per cycle. `app/coaching/journal.py`.
- [x] (P0) **Batch explanation layer (§6f):** Message Batches → **984/984** rich STRUCTURED
      explanations (core/distractors/concept/misconception/link/+opt) into `explanations`,
      tagged bank_version + Opus. `explain()` cache-first. ~$19.34 one-time. `explain_batch.py`.
- [x] (P0) **Adaptive reveal (§6f.5):** `/api/explain` picks default depth by §6d tier; quiz.js
      "Go deeper" expander reveals the full stack. Deterministic, free.
      *(Live per-user `diagnose()` layer: provider method built; UI surfacing is a small follow-on.)*
- [x] (P0) Readiness: ≥80% fresh-question accuracy in every section AND §6d.4 coverage ⇒
      "book the exam." `app/engine/readiness.py`.

## Phase 6 — Package & deploy  *(build artifacts DONE 2026-06-13; actual LXC deploy = Chris's step)*
- [x] (P0) Dockerfile + docker-compose. Single container (uvicorn), `data/` volume mount,
      env_file `.env`, healthcheck on `/api/health`, `.dockerignore` keeps data/secrets/refs out.
      *(Not build-tested here — no Docker on the dev box; builds on the LXC.)*
- [x] (P0) Deploy config: **one container, LXC LAN IP:port via `BIND_IP`/`PORT`, local-DNS
      hostname, home VPN, no reverse proxy/Cloudflare.** (Run `docker compose up -d` on the LXC.)
- [x] (P0) SQLite backup to NAS: `app/db/backup.py` (online WAL-safe snapshot + prune) + cron
      example in README.
- [x] `README.md`: run / update / **deploy** steps + bank-update path; journal → point Obsidian
      at `data/journal/`. ⚠️ documented: preserve `data/hamstudy.db` (has the paid batch).
- [ ] Optional: thin read-only Cowork deep-dive skill (`ham-coach-skill/SKILL.md`).

## Phase 7 — Advanced Qualification (later)
- [ ] Re-run ingest with the Advanced bank; reuse the engine; add Advanced-only tools.

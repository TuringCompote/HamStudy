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
- [~] (P0, do at build start) Download the bank PDF + Reference Material ZIP into
      `references/`. **Bank PDF: done** (`amateur_basic_questions_en.pdf`, via the
      lowercase apc-cap data-file URL). **ZIP still pending** — the dated `documents/...`
      URL 404s; needs a refreshed URL (non-blocking; feeds Phase 4). **English-only.**
- [ ] Download RIC-3, RBR-4, RIC-1 into `references/` for the AI explanation layer
      (prompt-cache these at runtime). *(URLs to resolve; tracked in `fetch_sources.py`.)*

## Phase 1 — Data foundation  *(done 2026-06-13 → see `LOG.md`)*
- [x] (P0) Build the ingest script: official bank → `questions` table (with `bank_version`).
      `app/db/ingest.py` — two-column-aware parser, 984/984 questions.
- [x] (P0) Stand up the SQLite schema (spec §7): `questions`, `attempts`, `progress`,
      `recommendation`, `journal` (+ `diagnostics`, `usage`, `meta`). `app/db/schema.sql`.
- [x] (P0) Validate: count==984, per-section counts, no missing correct answers, every ID
      parses to a valid section 1–8. `app/db/validate.py` — all checks pass.
- [x] Idempotent re-ingest: upsert by `id`, derive `bank_version` from the PDF title page,
      **never drop `attempts`** (verified with a probe attempt).

## Phase 2 — Quiz engine (MVP)
- [ ] (P0) Per-section drilling.
- [ ] (P0) Full 100-question mock exam: proportional sampling across subsections, 70% line
      shown, **80% Honours line also shown**, optional timer.
- [ ] (P0) Record every answer to `attempts` (id, section, sub, chosen, correct, ms, mode, ts).
- [ ] Deterministic engine v1: per-section mastery %.
- [ ] Minimal dashboard.

## Phase 3 — Interactive learning layer  *(the differentiator — prioritize)*
- [ ] (P0) Ohm's Law / power triangle solver.
- [ ] (P0) Reactance & resonance playground (L, C, f sliders; X_L, X_C, f_resonant).
- [ ] (P0) Decibel converter (ratio ↔ dB; 6 dB/S-unit worked examples).
- [ ] (P0) SWR / impedance matching visualizer (mismatch → SWR, reflected power, line loss).
- [ ] (P0) Wavelength ↔ frequency tool (½λ dipole, ¼λ vertical helper).
- [ ] Series/parallel resistance & capacitance calculator with live schematic.
- [ ] Band-plan explorer (Canadian bands, privileges by qualification, primary/secondary).
- [ ] Propagation visual (ionospheric layers vs day/night, sky/ground/LOS, MUF).
- [ ] (P0) Write **original** short lesson text per section (no copied course prose).
- [ ] (P0) Wire the "Learn → Interact → Drill" flow per section.

## Phase 4 — Spaced repetition + review queue
- [ ] (P0) Deterministic scheduler: ease/interval per question (Leitner or SM-2-lite).
- [ ] (P0) Review queue surfacing previously-missed questions.
- [ ] Formula-sheet trainer using the **unlabelled** ISED aid sheet (exam-legal sheet).

## Phase 4.5 — Adaptive learning engine (§6d)  *(the per-section adaptivity Chris asked for)*
- [ ] (P0) Diagnostic placement: short per-section probe (6–10 Q) + optional self-declared
      confidence prior; engine scores it and assigns a starting **depth tier**.
- [ ] (P0) Depth tiers (test-out / light / standard / deep) drive lesson depth + drill
      volume + spacing; store `tier` per section in `progress`.
- [ ] (P0) Elo/IRT-lite: per-question `difficulty_b` + per-section ability `θ`, updated
      online from `attempts`; drill selector serves questions near θ (~70–85% success zone).
      Must be deterministic.
- [ ] (P0) Continuous re-evaluation: tiers move with trend (decay drops test-out → light).
- [ ] (P0) **Coverage guarantee (§6d.4):** track per-subsection fresh-question recency;
      readiness requires ≥80%/section AND every subsection probed within the window.
- [ ] AI layer: condense lesson text to tier depth; generate Deep-tier worked examples;
      explain individual misses; narrate tier changes. (Anthropic, behind `AIProvider`.)
- [ ] `diagnostics` table (append-only) records every probe + resulting tier.

## Phase 5 — Close the loop (deterministic engine + Anthropic AI layer)
- [ ] (P0) Engine computes per-section/subsection mastery **+ trend** (improving /
      plateaued / regressing), fresh vs review accuracy, most-missed concepts, and
      fast-wrong vs slow-wrong classification. Idempotent.
- [ ] (P0) Engine writes `recommendation.json` (next session, focus, review queue,
      readiness, rationale) — versioned, human-readable.
- [ ] (P0) Dashboard reads `recommendation.json` and surfaces "today's session" — closing
      app → engine → docs → app.
- [ ] (P0) `AIProvider` interface (`explain()`, `diagnose()`, `narrate()`) + Anthropic impl;
      key from env/secrets. **Default model Opus**; stub/local impl behind the same interface.
- [ ] (P0) **Budget guard:** `usage` table (tokens/cost/type per call); enforce monthly
      ceiling (~$15); fall back to deterministic-only when exceeded. Prompt-cache the RIC
      reference docs. Set a Console spend limit too. (See QUESTIONS.md.)
- [ ] AI-written narrative `journal/YYYY-MM-DD.md` per cycle (scores + plan delta + why).
- [ ] (P0) Readiness detection: fresh-question accuracy ≥80% across all 8 sections **AND**
      the §6d.4 coverage guarantee (every subsection probed within the recency window) ⇒
      "book the exam."

## Phase 6 — Package & deploy
- [ ] (P0) Dockerfile + docker-compose.
- [ ] (P0) Deploy as **one container in a single Proxmox LXC**. **No reverse proxy / no
      Cloudflare** — bind to the LXC LAN IP:port, reach by **local DNS hostname**, remote
      via **home VPN**. LAN/VPN-only.
- [ ] (P0) SQLite backup to NAS.
- [ ] `README.md`: run / update / deploy steps. Journal export to Obsidian (path TBD).
- [ ] Optional: thin read-only Cowork deep-dive skill (`ham-coach-skill/SKILL.md`).

## Phase 7 — Advanced Qualification (later)
- [ ] Re-run ingest with the Advanced bank; reuse the engine; add Advanced-only tools.

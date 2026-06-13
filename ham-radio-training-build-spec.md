# Canadian Amateur Radio (Basic) — Training System Build Spec

> **Purpose of this file.** This is a self-contained briefing + build plan to hand to a
> Claude Opus build agent (in **Claude Code** — see §0.2 — or Cowork). It tells the agent
> what to research, what to download, what to build, and how to structure it. Read the
> whole file first — **including §0, which records decisions that override any conflicting
> text below** — then work the **Phased Build Plan** (Section 9) in order. Treat Sections
> 4–5 as ground truth for the syllabus and sources; verify every URL is live before relying
> on it, and re-fetch the *current* question bank rather than assuming a cached copy.

---

## 0. Resolved decisions (READ FIRST — supersedes any conflicting text below)

These were settled with the user during spec refinement on **2026-06-13**. Where the older
prose in §6a / §8 / §11 conflicts, **this section wins**.

### 0.1 Architecture & product decisions

- **Target qualification: Basic *with Honours*.** The system optimizes toward an **80%
  fresh-question readiness bar across all 8 sections**, not merely 70%. Honours unlocks
  HF (below 30 MHz) and full power. 70% is "passing"; 80% is "ready."
- **Adaptive depth, not exhaustive coverage (§6d).** The user is experienced in electronics
  and wants the system to *adapt per section* — diagnose where he's strong, compress or test
  out of those, and go deep where he's weak. Depth tiers + an Elo/IRT-lite adaptive question
  selector drive this. **Hard constraint:** adaptivity may compress but never fully skip —
  readiness requires ≥80% in every section AND minimum fresh-question coverage of every
  subsection, so no blind spots form.
- **Question bank facts (verified 2026-06-13, see `PHASE0-FINDINGS.md`):** current bank is
  **984 questions, effective 2025-07-15**; the official data-file URL is lowercase `.pdf`;
  parse the official PDF as ground truth and adapt the `canadian-ham-exam` parser, cross-
  checking the count against 984 and the HamStudy CA_B_2025 pool.
- **App-led architecture (not a standalone coach skill).** The **web app is the lead
  orchestrator.** The "coach" is no longer a separate Cowork/Claude Code skill that owns
  the loop. Coaching is split into two layers:
  - **Deterministic engine (plain code inside the app):** mastery %, trend, spaced-
    repetition scheduling, next-section selection, readiness detection. **No LLM. Idempotent
    — same `attempts` in ⇒ same recommendation out.** This is the loop's skeleton and is
    pure arithmetic over the event log.
  - **AI layer (Anthropic API, called by the app):** the *generative* work only —
    conceptual explanations of missed topics, diagnosing *why* a misconception recurs
    (the "fast + wrong" case), writing the narrative journal entry, and phrasing "today's
    session" in plain language. Nondeterminism is acceptable and expected here.
- **AI backend: Anthropic API (Claude), behind a swappable provider interface.** Chosen
  over a local model because the user's GPU (16 GB) can only host ~8–14B quantized models,
  which are too weak for high-quality misconception diagnosis and tutoring. **Build the AI
  calls behind a thin `AIProvider` abstraction** (e.g. `explain()`, `diagnose()`,
  `narrate()`) so a local model (Ollama) can be swapped in later if cost/privacy warrants.
  Keep the API key in env/secrets, never in the repo. Only question text + the user's miss
  patterns are sent; this is acceptable to the user.
- **Coach skill: folded into the app, with a thin optional Cowork skill retained.** The app
  owns the automatic live loop. A lightweight Cowork skill (reads the same SQLite, read-only)
  is kept *only* for interactive "sit down and review my weak areas with me" deep-dives and
  build-time help. It is **not load-bearing** — the loop closes without it.

### 0.2 Build-environment & stack decisions

- **Build in Claude Code, not Cowork, when the time comes.** This is a multi-file software
  project (FastAPI service + JS/SVG front end + ingest scripts + Dockerfile/compose +
  iterative run/test + git). Claude Code is purpose-built for that: terminal-native, git-
  aware, runs the dev server and tests in a loop, manages multi-file context. Cowork *can*
  do it but is optimized for file/document/task automation, not long iterative codebases.
  **Use Cowork for: this spec refinement, research/ground-truthing (§Phase 0), and the
  thin deep-dive coach skill. Use Claude Code for: the actual app build (Phases 1–7).**
- **This spec is written to be tool-portable.** It is the master brief either way.
  **`AGENT.md` is the build-agent's operating manual; copy or symlink it to `CLAUDE.md`**
  so Claude Code auto-loads it as project instructions.
- **Stack (locked): FastAPI (Python) + SQLite + a vanilla-JS / SVG client**, shipped as a
  **single container**. Rationale: one backend language that matches the `canadian-ham-exam`
  parser; no heavy JS build toolchain; the interactive concept tools are self-contained
  client-side math (pure JS + SVG), which is the easiest path to "lots of small calculators."
  HTMX is acceptable for the app shell/navigation if the agent prefers. Postgres is not
  needed at single-user scale.

### 0.2b Name & visual design (decided 2026-06-13)

- **App name: `Elmer`** — ham slang for the experienced operator who mentors a newcomer,
  which is exactly this app's role. Store it in a **single `APP_NAME` config constant** +
  the page `<title>`; never hardcode it across files, so it stays one-line changeable.
- **Visual direction: "instrument panel."** Calm neutral base (light + dark), **one accent**
  (phosphor teal or amber, à la a scope/meter), **monospace font for numbers, question IDs
  (`B-006-002-003`), and formula values**, clean sans (e.g. Inter) for body. Per-section
  mastery renders as a **segmented S-meter** whose color encodes the adaptive depth tier
  (§6d.2). Define all color/spacing/radius/typography as **CSS design tokens in one
  `tokens.css`**; the 8 SVG concept tools theme themselves from those variables so
  everything stays visually consistent across build phases. Keep styling lightweight — no
  heavy CSS framework (matches the vanilla-JS/SVG stack).

### 0.3 Scope of the current session

- **Spec refinement only — no app code was written.** Deliverables produced this session:
  this updated spec, plus `constitution.md`, `BACKLOG.md`, `QUESTIONS.md`, and
  `AGENT.md` (= `CLAUDE.md`). `README.md` and `LOG.md` are created at build kickoff.

### 0.4 Still-open (deployment-time) questions — see `QUESTIONS.md`

Exam date = **within 2026** (soft ~Q4; coach tightens once it sees early scores). Hosting =
**one container in a single Proxmox LXC, local-DNS hostname, home-VPN for remote, no reverse
proxy/Cloudflare.** Still open: exact Obsidian vault path for journal export, the placement-
test style (§6d.1), and whether to include the French bilingual pool (**default: English-
only for v1**).

---

## 1. TL;DR for the agent

Build a **two-part personal learning system** to get a human (Chris, in Alberta, Canada)
through the **ISED Basic Amateur Radio Qualification** exam:

1. **A Claude "learning coach" skill** — orchestrates a personalized study plan, tracks
   progress against the 8 official syllabus sections, identifies weak areas, schedules
   spaced review, and maintains a study journal.
2. **A self-hosted interactive web app** — the actual learning surface: short lessons
   per section, *interactive* electronics/theory components (not just multiple-choice
   drilling), and a practice-exam engine driven by the official ISED question bank.

The content spine is the **official, free ISED question bank** + **free club/course
material**. No paid material is required. Host the web app on the user's homelab
(Proxmox/R730, behind the existing reverse-proxy setup).

---

## 2. Project vision & goals

**What "done" looks like:**

- User can open a local web app, pick a syllabus section, learn the concept with
  *interactive* aids (e.g. an Ohm's-Law solver, an SWR/impedance visualizer, a
  resonance/reactance playground, a band-plan explorer), then drill the real exam
  questions for that section.
- A coach (Claude skill) that knows where the user is, what they're weak on, and what
  to do next — and writes it down so progress survives across sessions.
- A full practice-exam mode that mirrors the real exam: 100 questions, pass mark 70%,
  drawn proportionally from all sub-categories.
- Everything runs locally/self-hosted; data stays on the user's own infrastructure.

**Explicit design priorities (from the user):**

- **Interactive learning over rote drilling**, *especially* for electronics and theory.
  Visualize the math. Let the user manipulate values and see results.
- Clear **per-section** structure that mirrors the official syllabus.
- Mix of: (a) short learning content, (b) interactive concept tools, (c) question-bank
  practice.
- Track it all and make next-step recommendations.

**Non-goals (for v1):**

- Advanced Qualification (design for it, but Basic ships first).
- Morse code.
- Multi-user / public hosting (single-user personal tool; keep auth trivial or absent
  behind the homelab perimeter).

---

## 3. Target certification (facts to encode)

- **Certificate:** Basic Qualification, Amateur Radio Operator Certificate (Canada).
- **Regulator:** Innovation, Science and Economic Development Canada (**ISED**), Spectrum
  Management & Telecommunications.
- **Exam format:** 100 multiple-choice questions, 4 options each.
- **Pass mark:** **70%** (Basic with Honours is **80%+**, which unlocks all-band/HF
  privileges and full power — worth flagging to the user as a stretch target).
- **Question source:** ISED **RIC-7** Basic Qualification Question Bank; the public exam
  is drawn from this exact pool, so mastering the pool ≈ passing.
- **Syllabus reference docs:** **RIC-3** (Information on the Amateur Radio Service +
  syllabuses), **RBR-4** (Standards for Operation of Stations in the Amateur Service),
  **RIC-1** (examiner guide — useful for understanding exam construction rules).
- **Question ID scheme:** `B-AAA-BBB-CCC` where `B` = Basic, `AAA` = major section,
  `BBB` = sub-section, `CCC` = question number; the correct answer letter is published
  alongside each ID in the bank. Use this scheme as the natural primary key in the data
  model.

---

## 4. Official syllabus structure (the 8 sections)

The Basic exam is organized into **eight subject areas**. Build the app's navigation,
the question taxonomy, and the coach's progress model around these. Sub-topics below are
the canonical breakdown — expand each from RIC-3 / the question bank section headers when
you ingest the data.

1. **Regulations and Policies** — licences, eligibility, fees/terms, suspension &
   inspector powers, operator certificates & reciprocal recognition, operating on behalf
   of others, content restrictions (no music/profanity/secret code/commercial),
   installation/repeater/club-station rules, interference & protection, emergency
   communications, non-remuneration & privacy.
2. **Operating and Procedures** — VHF/UHF repeater & simplex voice procedures, HF voice,
   phonetic alphabet, tune-ups/dummy load/courteous operation, CW procedural signs,
   RST/S-meter signal reporting, Q-signals, emergency operating, record keeping.
3. **Station Assembly, Practice and Safety** — functional layouts (HF station, FM/SSB/CW
   transmitters & receivers, digital systems, regulated power supplies, Yagi),
   receiver/transmitter fundamentals, modulation (AM/SSB/FM/phase), digital modes
   (RTTY/ASCII/AMTOR/packet), batteries & charging, power supplies, **RF & electrical
   safety**, grounding/lightning.
4. **Circuit Components** — resistors, capacitors, inductors, transformers, diodes,
   transistors, tubes, ICs, switches, relays, meters; symbols and roles.
5. **Basic Electronics and Theory** — Ohm's Law, power, series/parallel, AC concepts,
   reactance/impedance, resonance, Q, decibels, amplification/gain, filters.
6. **Feedlines and Antenna Systems** — characteristic impedance, balanced/unbalanced &
   baluns, connector & coax types, line loss, standing waves/SWR/matching, polarization,
   wavelength vs physical length, gain/directivity/pattern/bandwidth, vertical/Yagi/wire/
   loop antennas.
7. **Radio Wave Propagation** — line-of-sight, ground wave, sky wave; ionospheric layers,
   MUF/critical frequency, sunspots & solar effects, fading, band characteristics by
   time/frequency.
8. **Interference and Suppression** — front-end overload, audio rectification,
   intermodulation, spurious emissions, key-clicks, harmonics, splatter, transmitter
   adjustment, filters, EMCAB-2 field-strength criteria, complaint resolution.

> Sections 4–8 are where **interactive learning matters most** — prioritize building
> concept tools there.

---

## 5. Source material (verify each URL is live before use)

### 5a. Official ISED / Government of Canada (authoritative — free)

- **Amateur radio operator certification (landing):**
  `https://ised-isde.canada.ca/site/amateur-radio-operator-certificate-services/en`
- **Amateur radio exam generator (study + practice):**
  `https://ised-isde.canada.ca/site/amateur-radio-operator-certificate-services/en/amateur-radio-exam-generator`
- **Print ALL Basic questions (full bank, HTML/PDF):**
  `https://ised-isde.canada.ca/site/amateur-radio-operator-certificate-services/en/amateur-radio-exam-generator/print-all-basic-questions`
- **Direct question-bank data files (machine-friendly):**
  - Basic: `https://apc-cap.ic.gc.ca/datafiles/amateur_basic_questions_en.PDF`
  - Advanced (for later): `https://apc-cap.ic.gc.ca/datafiles/amateur_advanced_questions_en.PDF`
  - *Note:* a French set also exists (`..._fr.PDF`). The bank is updated periodically
    (a 2025 revision exists) — **always pull the current file and record its effective
    date** in the data model so the user knows their pool is current.
- **Online study-questions tool (per category):**
  `https://apc-cap.ic.gc.ca/pls/apc_anon/apeg_study.study_questions_intro`
- **Online practice exam (level 1 = Basic):**
  `https://apc-cap.ic.gc.ca/pls/apc_anon/apeg_practice.practice_form?p_level_id=1`
- **Basic formula & block-diagram aid sheets (labelled + unlabelled):** linked under
  "Basic" on the exam-generator Downloads page. The **unlabelled** sheet is the one
  permitted *during* the real exam — train the user to use it.
- **Syllabus/standards circulars:** RIC-3, RBR-4, RIC-1 — search the ISED Spectrum
  Management site (`ised-isde.canada.ca`) for the current issues and download as
  reference docs for the coach's knowledge base.

### 5b. Free courses & study guides (community — free)

- **University of Waterloo ARC "Basic — The Essentials" PDF:**
  `https://uwarc.uwaterloo.ca/assets/basic-essentials-main.pdf`
- **Toronto Emergency Communications Group — Basic Amateur Radio Course** (free,
  multi-PDF lessons): locate via the RAC "Becoming a Ham" page and the group's site.
- **Hamshack.ca Basic course (free chapters, QSL approach):**
  `https://hamshack.ca/chapter/basic-amateur-radio/`
- **VE3FCQ Basic Exam Prep curriculum (excellent per-section topic breakdown):**
  `https://ve3fcq.ca/canadian-amateur-radio-basic-exam-prep/`
- **CLARS / Cold Lake Amateur Radio Society self-paced course** (free slide decks,
  videos, quizzes — Alberta-local, relevant to the user).
- **UBC Radio Science Lab syllabus notes:** `http://rsl.ece.ubc.ca/amateur.html`
- **Radio Amateurs of Canada (RAC) — "How to Start" / Becoming a Ham:** `https://www.rac.ca`

### 5c. Question-bank tooling & reference implementations (study before reinventing)

- **HamStudy.org** — mature flashcard/practice engine; supports the Canadian Basic pool.
  Study its question-pool JSON shape and spaced-repetition UX as a design reference:
  `https://hamstudy.org`
- **`canadian-ham-exam` (PyPI)** — Python tool that parses the official ISED bank into a
  practice engine; **use its parser as a reference for ingesting the ISED PDF/HTML into
  structured data:** `https://pypi.org/project/canadian-ham-exam/`
- Search GitHub for existing parsers of `amateur_basic_questions_en` before writing a new
  one (`*.github.com` is reachable from the build sandbox).

> **Copyright/licensing note for the agent:** The ISED question bank is a Government of
> Canada work published for exactly this purpose (study + exam administration) and is free
> to download and use. Community course PDFs vary — **link to them and download for the
> user's personal study; do not redistribute or republish** them in the app. Keep the
> app private/self-hosted. When in doubt, reference the source rather than copying its
> prose into the app's lesson text; write original lesson summaries.

---

## 6. System architecture

Two cooperating parts. They share one data store (the question bank + the user's
progress/journal) so the coach and the app stay in sync.

### 6a. Part 1 — The coaching layer (folded into the app; see §0.1)

> **Superseded by §0.1.** This is no longer a standalone `SKILL.md` that owns the loop.
> The responsibilities below are now split: the **deterministic engine** (mastery, trend,
> spaced repetition, next-section selection, readiness) lives in the **app as plain code**
> and must be idempotent; the **AI layer** (explanations, misconception diagnosis, journal
> narrative) is the app calling the **Anthropic API** behind a swappable `AIProvider`
> interface. A thin, read-only Cowork skill is retained only for interactive deep-dives.

**Responsibilities (now owned by the app's engine + AI layer):**
- Maintain a **study plan** mapped to the 8 sections, with a target exam date and a
  realistic weekly cadence.
- Read the app's progress data (per-question correct/incorrect history, per-section
  mastery %) and **recommend the next session**: which section, how many new questions,
  how much spaced review.
- Run **spaced repetition** logic (Leitner or SM-2-lite) over missed questions.
- Keep a **study journal** (markdown) of what was covered, scores, and reflections —
  fits the user's existing Obsidian/NAS pipeline pattern.
- Surface **conceptual explanations** on demand (using the RIC docs + course PDFs as a
  reference layer), tuned for someone with a strong technical/electronics background — go
  deep on the *why*, don't over-explain basics.
- Flag readiness: "you're consistently >85% across all sections on fresh questions →
  book the exam."

**Where this logic now lives (app modules, not a skill):**
```
app/
  coaching/
    engine.py         # DETERMINISTIC: mastery %, trend, next-section selection, readiness
    scheduler.py      # DETERMINISTIC: spaced-repetition queue (Leitner / SM-2-lite)
    ai_provider.py    # AIProvider interface: explain(), diagnose(), narrate()
    anthropic.py      # AIProvider impl calling the Anthropic API (default)
    # ollama.py       # future local-model impl, swap-in behind the same interface
  references/
    syllabus.md       # the 8 sections + subtopics (from Section 4 here)
    exam-facts.md     # format, pass marks, ID scheme, formula-sheet rules
    ric3-notes.md     # distilled regulatory reference (also feeds AI explanations)

# Thin OPTIONAL Cowork deep-dive skill (read-only; not load-bearing):
ham-coach-skill/
  SKILL.md            # "review my weak areas with me" — reads the same SQLite read-only
```

### 6b. Part 2 — Interactive web app

The learning surface. **Per section:** Learn → Interact → Drill.

**Core modules:**
- **Dashboard** — overall readiness, per-section mastery bars, streak, recommended next
  action (mirrors the coach's recommendation).
- **Section view** — short original lesson text + the section's **interactive tool(s)**
  + a "drill this section" button.
- **Practice/Quiz engine** — per-section drilling and full 100-question mock exams
  (proportional sampling, 70% pass line shown, timer optional). Tracks every answer.
- **Review queue** — spaced-repetition surfacing of previously-missed questions.
- **Formula-sheet trainer** — practice using the *unlabelled* ISED aid sheet, since
  that's what's allowed in the real exam.

**Interactive concept tools to build (this is the differentiator — prioritize):**
- **Ohm's Law / Power triangle** solver — enter any two of V/I/R/P, see the rest + the
  formula path.
- **Series/parallel resistance & capacitance** calculator with a live schematic.
- **Reactance & resonance** playground — sliders for L, C, f; show X_L, X_C, resonant
  frequency, and where they cross.
- **Decibel** converter — ratio ↔ dB, with worked S-meter examples (6 dB/S-unit).
- **SWR / impedance matching** visualizer — mismatch → SWR, reflected power, line loss.
- **Wavelength ↔ frequency** tool with antenna-length helper (½λ dipole, ¼λ vertical).
- **Band-plan explorer** — Canadian amateur bands, privileges by qualification, primary/
  secondary status (ties directly to regs + propagation sections).
- **Propagation visual** — ionospheric layers vs day/night, sky/ground/LOS, MUF concept.

Each tool should let the user **manipulate inputs and immediately see results**, then
optionally jump to the related exam questions.

### 6c — The closed-loop feedback system (core design principle)

This is not a "nice to have" — it is the backbone of the system. The **web app**, the
**coach skill**, and the **documentation** must form a single **self-reinforcing loop**:
the app generates evidence of how the user is performing against the bank, the coach reads
that evidence and decides what to do next, the documentation records the loop's state so it
survives across sessions, and the app then surfaces the coach's decision back to the user.
Every answer the user gives should make the next recommendation smarter.

**The loop, step by step:**

1. **App → data (capture).** Every interaction with a bank question is written to
   `attempts` with full granularity: question ID, section/subsection, chosen vs correct,
   correct/incorrect, response time, mode (drill / mock-exam / review), and timestamp.
   Nothing is discarded — wrong answers are the most valuable signal.
2. **Data → coach (analysis).** The coach reads the accumulated record and computes, per
   section and per subsection: mastery %, trend over time (improving / plateaued /
   regressing), accuracy on **fresh** questions vs **review** questions, the specific
   questions and *concepts* most often missed, and confidence-vs-correctness mismatches
   (slow + wrong = not learned; fast + wrong = a misconception to correct).
3. **Coach → recommendation (decision).** From that analysis the coach produces the next
   session: which section to focus on, how many new vs review questions, which concept
   tools to revisit first, and an updated spaced-repetition queue. Weak subsections get
   pulled forward; mastered ones get spaced out.
4. **Recommendation → documentation (record).** The coach writes its decision and its
   reasoning to the docs (journal entry + updated plan), so the loop's state is durable
   and inspectable — not locked inside a model's head.
5. **Documentation → app (surface).** The app reads the latest recommendation and presents
   it on the dashboard ("Today: 15 questions in Feedlines & Antennas, 10 review from
   Propagation, revisit the SWR tool"). The user acts on it — which generates the next
   batch of `attempts`, and the loop repeats. **Each cycle tightens.**

**The data contract (the shared interface between app and skill — define this explicitly):**

- **`attempts`** is the ground-truth event log the app owns and only ever appends to.
- **`progress`** is the derived per-section / per-subsection / per-question state
  (mastery %, ease, interval, last-seen, trend). Either the app computes it or the coach
  does — pick one owner and document it — but both read it.
- **`recommendation.json`** (or a row/table) is what the **coach writes** and the **app
  reads**: next session plan, focus areas, review queue, readiness status. This is the
  coach's output channel back into the app. Keep it a simple, versioned, human-readable
  file so it doubles as documentation.
- **`journal/`** markdown entries are the narrative record the coach appends each cycle:
  what was studied, scores, what changed in the plan and why. Exportable to the user's
  Obsidian vault.

> **Design rules for the loop:**
> - The app and skill communicate **only through the shared data store + `recommendation.json`** —
>   no hidden state. Anyone (or any future tool) can read the files and understand exactly
>   where the user stands.
> - The loop must be **idempotent and re-runnable**: re-running the coach over the same
>   `attempts` yields the same recommendation. No randomness in the analysis.
> - **Never lose history.** Re-ingesting a newer question bank or recomputing `progress`
>   must preserve every past `attempt`. The longitudinal record *is* the learning signal.
> - The coach should detect and report **trend**, not just snapshot — "82% in Regulations,
>   up from 61% last week" is more useful than a bare number, and it's what tells the user
>   the loop is working.
> - **Readiness is loop output:** when fresh-question accuracy holds above the target
>   threshold across all 8 sections (≥70% for Basic, ≥80% for Honours), the coach flags
>   "book the exam" — the loop's terminal signal.

**Minimal interface sketch (illustrative — agent to finalize):**
```
# app writes:
attempts.append({id, section, sub, chosen, correct, ms, mode, ts})

# coach reads attempts + progress, writes:
recommendation.json = {
  generated_at, bank_version,
  readiness: {overall_pct, per_section{1..8}, trend, exam_ready: bool},
  next_session: {focus_sections[], new_count, review_count, tools[]},
  review_queue: [question_ids...],   # spaced-repetition order
  rationale: "why this session — weakest subsections, recent regressions"
}

# coach also appends journal/YYYY-MM-DD.md (narrative + scores + plan delta)
# app reads recommendation.json -> renders the dashboard's "next session"
```

---

## 6d. Adaptive learning engine (added 2026-06-13 — core design)

The user is **not a beginner in electronics** and explicitly does **not** want exhaustive,
one-size-fits-all coverage. The system must **adapt depth per section** to where the user
actually is — compress or test out of strong areas, go deep on weak ones — while never
creating blind spots against an exam that samples the *whole* 984-question bank.

This is a natural extension of the closed loop in §6c. **It is deterministic** (it lives in
the engine, not the LLM); the AI layer only *explains* and *condenses*, it never decides
tiers or scores.

### 6d.1 Diagnostic placement (calibration)
- On first entering a section, the app serves a short **diagnostic probe**: ~6–10 questions
  sampled to span that section's subsections. Optionally a one-time global placement test
  across all 8 sections up front.
- The user may **self-declare confidence** per section ("I know this cold" / "rusty" /
  "new"). This *seeds a prior* only; measured performance always overrides self-report.
- The engine scores the probe and assigns a starting **depth tier** (below).

### 6d.2 Depth tiers (per section, re-evaluated continuously)
| Tier | Entry signal | Lesson depth | Drill volume | Spacing |
|---|---|---|---|---|
| **Test-out** | ≥90% on diagnostic, fast + confident | skipped | none up front; periodic maintenance probes only | long |
| **Light** | ~75–90% | condensed AI summary of only the missed subsections | few, targeted at gaps | medium |
| **Standard** | ~50–75% | full original lesson + interactive tool | normal | normal |
| **Deep** | <50%, or slow+wrong | full lesson + extra AI worked examples + explanation on every miss | high | short |

Tiers are **not fixed**: the engine re-evaluates after each session from the `attempts`
log. A test-out section that later shows decay drops back to Light/Standard (trend-aware,
per §6c).

### 6d.3 Adaptive difficulty *within* a section (the "adaptive question bank")
Use a lightweight **Elo / IRT-lite** model — deterministic given the attempt log:
- Each **question** carries a difficulty `b` (starts at the section mean; updated online
  from the user's hits/misses and response time).
- The **user** has an ability estimate `θ` per section (and optionally per subsection).
- The drill engine **serves questions near the user's current θ** to hold them in the
  productive zone (~70–85% success) — harder as θ rises, easier when struggling.
- Weak subsections are pulled forward; mastered ones are spaced out (ties into §6c's SR
  queue). This solves the cold-start problem with no external difficulty data: difficulty
  and ability co-calibrate from the user's own responses.

### 6d.4 Coverage guarantee (anti-blind-spot rule — non-negotiable)
Because the real exam draws from the entire bank, **adaptivity may compress but never fully
skip.** Readiness requires BOTH:
1. fresh-question accuracy **≥80% in every one of the 8 sections** (Honours bar), AND
2. a **minimum coverage threshold** — every subsection probed with fresh questions at least
   once within a recency window (so a "test-out" section is still verified, not assumed).

Until both hold, the engine will not flag "book the exam." This keeps the adaptivity honest.

### 6d.5 Deterministic vs AI split for adaptivity
- **Deterministic engine:** scoring diagnostics, assigning/adjusting tiers (threshold
  rules), the Elo/IRT-lite difficulty + ability updates, question selection, coverage
  tracking, readiness. Same `attempts` in ⇒ same decisions out.
- **AI layer (Anthropic API):** condensing lesson text to the chosen depth, generating
  extra worked examples for Deep tier, explaining *why* a specific miss happened, and
  narrating tier changes ("you tested out of Circuit Components — we'll just keep it warm
  with occasional review").

### 6d.6 AI-adapted content from a curated local corpus (decided 2026-06-13)
The displayed lesson/explanation content **adapts to the user's drill & exam results**, and
the AI draws on a **curated local reference corpus** to ground what it writes. This extends
§6d.5 — it does **not** move any decision into the LLM.

- **Corpus = curated + local (not live web scraping).** Source material is downloaded once
  into `references/` and indexed (retrieval-augmented generation). Freely-usable Government
  works — the **question bank, RIC-3, RIC-1, RBR-4, the formula sheets** — are grounding
  fodder; community/course material (UWARC, HamStudy, VE3FCQ, …) may be used to ground and
  is **cited/linked, never reproduced** (constitution §3 — original text only). The user can
  drop new PDFs into `references/` and re-index. Keeps data local (constitution §4).
- **Engine diagnoses, AI writes.** The deterministic engine decides *what* (weak
  subsections, depth tier, what to drill/review); the AI generates the *content shown* to fit
  that — a "Tuned for you" lesson block at the tier's depth, per-miss explanations, and the
  plain-language "Today's session" text. Retrieval grounds it; output is original prose.
- **Generate-on-demand + cache.** AI-adapted content is cached keyed by (section, subsection,
  depth tier, a hash of the user's miss-profile, `bank_version`, prompt-version); regenerate
  only when that key changes. Prompt-cache the corpus. Respect the `usage` budget guard.
- **Base lessons are the fallback.** The hand-written original lessons (`app/content/`)
  always render; the AI layer is enrichment on top, so the app degrades gracefully when the
  monthly AI budget is hit or it's offline (constitution requires this).

---

## 7. Data model

Single source of truth, file- or SQLite-based (keep it simple and portable).

**`questions`** (ingested from the official ISED bank):
```
id            TEXT  PK   -- e.g. "B-005-002-003"
section       INT        -- 1..8 (derive from ID)
subsection    INT
text          TEXT
options       JSON       -- ["...","...","...","..."]
correct_index INT
bank_version  TEXT       -- effective date of the source bank (e.g. "2025-07-15")
notes         TEXT       -- optional original explanation written by the coach
difficulty_b  REAL       -- IRT-lite difficulty (§6d.3); starts at section mean, updated online
```

**`attempts`** (every answer the user gives — the loop's ground-truth event log; append-only):
```
id, question_id, section, subsection, answered_at, chosen_index,
correct BOOL, response_ms, mode (drill|exam|review)
```

**`progress`** (derived/cached): per-section + per-subsection mastery %, trend, last-seen,
ease/interval per question for spaced repetition, **plus the adaptive state (§6d):** depth
`tier` per section (test-out/light/standard/deep), ability `θ` per section/subsection, and
per-subsection coverage recency (for the §6d.4 coverage guarantee).

**`diagnostics`** (§6d.1): each placement/diagnostic probe — section, questions served,
score, resulting tier, timestamp, and any self-declared confidence prior. Append-only.

**`usage`** (AI budget guard, §0.1): each Anthropic API call — timestamp, model, input/
output tokens, estimated cost, call type (explain/diagnose/narrate/condense). The engine
sums month-to-date cost and blocks further AI calls once the monthly ceiling (~$15) is hit,
degrading gracefully to deterministic-only.

**`content_cache`** (§6d.6): AI-adapted content generated from the local corpus, cached so
it's regenerated only when the user's state changes. Columns: `cache_key` (hash of section/
subsection + depth tier + miss-profile hash + `bank_version` + prompt-version), `kind`
(lesson|explanation|session), `section`, `body` (original generated markdown/HTML), `sources`
(JSON of corpus refs cited), `model`, `generated_at`. Lookup by `cache_key`; miss ⇒ generate
(if budget allows) and insert. The curated corpus itself lives as files in `references/` plus
a lightweight index (chunked text); it is not user data and need not live in SQLite.

**`recommendation`** (the coach's output channel back to the app — see 6c): next-session
plan, focus areas, review queue, readiness. Stored as a versioned, human-readable
`recommendation.json` so it doubles as documentation.

**`journal`** (markdown entries the coach writes each loop cycle): date, sections covered,
scores, plan changes + rationale — exportable to Obsidian.

> Ingest pipeline: download official bank → parse to `questions` rows → store
> `bank_version`. Re-running ingest with a newer bank should upsert by `id` and update
> `bank_version`, never silently dropping the user's `attempts` history.

---

## 8. Recommended tech stack & hosting

Tuned to the user's environment (Proxmox/R730 homelab, comfortable with containers,
reverse proxy, NAS-backed storage). **Stack is now locked — see §0.2.**

- **App (LOCKED, §0.2):** **FastAPI (Python) backend + SQLite + a vanilla-JS / SVG
  client**, single self-contained container. One backend language matching the
  `canadian-ham-exam` parser; no heavy JS build toolchain; interactive concept tools are
  self-contained client-side JS + SVG. HTMX acceptable for the app shell if preferred.
  (The earlier Next/Svelte option is superseded.)
- **AI backend (§0.1):** Anthropic API via a swappable `AIProvider` interface; API key in
  env/secrets, never in the repo. **Default model: Opus** (current Opus 4.8) for clarity;
  journal narrative may optionally route to Haiku. **Build an in-app budget guard:** log
  tokens + cost to a `usage` table, enforce a **monthly ceiling (~$15)**, and fall back to
  deterministic-only when exceeded. Also set a spend limit in the Anthropic Console. Use
  prompt caching for the reference docs. (Cost detail in `QUESTIONS.md`.)
- **Storage:** **SQLite** file on NAS-backed volume (simple, portable, single-user). No
  need for Postgres at this scale.
- **Packaging / hosting (LOCKED 2026-06-13 — keep it as simple as possible):** ship a
  **Dockerfile** + `docker-compose.yml`; run as **one container inside a single Proxmox
  LXC**. **No reverse proxy, no Cloudflare.** The app binds to its port on the LXC's LAN IP;
  the user reaches it by **hostname via local DNS**, and remotely over **VPN back home**.
  Restrict to LAN/VPN only. Simplicity is a feature here — don't add ingress complexity.
- **Coach skill:** runs in Cowork / Claude Code; reads the same SQLite (or a synced
  JSON export) to make recommendations. Can run interactively or headless on cron for a
  daily "here's today's session" note dropped into the Obsidian pipeline.
- **Ingest:** Python script (reuse/adapt `canadian-ham-exam`) → SQLite.

---

## 9. Phased build plan (work in order)

> Use the user's spec-driven pattern: for each phase, write a short spec, plan, tasks,
> then implement. Log progress as you go (Section 10).

**Phase 0 — Research & ground-truthing**
- [ ] Fetch and verify every URL in Section 5. Note any dead links + find replacements.
- [ ] Download the **current** Basic question bank; record its effective date.
- [ ] Download RIC-3, RBR-4, and the Basic formula/aid sheets into a `references/` folder.
- [ ] Skim `canadian-ham-exam` and HamStudy's pool format; decide on the parser approach.

**Phase 1 — Data foundation**
- [ ] Build the ingest script: official bank → `questions` table (with `bank_version`).
- [ ] Validate: question count per section, no missing correct answers, IDs parse cleanly.
- [ ] Stand up the SQLite schema (Section 7).

**Phase 2 — Quiz engine (MVP)**
- [ ] Per-section drilling + full 100-question mock exam (proportional sampling, 70% line).
- [ ] Record `attempts`; compute per-section mastery.
- [ ] Minimal dashboard.

**Phase 3 — Interactive learning layer**
- [ ] Build the concept tools in Section 6b, starting with **Ohm's Law, reactance/
  resonance, dB, SWR/impedance, wavelength↔frequency** (sections 4–6 first).
- [ ] Write **original** short lesson text per section (don't copy course PDFs).
- [ ] Wire "learn → interact → drill" flow per section.

**Phase 4 — Spaced repetition + review queue**
- [ ] Add ease/interval tracking; build the review queue surfacing missed questions.
- [ ] Formula-sheet trainer using the unlabelled aid sheet.

**Phase 5 — The coach skill + closing the loop**
- [ ] Author `SKILL.md` + references + `next_session.py` / `schedule.py`.
- [ ] Implement the analysis in 6c: read `attempts`, compute per-section/subsection
  mastery + **trend**, identify most-missed concepts and fast-wrong misconceptions.
- [ ] Write `recommendation.json` (next session, review queue, readiness) + append a
  `journal/` entry each cycle. Make the analysis idempotent (same input → same output).
- [ ] Have the app **read `recommendation.json`** and surface "today's session" on the
  dashboard — closing the app → coach → docs → app loop.
- [ ] Readiness detection ("book the exam") as the loop's terminal signal.

**Phase 6 — Package & deploy**
- [ ] Dockerfile + compose; deploy to R730; reverse-proxy + LAN/VPN-only access.
- [ ] Backup the SQLite to NAS. Document run/update steps in `README.md`.

**Phase 7 (later) — Advanced Qualification**
- [ ] Re-run ingest with the Advanced bank; reuse the engine; add Advanced-only tools.

---

## 10. Agent working files (create these in the repo)

Mirror the user's existing harness pattern so this drops into his workflow:

- **`README.md`** — what this is, how to run/update, deploy steps.
- **`AGENT.md`** — operating instructions for the build agent (scope, conventions,
  what not to touch).
- **`BACKLOG.md`** — the Section 9 plan as living tasks.
- **`LOG.md`** — append-only progress log (what was done each session).
- **`QUESTIONS.md`** — open questions for the human (see Section 11).
- **`constitution.md`** — project principles (interactive-first, original lesson text,
  data stays local, official bank is source of truth, never lose attempt history).

---

## 11. Open questions for the human (see QUESTIONS.md)

**Resolved 2026-06-13 (see §0):** ② target = **Basic with Honours, 80% bar**; ③ stack =
**FastAPI + SQLite + vanilla JS/SVG** (agent's call); AI backend = **Anthropic API**;
coach = **folded into app + thin optional skill**; build environment = **Claude Code**.

**Still open (deployment-time):**

1. **Target exam date?** None set yet — the coach proposes a cadence once it sees early
   scores. Provide one when ready to drive a firm schedule.
4. **Hosting target** — which R730 / LXC vs Docker, and which reverse-proxy hostname?
5. **Obsidian integration** — exact vault path for journal export (default: export to a
   dedicated folder the user can point Obsidian at, rather than writing into the vault).
6. **French questions** — **default English-only for v1**; confirm before adding the
   bilingual pool.

---

## 12. Appendix — quick facts to encode

- Pass: 70% of 100. Honours: 80%+ (unlocks below-30-MHz HF + max power).
- Question IDs: `B-AAA-BBB-CCC`; `AAA` maps to the 8 sections.
- The **unlabelled** formula/diagram sheet is permitted during the exam — train with it.
- Exam is administered by an **accredited examiner** (find via ISED's examiner search);
  the app is prep only — the user still books a real exam sitting.
- Bank is periodically revised — always show the user which bank version they're studying.

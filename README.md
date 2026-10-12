# Elmer — Canadian Basic + Advanced Amateur Radio trainer

A single-user, self-hosted study app to pass the **ISED Basic Amateur Radio
Qualification with Honours (80%)** — and, once you have, the **Advanced
Qualification** (`/advanced`, tracked completely separately). It pairs an interactive learning surface with a
coaching layer: a **deterministic engine** (mastery, adaptive difficulty, spaced
repetition, readiness — plain code, no LLM) and a **swappable AI layer** (Anthropic)
for explanations, misconception diagnosis, and the journal.

Stack: **FastAPI + SQLite + vanilla JS/SVG**, one Docker container, LAN/VPN-only.

> **Disclaimer.** I built this for my own use, to study for the Canadian Basic Amateur
> Radio exam, and I'm sharing it free for anyone to use. It is provided **"AS IS", with
> no warranties of any kind, express or implied** — including, without limitation,
> accuracy, currency, completeness, fitness for a particular purpose, or that using it
> will help you pass any exam. **Use at your own risk; the author accepts no liability**
> for any loss or damage arising from its use (see `LICENSE`).
>
> This is a **personal, unofficial** tool — **not affiliated with, endorsed by, or
> sponsored by** Innovation, Science and Economic Development Canada (ISED), Radio
> Amateurs of Canada (RAC), or any club or organization. It is **not a substitute for
> the official ISED study materials and regulations**; always confirm against the
> current official sources. The ISED question bank and reference documents are works of
> the Government of Canada obtained from public sources; the author **claims no ownership
> of that content**, and all rights and trademarks remain with their respective owners.
> Nothing here is legal advice.

---

## What it does

- **Two qualifications, two tracks.** Basic lives at `/`, Advanced at `/advanced`
  (topbar switcher; amber accent so you always know which). Each has its own bank,
  SQLite store, attempts/mastery/tiers, journal, recommendation and explanation seed —
  nothing mixes. Advanced: 7 sections, 50-question mock (70% pass line, 80% training
  target), an Advanced formula-sheet trainer, and deeper per-question explanations
  (derivations + worked examples).
- **Learn → Interact → Drill** per syllabus section (`/section/{n}`): an original
  short lesson, interactive SVG concept tools, then real ISED bank questions.
- **8 concept tools** (themed from `tokens.css`): Ohm's law/power, reactance &
  resonance, decibels, SWR/impedance, wavelength↔frequency, series/parallel R&C,
  Canadian band-plan explorer, propagation & the ionosphere.
- **Quiz engine:** per-section drill, **100-question mock exam** (section-proportional,
  70% pass + 80% Honours lines, timer), and a **spaced-repetition review queue**
  (Leitner). Every answer is graded server-side and appended to `attempts`.
- **Adaptive engine:** per-section diagnostic placement → depth tier
  (test-out / light / standard / deep) via Elo/IRT-lite ability θ; drills serve the
  ~75% productive zone; a coverage guarantee prevents blind spots.
- **Dashboard:** exam-readiness %, stat cards, an inline **journal week-strip**, a
  **"Today's session"** recommendation, and per-section **S-meters** colored by tier.
- **AI layer:** instant **batch-generated structured explanations** for every
  question (cache-first, revealed to a depth set by your tier), a live
  **"why do I keep missing this?"** diagnosis per section, and an AI-written
  **journal**. All budget-guarded; degrades to deterministic when no key / over budget.
- **Formula-sheet trainer** (`/formula-trainer`) for the exam-legal unlabelled sheet.

**Readiness ("book the exam") fires only when fresh-question accuracy is ≥80% in
every one of the 8 sections AND every subsection has been probed.**

---

## Run locally (dev)

```bash
pip install -r requirements.txt

# Build the DBs from the free ISED banks + the committed explanation seeds:
python -m app.db.fetch_sources          # downloads both banks into references/ (English-only)
python -m app.db.ingest                 # Basic: parse -> questions (984), bank_version from the PDF
python -m app.db.validate               # asserts count==984, ids/sections/options sane
python -m app.coaching.explain_batch import            # seed/explanations.jsonl
python -m app.db.ingest --qual advanced                # Advanced -> data/hamstudy_advanced.db
python -m app.db.validate --qual advanced
python -m app.coaching.explain_batch --qual advanced import   # seed/explanations_advanced.jsonl

uvicorn app.main:app --reload           # http://127.0.0.1:8000  (+ /advanced)
python tests/smoke_test.py              # end-to-end check, both tracks (throwaway DB copies)
```

`ANTHROPIC_API_KEY` (in a gitignored `.env`) is **optional** — without it the app runs
on the deterministic engine + the cached explanations; the live diagnose/journal calls
degrade gracefully. Paths/models are env-overridable (see `app/config.py`).

---

## Deploy (Proxmox LXC, LAN/VPN-only)

One command on a fresh Debian/Ubuntu LXC — installs Docker, builds the image,
reconstructs the DB (bank + committed seed, **no paid re-batch**), starts on port 80,
and registers a systemd unit so it comes up on boot:

```bash
git clone https://github.com/TuringCompote/HamStudy /opt/elmer && cd /opt/elmer
sudo PORT=80 ./deploy/install.sh
```

Reach it at `http://<lxc-ip-or-fqdn>:80` via local DNS, or over the home VPN. No reverse
proxy / Cloudflare — restrict at the LXC/VPN layer. Details in `AGENT.md` § Deploy & ops.

- **UI tweaks** (`app/static`, `app/templates`, `app/content` are mounted): `git pull`
  applies CSS/JS live; templates need `docker compose restart elmer`.
- **Code changes** (anything under `app/*.py`): `git pull && docker compose up -d --build`.
- **Backups:** `python -m app.db.backup --dest /mnt/nas/elmer-backups` (online, WAL-safe;
  cron example in `AGENT.md`).
- **Spend:** set a hard monthly limit in the Anthropic Console — the in-app `usage`
  guard ($15/mo default) covers live calls but not one-time batch generation.

---

## Project layout

```
app/
  main.py            FastAPI routes + JSON API, mounted at / (Basic) and /advanced
  quals.py           qualification profiles: sections, bank, paths, tools — the active one is a ContextVar
  config.py          env-driven settings (paths, AI models, budget, APP_NAME)
  tools.py           section -> concept-tool map      formulas.py  formula-trainer data
  db/                schema.sql · init_db · ingest · validate · fetch_sources · queries · backup
  engine/            deterministic: mastery · adaptive(θ) · scheduler(Leitner) · readiness
                     · analysis(trend/miss) · diagnostic(placement) · recommend · coach
  coaching/          AI: ai_provider(+stub) · anthropic_provider · usage(budget) · corpus(RIC)
                     · explain_batch(batch+seed) · journal · prompts(loader)
  content/sections/  original lesson markdown (Basic 1–8) · sections_advanced/ (Advanced 1–7)
  static/            tokens.css · style.css · quiz.js · journal.js · tools/*.js
  templates/         base · dashboard · section · quiz · formula_trainer
prompts/             explain · diagnose · narrate · condense · batch_explain  (Console-tunable)
seed/explanations.jsonl           committed Basic explanations (Opus batch; rebuilds the DB on deploy)
seed/explanations_advanced.jsonl  committed Advanced explanations (deeper; written in-session)
deploy/              install.sh · elmer.service          tests/  smoke_test.py
docs/ai-evals/       AI model comparison + eval cases (Console Evaluation tool)
Dockerfile · docker-compose.yml · requirements.txt
data/ (gitignored: SQLite, recommendation.json, journal/)   references/ (gitignored downloads)
```

## Core invariants (see `constitution.md`)

- Official ISED bank = source of truth; always record `bank_version`; re-ingest upserts by
  `id` and **never drops `attempts`** (append-only event log).
- The mastery/tier/scheduling/readiness path is **deterministic + idempotent** — no LLM.
- AI is for explanation/diagnosis/narrative only, and writes **original** text (grounds on
  reference docs, never reproduces them). All live calls are budget-guarded.
- Data stays local; secrets come from env, never the repo.

## Roadmap (not yet built)

Trend/decay window on tiers · tier-scaled lesson depth + a "tuned for you" condensed-lesson
cache (`content_cache`) · optional read-only Cowork deep-dive skill · Advanced-specific
concept tools (filters/Q, modulation envelopes, Smith-chart matching).

## License

Original code: **MIT** (see `LICENSE`) — provided "as is", no warranty. The ISED question
bank and reference documents are public Government of Canada works and are not covered by
that license; the author claims no ownership of them.

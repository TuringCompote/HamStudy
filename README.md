# HamStudy — Canadian Amateur Radio (Basic with Honours) training system

A single-user, self-hosted study system targeting the ISED **Basic Amateur Radio
Qualification with Honours (80%)**. An interactive web app (the learning surface)
plus a coaching layer — a **deterministic engine** (mastery, trend, spaced
repetition, adaptive difficulty, readiness; idempotent, no LLM) and an **AI layer**
(Anthropic API, behind a swappable `AIProvider`) for explanations and journaling.

> Authoritative docs: `ham-radio-training-build-spec.md` (read §0 first),
> `constitution.md`, `AGENT.md` (= build-agent manual), `BACKLOG.md`, `LOG.md`.

## Status
- **Phase 0** (research/ground-truthing) — done (`PHASE0-FINDINGS.md`).
- **Phase 1** (data foundation) — done: ingest + SQLite schema, **984/984**
  questions validated.
- **Phase 2+** — quiz engine, interactive tools, spaced repetition, the loop,
  deploy. See `BACKLOG.md`.

## Stack
FastAPI (Python) + SQLite + vanilla JS/SVG, shipped as a single container.
LAN/VPN-only. SQLite on a NAS-backed volume in production.

## Layout
```
app/
  config.py            # paths/settings from env (no hardcoded secrets/hosts)
  db/
    schema.sql         # SQLite schema (spec §7)
    init_db.py         # apply schema (idempotent)
    ingest.py          # parse official ISED bank PDF -> questions table
    validate.py        # assert count==984, ids/sections/options sane
    fetch_sources.py   # re-download source material into references/
references/            # downloaded ISED material (git-ignored; not redistributed)
data/                  # SQLite store (git-ignored)
```

## Setup & data load
```bash
pip install -r requirements.txt

# 1. Get the official question bank into references/ (English-only):
python -m app.db.fetch_sources
#    (or download manually to references/amateur_basic_questions_en.pdf)

# 2. Create schema + ingest + validate:
python -m app.db.ingest      # derives bank_version from the PDF title page
python -m app.db.validate    # exits non-zero if anything is off
```

Override locations via env: `HAMSTUDY_DB`, `HAMSTUDY_BANK_PDF`,
`HAMSTUDY_REFERENCES`.

## Key invariants (see `constitution.md`)
- The official ISED bank is the single source of truth; always record
  `bank_version`. Re-ingest **upserts by id** and **never drops `attempts`**.
- `attempts` is an append-only event log — the actual learning signal.
- The mastery/trend/scheduling/readiness path is deterministic; the LLM is only
  for explanation/diagnosis/narrative.
- Lesson text is original; source PDFs are referenced, not republished.
- Data stays local; secrets come from env, never the repo.

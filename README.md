# HamStudy — Canadian Amateur Radio (Basic with Honours) training system

A single-user, self-hosted study system targeting the ISED **Basic Amateur Radio
Qualification with Honours (80%)**. An interactive web app (the learning surface)
plus a coaching layer — a **deterministic engine** (mastery, trend, spaced
repetition, adaptive difficulty, readiness; idempotent, no LLM) and an **AI layer**
(Anthropic API, behind a swappable `AIProvider`) for explanations and journaling.

> Authoritative docs: `ham-radio-training-build-spec.md` (read §0 first),
> `constitution.md`, `AGENT.md` (= build-agent manual), `BACKLOG.md`, `LOG.md`.

## Status
- **Phase 0–1** — research + data foundation: ingest + SQLite schema, **984/984** validated.
- **Phase 2** — quiz engine: per-section drill + 100-Q proportional mock (70%/80% lines),
  `attempts`, deterministic mastery, dashboard.
- **Phase 3** — 8 interactive SVG concept tools + original lessons + Learn→Interact→Drill.
- **Phase 4 / 4.5** — spaced repetition (Leitner) + review queue + formula trainer; adaptive
  engine (diagnostic placement, depth tiers, Elo/IRT-lite θ, coverage guarantee).
- **Phase 5** — closed loop (`recommendation.json`) + Anthropic AI layer (budget guard,
  journal, prompts externalized, model routing) + **984 batch-generated structured
  explanations** with adaptive reveal; readiness = ≥80% fresh/section AND coverage.
- **Phase 6** — package & deploy (this section). See `BACKLOG.md` / `LOG.md`.

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

## Run the app (Phase 2)
```bash
uvicorn app.main:app --reload          # http://127.0.0.1:8000
python tests/smoke_test.py             # end-to-end API check (uses a throwaway DB copy)
```
Dashboard `/` shows per-section mastery + coverage and links to drills and the
100-question mock exam. Per-question grading happens server-side; every answer is
appended to `attempts`. Correct answers are never sent to the browser in the quiz
payload — only on submit.

## Deploy (Phase 6) — one container in a Proxmox LXC, LAN/VPN-only

> ⚠️ **Preserve `data/hamstudy.db`.** It holds the 984 questions, the **batch-generated
> explanations** (a one-time paid build), and your append-only `attempts`. Copy it into the
> deploy volume — do **not** start with an empty DB or re-run the batch.

```bash
# On the LXC (Docker + compose installed):
# 1. Put your built DB on the NAS-backed volume the compose mounts:
mkdir -p data && cp /path/to/hamstudy.db data/hamstudy.db

# 2. Secrets + optional bind/port (never commit .env):
#    ANTHROPIC_API_KEY=sk-ant-...
#    BIND_IP=10.0.0.42      # optional: bind to the LXC LAN IP (default: all interfaces)
#    PORT=8000
$EDITOR .env

# 3. Build + run:
docker compose up -d --build
docker compose ps           # healthcheck hits /api/health
```

Reach it at `http://<lxc-hostname>:8000` on the LAN, or over the home VPN remotely.
**No reverse proxy / no Cloudflare** — restrict access at the LXC/VPN layer.

**Set a hard spend limit in the Anthropic Console** (Billing → limits, e.g. $15/mo). The
in-app `usage` budget guard covers live study calls but NOT one-time batch generation.

**Backup the DB to the NAS** (cron on the LXC, online/WAL-safe):
```bash
0 3 * * *  cd /opt/elmer && docker compose exec -T elmer python -m app.db.backup --dest /mnt/nas/elmer-backups --keep 30
```

**Journal → Obsidian:** entries are plain Markdown in `data/journal/`. Point an Obsidian
vault (or a synced folder) at that directory; no special integration needed (QUESTIONS #11).

**Bank update (≈yearly):** re-run `fetch_sources` + `ingest` + `validate`, then regenerate the
explanation batch (new `bank_version`). Trim the RIC grounding / chunk the batch first to
control cost + rate limits (see `LOG.md`).

## Key invariants (see `constitution.md`)
- The official ISED bank is the single source of truth; always record
  `bank_version`. Re-ingest **upserts by id** and **never drops `attempts`**.
- `attempts` is an append-only event log — the actual learning signal.
- The mastery/trend/scheduling/readiness path is deterministic; the LLM is only
  for explanation/diagnosis/narrative.
- Lesson text is original; source PDFs are referenced, not republished.
- Data stays local; secrets come from env, never the repo.

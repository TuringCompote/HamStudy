# QUESTIONS.md — Decisions & open questions

## Resolved (2026-06-13, during spec refinement)

| # | Question | Decision |
|---|----------|----------|
| 1 | This session's scope | **Refine the spec only** — no app code. |
| 2 | Basic vs Basic with Honours | **Basic with Honours** — optimize to an **80% fresh-question bar** across all 8 sections. 70% = pass, 80% = ready. |
| 3 | Front-end / stack | Agent's call → **FastAPI + SQLite + vanilla JS/SVG**, single container. |
| 4 | AI backend location | **Anthropic API (Claude)**, behind a swappable `AIProvider`. Local model rejected for now (16 GB GPU → only ~8–14B quantized, too weak for tutoring/diagnosis). |
| 5 | Coach: separate skill vs folded | **Folded into the app** (deterministic engine + AI layer); thin **optional** read-only Cowork skill kept for deep-dives. |
| 6 | Build environment | **Claude Code** for the app build (Phases 1–7); **Cowork** for research (Phase 0) + the deep-dive skill. |
| 7 | Loop determinism | Core engine (mastery/trend/scheduling/readiness) is **deterministic code**; AI only for explanations/narrative. |
| 8 | Adaptive depth | **Yes** — per-section diagnostic → depth tiers (test-out/light/standard/deep) + Elo/IRT-lite adaptive difficulty, with a hard coverage guarantee so no blind spots. (Spec §6d.) |

## Resolved 2026-06-13 (second pass)

| # | Question | Decision |
|---|----------|----------|
| 9 | Target exam date | **Within 2026** (soft target ~Q4 2026). Coach builds cadence backward from year-end; tightens once it sees early scores. No hard date yet. |
| 10 | Hosting | **Single LXC on Proxmox, one container, simplest possible.** Accessed by hostname via **local DNS**; remote access over **VPN to home** — **no Cloudflare, no reverse proxy.** App binds to its LAN port; LAN/VPN-only. |

## Resolved 2026-06-13 (third pass)

| # | Question | Decision |
|---|----------|----------|
| 11 | Obsidian integration | **Not needed — `.md` is `.md`.** Journal writes plain Markdown files to a folder; no special vault integration. Point Obsidian at the folder if/when desired. |
| 12 | French bilingual pool | **English-only.** Do not ingest `..._fr.PDF`. |
| 13 | Claude model | **Opus** (current: Opus 4.8) for maximum clarity in explanations/diagnosis. Routine journal narrative *may* optionally route to Haiku to trim cost, but Opus is the default. |
| 14 | Placement style | **Per-section, just-in-time** diagnostic on first entering a section; self-declare "I know this" to test out faster. |
| 15 | API key + spend cap | Set up an Anthropic API account + key; enforce a **monthly spend ceiling** in the Anthropic Console **and** an in-app budget guard. **Recommended ceiling: $15/month** (realistic usage is a few $/month — see note). |

## API cost & budget guard (Phase 5 detail)

Current Anthropic pricing (per million tokens, verified 2026-06-13): **Opus 4.8 = $5 in /
$25 out**, Sonnet 4.6 = $3/$15, Haiku 4.5 = $1/$5. Prompt caching cuts cached input ~90%;
batch is 50% cheaper.

**Realistic cost for this app:** the AI layer fires only on misses, lesson condensation, and
the journal narrative — roughly **$0.20–0.50 per heavy study session** on Opus. Daily study
for ~3 months ≈ **$30–45 total**. A **$15/month** ceiling is comfortable headroom.

**Setup steps (Phase 5):**
1. Create an account at `console.anthropic.com`; add a payment method (prepaid credits work).
2. In the Console billing/limits settings, set a **monthly spend limit** (e.g. $15).
3. Create an API key; store it in the LXC env / `.env` — **never in the repo**.
4. **In-app budget guard (build this):** log every call's tokens + estimated cost to a
   `usage` table; before each call, check month-to-date spend vs the ceiling; if exceeded,
   **skip the AI call and fall back to deterministic-only** (queue the explanation, show
   "AI budget reached this month"). The core loop keeps working regardless.
5. Use **prompt caching** for the RIC reference docs to cut repeat input cost.

## Still open — minor, decide at the relevant phase
- None blocking. (Optional: route journal-narrative calls to Haiku to shave cost — default
  keeps everything on Opus.)

# constitution.md — Project principles

Non-negotiable principles for the Canadian Amateur Radio (Basic with Honours) training
system. When a design choice is ambiguous, these decide it. The full spec is
`ham-radio-training-build-spec.md`; the decisions in its §0 sit on top of these.

## 1. Interactive learning over rote drilling
The differentiator is *manipulating* concepts, not multiple-choice grinding — especially
for electronics and theory (syllabus sections 4–8). Every theory concept that can be
visualized should have a tool where the user changes inputs and immediately sees results.
A section is not "done" when it has questions; it is done when it has **Learn → Interact →
Drill**.

## 2. The official ISED question bank is the single source of truth
Questions, answers, and the `B-AAA-BBB-CCC` ID scheme come from the current official bank.
Always record `bank_version` (effective date). Never hand-edit question content. Re-ingest
the newer bank by upserting on `id` — never silently dropping rows or, critically, the
user's attempt history.

## 3. Original lesson text only — never republish course material
Community PDFs (UWARC, hamshack.ca, VE3FCQ, CLARS, etc.) are *reference for the user's
personal study and for the agent's understanding* — link to them, don't copy their prose
into the app. Lesson summaries in the app are written fresh. The app stays private and
self-hosted.

## 4. Data stays local
Single-user, self-hosted on the user's homelab, LAN/VPN-only. SQLite on NAS-backed storage.
The only data that leaves the LAN is what the Anthropic API call requires (question text +
miss patterns for explanation/diagnosis) — accepted by the user, and isolated behind the
`AIProvider` interface so it can be swapped for a local model later.

## 5. The loop core is deterministic; AI is for explanation only
Mastery %, trend, spaced-repetition scheduling, next-section selection, and readiness are
**plain code and idempotent**: the same `attempts` log always yields the same
recommendation. No LLM in that path. The Anthropic API is used only for generative work —
explanations, misconception diagnosis, journal narrative, plain-language session framing —
where nondeterminism is fine.

## 6. Never lose history
`attempts` is an append-only event log and is the actual learning signal. Wrong answers are
the most valuable data. Recomputing `progress` or re-ingesting a bank must preserve every
past attempt. Back up the SQLite to NAS.

## 7. No hidden state — everything is inspectable
The app and any external reader communicate only through the shared store +
`recommendation.json`. State lives in human-readable files/tables, not locked inside a
model's head. Anyone (or any future tool) can read the files and know exactly where the
user stands.

## 8. Report trend, not just snapshots
"82% in Regulations, up from 61% last week" beats a bare number — it tells the user the
loop is working. Readiness is loop output: when fresh-question accuracy holds **≥80% across
all 8 sections** (the Honours bar), flag "book the exam."

## 9. Build where the work fits the tool
Claude Code for the iterative software build (Phases 1–7). Cowork for research/ground-
truthing and the thin deep-dive skill. The spec and working files are tool-portable;
`AGENT.md` = `CLAUDE.md`.

## 10. Adapt depth; never create blind spots
The user is experienced — adapt per section (diagnose, then test-out / light / standard /
deep) and serve questions at the right difficulty rather than drilling everything equally.
But the real exam samples the whole 984-question bank, so **adaptivity may compress, never
fully skip**: readiness requires ≥80% in every section *and* minimum fresh-question coverage
of every subsection. Tiering and difficulty are **deterministic** (engine, not LLM); AI only
condenses and explains. (Full design: spec §6d.)

## 10b. Precompute explanations; reserve live AI for the personal
Explanations of why an answer is right/wrong are the same for everyone, so **batch-generate
them once for the whole bank** (Message Batches API, 50% off, + prompt caching) and store
them — instant and ~free at study time. Reserve *live* Claude calls for what's genuinely
per-user and real-time: misconception diagnosis and journal narrative. Regenerate the batch
only when the bank revises. This never touches the deterministic loop. (Spec §6f.)

## 11. Spec-driven, logged, reversible
For each phase: short spec → plan → tasks → implement. Append progress to `LOG.md`. Keep
changes small and committed. Design for Advanced Qualification later, but Basic-with-Honours
ships first.

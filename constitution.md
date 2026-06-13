# constitution.md — non-negotiable principles

When a design choice is ambiguous, these decide it. Context lives in `README.md`
(what/how) and `AGENT.md` (how it's built / how to extend).

1. **Interactive over rote.** Every theory concept that can be visualized has a tool
   where you change inputs and see results — especially electronics/antennas/theory. A
   section is done only with **Learn → Interact → Drill**.

2. **The official ISED bank is the single source of truth.** Questions, answers, and the
   `B-AAA-BBB-CCC` ID scheme come from the current official bank. Always record
   `bank_version`. Never hand-edit question content. Re-ingest upserts by `id`.

3. **Original text only.** Lessons and AI output are written fresh. Reference docs
   (RIC/RBR, community guides) inform accuracy and are cited/linked — never reproduced.

4. **Data stays local.** Single-user, self-hosted, LAN/VPN-only; SQLite on NAS-backed
   storage. The only data leaving the LAN is what an AI call needs (question text + miss
   patterns), isolated behind `AIProvider` so a local model can replace it later.

5. **The loop core is deterministic; AI is for explanation only.** Mastery, trend,
   spaced-repetition scheduling, tiering, selection, and readiness are plain, idempotent
   code: same `attempts` ⇒ same recommendation. No LLM in that path.

6. **Never lose history.** `attempts` is an append-only event log and the real learning
   signal. Recomputing or re-ingesting must preserve every past attempt. Back up to NAS.

7. **No hidden state.** App and any reader communicate only through the shared store +
   `recommendation.json`. State lives in human-readable files/tables, not a model's head.

8. **Report trend, not just snapshots.** "82%, up from 61% last week" beats a bare number.
   Readiness is loop output: flag "book the exam" when fresh-question accuracy holds
   **≥80% across all 8 sections AND every subsection has been probed**.

9. **Adapt depth; never create blind spots.** Diagnose per section, then test-out / light /
   standard / deep, serving questions at the right difficulty. The exam samples the whole
   984-question bank, so adaptivity may compress but **never fully skip**. Tiering and
   difficulty are deterministic; AI only condenses and explains.

10. **Spend is guarded.** Live AI calls log cost and respect a monthly ceiling, degrading to
    deterministic-only when exceeded. The core loop works regardless of AI availability.

11. **Spec-driven, logged, reversible.** Short steps, committed; append to `LOG.md`. Design
    for Advanced Qualification later, but Basic-with-Honours is the product.

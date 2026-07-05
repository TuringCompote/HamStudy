# evals/ai_layer — AI layer evals

Six real ISED-bank "miss" cases (electronics, antennas, regulations) plus two
journal-narration cases, each with an original *ideal output*, for comparing
models in the **Anthropic Console Evaluation tool** and confirming the
per-call-type model routing.

## Files
- `cases.jsonl` — one JSON object per line:
  - `id`, `call_type` (`explain` or `narrate`)
  - explain cases: `section`, `question`, `options`, `correct_index`, `chosen_index`,
    `needs_grounding` — `true` for regs sections (1/2); attach the RIC/RBR grounding (below)
  - `input` — the exact user message the app sends (mirrors `AnthropicProvider.explain`
    / `.narrate`; narrate inputs carry the deterministic day digest JSON)
  - `ideal_output` — the golden text to grade against

## How to run in the Console
1. **System prompt:** paste `prompts/explain.md` for explain cases, `prompts/narrate.md`
   for narrate cases (the files the app loads at runtime).
2. **Dataset:** import `cases.jsonl`; map `input` → the user message, `ideal_output` → the
   ideal/golden column.
3. **Grounding (regs cases, `needs_grounding: true`):** prepend the relevant reference text
   as a second system block — the app uses `app/coaching/corpus.ground_for_section()`
   (RBR-4 + RIC-3 for §1, RIC-3 for §2). For a quick Workbench test, paste an excerpt of
   `references/_corpus/rbr4.txt`. Electronics/antenna cases need no grounding.
4. **Compare models:** run the dataset on `claude-opus-4-8`, `claude-sonnet-4-6`, and
   `claude-haiku-4-5`. Grade for: factual correctness, naming the *why* (not just the answer),
   concision (2–4 sentences), and **no copied reference prose**.

## What we expect this to confirm
- **explain/diagnose stay on Opus** — these require correct technical reasoning and accurate
  grounding; Haiku tends to miss the subtle "why" (e.g. the Z₀-ratio point, X_C vs X_L).
- **narrate needs Sonnet since the day-digest switch (2026-07)** — the journal no longer
  just phrases a plan; it reasons over the digest (miss THEMES from question texts,
  fresh-accuracy deltas, exam score vs the 70/80 lines) and must never invent numbers.
  Grade narrate for: leads with what happened, names a concrete miss theme, flags
  fast-wrong as confident-but-wrong, no fabricated facts, no generic cheerleading.
  Haiku remains available via `HAMSTUDY_MODEL_NARRATE` if the evals say it's enough.

Routing lives in `app/config.py` (`AI_MODELS`); change it per type via env
(`HAMSTUDY_MODEL_EXPLAIN`, `HAMSTUDY_MODEL_NARRATE`, …) once the evals back a choice.

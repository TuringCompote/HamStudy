-- HamStudy — SQLite schema (spec §7)
-- Single source of truth for the question bank + the user's progress/journal.
-- Design rules: `attempts` is append-only (constitution §6); the deterministic
-- engine derives `progress` from it. Re-ingest upserts `questions` by id and
-- never touches `attempts`. JSON is stored as TEXT (validate at write time).

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- key/value meta: schema_version, last ingest timestamps, etc.
CREATE TABLE IF NOT EXISTS meta (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL
);

-- ingested from the official ISED Basic question bank
CREATE TABLE IF NOT EXISTS questions (
    id            TEXT PRIMARY KEY,        -- "B-AAA-BBB-CCC"
    section       INTEGER NOT NULL,        -- 1..8 (AAA)
    subsection    INTEGER NOT NULL,        -- BBB
    qnum          INTEGER NOT NULL,        -- CCC
    text          TEXT NOT NULL,           -- question stem
    options       TEXT NOT NULL,           -- JSON array of 4 strings
    correct_index INTEGER NOT NULL,        -- 0..3
    bank_version  TEXT NOT NULL,           -- effective date of source bank (e.g. "2025-08-26")
    notes         TEXT,                    -- optional ORIGINAL explanation (coach-written)
    difficulty_b  REAL,                    -- IRT-lite difficulty (§6d.3); NULL until calibrated
    CHECK (section BETWEEN 1 AND 8),
    CHECK (correct_index BETWEEN 0 AND 3)
);
CREATE INDEX IF NOT EXISTS idx_questions_section ON questions(section, subsection);

-- every answer the user gives — the loop's ground-truth event log. APPEND-ONLY.
CREATE TABLE IF NOT EXISTS attempts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id  TEXT NOT NULL REFERENCES questions(id),
    section      INTEGER NOT NULL,
    subsection   INTEGER NOT NULL,
    answered_at  TEXT NOT NULL,            -- ISO-8601 UTC
    chosen_index INTEGER NOT NULL,         -- 0..3
    correct      INTEGER NOT NULL,         -- 0/1
    response_ms  INTEGER,
    mode         TEXT NOT NULL CHECK (mode IN ('drill','exam','review','diagnostic'))
);
CREATE INDEX IF NOT EXISTS idx_attempts_q   ON attempts(question_id);
CREATE INDEX IF NOT EXISTS idx_attempts_sec ON attempts(section, subsection);
CREATE INDEX IF NOT EXISTS idx_attempts_ts  ON attempts(answered_at);

-- derived/cached engine state (mastery, trend, SR scheduling, adaptive tier/θ,
-- coverage recency). Keyed by scope so one table serves section/subsection/question.
-- Owner: the deterministic engine (recomputed from `attempts`; safe to rebuild).
CREATE TABLE IF NOT EXISTS progress (
    scope_type   TEXT NOT NULL CHECK (scope_type IN ('section','subsection','question')),
    scope_id     TEXT NOT NULL,           -- e.g. "5", "5-002", or "B-005-002-003"
    mastery_pct  REAL,
    trend        TEXT,                    -- 'improving' | 'plateaued' | 'regressing'
    tier         TEXT,                    -- §6d.2: 'test-out'|'light'|'standard'|'deep' (section scope)
    theta        REAL,                    -- §6d.3 ability estimate
    ease         REAL,                    -- SR (question scope)
    interval_days INTEGER,                -- SR (question scope)
    last_seen    TEXT,                    -- ISO-8601
    last_fresh   TEXT,                    -- §6d.4 coverage recency (last fresh-question probe)
    updated_at   TEXT,
    PRIMARY KEY (scope_type, scope_id)
);

-- §6d.1 placement/diagnostic probes. APPEND-ONLY.
CREATE TABLE IF NOT EXISTS diagnostics (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    section            INTEGER NOT NULL,
    served_ids         TEXT NOT NULL,     -- JSON array of question ids
    score              REAL NOT NULL,
    resulting_tier     TEXT NOT NULL,
    confidence_prior   TEXT,              -- self-declared: 'cold'|'rusty'|'new' (seeds prior only)
    created_at         TEXT NOT NULL
);

-- AI budget guard (§0.1 / QUESTIONS.md). One row per Anthropic API call.
CREATE TABLE IF NOT EXISTS usage (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    ts            TEXT NOT NULL,
    model         TEXT NOT NULL,
    input_tokens  INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    est_cost_usd  REAL NOT NULL,
    call_type     TEXT NOT NULL CHECK (call_type IN ('explain','diagnose','narrate','condense'))
);
CREATE INDEX IF NOT EXISTS idx_usage_ts ON usage(ts);

-- coach output channel back to the app (§6c). Versioned, human-readable JSON
-- blobs; the latest row is what the dashboard renders. Also mirrored to
-- recommendation.json on disk so it doubles as documentation.
CREATE TABLE IF NOT EXISTS recommendation (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    generated_at  TEXT NOT NULL,
    bank_version  TEXT NOT NULL,
    payload       TEXT NOT NULL            -- JSON: readiness, next_session, review_queue, rationale
);

-- batch-generated structured explanations (spec §6f). One row per question per
-- bank_version; `layers` is the structured-JSON superset (core/distractors/concept/
-- misconception/link/mnemonic/edge_cases). explain() reads this cache-first.
CREATE TABLE IF NOT EXISTS explanations (
    question_id   TEXT NOT NULL REFERENCES questions(id),
    bank_version  TEXT NOT NULL,
    model         TEXT NOT NULL,
    layers        TEXT NOT NULL,            -- JSON superset
    generated_at  TEXT NOT NULL,
    PRIMARY KEY (question_id, bank_version)
);

-- index of narrative journal entries (markdown lives on disk, exportable to Obsidian).
CREATE TABLE IF NOT EXISTS journal (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_date    TEXT NOT NULL,
    file_path     TEXT NOT NULL,
    summary       TEXT,
    created_at    TEXT NOT NULL
);

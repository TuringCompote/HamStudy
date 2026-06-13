"""Central config — paths and settings read from env, never hardcoded secrets/hosts.

Constitution §4: data stays local. AGENT.md: read paths from config, not literals.
"""
from __future__ import annotations

import os
from pathlib import Path

# Repo root = two levels up from this file (app/config.py -> repo root).
ROOT = Path(__file__).resolve().parent.parent

# Load .env (local dev secrets) if present. Never commit .env (constitution §4).
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except Exception:
    pass

# App identity (QUESTIONS #16 / spec §0.2b). One-line changeable; never hardcode
# the name elsewhere — read APP_NAME and theme from tokens.css.
APP_NAME = os.environ.get("APP_NAME", "Elmer")

# SQLite store. Prod points HAMSTUDY_DB at the NAS-backed volume; default is local.
DB_PATH = Path(os.environ.get("HAMSTUDY_DB", ROOT / "data" / "hamstudy.db"))

# Downloaded source material (git-ignored; re-fetchable).
REFERENCES_DIR = Path(os.environ.get("HAMSTUDY_REFERENCES", ROOT / "references"))
BANK_PDF = Path(
    os.environ.get("HAMSTUDY_BANK_PDF", REFERENCES_DIR / "amateur_basic_questions_en.pdf")
)

# Schema lives beside this module.
SCHEMA_SQL = Path(__file__).resolve().parent / "db" / "schema.sql"

SCHEMA_VERSION = "1"

# Coach output channel (spec §6c) + AI-written journal (spec §7).
RECOMMENDATION_PATH = Path(
    os.environ.get("HAMSTUDY_RECOMMENDATION", ROOT / "data" / "recommendation.json")
)
JOURNAL_DIR = Path(os.environ.get("HAMSTUDY_JOURNAL", ROOT / "data" / "journal"))

# AI layer (spec §0.1 / QUESTIONS #13/#15). Key from env — never hardcode.
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
AI_MODEL = os.environ.get("HAMSTUDY_AI_MODEL", "claude-opus-4-8")
AI_MODEL_CHEAP = os.environ.get("HAMSTUDY_AI_MODEL_CHEAP", "claude-haiku-4-5")
AI_MONTHLY_BUDGET_USD = float(os.environ.get("HAMSTUDY_AI_BUDGET", "15"))

# Per-call-type model routing (configurable). Reasoning + content grounded in the
# reference docs stays on Opus for quality (explain/diagnose/condense); plain-language
# phrasing (narrate) routes to the cheaper model. Override per type via env.
AI_MODELS = {
    "explain": os.environ.get("HAMSTUDY_MODEL_EXPLAIN", AI_MODEL),
    "diagnose": os.environ.get("HAMSTUDY_MODEL_DIAGNOSE", AI_MODEL),
    "condense": os.environ.get("HAMSTUDY_MODEL_CONDENSE", AI_MODEL),
    "narrate": os.environ.get("HAMSTUDY_MODEL_NARRATE", AI_MODEL_CHEAP),
}

# Externalized, Console-tunable prompts (prompts/<call_type>.md).
PROMPTS_DIR = Path(os.environ.get("HAMSTUDY_PROMPTS", ROOT / "prompts"))
# "anthropic" when a key is present, else "stub" (deterministic, offline).
AI_PROVIDER = os.environ.get(
    "HAMSTUDY_AI_PROVIDER", "anthropic" if ANTHROPIC_API_KEY else "stub"
)

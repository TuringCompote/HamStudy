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

# The user's local timezone (IANA name). `attempts` timestamps stay UTC, but a
# "study day" — streaks, the scheduler's one-outcome-per-day collapse, journal
# dates — is a LOCAL day; on UTC days an evening session lands on tomorrow.
# Fixed via config (not the host clock's zone) so the engine stays deterministic:
# same attempts + same config ⇒ same output. Requires tzdata (in requirements).
_TZ_DEFAULT = "America/Edmonton"


def _load_tz():
    name = os.environ.get("HAMSTUDY_TZ", _TZ_DEFAULT)
    try:
        from zoneinfo import ZoneInfo
    except Exception:                  # no zoneinfo at all — behave as before (UTC days)
        from datetime import timezone as _timezone
        return _timezone.utc
    try:
        return ZoneInfo(name)
    except Exception:
        # a mistyped HAMSTUDY_TZ must not silently revert to UTC-day semantics
        import sys
        print(f"[config] unknown HAMSTUDY_TZ={name!r} — using {_TZ_DEFAULT}",
              file=sys.stderr)
        try:
            return ZoneInfo(_TZ_DEFAULT)
        except Exception:              # tz database missing entirely
            from datetime import timezone as _timezone
            return _timezone.utc


TZ = _load_tz()

# Cold-recall window (spec §8 / engine `mastery.py`). An attempt counts as a
# "fresh" probe of a question when it is the first-ever attempt OR it lands at
# least this many days after the previous attempt on that same question —
# re-answering something you drilled minutes ago tests recognition, not recall.
# 0 disables the cooldown, which reverts fresh accuracy to first-exposure-only
# (the old behavior: permanently frozen once the bank has been seen).
FRESH_COOLDOWN_DAYS = float(os.environ.get("HAMSTUDY_FRESH_COOLDOWN_DAYS", "3"))

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
AI_MODEL = os.environ.get("HAMSTUDY_AI_MODEL", "claude-opus-4-8")        # best (one-time batch)
AI_MODEL_MID = os.environ.get("HAMSTUDY_AI_MODEL_MID", "claude-sonnet-4-6")  # live reasoning
AI_MODEL_CHEAP = os.environ.get("HAMSTUDY_AI_MODEL_CHEAP", "claude-haiku-4-5")  # phrasing
AI_MONTHLY_BUDGET_USD = float(os.environ.get("HAMSTUDY_AI_BUDGET", "15"))

# Per-call-type model routing (configurable). LIVE calls avoid Opus (cost/credits):
# everything routes to Sonnet, including narrate — the journal now reasons over a
# real day digest (miss themes, deltas), not just phrasing; ~$0.01/entry. Haiku
# stays available via HAMSTUDY_MODEL_NARRATE. The one-time batch was generated on
# Opus (highest quality); a re-batch can opt back via HAMSTUDY_MODEL_EXPLAIN.
AI_MODELS = {
    "explain": os.environ.get("HAMSTUDY_MODEL_EXPLAIN", AI_MODEL_MID),
    "diagnose": os.environ.get("HAMSTUDY_MODEL_DIAGNOSE", AI_MODEL_MID),
    "condense": os.environ.get("HAMSTUDY_MODEL_CONDENSE", AI_MODEL_MID),
    "narrate": os.environ.get("HAMSTUDY_MODEL_NARRATE", AI_MODEL_MID),
}

# Externalized, Console-tunable prompts (prompts/<call_type>.md).
PROMPTS_DIR = Path(os.environ.get("HAMSTUDY_PROMPTS", ROOT / "prompts"))
# "anthropic" when a key is present, else "stub" (deterministic, offline).
AI_PROVIDER = os.environ.get(
    "HAMSTUDY_AI_PROVIDER", "anthropic" if ANTHROPIC_API_KEY else "stub"
)

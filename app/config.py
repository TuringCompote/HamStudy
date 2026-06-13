"""Central config — paths and settings read from env, never hardcoded secrets/hosts.

Constitution §4: data stays local. AGENT.md: read paths from config, not literals.
"""
from __future__ import annotations

import os
from pathlib import Path

# Repo root = two levels up from this file (app/config.py -> repo root).
ROOT = Path(__file__).resolve().parent.parent

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

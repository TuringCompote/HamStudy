"""Stand up the SQLite schema (spec §7). Idempotent: safe to run repeatedly.

Usage:
    python -m app.db.init_db

Applies schema.sql (all CREATE ... IF NOT EXISTS) and records schema_version.
Never drops or mutates existing tables/rows — in particular, `attempts`.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from app import config


def connect(db_path=None) -> sqlite3.Connection:
    """Open a connection with sane pragmas and row access by name."""
    path = db_path or config.DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA busy_timeout = 5000;")  # wait out transient locks (WAL)
    return conn


def init_db(db_path=None) -> sqlite3.Connection:
    conn = connect(db_path)
    sql = config.SCHEMA_SQL.read_text(encoding="utf-8")
    conn.executescript(sql)
    conn.execute(
        "INSERT INTO meta(key, value) VALUES('schema_version', ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (config.SCHEMA_VERSION,),
    )
    conn.execute(
        "INSERT INTO meta(key, value) VALUES('schema_applied_at', ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (datetime.now(timezone.utc).isoformat(),),
    )
    conn.commit()
    return conn


if __name__ == "__main__":
    conn = init_db()
    tables = [
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
    ]
    print(f"schema applied to {config.DB_PATH}")
    print("tables:", ", ".join(tables))

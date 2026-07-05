"""Local-day conversion for the deterministic engine.

`attempts.answered_at` is stored UTC (append-only, never rewritten — constitution
§6). But everything the user experiences as a "day" — the streak, the scheduler's
one-outcome-per-day collapse, journal entry dates — must be their LOCAL day, or
any evening session splits across two days. `config.TZ` pins the zone, keeping
these functions pure: same timestamps + same config ⇒ same days.
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from app import config


def local_day(utc_iso: str) -> str:
    """ISO-8601 UTC timestamp → local calendar day as 'YYYY-MM-DD'."""
    dt = datetime.fromisoformat(utc_iso)
    if dt.tzinfo is None:              # legacy naive timestamps are UTC
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(config.TZ).date().isoformat()


def today_local() -> date:
    """Today in the configured zone (journal dates, due-date filtering)."""
    return datetime.now(config.TZ).date()

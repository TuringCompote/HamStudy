"""Build + persist the coach's recommendation (spec §6c) — deterministic.

`build_recommendation` is pure over `attempts` (+ derived state): same log ⇒ same
plan. `refresh` writes it to `recommendation.json` (the durable, human-readable
output channel the app reads back) and appends a `recommendation` table row only
when the content actually changes — so the table is a history of real changes, not
one row per page view. `generated_at` is stamped at write time and excluded from
the change-detection hash (it isn't part of the deterministic content).
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from app import config
from app.engine import mastery, readiness as readiness_mod, scheduler, analysis, coach, diagnostic

NEW_PER_SESSION = 15
REVIEW_CAP = 10
REVIEW_QUEUE_CAP = 50


def build_recommendation(conn) -> dict:
    by_section = mastery.compute_section_mastery(conn)
    diagnostic.apply_diagnostic_tiers(conn, by_section)
    rd = readiness_mod.readiness(conn, by_section)
    trend = analysis.section_trend(conn)
    session = coach.suggest_session(conn, by_section)
    due = scheduler.due_reviews(conn, limit=REVIEW_QUEUE_CAP)

    bv = conn.execute("SELECT value FROM meta WHERE key='bank_version'").fetchone()
    bank_version = bv["value"] if bv else None

    per_section = {
        s["section"]: {
            "fresh_pct": s["fresh_pct"],
            "tier": s["tier"],
            "tier_source": s.get("tier_source"),
            "trend": trend.get(s["section"], "new"),
            "meets_honours": s["meets_honours"],
        }
        for s in by_section.values()
    }

    return {
        "bank_version": bank_version,
        "readiness": {
            "exam_ready": rd["exam_ready"],
            "sections_honours": rd["sections_honours"],
            "coverage_pct": rd["coverage_pct"],
            "blockers": rd["blockers"],
            "weakest_sections": rd["weakest_sections"],
            "per_section": per_section,
        },
        "next_session": {
            "focus_section": session.get("focus_section"),
            "new_count": NEW_PER_SESSION,
            "review_count": min(len(due), REVIEW_CAP),
            "tools": [t["name"] for t in _focus_tools(session.get("focus_section"))],
            "rationale": session.get("detail", ""),
        },
        "review_queue": due,
        "most_missed": analysis.most_missed(conn, 10),
    }


def _focus_tools(section):
    if not section:
        return []
    from app.tools import tools_for_section
    return tools_for_section(section)


def _content_hash(rec: dict) -> str:
    return hashlib.sha256(
        json.dumps(rec, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def refresh(conn) -> dict:
    """Build, write recommendation.json, and append a history row if changed.
    Returns the recommendation dict (with generated_at stamped)."""
    rec = build_recommendation(conn)
    digest = _content_hash(rec)

    last = conn.execute(
        "SELECT payload FROM recommendation ORDER BY id DESC LIMIT 1"
    ).fetchone()
    changed = True
    if last:
        try:
            prev = json.loads(last["payload"])
            changed = _content_hash({k: prev[k] for k in rec if k in prev}) != digest
        except Exception:
            changed = True

    stamped = {"generated_at": datetime.now(timezone.utc).isoformat(), **rec}

    # always refresh the on-disk artifact (the app reads this back)
    config.RECOMMENDATION_PATH.parent.mkdir(parents=True, exist_ok=True)
    config.RECOMMENDATION_PATH.write_text(
        json.dumps(stamped, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    if changed:
        conn.execute(
            "INSERT INTO recommendation (generated_at, bank_version, payload) VALUES (?,?,?)",
            (stamped["generated_at"], rec.get("bank_version") or "",
             json.dumps(rec, ensure_ascii=False)),
        )
        conn.commit()
    return stamped

"""Diagnostic placement (spec §6d.1) — deterministic.

On first entering a section the app serves a short probe (~8 questions spanning
the section's subsections). The user may self-declare confidence (cold/rusty/new)
which is recorded as a prior; measured performance decides the tier. The probe
score → a starting depth tier, stored in the append-only `diagnostics` table.

Until a section has enough FRESH attempts to stand on its own, its dashboard tier
is seeded from the latest diagnostic (measured performance overrides once it
accumulates — §6d.1).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from app.engine.mastery import depth_tier, tier_css

# below this many fresh attempts, trust the diagnostic tier over the thin sample
MIN_FRESH_FOR_TIER = 6
VALID_CONFIDENCE = {"cold", "rusty", "new"}


def score_served(conn, served_ids: list[str]) -> float:
    """Fraction correct over the most-recent diagnostic-mode attempt for each id."""
    if not served_ids:
        return 0.0
    correct = 0
    counted = 0
    for qid in served_ids:
        row = conn.execute(
            """
            SELECT correct FROM attempts
            WHERE question_id = ? AND mode = 'diagnostic'
            ORDER BY answered_at DESC, id DESC LIMIT 1
            """,
            (qid,),
        ).fetchone()
        if row is not None:
            counted += 1
            correct += row["correct"]
    return (correct / counted) if counted else 0.0


def record_diagnostic(conn, section: int, served_ids: list[str],
                      confidence_prior: str | None = None) -> dict:
    score = score_served(conn, served_ids)         # 0..1
    tier = depth_tier(round(score * 100, 1))
    prior = confidence_prior if confidence_prior in VALID_CONFIDENCE else None
    conn.execute(
        """
        INSERT INTO diagnostics
            (section, served_ids, score, resulting_tier, confidence_prior, created_at)
        VALUES (?,?,?,?,?,?)
        """,
        (section, json.dumps(served_ids), score, tier, prior,
         datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    return {"section": section, "score_pct": round(score * 100, 1),
            "tier": tier, "confidence_prior": prior}


def latest_tiers(conn) -> dict[int, str]:
    """{section: resulting_tier} from the most recent diagnostic per section."""
    rows = conn.execute(
        """
        SELECT section, resulting_tier FROM diagnostics d
        WHERE id = (SELECT MAX(id) FROM diagnostics WHERE section = d.section)
        """
    ).fetchall()
    return {r["section"]: r["resulting_tier"] for r in rows if r["resulting_tier"]}


def has_diagnostic(conn, section: int) -> bool:
    row = conn.execute(
        "SELECT 1 FROM diagnostics WHERE section = ? LIMIT 1", (section,)
    ).fetchone()
    return row is not None


def apply_diagnostic_tiers(conn, by_section: dict) -> dict:
    """Overlay diagnostic-seeded tiers onto sections with too few fresh attempts.
    Adds 'tier_source' (measured | diagnostic | unrated) to each section dict."""
    diag = latest_tiers(conn)
    for s in by_section.values():
        if s["fresh_answered"] < MIN_FRESH_FOR_TIER and s["section"] in diag:
            s["tier"] = diag[s["section"]]
            s["tier_css"] = tier_css(s["tier"])
            s["tier_source"] = "diagnostic"
        else:
            s["tier_source"] = "measured" if s["tier"] else "unrated"
    return by_section

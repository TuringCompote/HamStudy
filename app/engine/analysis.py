"""Deterministic analysis over `attempts` (spec §6c, constitution §5).

Trend, fresh-vs-review accuracy, most-missed questions, and the fast-wrong vs
slow-wrong split that distinguishes a misconception from "not learned yet". All
pure over the attempt log — no LLM, no wall-clock, no randomness. The AI layer
(Phase 5) only *explains* these; it never computes them.
"""
from __future__ import annotations

from app.engine.mastery import cold_params, cold_sql

# A wrong answer faster than this reads as a confident misconception ("fast +
# wrong"); slower reads as "not learned / guessing" ("slow + wrong"). ms.
FAST_WRONG_MS = 8000
TREND_DELTA = 8.0  # ±pct to call a section improving / regressing vs plateaued


def _fresh_rows(conn):
    """Every COLD attempt, in chronological order, with section + correct.

    All of them, not just the latest per question: trend compares the earlier
    half of a section's cold attempts against the later half, so it needs the
    sequence. (Keying on first-exposure-only froze every section's trend the
    moment the bank had been seen once.)"""
    return conn.execute(
        cold_sql(
            "SELECT section, subsection, question_id, correct, answered_at "
            "FROM cold ORDER BY answered_at, id"
        ),
        cold_params(),
    ).fetchall()


def section_trend(conn) -> dict[int, str]:
    """Per section: 'improving' | 'plateaued' | 'regressing' | 'new' — from the
    later half vs earlier half of that section's fresh attempts (chronological)."""
    by_sec: dict[int, list[int]] = {}
    for r in _fresh_rows(conn):
        by_sec.setdefault(r["section"], []).append(r["correct"])

    out: dict[int, str] = {}
    for section in range(1, 9):
        seq = by_sec.get(section, [])
        if len(seq) < 6:
            out[section] = "new"
            continue
        half = len(seq) // 2
        earlier = seq[:half]
        later = seq[half:]
        e = 100.0 * sum(earlier) / len(earlier)
        l = 100.0 * sum(later) / len(later)
        if l - e >= TREND_DELTA:
            out[section] = "improving"
        elif e - l >= TREND_DELTA:
            out[section] = "regressing"
        else:
            out[section] = "plateaued"
    return out


def fresh_vs_review(conn) -> dict[int, dict]:
    """Per section: cold accuracy (fresh probes) vs warm accuracy (repeats inside
    the cooldown — i.e. the same material seen again while it's still hot)."""
    rows = conn.execute(
        cold_sql(
            """
            SELECT section,
                   SUM(is_cold)                                        AS fresh_n,
                   SUM(CASE WHEN is_cold = 1 THEN correct ELSE 0 END)  AS fresh_c,
                   SUM(1 - is_cold)                                    AS rev_n,
                   SUM(CASE WHEN is_cold = 0 THEN correct ELSE 0 END)  AS rev_c
            FROM flagged GROUP BY section
            """
        ),
        cold_params(),
    ).fetchall()
    out = {}
    for r in rows:
        fn, rn = r["fresh_n"] or 0, r["rev_n"] or 0
        out[r["section"]] = {
            "fresh_pct": round(100.0 * (r["fresh_c"] or 0) / fn, 1) if fn else None,
            "review_pct": round(100.0 * (r["rev_c"] or 0) / rn, 1) if rn else None,
        }
    return out


def most_missed(conn, limit: int = 10) -> list[dict]:
    """Questions ranked by miss rate (then misses), among those attempted ≥1×."""
    rows = conn.execute(
        """
        SELECT question_id, section, subsection,
               COUNT(*) attempts, SUM(1 - correct) misses
        FROM attempts GROUP BY question_id
        HAVING misses > 0
        ORDER BY (CAST(misses AS REAL) / attempts) DESC, misses DESC, question_id
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def section_miss_summary(conn, section: int, limit: int = 5) -> str:
    """Deterministic plain-text summary of a section's recurring misses, to hand
    to the live `diagnose()` call. Empty string when there are no misses."""
    rows = conn.execute(
        """
        SELECT a.question_id, q.text, SUM(1 - a.correct) misses, COUNT(*) n
        FROM attempts a JOIN questions q ON q.id = a.question_id
        WHERE a.section = ?
        GROUP BY a.question_id HAVING misses > 0
        ORDER BY misses DESC, n DESC, a.question_id
        LIMIT ?
        """,
        (section, limit),
    ).fetchall()
    if not rows:
        return ""
    wc = wrong_classification(conn).get(section, {"fast_wrong": 0, "slow_wrong": 0})
    lines = [
        f"fast-wrong (confident but wrong → likely misconception): {wc['fast_wrong']}; "
        f"slow-wrong (hesitant/guessing → not yet learned): {wc['slow_wrong']}.",
        "Most-missed questions (times wrong):",
    ]
    for r in rows:
        lines.append(f"- ({r['misses']}× wrong) {r['text']}")
    return "\n".join(lines)


def wrong_classification(conn) -> dict[int, dict]:
    """Per section: fast-wrong (misconception) vs slow-wrong (not learned) counts,
    over all wrong attempts that recorded a response time."""
    rows = conn.execute(
        """
        SELECT section,
               SUM(CASE WHEN response_ms IS NOT NULL AND response_ms < ? THEN 1 ELSE 0 END) AS fast_wrong,
               SUM(CASE WHEN response_ms IS NOT NULL AND response_ms >= ? THEN 1 ELSE 0 END) AS slow_wrong
        FROM attempts WHERE correct = 0
        GROUP BY section
        """,
        (FAST_WRONG_MS, FAST_WRONG_MS),
    ).fetchall()
    return {
        r["section"]: {"fast_wrong": r["fast_wrong"] or 0, "slow_wrong": r["slow_wrong"] or 0}
        for r in rows
    }

"""Deterministic dashboard aggregates + a provisional "Today's session".

All pure functions over `attempts` (constitution §5) — no LLM, no randomness.
This is the Phase-2/3 stand-in for what Phase 5 will produce as a full
`recommendation.json` (and phrase via the AI layer). Same attempts in ⇒ same
output. Streak is computed from attempt timestamps converted to the configured
local zone (config.TZ) — no wall-clock — so it stays reproducible.
"""
from __future__ import annotations

from datetime import date

from app import timeutil
from app.engine.mastery import compute_section_mastery, HONOURS_BAR
from app.engine import scheduler, readiness as readiness_mod


def day_streak(conn) -> int:
    """Consecutive LOCAL calendar days (ending at the most recent attempt day)
    that have at least one attempt. Attempt-derived + fixed TZ → deterministic."""
    rows = conn.execute("SELECT answered_at FROM attempts").fetchall()
    days = sorted(
        {timeutil.local_day(r["answered_at"]) for r in rows if r["answered_at"]},
        reverse=True,
    )
    if not days:
        return 0
    streak = 1
    prev = date.fromisoformat(days[0])
    for d in days[1:]:
        cur = date.fromisoformat(d)
        if (prev - cur).days == 1:
            streak += 1
            prev = cur
        else:
            break
    return streak


def mastered_count(conn) -> int:
    """Distinct questions whose MOST RECENT attempt was correct."""
    row = conn.execute(
        """
        SELECT COUNT(*) c FROM (
            SELECT correct,
                   ROW_NUMBER() OVER (
                       PARTITION BY question_id ORDER BY answered_at DESC, id DESC
                   ) rn
            FROM attempts
        ) WHERE rn = 1 AND correct = 1
        """
    ).fetchone()
    return row["c"] or 0


def dashboard_summary(conn, by_section: dict | None = None) -> dict:
    by_section = by_section or compute_section_mastery(conn)
    answered = sum(s["answered"] for s in by_section.values())
    bank_size = sum(s["size"] for s in by_section.values())
    mastered = mastered_count(conn)

    # Exam readiness is FRESH-question accuracy (spec §8) — overall first-exposure.
    fresh_a = sum(s["fresh_answered"] for s in by_section.values())
    fresh_c = sum(s["fresh_correct"] for s in by_section.values())
    rd = readiness_mod.readiness(conn, by_section)

    return {
        "readiness_pct": round(100.0 * fresh_c / fresh_a, 1) if fresh_a else None,
        "sections_ready": rd["sections_honours"],
        "streak": day_streak(conn),
        "mastered": mastered,
        "bank_size": bank_size,
        "mastered_pct": round(100.0 * mastered / bank_size, 1) if bank_size else 0.0,
        "review_due": scheduler.review_due_count(conn),
        "exam_ready": rd["exam_ready"],
        "coverage_pct": rd["coverage_pct"],
        "blockers": rd["blockers"],
        "honours_bar": HONOURS_BAR,
        "answered": answered,
    }


def suggest_session(conn, by_section: dict | None = None) -> dict:
    """Provisional next-session suggestion (Phase 5 replaces with the full engine
    recommendation + AI phrasing). Focus = weakest studied section; review = next
    weakest; surface that section's first concept tool if it has one."""
    from app.tools import tools_for_section

    by_section = by_section or compute_section_mastery(conn)
    studied = [s for s in by_section.values() if s["answered"] > 0]
    if not studied:
        return {
            "headline": "Today's session",
            "detail": "Run a drill or a mock exam to begin — once the coach sees "
                      "your first results it will tailor each session to your weak spots.",
            "focus_section": None,
        }

    # Rank by FRESH accuracy — the same number the dashboard rows, the tiers and
    # readiness.weakest_sections use. Ranking by all-attempts mastery_pct made the
    # coach name a different "weakest section" than the one the S-meters showed.
    weakest = sorted(
        studied,
        key=lambda s: (s["fresh_pct"] if s["fresh_pct"] is not None else 0.0,
                       s["mastery_pct"] if s["mastery_pct"] is not None else 0.0),
    )
    focus = weakest[0]
    tools = tools_for_section(focus["section"])
    due = scheduler.review_due_count(conn)

    # "new" is only honest while the section still has unseen questions; past that
    # a session is cold-recall re-probing, and saying "new" reads as a broken app.
    unseen = focus["size"] - focus["seen"]
    detail = (f"15 new in {focus['short'].lower()}" if unseen >= 15
              else f"15 cold-recall in {focus['short'].lower()}")
    if due:
        detail += f", {due} due for review"
    if tools:
        detail += f", then revisit the {tools[0]['name']} tool"
    detail += f". Weakest section right now: {focus['short'].lower()}."
    return {"headline": "Today's session", "detail": detail,
            "focus_section": focus["section"], "review_due": due}

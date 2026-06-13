"""Deterministic dashboard aggregates + a provisional "Today's session".

All pure functions over `attempts` (constitution §5) — no LLM, no randomness.
This is the Phase-2/3 stand-in for what Phase 5 will produce as a full
`recommendation.json` (and phrase via the AI layer). Same attempts in ⇒ same
output. Streak is computed from attempt dates only (no wall-clock) so it stays
reproducible.
"""
from __future__ import annotations

from datetime import date

from app.engine.mastery import compute_section_mastery, HONOURS_BAR
from app.engine import scheduler


def day_streak(conn) -> int:
    """Consecutive calendar days (ending at the most recent attempt day) that
    have at least one attempt. Date-only and attempt-derived → deterministic."""
    rows = conn.execute(
        "SELECT DISTINCT substr(answered_at, 1, 10) d FROM attempts ORDER BY d DESC"
    ).fetchall()
    days = [r["d"] for r in rows if r["d"]]
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
    correct = sum(s["correct"] for s in by_section.values())
    bank_size = sum(s["size"] for s in by_section.values())
    mastered = mastered_count(conn)
    return {
        "readiness_pct": round(100.0 * correct / answered, 1) if answered else None,
        "sections_ready": sum(1 for s in by_section.values() if s["meets_honours"]),
        "streak": day_streak(conn),
        "mastered": mastered,
        "bank_size": bank_size,
        "mastered_pct": round(100.0 * mastered / bank_size, 1) if bank_size else 0.0,
        "review_due": scheduler.review_due_count(conn),
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

    weakest = sorted(studied, key=lambda s: s["mastery_pct"] if s["mastery_pct"] is not None else 0.0)
    focus = weakest[0]
    tools = tools_for_section(focus["section"])
    due = scheduler.review_due_count(conn)

    detail = f"15 new in {focus['short'].lower()}"
    if due:
        detail += f", {due} due for review"
    if tools:
        detail += f", then revisit the {tools[0]['name']} tool"
    detail += f". Weakest section right now: {focus['short'].lower()}."
    return {"headline": "Today's session", "detail": detail,
            "focus_section": focus["section"], "review_due": due}

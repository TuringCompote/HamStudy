"""Deterministic per-section mastery (constitution §5).

Pure arithmetic over the `attempts` event log: same attempts in => same numbers
out. No LLM, no randomness, no wall-clock dependence. This is the Phase-2 seed of
the engine; trend / fresh-vs-review / adaptive state come in later phases.

Definitions (v1):
  answered      = total attempts in the section
  correct       = correct attempts in the section
  mastery_pct   = 100 * correct / answered     (None if never answered)
  coverage_pct  = 100 * distinct questions attempted / section size
  seen          = distinct questions attempted
The Honours bar is 80% (spec §0.1); 70% is a pass.
"""
from __future__ import annotations

from app.db.queries import SECTION_NAMES

HONOURS_BAR = 80.0
PASS_BAR = 70.0


def mastery_band(pct: float | None) -> str | None:
    """S-meter color band for a mastery %. Phase-2 placeholder for the depth-tier
    coloring that Phase 4.5 will drive: ok (≥80 Honours), warn (70–80), low (<70)."""
    if pct is None:
        return None
    if pct >= HONOURS_BAR:
        return "ok"
    if pct >= PASS_BAR:
        return "warn"
    return "low"


def compute_section_mastery(conn) -> dict[int, dict]:
    """Return {section: {name, answered, correct, mastery_pct, seen,
    size, coverage_pct, meets_honours}} for sections 1..8."""
    sizes = {
        r["section"]: r["n"]
        for r in conn.execute(
            "SELECT section, COUNT(*) n FROM questions GROUP BY section"
        ).fetchall()
    }
    stats = {
        r["section"]: r
        for r in conn.execute(
            """
            SELECT section,
                   COUNT(*)                         AS answered,
                   SUM(correct)                     AS correct,
                   COUNT(DISTINCT question_id)      AS seen
            FROM attempts
            GROUP BY section
            """
        ).fetchall()
    }

    out: dict[int, dict] = {}
    for section in range(1, 9):
        size = sizes.get(section, 0)
        s = stats.get(section)
        answered = s["answered"] if s else 0
        correct = (s["correct"] or 0) if s else 0
        seen = s["seen"] if s else 0
        mastery = round(100.0 * correct / answered, 1) if answered else None
        coverage = round(100.0 * seen / size, 1) if size else 0.0
        out[section] = {
            "section": section,
            "name": SECTION_NAMES.get(section, f"Section {section}"),
            "size": size,
            "answered": answered,
            "correct": correct,
            "seen": seen,
            "mastery_pct": mastery,
            "coverage_pct": coverage,
            "meets_honours": mastery is not None and mastery >= HONOURS_BAR,
            "band": mastery_band(mastery),
        }
    return out


def overall_summary(conn) -> dict:
    """Aggregate readiness snapshot for the dashboard header."""
    by_section = compute_section_mastery(conn)
    answered = sum(s["answered"] for s in by_section.values())
    correct = sum(s["correct"] for s in by_section.values())
    overall = round(100.0 * correct / answered, 1) if answered else None
    sections_meeting = sum(1 for s in by_section.values() if s["meets_honours"])
    return {
        "answered": answered,
        "correct": correct,
        "overall_pct": overall,
        "sections_meeting_honours": sections_meeting,
        # NB: true readiness also needs the §6d.4 coverage guarantee (Phase 4.5/5);
        # this flag is a coarse Phase-2 placeholder, not the terminal signal.
        "all_sections_honours": sections_meeting == 8,
        "pass_bar": PASS_BAR,
        "honours_bar": HONOURS_BAR,
    }

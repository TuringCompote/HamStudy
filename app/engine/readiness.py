"""Deterministic readiness + coverage guarantee (spec §6d.4, constitution §8).

"Book the exam" fires only when BOTH hold:
  1. fresh-question accuracy ≥ 80% (Honours) in every one of the 8 sections, AND
  2. every subsection has been probed with a fresh question (coverage), so a
     strong section is verified, not assumed.

Pure over `attempts` + `questions`. Fresh = a question's first-ever attempt.
"""
from __future__ import annotations

from app.engine.mastery import compute_section_mastery, HONOURS_BAR


def coverage(conn) -> dict:
    """Per-section subsection coverage by FRESH questions.

    Returns {section: {total_subsections, covered_subsections, complete}} plus an
    'overall_complete' / counts roll-up under key 0.
    """
    total = {}
    for r in conn.execute(
        "SELECT section, COUNT(DISTINCT subsection) n FROM questions GROUP BY section"
    ).fetchall():
        total[r["section"]] = r["n"]

    covered = {}
    for r in conn.execute(
        """
        SELECT section, COUNT(DISTINCT subsection) n FROM (
            SELECT section, subsection,
                   ROW_NUMBER() OVER (
                       PARTITION BY question_id ORDER BY answered_at, id
                   ) rn
            FROM attempts
        ) WHERE rn = 1
        GROUP BY section
        """
    ).fetchall():
        covered[r["section"]] = r["n"]

    out = {}
    tot_sub = cov_sub = 0
    for section in range(1, 9):
        t = total.get(section, 0)
        c = covered.get(section, 0)
        tot_sub += t
        cov_sub += c
        out[section] = {
            "total_subsections": t,
            "covered_subsections": c,
            "complete": t > 0 and c >= t,
        }
    out[0] = {
        "total_subsections": tot_sub,
        "covered_subsections": cov_sub,
        "overall_complete": tot_sub > 0 and cov_sub >= tot_sub,
        "pct": round(100.0 * cov_sub / tot_sub, 1) if tot_sub else 0.0,
    }
    return out


def readiness(conn, by_section: dict | None = None) -> dict:
    """Overall readiness signal (the loop's terminal output)."""
    by_section = by_section or compute_section_mastery(conn)
    cov = coverage(conn)

    sections_honours = sum(1 for s in by_section.values() if s["meets_honours"])
    all_honours = sections_honours == 8
    coverage_complete = cov[0]["overall_complete"]
    exam_ready = all_honours and coverage_complete

    # weakest sections (lowest fresh accuracy among those with data) for guidance
    rated = [s for s in by_section.values() if s["fresh_pct"] is not None]
    weakest = sorted(rated, key=lambda s: s["fresh_pct"])[:3]

    return {
        "exam_ready": exam_ready,
        "sections_honours": sections_honours,
        "all_sections_honours": all_honours,
        "coverage_complete": coverage_complete,
        "coverage_pct": cov[0]["pct"],
        "honours_bar": HONOURS_BAR,
        "weakest_sections": [s["section"] for s in weakest],
        # what's blocking "book the exam", in plain terms
        "blockers": _blockers(by_section, cov),
    }


def _blockers(by_section: dict, cov: dict) -> list[str]:
    out = []
    below = [s for s in by_section.values()
             if s["fresh_pct"] is None or s["fresh_pct"] < HONOURS_BAR]
    if below:
        out.append(f"{len(below)} section(s) below the 80% fresh-accuracy bar")
    if not cov[0]["overall_complete"]:
        missing = cov[0]["total_subsections"] - cov[0]["covered_subsections"]
        out.append(f"{missing} subsection(s) not yet probed with a fresh question")
    return out

"""Deterministic day digest — the facts of one study day (constitution §5).

The journal's narrate() call used to see only the forward-looking plan and
nothing about the day's actual work, which is why entries read generic. This
module assembles what happened on a given LOCAL day (config.TZ): totals, per-mode
and per-section results with start-of-day → now fresh-accuracy deltas, the actual
missed questions (stem + what was chosen vs correct), and the fast-wrong signal
(answered quickly but wrong = confident misconception). Pure over `attempts` +
fixed config: same log + same TZ ⇒ same digest. The AI layer only PHRASES this;
it computes nothing.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from app import config, timeutil
from app.engine import mastery, readiness as readiness_mod, coach
from app.engine.analysis import FAST_WRONG_MS

MAX_MISSES = 8          # cap the miss detail handed to the narrator / journal body
MODE_ORDER = ("drill", "exam", "review", "diagnostic")


def _day_bounds_utc(day: str) -> tuple[str, str]:
    """Local calendar day 'YYYY-MM-DD' → [start, end) as UTC ISO strings that
    compare correctly against attempts.answered_at."""
    start_local = datetime.fromisoformat(day + "T00:00:00").replace(tzinfo=config.TZ)
    end_local = (datetime.fromisoformat(day + "T00:00:00") + timedelta(days=1)).replace(
        tzinfo=config.TZ)
    return (start_local.astimezone(timezone.utc).isoformat(),
            end_local.astimezone(timezone.utc).isoformat())


def build_day_digest(conn, day: str | None = None) -> dict:
    day = day or timeutil.today_local().isoformat()
    lo, hi = _day_bounds_utc(day)
    rows = conn.execute(
        """
        SELECT a.question_id, a.section, a.mode, a.correct, a.chosen_index,
               a.response_ms, q.text, q.options, q.correct_index
        FROM attempts a JOIN questions q ON q.id = a.question_id
        WHERE a.answered_at >= ? AND a.answered_at < ?
        ORDER BY a.answered_at, a.id
        """,
        (lo, hi),
    ).fetchall()

    answered = len(rows)
    correct = sum(r["correct"] for r in rows)
    by_mode: dict[str, dict] = {}
    sec_counts: dict[int, dict] = {}
    misses: list[dict] = []
    seen_miss_ids: dict[str, dict] = {}
    fast_wrong = slow_wrong = 0

    for r in rows:
        m = by_mode.setdefault(r["mode"], {"answered": 0, "correct": 0})
        m["answered"] += 1
        m["correct"] += r["correct"]
        s = sec_counts.setdefault(r["section"], {"answered": 0, "correct": 0})
        s["answered"] += 1
        s["correct"] += r["correct"]

        if not r["correct"]:
            fast = r["response_ms"] is not None and r["response_ms"] < FAST_WRONG_MS
            if r["response_ms"] is not None:
                fast_wrong += 1 if fast else 0
                slow_wrong += 0 if fast else 1
            prev = seen_miss_ids.get(r["question_id"])
            if prev is not None:
                prev["times"] += 1                 # missed the same question again
                prev["fast"] = prev["fast"] or fast
            elif len(misses) < MAX_MISSES:
                opts = json.loads(r["options"])
                entry = {
                    "question_id": r["question_id"],
                    "section": r["section"],
                    "text": r["text"],
                    "chosen": opts[r["chosen_index"]]
                              if 0 <= r["chosen_index"] < len(opts) else "",
                    "correct_answer": opts[r["correct_index"]],
                    "fast": fast,
                    "times": 1,
                }
                misses.append(entry)
                seen_miss_ids[r["question_id"]] = entry

    for m in by_mode.values():
        m["pct"] = round(100.0 * m["correct"] / m["answered"], 1) if m["answered"] else None

    # per-section fresh-accuracy deltas: state at start of day vs now
    now_m = mastery.compute_section_mastery(conn)
    prev_m = mastery.compute_section_mastery(conn, before=lo)
    sections = []
    for sec in sorted(sec_counts):
        cur = now_m[sec]
        sections.append({
            "section": sec,
            "short": cur["short"],
            "answered": sec_counts[sec]["answered"],
            "correct": sec_counts[sec]["correct"],
            "fresh_pct_start": prev_m[sec]["fresh_pct"],
            "fresh_pct": cur["fresh_pct"],
            "tier": cur["tier"],
        })

    rd = readiness_mod.readiness(conn, now_m)
    return {
        "date": day,
        "answered": answered,
        "correct": correct,
        "pct": round(100.0 * correct / answered, 1) if answered else None,
        "streak": coach.day_streak(conn),
        "by_mode": {k: by_mode[k] for k in MODE_ORDER if k in by_mode},
        "sections": sections,
        "misses": misses,
        "miss_count": answered - correct,
        "fast_wrong": fast_wrong,
        "slow_wrong": slow_wrong,
        "exam_ready": rd["exam_ready"],
        "sections_honours": rd["sections_honours"],
        "blockers": rd["blockers"],
    }

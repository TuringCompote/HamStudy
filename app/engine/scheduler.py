"""Deterministic spaced-repetition scheduler (constitution §5).

Leitner-style boxes computed purely from the `attempts` log:
  - Attempts are collapsed to ONE review outcome per calendar day (the last
    attempt that day) so drilling a question repeatedly in one session can't
    inflate its box.
  - Each review day: correct ⇒ promote one box (capped), wrong ⇒ reset to box 1.
  - A box maps to an interval (days); `due_date = last_review_day + interval`.

Same `attempts` in ⇒ same schedule out. No LLM, no randomness. The only external
input is "today", and it's used solely to FILTER which scheduled items are due —
the per-question box/interval/due state is pure over the attempt log.
"""
from __future__ import annotations

from datetime import date, timedelta

MAX_BOX = 6
# box -> interval in days. Box 1 (just lapsed / new-wrong) is due immediately.
INTERVALS = {1: 0, 2: 1, 3: 3, 4: 7, 5: 16, 6: 35}


def _attempt_rows(conn):
    return conn.execute(
        "SELECT question_id, substr(answered_at,1,10) AS day, correct, answered_at "
        "FROM attempts ORDER BY question_id, answered_at, id"
    ).fetchall()


def compute_schedule(conn) -> dict[str, dict]:
    """{question_id: {box, interval_days, last_review, due_date, reviews, lapses}}.

    `last_review` and `due_date` are ISO date strings. Pure over `attempts`.
    """
    # group attempts by question, then collapse to one outcome per day
    by_q: dict[str, list] = {}
    for r in _attempt_rows(conn):
        by_q.setdefault(r["question_id"], []).append(r)

    schedule: dict[str, dict] = {}
    for qid, rows in by_q.items():
        # last attempt of each day = that day's review outcome (rows already ordered)
        day_outcome: dict[str, int] = {}
        for r in rows:
            day_outcome[r["day"]] = r["correct"]

        box = 1
        reviews = 0
        lapses = 0
        last_day = None
        for day in sorted(day_outcome):
            correct = day_outcome[day]
            if correct:
                box = min(box + 1, MAX_BOX)
            else:
                box = 1
                lapses += 1
            reviews += 1
            last_day = day

        interval = INTERVALS[box]
        due = date.fromisoformat(last_day) + timedelta(days=interval)
        schedule[qid] = {
            "box": box,
            "interval_days": interval,
            "last_review": last_day,
            "due_date": due.isoformat(),
            "reviews": reviews,
            "lapses": lapses,
        }
    return schedule


def due_reviews(conn, today: date | None = None, limit: int | None = None) -> list[str]:
    """Question ids due for review (due_date <= today), most-overdue first, then
    lowest box (weakest) first, then id for a stable order."""
    today = today or date.today()
    sched = compute_schedule(conn)
    due = [
        (qid, s) for qid, s in sched.items()
        if date.fromisoformat(s["due_date"]) <= today
    ]
    due.sort(key=lambda t: (t[1]["due_date"], t[1]["box"], t[0]))
    ids = [qid for qid, _ in due]
    return ids[:limit] if limit else ids


def review_due_count(conn, today: date | None = None) -> int:
    return len(due_reviews(conn, today))

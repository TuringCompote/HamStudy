"""Elo / IRT-lite ability + difficulty, and θ-aware drill selection (spec §6d.3).

Deterministic: ability θ (per section) and difficulty b (per question) co-calibrate
by replaying the `attempts` log in chronological order with fixed update constants
and fixed initial values (θ=0, b=0). Same attempts in ⇒ same θ/b out.

Drill selection serves questions in the learner's productive zone (~75% success,
i.e. difficulty a little below ability), pulling forward under-probed subsections
and unseen questions. The SELECTION POLICY is deterministic given the attempt log;
only the cold-start case (no attempts in a section yet, so no signal) samples
randomly for variety.
"""
from __future__ import annotations

import math
import random

from app import timeutil
from app.db import queries
from app.engine.mastery import cold_params, cold_sql

K_THETA = 0.30   # ability step per answer
K_B = 0.15       # difficulty step per answer (questions drift slower than ability)
# target difficulty offset below ability for ~75% success: logit(0.75) ≈ 1.10
TARGET_OFFSET = 1.10


def compute_ability_difficulty(conn) -> tuple[dict[int, float], dict[str, float]]:
    """Replay attempts → (theta[section], difficulty_b[question_id]). Deterministic."""
    theta = {s: 0.0 for s in range(1, 9)}
    b: dict[str, float] = {}
    for r in conn.execute(
        "SELECT question_id, section, correct FROM attempts ORDER BY answered_at, id"
    ).fetchall():
        q, s, o = r["question_id"], r["section"], r["correct"]
        bq = b.get(q, 0.0)
        th = theta.get(s, 0.0)
        expected = 1.0 / (1.0 + math.exp(-(th - bq)))
        theta[s] = th + K_THETA * (o - expected)
        b[q] = bq + K_B * (expected - o)
    return theta, b


def expected_success(theta: float, b: float) -> float:
    return 1.0 / (1.0 + math.exp(-(theta - b)))


def select_drill(conn, section: int, count: int,
                 rng: random.Random | None = None) -> list[str]:
    """θ-aware, coverage-aware, deterministic drill selection for one section.

    Priority (ascending sort key, so smallest first):
      1. subsections with no cold probe at all (close real blind spots first)
      2. unseen before seen (new material first)
      3. outstanding misses — questions whose last answer was wrong
      4. least-recently-seen LOCAL day (rotation: this is what stops a drill from
         re-serving the same handful of questions every session)
      5. closeness of difficulty b to the productive-zone target (θ - offset)
      6. id (stable tiebreak)
    Cold start (no attempts in the section) → random sample for variety.

    Key 1 used to be the RAW count of fresh attempts per subsection. Once the
    bank had been seen, those counts froze, so the smallest subsections sorted
    first forever and the drill served the same ~20 questions on every run —
    the rest of the section was unreachable. Bucketing it to probed/unprobed and
    rotating on last-seen day fixes that while keeping the coverage intent.
    Key 4 is a DAY, not a timestamp, so the productive-zone ordering still
    decides within a day's worth of material.
    """
    rng = rng or random.Random()
    pool = conn.execute(
        "SELECT id, subsection FROM questions WHERE section = ? ORDER BY id", (section,)
    ).fetchall()
    if not pool:
        return []

    # attempts in this section?
    seen_rows = conn.execute(
        "SELECT DISTINCT question_id FROM attempts WHERE section = ?", (section,)
    ).fetchall()
    seen = {r["question_id"] for r in seen_rows}
    if not seen:
        ids = [r["id"] for r in pool]
        return rng.sample(ids, min(count, len(ids)))

    # subsections that have been cold-probed at least once (coverage pull-forward)
    probed_subs = {
        r["subsection"]
        for r in conn.execute(
            # tail placeholders bind after the CTE's own — hence params + (section,)
            cold_sql("SELECT DISTINCT subsection FROM cold WHERE section = ?"),
            cold_params() + (section,),
        ).fetchall()
    }

    # per question: most recent attempt (local day) and whether it was wrong
    last = {
        r["question_id"]: r
        for r in conn.execute(
            """
            SELECT question_id, answered_at, correct FROM (
                SELECT question_id, answered_at, correct,
                       ROW_NUMBER() OVER (
                           PARTITION BY question_id ORDER BY answered_at DESC, id DESC) rn
                FROM attempts WHERE section = ?
            ) WHERE rn = 1
            """,
            (section,),
        ).fetchall()
    }
    last_day = {q: timeutil.local_day(r["answered_at"]) for q, r in last.items()}

    theta, b = compute_ability_difficulty(conn)
    target_b = theta.get(section, 0.0) - TARGET_OFFSET

    def key(row):
        qid, sub = row["id"], row["subsection"]
        return (
            1 if sub in probed_subs else 0,
            0 if qid not in seen else 1,
            0 if (qid in last and not last[qid]["correct"]) else 1,
            last_day.get(qid, ""),
            abs(b.get(qid, 0.0) - target_b),
            qid,
        )

    ordered = sorted(pool, key=key)
    return [r["id"] for r in ordered[:count]]

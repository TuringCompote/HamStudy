"""Quiz construction: per-section drill + full mock exam.

Selection here uses randomness on purpose — it is NOT the deterministic analysis
path (constitution §5 governs mastery/trend/scheduling/readiness, not which
questions get served). Adaptive, ability-aware selection arrives in Phase 4.5;
this is uniform-random sampling for the MVP.

Mock exam mirrors the real exam: 100 questions sampled proportionally to each
section's share of the bank, via the largest-remainder method so the counts sum
to exactly 100 and match the bank's section distribution.
"""
from __future__ import annotations

import random

from app.db import queries
from app.engine import scheduler, adaptive

MOCK_EXAM_SIZE = 100
DEFAULT_DRILL_SIZE = 20
DEFAULT_REVIEW_SIZE = 20
DIAGNOSTIC_SIZE = 8


def allocate_proportional(sizes: dict[int, int], total: int) -> dict[int, int]:
    """Largest-remainder apportionment of `total` across sections by `sizes`."""
    grand = sum(sizes.values())
    if grand == 0:
        return {s: 0 for s in sizes}
    exact = {s: total * n / grand for s, n in sizes.items()}
    floors = {s: int(v) for s, v in exact.items()}
    remainder = total - sum(floors.values())
    # hand out the leftover seats to the largest fractional remainders
    order = sorted(exact, key=lambda s: (exact[s] - floors[s], sizes[s]), reverse=True)
    for s in order[:remainder]:
        floors[s] += 1
    return floors


def build_drill(conn, section: int, count: int = DEFAULT_DRILL_SIZE,
                rng: random.Random | None = None) -> list[dict]:
    """`count` questions from one section, chosen by the adaptive selector
    (θ-aware + coverage-aware; random only at cold start). No answers in payload."""
    chosen = adaptive.select_drill(conn, section, count, rng=rng)
    return queries.questions_for_ids(conn, chosen)


def build_diagnostic(conn, section: int, size: int = DIAGNOSTIC_SIZE,
                     rng: random.Random | None = None) -> list[dict]:
    """A short placement probe spanning the section's subsections (§6d.1).
    Round-robin over shuffled subsection buckets so the probe isn't all from one
    subsection. No answers in the payload."""
    rng = rng or random.Random()
    frame = queries.all_question_ids_by_subsection(conn)
    buckets = [list(ids) for (sec, _sub), ids in frame.items() if sec == section]
    if not buckets:
        return []
    for b in buckets:
        rng.shuffle(b)
    rng.shuffle(buckets)
    picked: list[str] = []
    while len(picked) < size and any(buckets):
        for b in buckets:
            if b:
                picked.append(b.pop())
                if len(picked) >= size:
                    break
        buckets = [b for b in buckets if b]
    return queries.questions_for_ids(conn, picked)


def build_review(conn, count: int = DEFAULT_REVIEW_SIZE) -> list[dict]:
    """Up to `count` questions that are due for spaced-repetition review, most
    overdue / weakest first (order from the deterministic scheduler; no answers
    in the payload)."""
    due = scheduler.due_reviews(conn, limit=count)
    return queries.questions_for_ids(conn, due)


def build_mock_exam(conn, size: int = MOCK_EXAM_SIZE,
                    rng: random.Random | None = None) -> list[dict]:
    """`size`-question exam, section-proportional, sampled across subsections.

    Within each section we spread picks across its subsections (round-robin over
    shuffled subsection buckets) so a section's allocation isn't drawn from a
    single subsection — a lightweight nod to the real exam's sub-category spread.
    """
    rng = rng or random.Random()
    sizes = queries.section_sizes(conn)
    alloc = allocate_proportional(sizes, size)
    frame = queries.all_question_ids_by_subsection(conn)

    # group the sampling frame by section -> list of subsection buckets
    by_section: dict[int, list[list[str]]] = {}
    for (sec, _sub), ids in frame.items():
        by_section.setdefault(sec, []).append(list(ids))

    picked: list[str] = []
    for section, n in alloc.items():
        buckets = [b[:] for b in by_section.get(section, [])]
        for b in buckets:
            rng.shuffle(b)
        rng.shuffle(buckets)
        taken = 0
        # round-robin across subsection buckets until we've taken `n`
        while taken < n and any(buckets):
            for b in buckets:
                if not b:
                    continue
                picked.append(b.pop())
                taken += 1
                if taken >= n:
                    break
            buckets = [b for b in buckets if b]

    rng.shuffle(picked)
    return queries.questions_for_ids(conn, picked)

"""Self-contained engine regression tests (no real DB, no AI, never spends).

Unlike `smoke_test.py` (which runs the HTTP surface against a copy of the real
`data/hamstudy.db`), this builds a synthetic bank + attempt log in a temp file,
so it runs anywhere — including a fresh clone with no data/ directory.

Run from the repo root:

    python tests/engine_test.py

Covers the "my scores never change" class of bug:
  1. fresh accuracy RECOVERS as questions are re-earned after the cooldown
  2. ...but warm repeats inside the cooldown never inflate it
  3. the engine stays deterministic (constitution §5)
  4. repeated drills rotate through the section instead of re-serving the same
     handful of questions
  5. the coach's focus section is the one the dashboard shows as weakest
"""
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # repo root on path

_tmp = Path(tempfile.mkdtemp(prefix="hamstudy_engine_")) / "engine_test.db"
os.environ["HAMSTUDY_DB"] = str(_tmp)

from app import config  # noqa: E402

config.DB_PATH = _tmp
config.AI_PROVIDER = "stub"

from app.db.init_db import init_db  # noqa: E402
from app.engine import adaptive, analysis, coach, mastery, readiness  # noqa: E402

SECTION_SIZES = {1: 40, 2: 40, 3: 40, 4: 40, 5: 40, 6: 40, 7: 40, 8: 40}
SUBSECTIONS = 4
T0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)


def build_bank(conn):
    ids = {}
    for sec, n in SECTION_SIZES.items():
        ids[sec] = []
        for i in range(n):
            sub = (i % SUBSECTIONS) + 1
            qid = f"B-{sec:03d}-{sub:03d}-{i:03d}"
            conn.execute(
                "INSERT INTO questions"
                "(id,section,subsection,qnum,text,options,correct_index,bank_version)"
                " VALUES (?,?,?,?,?,?,?,?)",
                (qid, sec, sub, i, f"question {i}",
                 json.dumps(["a", "b", "c", "d"]), 0, "test"),
            )
            ids[sec].append(qid)
    conn.commit()
    return ids


def attempt(conn, qid, when, ok, mode="drill"):
    sec, sub = int(qid.split("-")[1]), int(qid.split("-")[2])
    conn.execute(
        "INSERT INTO attempts"
        "(question_id,section,subsection,answered_at,chosen_index,correct,response_ms,mode)"
        " VALUES (?,?,?,?,?,?,?,?)",
        (qid, sec, sub, when.isoformat(), 0 if ok else 1, 1 if ok else 0, 9000, mode),
    )


def fresh(conn, section):
    return mastery.compute_section_mastery(conn)[section]["fresh_pct"]


def main():
    conn = init_db()
    ids = build_bank(conn)
    cooldown = timedelta(days=config.FRESH_COOLDOWN_DAYS)

    # --- day 0: first exposure across the whole bank, 50% right in section 1 ---
    for sec, qids in ids.items():
        for i, qid in enumerate(qids):
            attempt(conn, qid, T0 + timedelta(seconds=i), ok=(i % 2 == 0))
    conn.commit()
    baseline = fresh(conn, 1)
    assert baseline == 50.0, f"expected 50% first-exposure accuracy, got {baseline}"
    print(f"1. first exposure: section 1 fresh = {baseline}%")

    # --- warm repeats (same day) must NOT move fresh accuracy ----------------
    for round_ in range(3):
        for i, qid in enumerate(ids[1]):
            attempt(conn, qid, T0 + timedelta(hours=1 + round_, seconds=i), ok=True)
    conn.commit()
    warm = fresh(conn, 1)
    assert warm == baseline, (
        f"warm cramming inflated fresh accuracy: {baseline}% -> {warm}%")
    print(f"2. 120 warm repeats, all correct: fresh still {warm}% (correctly ignored)")
    fvr = analysis.fresh_vs_review(conn)[1]
    assert fvr["review_pct"] == 100.0 and fvr["fresh_pct"] == baseline
    print(f"   fresh/review split: {fvr['fresh_pct']}% cold vs {fvr['review_pct']}% warm")

    # --- re-earning AFTER the cooldown must move it (the reported bug) -------
    later = T0 + cooldown + timedelta(days=1)
    for i, qid in enumerate(ids[1]):
        attempt(conn, qid, later + timedelta(seconds=i), ok=True)
    conn.commit()
    recovered = fresh(conn, 1)
    assert recovered == 100.0, (
        f"REGRESSION: fresh accuracy frozen at {recovered}% after re-earning "
        f"every question past the cooldown (expected 100%)")
    print(f"3. re-earned past the cooldown: fresh {baseline}% -> {recovered}%")

    st = mastery.compute_section_mastery(conn)[1]
    assert st["tier"] == "test-out" and st["meets_honours"], st["tier"]
    assert 1 not in readiness.readiness(conn)["weakest_sections"]
    print(f"   tier now '{st['tier']}', section no longer flagged weakest")

    # a later lapse must pull it back down — the metric tracks current recall
    lapse = later + cooldown + timedelta(days=1)
    for i, qid in enumerate(ids[1][:20]):
        attempt(conn, qid, lapse + timedelta(seconds=i), ok=False)
    conn.commit()
    lapsed = fresh(conn, 1)
    assert lapsed == 50.0, f"expected 50% after lapsing half the section, got {lapsed}"
    print(f"4. lapsed half the section: fresh {recovered}% -> {lapsed}% (moves both ways)")

    # --- determinism (constitution §5): same log in => same numbers out ------
    a = mastery.compute_section_mastery(conn)
    b = mastery.compute_section_mastery(conn)
    assert a == b, "compute_section_mastery is not idempotent"
    assert analysis.section_trend(conn) == analysis.section_trend(conn)
    assert readiness.readiness(conn) == readiness.readiness(conn)
    assert adaptive.select_drill(conn, 2, 10) == adaptive.select_drill(conn, 2, 10)
    print("5. deterministic: repeated computation returns identical results")

    # --- drill rotation: consecutive drills must not re-serve the same set ---
    served = []
    t = lapse + timedelta(days=1)
    for run in range(4):
        picked = adaptive.select_drill(conn, 3, 10)
        assert len(set(picked)) == 10, "drill served duplicate questions"
        served.append(set(picked))
        for i, qid in enumerate(picked):
            attempt(conn, qid, t + timedelta(days=run, seconds=i), ok=True)
        conn.commit()
    union = set().union(*served)
    assert len(union) >= 30, (
        f"REGRESSION: 4 drills of 10 covered only {len(union)} distinct questions "
        f"— selection is stuck on the same subset")
    print(f"6. 4 consecutive drills of 10 covered {len(union)}/{SECTION_SIZES[3]} "
          f"distinct questions in the section")

    # --- coach focus agrees with the dashboard's weakest row ----------------
    by_section = mastery.compute_section_mastery(conn)
    session = coach.suggest_session(conn, by_section)
    rated = [s for s in by_section.values() if s["fresh_pct"] is not None]
    weakest_shown = min(rated, key=lambda s: s["fresh_pct"])
    assert by_section[session["focus_section"]]["fresh_pct"] == weakest_shown["fresh_pct"], (
        f"coach focuses section {session['focus_section']} but the dashboard shows "
        f"section {weakest_shown['section']} as weakest")
    print(f"7. coach focus = section {session['focus_section']} "
          f"({by_section[session['focus_section']]['fresh_pct']}%), matches weakest row")

    conn.close()
    print("\nengine_test: all assertions passed")


if __name__ == "__main__":
    main()

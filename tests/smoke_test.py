"""End-to-end smoke test for the Phase-2 quiz engine.

Runs against a disposable COPY of the real DB (so it never pollutes the real
`attempts` log). Run from the repo root:

    python tests/smoke_test.py

Exits non-zero on any failed assertion.
"""
import collections
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # repo root on path

from app import config

# Disposable DB copy, wired in before the app reads config.DB_PATH.
_src = config.DB_PATH
_tmp = os.path.join(tempfile.gettempdir(), "hamstudy_smoke.db")
shutil.copy(_src, _tmp)
os.environ["HAMSTUDY_DB"] = _tmp
config.DB_PATH = config.Path(_tmp)  # override the already-imported value

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.db.init_db import connect  # noqa: E402
from app.engine.mastery import compute_section_mastery  # noqa: E402

c = TestClient(app)


def main() -> None:
    h = c.get("/api/health").json()
    print("health:", h)
    assert h["questions"] == 984

    # drill must not leak answers
    dq = c.post("/api/quiz", json={"mode": "drill", "section": 5, "count": 10}).json()
    print("drill:", dq["count"], "questions")
    assert dq["count"] == 10
    assert all("correct_index" not in q for q in dq["questions"]), "ANSWER LEAKED (drill)"
    assert all(q["section"] == 5 for q in dq["questions"])

    # mock exam: 100 q, section-proportional, no answers
    mq = c.post("/api/quiz", json={"mode": "exam"}).json()
    dist = collections.Counter(q["section"] for q in mq["questions"])
    print("mock:", mq["count"], "questions; section dist:", dict(sorted(dist.items())))
    assert mq["count"] == 100
    assert all("correct_index" not in q for q in mq["questions"]), "ANSWER LEAKED (exam)"
    assert sum(dist.values()) == 100

    # grading + recording
    conn = connect()
    qid = dq["questions"][0]["id"]
    ci = conn.execute(
        "SELECT correct_index FROM questions WHERE id=?", (qid,)
    ).fetchone()["correct_index"]
    before = conn.execute("SELECT COUNT(*) c FROM attempts").fetchone()["c"]
    r_ok = c.post("/api/attempt", json={
        "question_id": qid, "chosen_index": ci, "mode": "drill", "response_ms": 1500
    }).json()
    r_bad = c.post("/api/attempt", json={
        "question_id": qid, "chosen_index": (ci + 1) % 4, "mode": "drill"
    }).json()
    after = conn.execute("SELECT COUNT(*) c FROM attempts").fetchone()["c"]
    print("grade ok:", r_ok, "| grade wrong:", r_bad, "| attempts +", after - before)
    assert r_ok["correct"] is True and r_bad["correct"] is False
    assert r_ok["correct_index"] == ci
    assert after - before == 2

    # deterministic mastery reflects the two attempts (1/2 = 50%)
    m = compute_section_mastery(conn)[5]
    print("section 5 mastery:", m["mastery_pct"], "answered", m["answered"])
    assert m["answered"] == 2 and m["correct"] == 1 and m["mastery_pct"] == 50.0

    # allocate_proportional sums correctly and tracks the bank distribution
    from app.quiz import allocate_proportional
    sizes = {1: 199, 2: 99, 3: 199, 4: 63, 5: 142, 6: 140, 7: 87, 8: 55}
    alloc = allocate_proportional(sizes, 100)
    assert sum(alloc.values()) == 100, alloc
    assert alloc[1] >= alloc[8], alloc  # bigger section gets >= share

    # pages render
    assert c.get("/").status_code == 200
    assert c.get("/quiz?mode=exam").status_code == 200
    assert c.get("/quiz?mode=drill&section=3").status_code == 200

    # section pages (Learn -> Interact -> Drill)
    for s in range(1, 9):
        assert c.get(f"/section/{s}").status_code == 200, s
    assert c.get("/section/9").status_code == 404
    s5 = c.get("/section/5").text
    assert "Learn" in s5 and "Interact" in s5 and "Drill" in s5
    assert 'data-tool="ohms"' in s5
    assert "Basic Electronics" in s5

    # tool assets + lesson content served
    assert c.get("/static/tokens.css").status_code == 200
    for f in ["registry", "ohms", "reactance", "decibel", "swr", "wavelength"]:
        assert c.get(f"/static/tools/{f}.js").status_code == 200, f

    # lesson text exists for every section (original content)
    from app import content
    for s in range(1, 9):
        assert content.lesson_html(s), f"missing lesson for section {s}"

    conn.close()
    print("\nALL SMOKE CHECKS PASSED")


if __name__ == "__main__":
    main()

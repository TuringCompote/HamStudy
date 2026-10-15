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
config.AI_PROVIDER = "stub"         # never spend real money during tests

# Redirect the OTHER durable outputs too — journal .md files and
# recommendation.json used to leak into the real data/ tree on every test run.
_tmpdir = tempfile.mkdtemp(prefix="hamstudy_smoke_")
config.JOURNAL_DIR = config.Path(_tmpdir) / "journal"
config.RECOMMENDATION_PATH = config.Path(_tmpdir) / "recommendation.json"

# Advanced track (Phase 7): its own disposable copy — the two stores never mix.
_HAVE_ADV = config.DB_PATH_ADVANCED.exists()
if _HAVE_ADV:
    _tmp_adv = os.path.join(tempfile.gettempdir(), "hamstudy_smoke_advanced.db")
    shutil.copy(config.DB_PATH_ADVANCED, _tmp_adv)
    config.DB_PATH_ADVANCED = config.Path(_tmp_adv)
else:
    config.DB_PATH_ADVANCED = config.Path(_tmpdir) / "advanced_empty.db"
config.JOURNAL_DIR_ADVANCED = config.Path(_tmpdir) / "journal_advanced"
config.RECOMMENDATION_PATH_ADVANCED = config.Path(_tmpdir) / "recommendation_advanced.json"

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
    m_before = compute_section_mastery(conn)[5]   # source DB may already have s5 attempts
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

    # deterministic mastery reflects the two new attempts (delta, not absolute —
    # the source DB is a copy of real study data and may already have s5 attempts)
    m = compute_section_mastery(conn)[5]
    print("section 5 mastery:", m["mastery_pct"], "answered", m["answered"])
    assert m["answered"] == m_before["answered"] + 2
    assert m["correct"] == m_before["correct"] + 1

    # allocate_proportional sums correctly and tracks the bank distribution
    from app.quiz import allocate_proportional
    sizes = {1: 199, 2: 99, 3: 199, 4: 63, 5: 142, 6: 140, 7: 87, 8: 55}
    alloc = allocate_proportional(sizes, 100)
    assert sum(alloc.values()) == 100, alloc
    assert alloc[1] >= alloc[8], alloc  # bigger section gets >= share

    # recommendation engine (deterministic) + AIProvider stub
    from app.engine import recommend, analysis
    assert analysis.section_trend(conn) == analysis.section_trend(conn), "trend not deterministic"
    rec = recommend.build_recommendation(conn)
    assert rec == recommend.build_recommendation(conn), "recommendation not deterministic"
    assert "next_session" in rec and "readiness" in rec and "review_queue" in rec
    from app.coaching.ai_provider import get_provider, StubProvider
    prov = get_provider(force_stub=True)
    assert isinstance(prov, StubProvider)
    ex = prov.explain(question={"options": ["a", "b", "c", "d"], "correct_index": 2}, chosen_index=0)
    assert ex.degraded and ex.cost_usd == 0.0 and "correct answer" in ex.text.lower()

    # dashboard renders the instrument-panel layout (also refreshes recommendation.json)
    dash = c.get("/")
    assert dash.status_code == 200
    assert config.RECOMMENDATION_PATH.exists(), "recommendation.json not written"
    assert conn.execute("SELECT COUNT(*) c FROM recommendation").fetchone()["c"] >= 1
    for marker in ["readiness-val", "stat-cards", "session-card",
                   "Per-section mastery", "tier-text-deep", "app-badge"]:
        assert marker in dash.text, marker

    # deterministic coach aggregates
    from app.engine import coach
    summ = coach.dashboard_summary(conn)
    assert summ["bank_size"] == 984
    assert 0 <= summ["mastered"] <= 984
    assert isinstance(summ["streak"], int)
    assert "review_due" in summ

    # spaced-repetition scheduler + review mode
    from app.engine import scheduler
    assert scheduler.compute_schedule(conn) == scheduler.compute_schedule(conn), "scheduler not deterministic"
    # the wrong attempt recorded above is in box 1, due immediately
    assert scheduler.review_due_count(conn) >= 1
    rv = c.post("/api/quiz", json={"mode": "review"}).json()
    print("review:", rv["count"], "due questions")
    assert rv["count"] >= 1
    assert all("correct_index" not in q for q in rv["questions"]), "ANSWER LEAKED (review)"
    assert c.get("/quiz?mode=review").status_code == 200

    # readiness + coverage guarantee (§6d.4)
    from app.engine import readiness as rmod
    rd = rmod.readiness(conn)
    assert isinstance(rd["exam_ready"], bool)
    assert not rd["exam_ready"]  # smoke state is nowhere near ready
    cov = rmod.coverage(conn)
    assert cov[0]["total_subsections"] > 0
    bs = compute_section_mastery(conn)
    assert "fresh_pct" in bs[5] and "tier" in bs[5]

    # adaptive Elo/IRT-lite — deterministic θ + difficulty
    from app.engine import adaptive
    t1, b1 = adaptive.compute_ability_difficulty(conn)
    t2, b2 = adaptive.compute_ability_difficulty(conn)
    assert t1 == t2 and b1 == b2, "adaptive not deterministic"
    assert len(adaptive.select_drill(conn, 5, 10)) == 10

    # diagnostic placement (§6d.1)
    dgq = c.post("/api/quiz", json={"mode": "diagnostic", "section": 7}).json()
    print("diagnostic:", dgq["count"], "questions")
    assert 1 <= dgq["count"] <= 10
    assert all("correct_index" not in q for q in dgq["questions"]), "ANSWER LEAKED (diagnostic)"
    served = [q["id"] for q in dgq["questions"]]
    for q in served:
        ci = conn.execute("SELECT correct_index FROM questions WHERE id=?", (q,)).fetchone()["correct_index"]
        c.post("/api/attempt", json={"question_id": q, "chosen_index": ci, "mode": "diagnostic"})
    dres = c.post("/api/diagnostic", json={"section": 7, "served_ids": served, "confidence_prior": "rusty"}).json()
    assert dres["tier"] == "test-out" and dres["score_pct"] == 100.0, dres  # all answered correctly
    from app.engine import diagnostic as diagmod
    assert diagmod.has_diagnostic(conn, 7)
    assert c.get("/quiz?mode=diagnostic&section=7&confidence=rusty").status_code == 200

    # AI layer (stub-forced — no spend), budget guard, journal
    from app.coaching.ai_provider import get_provider, StubProvider
    from app.coaching import usage as usagemod
    assert isinstance(get_provider(), StubProvider)
    ex = c.post("/api/explain", json={"question_id": served[0], "chosen_index": 0}).json()
    if ex["source"] == "batch":                      # stored explanation present
        assert ex["layers"]["core"] and "default_layers" in ex
    else:                                            # live fallback (stub-forced)
        assert ex["degraded"] is True and ex["text"] and ex["cost_usd"] == 0
    assert usagemod.estimate_cost("claude-opus-4-8", 1_000_000, 1_000_000) == 30.0  # $5 + $25
    ok, mtd = usagemod.within_budget(conn)
    assert ok and mtd == 0.0
    st = c.get("/api/ai-status").json()
    assert "within_budget" in st and st["provider"] == "stub"
    jr = c.post("/api/journal").json()
    assert jr["degraded"] is True
    assert Path(jr["path"]).exists()

    # day digest (deterministic facts the journal narrates) + journal body
    from app.engine import day_digest
    d1 = day_digest.build_day_digest(conn)
    assert d1 == day_digest.build_day_digest(conn), "day digest not deterministic"
    assert d1["answered"] >= 2 and d1["miss_count"] >= 1   # this run's attempts
    assert d1["misses"] and d1["misses"][0]["chosen"]      # miss detail carries texts
    jtext = Path(jr["path"]).read_text(encoding="utf-8")
    assert "## Today" in jtext and "### Missed today" in jtext

    # journal week view (embedded on the dashboard)
    assert "jr-days" in c.get("/").text and "journal.js" in c.get("/").text
    dts = c.get("/api/journal/dates").json()["dates"]
    today = jr["entry_date"]        # the date the write itself used (config.TZ local day)
    assert today in dts                                  # just wrote it above
    assert c.get(f"/api/journal/entry/{today}").json()["html"]
    assert c.get("/api/journal/entry/not-a-date").status_code == 400
    assert c.get("/api/journal/entry/2000-01-01").status_code == 404

    # diagnose (stub-forced): section 5 has a wrong attempt -> real summary -> stub;
    # a section with no attempts -> friendly empty note
    dg = c.post("/api/diagnose", json={"section": 5}).json()
    assert dg["text"] and dg["empty"] is False and dg["degraded"] is True
    dg2 = c.post("/api/diagnose", json={"section": 2}).json()
    assert dg2["empty"] is True
    assert analysis.section_miss_summary(conn, 5)        # deterministic, non-empty

    # formula-sheet trainer
    ft = c.get("/formula-trainer")
    assert ft.status_code == 200
    assert "formula-trainer" in ft.text and "data-formulas" in ft.text
    assert c.get("/static/tools/formulatrainer.js").status_code == 200
    from app import formulas as _f
    assert len(_f.FORMULAS) >= 15

    # pages render
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
    for f in ["registry", "ohms", "reactance", "decibel", "swr", "wavelength", "seriesparallel", "bandplan", "propagation"]:
        assert c.get(f"/static/tools/{f}.js").status_code == 200, f

    # lesson text exists for every section (original content)
    from app import content
    for s in range(1, 9):
        assert content.lesson_html(s), f"missing lesson for section {s}"

    conn.close()

    advanced()
    print("\nALL SMOKE CHECKS PASSED")


def advanced() -> None:
    """The Advanced track: same engine, separate URL space + store. Every
    assertion here is the mirror of a Basic one above, through `/advanced`."""
    from app import quals
    from app.db.init_db import connect as _connect

    h = c.get("/advanced/api/health").json()
    print("advanced health:", h)
    assert h["qual"] == "advanced" and h["sections"] == 7 and h["exam_size"] == 50
    assert c.get("/advanced", follow_redirects=False).status_code == 307
    page = c.get("/advanced/")
    assert page.status_code == 200 and 'data-qual="advanced"' in page.text
    assert "/advanced/quiz?mode=exam" in page.text          # links stay in the track
    assert "qual-switch" in page.text and "qual-link on" in page.text
    # Basic pages must not link into the Advanced space and vice versa
    assert "/advanced/section/" not in c.get("/").text

    if not _HAVE_ADV:
        print("advanced: bank not ingested here — structural checks only "
              "(python -m app.db.ingest --qual advanced to enable the full run)")
        assert "No Advanced bank yet" in page.text
        return

    # isolation: the stores are different files with different banks
    assert h["questions"] > 0 and h["questions"] != 984
    assert config.DB_PATH_ADVANCED != config.DB_PATH

    dq = c.post("/advanced/api/quiz", json={"mode": "drill", "section": 1, "count": 10}).json()
    assert dq["count"] == 10 and all("correct_index" not in q for q in dq["questions"])
    assert all(q["id"].startswith("A-") and q["section"] == 1 for q in dq["questions"])

    mq = c.post("/advanced/api/quiz", json={"mode": "exam"}).json()
    dist = collections.Counter(q["section"] for q in mq["questions"])
    print("advanced mock:", mq["count"], "questions; section dist:", dict(sorted(dist.items())))
    assert mq["count"] == 50 and set(dist) <= set(range(1, 8))
    assert all("correct_index" not in q for q in mq["questions"]), "ANSWER LEAKED (adv exam)"
    assert c.post("/advanced/api/quiz", json={"mode": "drill", "section": 8}).status_code == 404

    # an Advanced attempt lands ONLY in the Advanced store
    tok = quals.activate("advanced")
    try:
        aconn = _connect()
        qid = dq["questions"][0]["id"]
        ci = aconn.execute("SELECT correct_index FROM questions WHERE id=?", (qid,)).fetchone()["correct_index"]
        a_before = aconn.execute("SELECT COUNT(*) c FROM attempts").fetchone()["c"]
    finally:
        quals.reset(tok)
    bconn = _connect()                                   # Basic store (default context)
    b_before = bconn.execute("SELECT COUNT(*) c FROM attempts").fetchone()["c"]
    r = c.post("/advanced/api/attempt", json={"question_id": qid, "chosen_index": (ci + 1) % 4,
                                              "mode": "drill", "response_ms": 2000}).json()
    assert r["correct"] is False
    assert bconn.execute("SELECT COUNT(*) c FROM attempts").fetchone()["c"] == b_before
    assert aconn.execute("SELECT COUNT(*) c FROM attempts").fetchone()["c"] == a_before + 1
    # and a Basic id is unknown to the Advanced track
    assert c.post("/advanced/api/attempt", json={"question_id": "B-001-001-001",
                                                 "chosen_index": 0, "mode": "drill"}).status_code == 404

    # explanations: the committed Advanced seed (deeper layers incl. worked_example)
    ex = c.post("/advanced/api/explain", json={"question_id": qid, "chosen_index": 0}).json()
    if ex["source"] == "batch":
        assert ex["layers"]["core"] and ex["layers"]["distractors"]
    have = aconn.execute("SELECT COUNT(*) c FROM explanations").fetchone()["c"]
    print("advanced explanations stored:", have, "/", h["questions"])

    # journal + recommendation go to the Advanced paths, section pages render
    jr = c.post("/advanced/api/journal").json()
    assert Path(jr["path"]).parent == config.JOURNAL_DIR_ADVANCED
    assert "(Advanced)" in Path(jr["path"]).read_text(encoding="utf-8")
    assert config.RECOMMENDATION_PATH_ADVANCED.exists()
    for s in range(1, 8):
        assert c.get(f"/advanced/section/{s}").status_code == 200, s
    assert c.get("/advanced/section/8").status_code == 404
    assert "Advanced theory" in c.get("/advanced/").text
    ft = c.get("/advanced/formula-trainer")
    assert ft.status_code == 200 and "Carson" in ft.text
    from app import content
    tok = quals.activate("advanced")
    try:
        missing = [s for s in range(1, 8) if not content.lesson_html(s)]
    finally:
        quals.reset(tok)
    assert not missing, f"missing Advanced lesson(s): {missing}"
    aconn.close(); bconn.close()
    print("advanced: OK")


if __name__ == "__main__":
    main()

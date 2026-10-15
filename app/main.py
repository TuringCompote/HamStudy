"""FastAPI app — quiz engine + dashboard for BOTH qualifications.

Server-rendered dashboard + quiz-runner shell (Jinja); the quiz itself runs in
vanilla JS against a small JSON API. Correct answers are NEVER included in the
quiz payload — the server grades each submission and appends to `attempts`.

Two qualifications, two URL spaces, two stores (Phase 7):
    /            Basic     -> data/hamstudy.db
    /advanced    Advanced  -> data/hamstudy_advanced.db
The same `router` is mounted twice; `_QualScope` is a tiny ASGI wrapper that
activates the right profile (app/quals.py ContextVar) for each request, so
`connect()`, section lists, paths and labels all resolve to the right track with
no branching in the routes or the engine. `/static` is shared (one UI, themed per
qualification via <html data-qual>). Templates/JS build links from `BASE`
(the qualification's URL prefix) — never a hardcoded "/".

Run:  uvicorn app.main:app --reload
"""
from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from app.db import queries
from app.db.init_db import connect
from app.engine import mastery, coach, diagnostic, recommend, analysis, adaptive
from app import quiz, config, tools, content, formulas, quals
from app.coaching.ai_provider import get_provider
from app.coaching import journal as journal_mod, usage as usage_mod, corpus as corpus_mod
from app.coaching import explain_batch

BASE = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE / "templates"))
templates.env.globals["APP_NAME"] = config.APP_NAME  # available in every template
templates.env.globals["QUALS"] = list(quals.QUALS.values())  # topbar switcher

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MAX_SECTION = max(q.section_count for q in quals.QUALS.values())

router = APIRouter()


def _render(request: Request, name: str, ctx: dict):
    """TemplateResponse with the per-qualification context folded in: UI_CONFIG
    (tier map + bars + qual context → window.ElmerConfig), QUAL (the profile) and
    BASE (its URL prefix; every link/fetch in templates and JS is built on it)."""
    q = quals.current()
    return templates.TemplateResponse(
        request, name,
        {**ctx, "UI_CONFIG": mastery.ui_config(), "QUAL": q, "BASE": q.url_prefix},
    )


def _check_section(section: int) -> None:
    if section not in quals.current().sections:
        raise HTTPException(404, f"section must be one of {quals.current().sections}")


# --- request models ---
class QuizRequest(BaseModel):
    mode: str = Field(pattern="^(drill|exam|review|diagnostic)$")
    section: int | None = Field(default=None, ge=1, le=MAX_SECTION)
    count: int | None = Field(default=None, ge=1, le=200)


class AttemptRequest(BaseModel):
    question_id: str
    chosen_index: int = Field(ge=0, le=3)
    mode: str = Field(pattern="^(drill|exam|review|diagnostic)$")
    response_ms: int | None = Field(default=None, ge=0)


class DiagnosticRequest(BaseModel):
    section: int = Field(ge=1, le=MAX_SECTION)
    served_ids: list[str] = Field(min_length=1, max_length=20)
    confidence_prior: str | None = None


class ExplainRequest(BaseModel):
    question_id: str
    chosen_index: int = Field(ge=0, le=3)


class DiagnoseRequest(BaseModel):
    section: int = Field(ge=1, le=MAX_SECTION)


# --- pages ---
@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    conn = connect()
    try:
        by_section = mastery.compute_section_mastery(conn)
        diagnostic.apply_diagnostic_tiers(conn, by_section)
        summary = coach.dashboard_summary(conn, by_section)
        rec = recommend.refresh(conn)  # build + persist recommendation.json, then read it back
        # surface per-section trend + the confident-but-wrong lamp on the rows
        wrong = analysis.wrong_classification(conn)
        for s in by_section.values():
            ps = rec["readiness"]["per_section"].get(s["section"], {})
            s["trend"] = ps.get("trend", "new")
            s["fast_wrong"] = wrong.get(s["section"], {}).get("fast_wrong", 0)
    finally:
        conn.close()
    return _render(
        request,
        "dashboard.html",
        {"sections": by_section, "summary": summary,
         "session": rec["next_session"], "rec": rec},
    )


@router.get("/section/{section}", response_class=HTMLResponse)
def section_page(request: Request, section: int):
    _check_section(section)
    conn = connect()
    try:
        by_section = mastery.compute_section_mastery(conn)
        diagnostic.apply_diagnostic_tiers(conn, by_section)
        stats = by_section[section]
        has_diag = diagnostic.has_diagnostic(conn, section)
        # instrument telemetry the engine already computes (pure presentation):
        # ability θ, fresh-vs-review split, confident-but-wrong count
        telemetry = None
        if stats["answered"]:
            theta, _b = adaptive.compute_ability_difficulty(conn)
            fvr = analysis.fresh_vs_review(conn).get(section, {})
            wc = analysis.wrong_classification(conn).get(
                section, {"fast_wrong": 0, "slow_wrong": 0})
            telemetry = {
                "theta": f"{theta.get(section, 0.0):+.2f}",
                "fresh_pct": fvr.get("fresh_pct"),
                "review_pct": fvr.get("review_pct"),
                "fast_wrong": wc["fast_wrong"],
            }
    finally:
        conn.close()
    # offer the placement probe when the section is essentially unrated
    offer_diagnostic = (not has_diag) and stats["fresh_answered"] < diagnostic.MIN_FRESH_FOR_TIER
    return _render(
        request,
        "section.html",
        {
            "section": section,
            "name": queries.section_names()[section],
            "lesson_html": content.lesson_html(section),
            "tools": tools.tools_for_section(section),
            "stats": stats,
            "offer_diagnostic": offer_diagnostic,
            "telemetry": telemetry,
        },
    )


@router.post("/api/diagnostic")
def api_diagnostic(req: DiagnosticRequest):
    _check_section(req.section)
    conn = connect()
    try:
        return diagnostic.record_diagnostic(
            conn, req.section, req.served_ids, req.confidence_prior
        )
    finally:
        conn.close()


@router.get("/manifest.webmanifest")
def manifest():
    """Web app manifest (name from config — never hardcode APP_NAME). iOS uses
    the apple-* metas in base.html for Add to Home Screen; this serves desktop
    Chrome/Edge and keeps the colors/icons in one generated place. Each
    qualification serves its own (start_url + name), so both can sit on the
    home screen as separate apps."""
    q = quals.current()
    return JSONResponse(
        {
            "name": f"{config.APP_NAME} — {q.label}",
            "short_name": q.short_name or config.APP_NAME,
            "start_url": f"{q.url_prefix}/",
            "display": "standalone",
            "background_color": "#0a0e0d",   # mirrors --bg (dark) in tokens.css
            "theme_color": "#0a0e0d",
            "icons": [
                {"src": "/static/icons/icon-192.png", "sizes": "192x192", "type": "image/png"},
                {"src": "/static/icons/icon-512.png", "sizes": "512x512", "type": "image/png"},
            ],
        },
        media_type="application/manifest+json",
    )


@router.get("/formula-trainer", response_class=HTMLResponse)
def formula_trainer(request: Request):
    return _render(request, "formula_trainer.html",
                   {"formulas": formulas.formulas_for(quals.current())})


@router.get("/quiz", response_class=HTMLResponse)
def quiz_page(request: Request, mode: str = "drill", section: int | None = None,
              confidence: str | None = None):
    if mode not in ("drill", "exam", "review", "diagnostic"):
        raise HTTPException(400, "mode must be 'drill', 'exam', 'review', or 'diagnostic'")
    if section is not None:
        _check_section(section)
    title = {"exam": "Mock Exam", "review": "Review",
             "diagnostic": f"Diagnostic — Section {section}"}.get(mode, f"Drill — Section {section}")
    return _render(
        request,
        "quiz.html",
        {"mode": mode, "section": section, "title": title,
         "confidence": confidence,
         "section_name": queries.section_names().get(section or 0, "")},
    )


# --- JSON API ---
@router.get("/api/sections")
def api_sections():
    conn = connect()
    try:
        by_section = mastery.compute_section_mastery(conn)
        # same tier semantics as the dashboard: diagnostic placement fills in
        # sections that don't have enough fresh attempts yet
        diagnostic.apply_diagnostic_tiers(conn, by_section)
        return {"sections": by_section,
                "summary": mastery.overall_summary(conn)}
    finally:
        conn.close()


@router.post("/api/quiz")
def api_quiz(req: QuizRequest):
    conn = connect()
    try:
        if req.mode == "exam":
            questions = quiz.build_mock_exam(conn)
        elif req.mode == "review":
            questions = quiz.build_review(conn, req.count or quiz.DEFAULT_REVIEW_SIZE)
            if not questions:
                raise HTTPException(404, "nothing is due for review right now")
        elif req.mode == "diagnostic":
            if req.section is None:
                raise HTTPException(400, "diagnostic requires a section")
            _check_section(req.section)
            questions = quiz.build_diagnostic(conn, req.section)
        else:
            if req.section is None:
                raise HTTPException(400, "drill requires a section")
            _check_section(req.section)
            questions = quiz.build_drill(
                conn, req.section, req.count or quiz.DEFAULT_DRILL_SIZE
            )
        if not questions:
            raise HTTPException(404, "no questions available for this request")
        return {"mode": req.mode, "count": len(questions), "questions": questions}
    finally:
        conn.close()


@router.post("/api/attempt")
def api_attempt(req: AttemptRequest):
    conn = connect()
    try:
        return queries.record_attempt(
            conn,
            question_id=req.question_id,
            chosen_index=req.chosen_index,
            mode=req.mode,
            response_ms=req.response_ms,
        )
    except ValueError as e:
        raise HTTPException(404, str(e))
    finally:
        conn.close()


@router.post("/api/explain")
def api_explain(req: ExplainRequest):
    """Cache-first (§6f): return the batch-generated structured layers if present,
    with adaptive reveal depth from the user's §6d tier. Falls back to a live
    explain() call (stub when over budget / no key) only if none is stored."""
    conn = connect()
    try:
        q = queries.get_question(conn, req.question_id, with_answer=True)
        if q is None:
            raise HTTPException(404, "unknown question id")
        # Pin the cache read to the question's CURRENT bank_version: after a bank
        # update rewords a question, its stale explanation must not surface — the
        # live fallback below covers the gap until a targeted re-batch.
        bv_row = conn.execute(
            "SELECT bank_version FROM questions WHERE id=?", (req.question_id,)
        ).fetchone()
        layers = explain_batch.get_explanation(
            conn, req.question_id, bank_version=bv_row["bank_version"])
        if layers is not None:
            by_section = mastery.compute_section_mastery(conn)
            diagnostic.apply_diagnostic_tiers(conn, by_section)
            tier = by_section[q["section"]]["tier"]
            default_layers = explain_batch.DEPTH_LAYERS.get(
                tier, explain_batch.DEPTH_LAYERS[None])
            return {"source": "batch", "tier": tier,
                    "default_layers": default_layers, "layers": layers}
        grounding = corpus_mod.ground_for_section(q["section"])
    finally:
        conn.close()
    # live fallback (no stored explanation yet)
    result = get_provider().explain(
        question=q, chosen_index=req.chosen_index, grounding=grounding)
    return {"source": "live", "text": result.text, "degraded": result.degraded,
            "model": result.model, "cost_usd": round(result.cost_usd, 6)}


@router.post("/api/diagnose")
def api_diagnose(req: DiagnoseRequest):
    """Live per-user misconception diagnosis for a section (Sonnet, budget-gated).
    Builds the miss summary deterministically from attempts; falls back to the stub
    when over budget / no key. Returns a friendly note when there are no misses."""
    _check_section(req.section)
    conn = connect()
    try:
        summary = analysis.section_miss_summary(conn, req.section)
        name = queries.section_names()[req.section]
        grounding = corpus_mod.ground_for_section(req.section)
    finally:
        conn.close()
    if not summary:
        return {"text": "No recurring misses in this section yet — drill some questions "
                        "and come back.", "degraded": False, "model": "-",
                "cost_usd": 0.0, "empty": True}
    res = get_provider().diagnose(section_name=name, miss_summary=summary, grounding=grounding)
    return {"text": res.text, "degraded": res.degraded, "model": res.model,
            "cost_usd": round(res.cost_usd, 6), "empty": False}


@router.post("/api/journal")
def api_journal():
    conn = connect()
    try:
        return journal_mod.write_journal(conn)
    finally:
        conn.close()


@router.get("/api/journal/dates")
def api_journal_dates():
    conn = connect()
    try:
        rows = conn.execute(
            "SELECT DISTINCT entry_date FROM journal ORDER BY entry_date"
        ).fetchall()
    finally:
        conn.close()
    return {"dates": [r["entry_date"] for r in rows]}


@router.get("/api/journal/entry/{entry_date}")
def api_journal_entry(entry_date: str):
    if not _DATE_RE.match(entry_date):       # guard against path traversal / junk
        raise HTTPException(400, "date must be YYYY-MM-DD")
    conn = connect()
    try:
        row = conn.execute(
            "SELECT file_path, summary FROM journal WHERE entry_date=? ORDER BY id DESC LIMIT 1",
            (entry_date,),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        raise HTTPException(404, "no journal entry for that date")
    import markdown as _md
    p = Path(row["file_path"])
    text = p.read_text(encoding="utf-8") if p.exists() else (row["summary"] or "")
    return {"date": entry_date, "html": _md.markdown(text, extensions=["extra"])}


@router.get("/api/ai-status")
def api_ai_status():
    conn = connect()
    try:
        ok, mtd = usage_mod.within_budget(conn)
    finally:
        conn.close()
    return {"provider": config.AI_PROVIDER, "within_budget": ok,
            "month_to_date_usd": round(mtd, 4), "ceiling_usd": config.AI_MONTHLY_BUDGET_USD}


@router.get("/api/health")
def health():
    conn = connect()
    try:
        n = conn.execute("SELECT COUNT(*) c FROM questions").fetchone()["c"]
        bv = conn.execute(
            "SELECT value FROM meta WHERE key='bank_version'"
        ).fetchone()
    finally:
        conn.close()
    q = quals.current()
    return {"status": "ok", "qual": q.code, "questions": n,
            "bank_version": bv["value"] if bv else None,
            "sections": q.section_count, "exam_size": q.exam_size}


# --- assembly: one trainer per qualification, mounted side by side -------------
class _QualScope:
    """ASGI wrapper: activate a qualification profile for the life of a request.
    Starlette's Mount already strips the prefix and sets scope["root_path"]; this
    only flips the ContextVar so `connect()` / `quals.current()` resolve correctly
    (contextvars propagate into the threadpool that runs the sync endpoints)."""

    def __init__(self, inner, code: str):
        self.inner, self.code = inner, code

    async def __call__(self, scope, receive, send):
        token = quals.activate(self.code)
        try:
            q = quals.current()
            if not q.db_path.exists():
                # a track whose bank hasn't been ingested yet still renders (empty),
                # with the dashboard pointing at the ingest step
                from app.db.init_db import init_db
                init_db(q.db_path).close()
            await self.inner(scope, receive, send)
        finally:
            quals.reset(token)


def create_app(qual: quals.Qual) -> FastAPI:
    sub = FastAPI(title=f"{config.APP_NAME} — Canadian {qual.label} trainer")
    sub.include_router(router)
    return sub


app = FastAPI(title=f"{config.APP_NAME} — Canadian Basic + Advanced trainer")
app.mount("/static", StaticFiles(directory=str(BASE / "static")), name="static")


@app.get("/advanced", include_in_schema=False)
def _advanced_slash():
    """`/advanced` (no slash) → the Advanced dashboard. Mounts only match with
    the trailing slash; this keeps a typed URL working."""
    return RedirectResponse("/advanced/", status_code=307)

# order matters: the longer prefix first, Basic as the catch-all at "/"
for _q in sorted(quals.QUALS.values(), key=lambda q: -len(q.url_prefix)):
    app.mount(_q.url_prefix or "/", _QualScope(create_app(_q), _q.code), name=_q.code)

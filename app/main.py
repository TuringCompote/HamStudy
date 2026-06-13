"""FastAPI app — Phase 2 quiz engine MVP.

Server-rendered dashboard + quiz-runner shell (Jinja); the quiz itself runs in
vanilla JS against a small JSON API. Correct answers are NEVER included in the
quiz payload — the server grades each submission and appends to `attempts`.

Run:  uvicorn app.main:app --reload
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from app.db import queries
from app.db.init_db import connect
from app.engine import mastery, coach, diagnostic, recommend
from app import quiz, config, tools, content, formulas
from app.coaching.ai_provider import get_provider
from app.coaching import journal as journal_mod, usage as usage_mod, corpus as corpus_mod

BASE = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE / "templates"))
templates.env.globals["APP_NAME"] = config.APP_NAME  # available in every template

app = FastAPI(title=f"{config.APP_NAME} — Canadian Basic (Honours) trainer")
app.mount("/static", StaticFiles(directory=str(BASE / "static")), name="static")


# --- request models ---
class QuizRequest(BaseModel):
    mode: str = Field(pattern="^(drill|exam|review|diagnostic)$")
    section: int | None = Field(default=None, ge=1, le=8)
    count: int | None = Field(default=None, ge=1, le=200)


class AttemptRequest(BaseModel):
    question_id: str
    chosen_index: int = Field(ge=0, le=3)
    mode: str = Field(pattern="^(drill|exam|review|diagnostic)$")
    response_ms: int | None = Field(default=None, ge=0)


class DiagnosticRequest(BaseModel):
    section: int = Field(ge=1, le=8)
    served_ids: list[str] = Field(min_length=1, max_length=20)
    confidence_prior: str | None = None


class ExplainRequest(BaseModel):
    question_id: str
    chosen_index: int = Field(ge=0, le=3)


# --- pages ---
@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    conn = connect()
    try:
        by_section = mastery.compute_section_mastery(conn)
        diagnostic.apply_diagnostic_tiers(conn, by_section)
        summary = coach.dashboard_summary(conn, by_section)
        rec = recommend.refresh(conn)  # build + persist recommendation.json, then read it back
        # surface per-section trend on the rows
        for s in by_section.values():
            ps = rec["readiness"]["per_section"].get(s["section"], {})
            s["trend"] = ps.get("trend", "new")
    finally:
        conn.close()
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {"sections": by_section, "summary": summary,
         "session": rec["next_session"], "rec": rec},
    )


@app.get("/section/{section}", response_class=HTMLResponse)
def section_page(request: Request, section: int):
    if not 1 <= section <= 8:
        raise HTTPException(404, "section must be 1..8")
    conn = connect()
    try:
        by_section = mastery.compute_section_mastery(conn)
        diagnostic.apply_diagnostic_tiers(conn, by_section)
        stats = by_section[section]
        has_diag = diagnostic.has_diagnostic(conn, section)
    finally:
        conn.close()
    # offer the placement probe when the section is essentially unrated
    offer_diagnostic = (not has_diag) and stats["fresh_answered"] < diagnostic.MIN_FRESH_FOR_TIER
    return templates.TemplateResponse(
        request,
        "section.html",
        {
            "section": section,
            "name": queries.SECTION_NAMES[section],
            "lesson_html": content.lesson_html(section),
            "tools": tools.tools_for_section(section),
            "stats": stats,
            "offer_diagnostic": offer_diagnostic,
        },
    )


@app.post("/api/diagnostic")
def api_diagnostic(req: DiagnosticRequest):
    conn = connect()
    try:
        return diagnostic.record_diagnostic(
            conn, req.section, req.served_ids, req.confidence_prior
        )
    finally:
        conn.close()


@app.get("/formula-trainer", response_class=HTMLResponse)
def formula_trainer(request: Request):
    return templates.TemplateResponse(
        request, "formula_trainer.html", {"formulas": formulas.FORMULAS},
    )


@app.get("/quiz", response_class=HTMLResponse)
def quiz_page(request: Request, mode: str = "drill", section: int | None = None,
              confidence: str | None = None):
    if mode not in ("drill", "exam", "review", "diagnostic"):
        raise HTTPException(400, "mode must be 'drill', 'exam', 'review', or 'diagnostic'")
    title = {"exam": "Mock Exam", "review": "Review",
             "diagnostic": f"Diagnostic — Section {section}"}.get(mode, f"Drill — Section {section}")
    return templates.TemplateResponse(
        request,
        "quiz.html",
        {"mode": mode, "section": section, "title": title,
         "confidence": confidence,
         "section_name": queries.SECTION_NAMES.get(section or 0, "")},
    )


# --- JSON API ---
@app.get("/api/sections")
def api_sections():
    conn = connect()
    try:
        return {"sections": mastery.compute_section_mastery(conn),
                "summary": mastery.overall_summary(conn)}
    finally:
        conn.close()


@app.post("/api/quiz")
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
            questions = quiz.build_diagnostic(conn, req.section)
        else:
            if req.section is None:
                raise HTTPException(400, "drill requires a section")
            questions = quiz.build_drill(
                conn, req.section, req.count or quiz.DEFAULT_DRILL_SIZE
            )
        if not questions:
            raise HTTPException(404, "no questions available for this request")
        return {"mode": req.mode, "count": len(questions), "questions": questions}
    finally:
        conn.close()


@app.post("/api/attempt")
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


@app.post("/api/explain")
def api_explain(req: ExplainRequest):
    """On-demand AI explanation of a question/miss (falls back to a stub when the
    AI budget is reached or no key is set). Grounding corpus arrives in Phase 5.3."""
    conn = connect()
    try:
        q = queries.get_question(conn, req.question_id, with_answer=True)
        if q is None:
            raise HTTPException(404, "unknown question id")
    finally:
        conn.close()
    grounding = corpus_mod.ground_for_section(q["section"])  # RIC/RBR for regs sections
    result = get_provider().explain(
        question=q, chosen_index=req.chosen_index, grounding=grounding
    )
    return {"text": result.text, "degraded": result.degraded,
            "model": result.model, "cost_usd": round(result.cost_usd, 6)}


@app.post("/api/journal")
def api_journal():
    conn = connect()
    try:
        return journal_mod.write_journal(conn)
    finally:
        conn.close()


@app.get("/api/ai-status")
def api_ai_status():
    conn = connect()
    try:
        ok, mtd = usage_mod.within_budget(conn)
    finally:
        conn.close()
    return {"provider": config.AI_PROVIDER, "within_budget": ok,
            "month_to_date_usd": round(mtd, 4), "ceiling_usd": config.AI_MONTHLY_BUDGET_USD}


@app.get("/api/health")
def health():
    conn = connect()
    try:
        n = conn.execute("SELECT COUNT(*) c FROM questions").fetchone()["c"]
        bv = conn.execute(
            "SELECT value FROM meta WHERE key='bank_version'"
        ).fetchone()
    finally:
        conn.close()
    return {"status": "ok", "questions": n,
            "bank_version": bv["value"] if bv else None}

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
from app.engine import mastery
from app import quiz, config

BASE = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE / "templates"))
templates.env.globals["APP_NAME"] = config.APP_NAME  # available in every template

app = FastAPI(title=f"{config.APP_NAME} — Canadian Basic (Honours) trainer")
app.mount("/static", StaticFiles(directory=str(BASE / "static")), name="static")


# --- request models ---
class QuizRequest(BaseModel):
    mode: str = Field(pattern="^(drill|exam)$")
    section: int | None = Field(default=None, ge=1, le=8)
    count: int | None = Field(default=None, ge=1, le=200)


class AttemptRequest(BaseModel):
    question_id: str
    chosen_index: int = Field(ge=0, le=3)
    mode: str = Field(pattern="^(drill|exam|review)$")
    response_ms: int | None = Field(default=None, ge=0)


# --- pages ---
@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    conn = connect()
    try:
        by_section = mastery.compute_section_mastery(conn)
        summary = mastery.overall_summary(conn)
    finally:
        conn.close()
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {"sections": by_section, "summary": summary},
    )


@app.get("/quiz", response_class=HTMLResponse)
def quiz_page(request: Request, mode: str = "drill", section: int | None = None):
    if mode not in ("drill", "exam"):
        raise HTTPException(400, "mode must be 'drill' or 'exam'")
    title = "Mock Exam" if mode == "exam" else f"Drill — Section {section}"
    return templates.TemplateResponse(
        request,
        "quiz.html",
        {"mode": mode, "section": section, "title": title,
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

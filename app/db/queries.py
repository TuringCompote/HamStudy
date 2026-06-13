"""Data-access helpers for the quiz engine. Thin wrappers over SQLite.

No business logic here beyond reads/writes; quiz construction lives in
`app.quiz` and analysis in `app.engine`.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from app.db.init_db import connect

# The 8 official syllabus sections (spec §4). Names are ours (original), used
# for navigation labels only — not lesson content.
SECTION_NAMES = {
    1: "Regulations and Policies",
    2: "Operating and Procedures",
    3: "Station Assembly, Practice and Safety",
    4: "Circuit Components",
    5: "Basic Electronics and Theory",
    6: "Feedlines and Antenna Systems",
    7: "Radio Wave Propagation",
    8: "Interference and Suppression",
}

# compact labels for the dashboard rows (matches the design mockup)
SECTION_SHORT_NAMES = {
    1: "Regulations & policies",
    2: "Operating & procedures",
    3: "Station assembly & safety",
    4: "Circuit components",
    5: "Basic electronics & theory",
    6: "Feedlines & antennas",
    7: "Radio wave propagation",
    8: "Interference & suppression",
}


def _row_to_question(row, *, with_answer: bool = False) -> dict:
    q = {
        "id": row["id"],
        "section": row["section"],
        "subsection": row["subsection"],
        "text": row["text"],
        "options": json.loads(row["options"]),
    }
    if with_answer:
        q["correct_index"] = row["correct_index"]
    return q


def get_question(conn, qid: str, *, with_answer: bool = False):
    row = conn.execute("SELECT * FROM questions WHERE id = ?", (qid,)).fetchone()
    return _row_to_question(row, with_answer=with_answer) if row else None


def correct_index(conn, qid: str):
    row = conn.execute(
        "SELECT correct_index FROM questions WHERE id = ?", (qid,)
    ).fetchone()
    return row["correct_index"] if row else None


def section_question_ids(conn, section: int) -> list[str]:
    rows = conn.execute(
        "SELECT id FROM questions WHERE section = ? ORDER BY id", (section,)
    ).fetchall()
    return [r["id"] for r in rows]


def all_question_ids_by_subsection(conn) -> dict[tuple[int, int], list[str]]:
    """{(section, subsection): [ids...]} — the sampling frame for mock exams."""
    frame: dict[tuple[int, int], list[str]] = {}
    for r in conn.execute(
        "SELECT id, section, subsection FROM questions ORDER BY id"
    ).fetchall():
        frame.setdefault((r["section"], r["subsection"]), []).append(r["id"])
    return frame


def section_sizes(conn) -> dict[int, int]:
    rows = conn.execute(
        "SELECT section, COUNT(*) n FROM questions GROUP BY section"
    ).fetchall()
    return {r["section"]: r["n"] for r in rows}


def questions_for_ids(conn, ids: list[str]) -> list[dict]:
    """Fetch questions for a quiz — WITHOUT correct answers (never shipped to
    the client). Order follows the input `ids`."""
    if not ids:
        return []
    placeholders = ",".join("?" * len(ids))
    rows = conn.execute(
        f"SELECT * FROM questions WHERE id IN ({placeholders})", ids
    ).fetchall()
    by_id = {r["id"]: r for r in rows}
    return [_row_to_question(by_id[i]) for i in ids if i in by_id]


def record_attempt(
    conn,
    *,
    question_id: str,
    chosen_index: int,
    mode: str,
    response_ms: int | None = None,
) -> dict:
    """Grade server-side and append to `attempts` (append-only, ground truth).

    Returns {correct, correct_index} so the caller (drill) can show feedback.
    """
    row = conn.execute(
        "SELECT section, subsection, correct_index FROM questions WHERE id = ?",
        (question_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"unknown question id: {question_id}")
    is_correct = int(chosen_index == row["correct_index"])
    conn.execute(
        """
        INSERT INTO attempts
            (question_id, section, subsection, answered_at, chosen_index,
             correct, response_ms, mode)
        VALUES (?,?,?,?,?,?,?,?)
        """,
        (
            question_id, row["section"], row["subsection"],
            datetime.now(timezone.utc).isoformat(), chosen_index,
            is_correct, response_ms, mode,
        ),
    )
    conn.commit()
    return {"correct": bool(is_correct), "correct_index": row["correct_index"]}

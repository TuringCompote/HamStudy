"""Ingest the official ISED Basic question bank PDF into the `questions` table.

Ground truth = the official PDF (constitution §2). The bank is a two-column
layout; naive text extraction interleaves the columns, so we reconstruct each
page column-by-column (split at the empty gutter) before parsing.

Question format (per the bank's foreword):
    B-AAA-BBB-CCC (X)        <- id + correct-answer letter in brackets
    <stem, 1+ lines>
    A <option a, 1+ lines>
    B <option b ...>
    C <option c ...>
    D <option d ...>
In ~37 cases the answer marker x-sorts before the id ("(X) B-AAA-BBB-CCC");
both orderings are accepted (the bracketed letter is that id's answer either way).

Idempotent: upserts by `id`, (re)sets `bank_version`, and NEVER touches
`attempts` (constitution §6). `bank_version` is derived from the PDF title-page
effective date, not hardcoded.

Usage:
    python -m app.db.ingest                 # uses config.BANK_PDF -> config.DB_PATH
    python -m app.db.ingest --pdf path.pdf --db path.db
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
from datetime import datetime, timezone

import pdfplumber

from app import config
from app.db.init_db import init_db

# --- layout constants (verified against the 2025 bank, 612x792 pt pages) ---
COLUMN_SPLIT_X = 257   # empty vertical gutter between the two columns
LINE_Y_TOL = 3         # words within this many pts of `top` are the same line

_ID_RE = re.compile(
    r"^(?:"
    r"B-(\d{3})-(\d{3})-(\d{3})\s+\(([A-D])\)"      # normal: id (X)
    r"|\(([A-D])\)\s+B-(\d{3})-(\d{3})-(\d{3})"     # reversed: (X) id
    r")$"
)
_OPT_RE = re.compile(r"^([A-D])\s+(.*)$")
_DATE_RE = re.compile(
    r"(\d{1,2})\s+"
    r"(January|February|March|April|May|June|July|August|September|October|November|December)"
    r",?\s+(\d{4})"
)
_MONTHS = {m: i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"], start=1)}


def _render_column(words) -> list[str]:
    """Group a single column's words into visual lines (top order)."""
    words = sorted(words, key=lambda w: (w["top"], w["x0"]))
    lines, cur, base = [], [], None
    for w in words:
        if base is None or abs(w["top"] - base) <= LINE_Y_TOL:
            cur.append(w)
            if base is None:
                base = w["top"]
        else:
            lines.append(cur)
            cur, base = [w], w["top"]
    if cur:
        lines.append(cur)
    return [" ".join(w["text"] for w in ln) for ln in lines]


def page_lines(page) -> list[str]:
    """Left column top-to-bottom, then right column — the natural reading order."""
    words = page.extract_words(use_text_flow=False)
    left = [w for w in words if w["x0"] < COLUMN_SPLIT_X]
    right = [w for w in words if w["x0"] >= COLUMN_SPLIT_X]
    return _render_column(left) + _render_column(right)


def extract_bank_version(pdf) -> str:
    """Effective date from the title page -> ISO (foreword: 'effective the date
    printed on the title page')."""
    text = pdf.pages[0].extract_text() or ""
    m = _DATE_RE.search(text)
    if not m:
        raise ValueError("could not find effective date on the PDF title page")
    day, month, year = int(m.group(1)), _MONTHS[m.group(2)], int(m.group(3))
    return f"{year:04d}-{month:02d}-{day:02d}"


def _parse_block(qid: str, ans: str, body: list[str]) -> dict:
    """Split a question block's body lines into stem + 4 options.

    Options are the trailing A,B,C,D groups (in label order). Scanning from the
    last 'D' marker backward avoids mistaking a stem that starts with 'A ...'
    (e.g. "A radio inspector asks...") for option A.
    """
    ls = [l for l in body if l.strip()]
    marks: dict[str, list[int]] = {}
    for i, l in enumerate(ls):
        m = _OPT_RE.match(l)
        if m:
            marks.setdefault(m.group(1), []).append(i)

    def last_before(label: str, limit: int):
        cands = [i for i in marks.get(label, []) if i < limit]
        return cands[-1] if cands else None

    if not marks.get("D"):
        raise ValueError(f"{qid}: no option D found")
    d = marks["D"][-1]
    c = last_before("C", d)
    b = last_before("B", c) if c is not None else None
    a = last_before("A", b) if b is not None else None
    if None in (a, b, c):
        raise ValueError(f"{qid}: could not locate A/B/C/D option markers")

    stem = " ".join(ls[:a]).strip()
    options = []
    for start, end in [(a, b), (b, c), (c, d), (d, len(ls))]:
        head = _OPT_RE.match(ls[start]).group(2)
        tail = " ".join(ls[start + 1:end])
        options.append((head + " " + tail).strip())

    if not stem:
        raise ValueError(f"{qid}: empty stem")
    if len(options) != 4 or any(not o for o in options):
        raise ValueError(f"{qid}: expected 4 non-empty options, got {options}")

    s, sub, qn = qid.split("-")[1:]
    return {
        "id": qid,
        "section": int(s),
        "subsection": int(sub),
        "qnum": int(qn),
        "text": stem,
        "options": options,
        "correct_index": "ABCD".index(ans),
    }


def parse_pdf(pdf_path) -> tuple[list[dict], str]:
    """Parse the bank PDF -> (list of question dicts, bank_version)."""
    questions: list[dict] = []
    with pdfplumber.open(pdf_path) as pdf:
        bank_version = extract_bank_version(pdf)
        lines: list[str] = []
        for page in pdf.pages[2:]:        # pages 0-1 are title + foreword
            lines.extend(page_lines(page))

    cur_id = cur_ans = None
    body: list[str] = []
    for raw in lines:
        m = _ID_RE.match(raw.strip())
        if m:
            if cur_id is not None:
                questions.append(_parse_block(cur_id, cur_ans, body))
            if m.group(1):                # normal "id (X)"
                cur_id = f"B-{m.group(1)}-{m.group(2)}-{m.group(3)}"
                cur_ans = m.group(4)
            else:                         # reversed "(X) id"
                cur_id = f"B-{m.group(6)}-{m.group(7)}-{m.group(8)}"
                cur_ans = m.group(5)
            body = []
        elif cur_id is not None:
            body.append(raw)
    if cur_id is not None:
        questions.append(_parse_block(cur_id, cur_ans, body))

    return questions, bank_version


def upsert_questions(conn: sqlite3.Connection, questions: list[dict], bank_version: str) -> int:
    """Upsert by id; set bank_version; preserve coach-written `notes` and
    calibrated `difficulty_b`. Never touches `attempts`."""
    rows = [
        (
            q["id"], q["section"], q["subsection"], q["qnum"], q["text"],
            json.dumps(q["options"], ensure_ascii=False), q["correct_index"],
            bank_version,
        )
        for q in questions
    ]
    conn.executemany(
        """
        INSERT INTO questions
            (id, section, subsection, qnum, text, options, correct_index, bank_version)
        VALUES (?,?,?,?,?,?,?,?)
        ON CONFLICT(id) DO UPDATE SET
            section=excluded.section,
            subsection=excluded.subsection,
            qnum=excluded.qnum,
            text=excluded.text,
            options=excluded.options,
            correct_index=excluded.correct_index,
            bank_version=excluded.bank_version
        """,
        rows,
    )
    conn.execute(
        "INSERT INTO meta(key, value) VALUES('bank_version', ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (bank_version,),
    )
    conn.execute(
        "INSERT INTO meta(key, value) VALUES('last_ingest_at', ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (datetime.now(timezone.utc).isoformat(),),
    )
    conn.commit()
    return len(rows)


def ingest(pdf_path=None, db_path=None) -> dict:
    pdf_path = pdf_path or config.BANK_PDF
    if not pdf_path.exists():
        raise FileNotFoundError(
            f"bank PDF not found at {pdf_path} — download it into references/ first"
        )
    questions, bank_version = parse_pdf(pdf_path)
    conn = init_db(db_path)               # ensure schema exists; idempotent
    n = upsert_questions(conn, questions, bank_version)
    conn.close()
    return {"ingested": n, "bank_version": bank_version, "pdf": str(pdf_path)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Ingest the ISED Basic question bank.")
    ap.add_argument("--pdf", type=lambda p: __import__("pathlib").Path(p))
    ap.add_argument("--db", type=lambda p: __import__("pathlib").Path(p))
    args = ap.parse_args()
    result = ingest(args.pdf, args.db)
    print(
        f"ingested {result['ingested']} questions "
        f"(bank_version={result['bank_version']}) into {db_path if (db_path:=args.db) else config.DB_PATH}"
    )

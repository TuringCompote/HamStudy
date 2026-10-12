"""Validate the ingested `questions` table against known ground truth.

Checks (BACKLOG Phase 1), per qualification (--qual basic|advanced):
  - total count == the profile's expected_total (984 Basic; Advanced is pinned
    at first ingest via meta.expected_total so a later re-ingest can't silently
    shrink the bank)
  - every id matches <prefix>-AAA-BBB-CCC and parses to one of the profile's sections
  - exactly 4 options per question; correct_index in 0..3
  - no duplicate ids; no NULL/empty stems or options
  - reports per-section counts and answer-letter distribution

Exit code 0 = all checks pass, 1 = any failure. Run after ingest:
    python -m app.db.validate
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter

from app import quals
from app.db.init_db import connect

EXPECTED_TOTAL = 984          # PHASE0-FINDINGS: current Basic bank size (quals.BASIC)


def crosscheck_delimited(rows, q) -> list[str]:
    """Exact cross-check of the PDF parse against ISED's own delimited data file
    (references/_extracted/<delim_filename>, from fetch_sources), when present:
    every stem, the full option set and the keyed answer must match character for
    character (the data file drops ';' — its delimiter — so that's normalised).
    Skipped silently if the file isn't there."""
    import csv
    path = q.delim_path
    if not q.delim_filename or not path.exists():
        print("delimited x-check   : (file not present — skipped)")
        return []
    with open(path, encoding="utf-8", newline="") as f:
        recs = [r for r in csv.reader(f, delimiter=";")][1:]
    norm = lambda s: re.sub(r"\s+", " ", s.replace(";", " ")).strip()   # noqa: E731
    by_id = {r["id"]: r for r in rows}
    out = []
    for r in recs:
        qid = r[0].strip()
        d = by_id.get(qid)
        if d is None:
            out.append(f"{qid}: in ISED data file but not ingested"); continue
        opts = json.loads(d["options"])
        if norm(r[1]) != norm(d["text"]):
            out.append(f"{qid}: stem differs from ISED data file")
        if sorted(map(norm, r[2:6])) != sorted(map(norm, opts)):
            out.append(f"{qid}: option set differs from ISED data file")
        elif norm(r[2]) != norm(opts[d["correct_index"]]):
            out.append(f"{qid}: answer key differs from ISED data file")
    extra = sorted(set(by_id) - {r[0].strip() for r in recs})
    if extra:
        out.append(f"{len(extra)} ingested id(s) absent from ISED data file: {extra[:5]}")
    print(f"delimited x-check   : {len(recs)} records, {len(out)} mismatch(es)")
    return out


def validate(db_path=None) -> bool:
    q = quals.current()
    _id_re = re.compile(rf"^{q.id_prefix}-(\d{{3}})-(\d{{3}})-(\d{{3}})$")
    conn = connect(db_path)
    expected = q.expected_total
    if not expected:
        # Advanced: pin the size seen at first validation in meta, then hold it
        row = conn.execute("SELECT value FROM meta WHERE key='expected_total'").fetchone()
        if row:
            expected = int(row["value"])
        else:
            expected = conn.execute("SELECT COUNT(*) c FROM questions").fetchone()["c"]
            conn.execute("INSERT INTO meta(key,value) VALUES('expected_total', ?)", (str(expected),))
            conn.commit()
    rows = conn.execute(
        "SELECT id, section, subsection, qnum, text, options, correct_index, bank_version "
        "FROM questions"
    ).fetchall()
    failures: list[str] = []

    total = len(rows)
    if total != expected:
        failures.append(f"count: expected {expected}, got {total}")
    if total == 0:
        failures.append("no questions ingested")

    seen: set[str] = set()
    sections = Counter()
    answers = Counter()
    bank_versions = set()

    for r in rows:
        qid = r["id"]
        if qid in seen:
            failures.append(f"{qid}: duplicate id")
        seen.add(qid)

        m = _id_re.match(qid)
        if not m:
            failures.append(f"{qid}: id does not match {q.id_prefix}-AAA-BBB-CCC")
            continue
        if r["section"] not in q.sections or r["section"] != int(m.group(1)):
            failures.append(f"{qid}: section {r['section']} invalid / != id prefix")

        try:
            opts = json.loads(r["options"])
        except json.JSONDecodeError:
            failures.append(f"{qid}: options is not valid JSON")
            opts = []
        if len(opts) != 4 or any(not str(o).strip() for o in opts):
            failures.append(f"{qid}: expected 4 non-empty options, got {len(opts)}")

        if r["correct_index"] is None or not (0 <= r["correct_index"] <= 3):
            failures.append(f"{qid}: correct_index out of range: {r['correct_index']}")
        if not (r["text"] or "").strip():
            failures.append(f"{qid}: empty stem")

        sections[r["section"]] += 1
        ci = r["correct_index"]
        if ci is not None and 0 <= ci <= 3:
            answers["ABCD"[ci]] += 1
        bank_versions.add(r["bank_version"])

    conn.close()

    # --- report ---
    print(f"qualification      : {q.label}")
    print(f"questions ingested : {total}")
    print(f"bank_version(s)    : {sorted(bank_versions)}")
    print("per-section counts :")
    for s in q.sections:
        print(f"    section {s}: {sections.get(s, 0)}")
    stray = sorted(set(sections) - set(q.sections))
    if stray:
        failures.append(f"questions in sections outside the profile: {stray}")
    print(f"answer distribution: {dict(sorted(answers.items()))}")

    if len(bank_versions) > 1:
        failures.append(f"mixed bank_version values: {sorted(bank_versions)}")

    failures += crosscheck_delimited(rows, q)

    if failures:
        print(f"\nFAILED ({len(failures)} issue(s)):")
        for f in failures[:25]:
            print(f"  - {f}")
        if len(failures) > 25:
            print(f"  ... and {len(failures) - 25} more")
        return False

    print("\nOK - all validation checks passed.")
    return True


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Validate an ingested question bank.")
    quals.add_cli_arg(ap)
    quals.activate(ap.parse_args().qual)
    sys.exit(0 if validate() else 1)

"""Validate the ingested `questions` table against known ground truth.

Checks (BACKLOG Phase 1):
  - total count == EXPECTED_TOTAL (984)
  - every id matches B-AAA-BBB-CCC and parses to a section 1..8
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

from app import config
from app.db.init_db import connect

EXPECTED_TOTAL = 984          # PHASE0-FINDINGS: current Basic bank size
_ID_RE = re.compile(r"^B-(\d{3})-(\d{3})-(\d{3})$")


def validate(db_path=None) -> bool:
    conn = connect(db_path)
    rows = conn.execute(
        "SELECT id, section, subsection, qnum, text, options, correct_index, bank_version "
        "FROM questions"
    ).fetchall()
    failures: list[str] = []

    total = len(rows)
    if total != EXPECTED_TOTAL:
        failures.append(f"count: expected {EXPECTED_TOTAL}, got {total}")

    seen: set[str] = set()
    sections = Counter()
    answers = Counter()
    bank_versions = set()

    for r in rows:
        qid = r["id"]
        if qid in seen:
            failures.append(f"{qid}: duplicate id")
        seen.add(qid)

        m = _ID_RE.match(qid)
        if not m:
            failures.append(f"{qid}: id does not match B-AAA-BBB-CCC")
            continue
        if not (1 <= r["section"] <= 8) or r["section"] != int(m.group(1)):
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
    print(f"questions ingested : {total}")
    print(f"bank_version(s)    : {sorted(bank_versions)}")
    print("per-section counts :")
    for s in range(1, 9):
        print(f"    section {s}: {sections.get(s, 0)}")
    print(f"answer distribution: {dict(sorted(answers.items()))}")

    if len(bank_versions) > 1:
        failures.append(f"mixed bank_version values: {sorted(bank_versions)}")

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
    sys.exit(0 if validate() else 1)

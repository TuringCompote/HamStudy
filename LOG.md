# LOG.md — Build progress log

Append-only. Newest entries at the bottom. Each session: date, what was done,
decisions, next step.

---

## 2026-06-13 — Phase 0 finish + Phase 1 (data foundation)

**Done**
- Scaffolded the project: `app/`, `app/db/`, `data/` (git-ignored), `references/`
  (git-ignored), `.gitignore`, `requirements.txt`.
- Downloaded the official ISED Basic question bank PDF into
  `references/amateur_basic_questions_en.pdf` (322 KB, valid PDF) from the
  authoritative `apc-cap.ic.gc.ca` data-file URL (the dated `documents/...` URLs
  in PHASE0 404'd; the lowercase `.pdf` data file is live, per PHASE0's note).
- Stood up the SQLite schema (spec §7) — `app/db/schema.sql` +
  `app/db/init_db.py`. Tables: `questions`, `attempts` (append-only),
  `progress`, `diagnostics`, `usage`, `recommendation`, `journal`, plus a
  `meta` k/v table. `init_db` is idempotent (`CREATE ... IF NOT EXISTS`).
- Built the ingest parser (`app/db/ingest.py`). The bank is a **two-column**
  layout; naive `extract_text()` interleaves columns. Solution: reconstruct each
  page column-by-column, splitting at the empty gutter (x≈257), grouping words
  into lines by `top`. Parsed **984/984 questions, 0 bad, 0 duplicates**, all
  mapping to sections 1–8.
- Wrote `app/db/validate.py`: asserts count==984, id format, section 1–8, 4
  options each, correct_index 0–3, no dupes/empties; reports per-section + answer
  distribution. **All checks pass.**
- Verified idempotent re-ingest: re-running keeps `questions` at 984 and
  **preserves `attempts`** (inserted a probe attempt, re-ran ingest, probe
  survived) — constitution §6 satisfied. Upsert preserves `notes` / `difficulty_b`.

**Decisions**
- **`bank_version = 2025-08-26`, not 2025-07-15.** The live authoritative file's
  title page reads "26 August, 2025", and the foreword states questions are
  "effective the date printed on the title page." Same 984-question count, so
  it's an ISED re-issue of the same pool with a newer effective date. Ingest
  **derives `bank_version` from the PDF title page** rather than hardcoding, so
  this self-corrects on future re-issues. (Flagged to Chris.)
- Parser handles two ID/answer orderings: normal `B-AAA-BBB-CCC (X)` and the
  ~37 cases where x-sorting puts the answer first, `(X) B-AAA-BBB-CCC`. Both
  carry that id's correct answer.
- Wrote our own parser (studied `canadian-ham-exam`'s approach as reference per
  PHASE0) — the column-split + trailing-A/B/C/D-marker logic is specific to this
  PDF and worth owning.
- Per-section counts (this bank): S1=199, S2=99, S3=199, S4=63, S5=142, S6=140,
  S7=87, S8=55.
- Downloaded PDFs/ZIPs are git-ignored (constitution §2/§3 — don't redistribute
  source binaries); the parsed SQLite is the app's data. Re-download is scripted
  in `app/db/fetch_sources.py`.

**Reference material (resolved same session)**
- Found the working URLs (the PHASE0 `documents/...` paths were missing the
  `sites/default/files/` segment). Downloaded into `references/` (git-ignored):
  - **Reference Material ZIP** → auto-extracted to `_extracted/`: the **"Exam"**
    PDF (5 pp, *unlabelled* — exam-legal sheet to train with) and the **"Training"**
    PDF (7 pp, *labelled* study aid). For Phase 4 formula trainer.
  - **RBR-4** (Standards for Operation) → PDF.
  - **RIC-3** and **RIC-1** → HTML-only on ISED (no PDF published), saved as
    faithful server-rendered HTML; clean text extraction deferred to Phase 5 when
    the AI reference layer consumes them.
- `app/db/fetch_sources.py` now re-downloads all five sources reproducibly
  (verified end-to-end; ZIP auto-extracts). `.gitignore` excludes `*.html` too.
- Note: a 2025-07-15-dated bank copy also exists on ised-isde, while the apc-cap
  data file is the 2025-08-26 re-issue — same 984 pool. We use apc-cap (newer).

**Open / next step**
- **Next: Phase 2** — quiz engine MVP (per-section drill + 100-Q mock with 70%
  and 80% lines), recording every answer to `attempts`, minimal dashboard.

**How to run**
```
pip install -r requirements.txt
python -m app.db.ingest      # downloads must already be in references/
python -m app.db.validate
```

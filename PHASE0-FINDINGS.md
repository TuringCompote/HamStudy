# PHASE0-FINDINGS.md — Research & ground-truthing

Date of research: **2026-06-13** (verified live via web fetch + search).

## Headline facts (encode these)
- **The Basic question bank was revised effective 2025-07-15.** Any tool/pool dated before
  that is stale. The print page was last modified 2025-10-01.
- **The Basic bank contains 984 questions** (per HamStudy's CA_B_2025 pool). Use this as the
  ingest sanity-check count.
- Exam unchanged: 100 Q, 4 options, **70% pass / 80% Honours**. Honours unlocks below-30-MHz
  HF + full power.
- ISED also publishes a **Reference Material ZIP (2025)** containing the **labelled** (study)
  and **unlabelled** (exam-legal) formula + block-diagram sheets.

## A. Official ISED / Gov-Canada sources — ALL VERIFIED LIVE

| Resource | URL | Status / notes |
|---|---|---|
| Exam generator (landing) | `https://ised-isde.canada.ca/site/amateur-radio-operator-certificate-services/en/amateur-radio-exam-generator` | LIVE. Modified 2025-07-15. Announces the new Basic exam. |
| Print all Basic questions (page) | `https://ised-isde.canada.ca/site/.../amateur-radio-exam-generator/print-all-basic-questions` | LIVE. Modified 2025-10-01. Confirms `B-001-001-001 (A)` ID + answer format. |
| **Basic bank data file (authoritative ground truth)** | `https://apc-cap.ic.gc.ca/datafiles/amateur_basic_questions_en.pdf` | LIVE. **URL is now lowercase `.pdf`** (spec had `.PDF`). Binary — download + parse in Claude Code. |
| Dated canonical copy | `https://ised-isde.canada.ca/site/.../documents/amateur_basic_questions_en_2025-07-15.pdf` | LIVE. Use to lock `bank_version = 2025-07-15`. |
| Advanced bank data file (later) | `https://apc-cap.ic.gc.ca/datafiles/amateur_advanced_questions_en.pdf` | LIVE (Phase 7). |
| Basic study questions (per category) | `http://apc-cap.ic.gc.ca/pls/apc_anon/apeg_study.study_questions_intro` | LIVE. Basic = **no** `p_level_id`. |
| Basic practice exam (100 Q) | `http://apc-cap.ic.gc.ca/pls/apc_anon/apeg_practice.practice_form` | LIVE. |
| Print a Basic practice exam | `http://apc-cap.ic.gc.ca/pls/apc_anon/apeg_print.basic_exam` | LIVE. |
| Reference Material ZIP (formula/diagram sheets, 2025) | `https://ised-isde.canada.ca/site/.../documents/Reference%20Material%20for%20Amateur%20Radio%20Basic%20EN%202025%20.zip` | LIVE. Contains labelled + **unlabelled** sheets. |

> **Spec correction:** §5a said "Online practice exam (level 1 = Basic)" with
> `?p_level_id=1`. **Wrong — `p_level_id=1` is the *Advanced* level.** Basic uses the
> bare URL. Fixed in the inventory above.

## B. Free / community courses & study material

| Resource | URL | Status / value |
|---|---|---|
| RAC — Study Guides hub | `https://www.rac.ca/study-guides-2/` | LIVE (mod. 2026-01). Points to HamStudy + Coax. |
| RAC — Amateur Radio Courses (clubs, online+in-person) | `https://www.rac.ca/amateur-radio-courses/` | LIVE. Find Alberta-local + RAC online courses. |
| HamStudy.org — CA_B_2025 pool (browseable, per-question instructional notes) | `https://hamstudy.org/browse/CA_B_2025` | LIVE. **Current 2025 pool, 984 Q.** Best free interactive study reference. |
| HamStudy self-study course (RAC partner) | `https://hamstudy.com/2025/` | LIVE. "HamStudy Basic 2026" now available. |
| University of Waterloo ARC — "Basic, The Essentials" PDF | `https://uwarc.uwaterloo.ca/assets/basic-essentials-main.pdf` | LIVE (large, ~1840 lines). Solid free written guide. |
| Coax Publications — Student Success Pages ("Ask the Professor") | `https://www.coaxpublications.ca/hpg0001.html` | LIVE. Free interactive Q&A w/ feedback; Coax has wound down but pages persist. Good interactive reference. |
| VE3FCQ — Basic Exam Prep course | `https://ve3fcq.ca/canadian-amateur-radio-basic-exam-prep/` | LIVE but **PAID Moodle course, June-2022 bank, aimed at non-engineers.** Use only as *design inspiration* — notably it includes pre-/post-assessment + subject tests, which validates our adaptive approach. Not a content source. |
| ylab.ca radio class | `https://www.ylab.ca/radioclass/` | LIVE. Free class slides/notes (verify currency before use). |

> The spec's §5b also lists hamshack.ca, Toronto ECG, CLARS (Alberta-local), and UBC RSL.
> These were not re-verified this pass; check at use time. **Alberta-local clubs (CLARS,
> and others via the RAC courses page) are worth surfacing to the user for booking the
> in-person exam with an accredited examiner.**

## C. Question-bank tooling & parser references

| Tool | URL | Verdict |
|---|---|---|
| **`canadian-ham-exam`** (PyPI / Launchpad) | `https://launchpad.net/canadian-ham-exam` | **Best parser candidate.** v1.0.1 (2025-02-26) added UTF-8 support for the new bank format; pulls the official file directly. Verify it ingests the 2025-07-15 bank cleanly; adapt its parser. |
| `fredlarochelle/Canada-Ham-Pool` | `https://github.com/fredlarochelle/Canada-Ham-Pool` | JSON pools + a `Parsing_the_IC_files.ipynb` Colab. **Data is Aug-2022 (stale)** — use the *parsing approach* as reference, not the data. |
| HamStudy pools (open) | `https://hamstudy.org/browse/CA_B_2025` | Current pool incl. per-question explanations. Study the JSON/YAML pool shape + SR UX as the design reference. |
| `rprouse/HamRadioStudy` | `https://github.com/rprouse/HamRadioStudy` | Canadian Basic study app, **Feb-2024 bank (stale).** Reference only. |

**Parser decision:** treat the **official 2025-07-15 PDF as ground truth**; adapt
`canadian-ham-exam`'s parser to produce our `questions` rows; **cross-check the parsed
count against 984 and against the HamStudy CA_B_2025 pool** to catch parse errors. Record
`bank_version = 2025-07-15`.

## D. Licensing (unchanged from spec §5 note)
ISED bank = Government of Canada work, free to download/use for study + exam admin.
Community PDFs/courses (UWARC, VE3FCQ, Coax, HamStudy): link + download for personal study;
**do not republish their prose** in the app. Write original lesson text. App stays private/
self-hosted.

## E. Implications fed into the design
- Adaptivity must not create blind spots: the real exam samples the **whole** 984-question
  bank, so "test-out" sections still need minimum verification coverage before readiness.
  (See spec §6d.)
- The per-question instructional notes in HamStudy/Coax confirm there's appetite for
  explanation-per-question — our AI layer fills that role with original explanations.

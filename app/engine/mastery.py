"""Deterministic per-section mastery (constitution §5).

Pure arithmetic over the `attempts` event log: same attempts in => same numbers
out. No LLM, no randomness, no wall-clock dependence. This is the Phase-2 seed of
the engine; trend / fresh-vs-review / adaptive state come in later phases.

Definitions (v1):
  answered      = total attempts in the section
  correct       = correct attempts in the section
  mastery_pct   = 100 * correct / answered     (None if never answered)
  coverage_pct  = 100 * distinct questions attempted / section size
  seen          = distinct questions attempted
  fresh_pct     = COLD-RECALL accuracy — see below. This is what the dashboard,
                  the depth tiers and readiness (spec §8) are driven by.
The Honours bar is 80% (spec §0.1); 70% is a pass.

Cold recall (why "fresh" is not "first attempt ever")
-----------------------------------------------------
"Fresh" exists to measure recall on an exam-like cold start, not recognition of
something drilled minutes ago. v1 implemented that as *the first attempt a
question ever got* — which silently makes the metric terminal: once the bank has
been seen, every later attempt is excluded, so fresh accuracy (and therefore the
tiers, the trend and readiness) can never move again no matter how much the user
studies. Honours became unreachable by construction.

An attempt is COLD when it is a question's first-ever attempt, or it lands at
least `config.FRESH_COOLDOWN_DAYS` after the previous attempt on that question.
A section's fresh accuracy is taken over each question's MOST RECENT cold
attempt, so it reads as "if the exam were today, how much do I actually recall?"
and recovers as the user re-earns each question after the cooldown.

Still deterministic (constitution §5): the cooldown is measured between two
timestamps that are already in the log, never against the wall clock. Same
`attempts` + same config ⇒ same numbers.
"""
from __future__ import annotations

from app import config, quals
from app.db.queries import section_names, section_short_names

FRESH_COOLDOWN_DAYS = config.FRESH_COOLDOWN_DAYS

HONOURS_BAR = 80.0
PASS_BAR = 70.0

# Depth tiers (spec §6d.2). Driven by FRESH-question accuracy (first exposure) —
# the exam-relevant signal. Cutoffs match the dashboard legend (test-out ≥80%);
# tunable here. A diagnostic probe (§6d.1) can seed the tier before enough fresh
# attempts exist. Colors: test-out=teal, light=blue, standard=grey, deep=amber.
TIER_CUTOFFS = (("test-out", 80.0), ("light", 70.0), ("standard", 55.0))  # else "deep"
TIER_CSS = {"test-out": "testout", "light": "light", "standard": "standard", "deep": "deep"}
_TIER_CSS = TIER_CSS  # back-compat alias


def ui_config() -> dict:
    """The single UI contract for tier names/colors and the exam bars.

    Injected into every page as `window.ElmerConfig` (base.html) and looped for
    the dashboard tier legend. quiz.js and the templates read this — they must
    never restate the cutoffs or the tier→CSS map."""
    tiers = [{"name": n, "css": TIER_CSS[n], "min_pct": c} for n, c in TIER_CUTOFFS]
    tiers.append({"name": "deep", "css": TIER_CSS["deep"], "min_pct": None})
    q = quals.current()
    return {
        "pass_bar": PASS_BAR,
        "honours_bar": HONOURS_BAR,
        "tier_css": TIER_CSS,
        "tiers": tiers,
        "fresh_cooldown_days": FRESH_COOLDOWN_DAYS,
        # qualification context (the UI never hardcodes these)
        "qual": q.code,
        "qual_label": q.label,
        "base": q.url_prefix,                 # URL space of this qualification
        "honours": q.honours,                 # does the exam award Honours?
        "target_label": q.target_label,       # "Honours" | "target" for the 80% bar
        "exam_size": q.exam_size,
        "section_count": q.section_count,
    }


def cold_sql(tail: str, *, before: bool = False) -> str:
    """Wrap `tail` in the shared cold-attempt CTEs. THE single definition of
    "fresh" in the engine — mastery, readiness coverage, trend and drill
    selection all read through this so they can never drift apart.

    Exposes two relations to `tail`:
      flagged — every attempt, with `is_cold` (1/0) and `prev_at`
      cold    — the cold attempts only, with `cold_rn` = 1 on each question's
                MOST RECENT cold attempt

    `before=True` adds a leading `?` placeholder restricting the log to attempts
    strictly earlier than that instant (mastery-as-it-stood-then). Bind params
    with `cold_params(before)`.
    """
    cond = "WHERE answered_at < ?" if before else ""
    return f"""
        WITH marked AS (
            SELECT id, question_id, section, subsection, correct, answered_at,
                   response_ms, mode,
                   LAG(answered_at) OVER (
                       PARTITION BY question_id ORDER BY answered_at, id) AS prev_at
            FROM attempts
            {cond}
        ),
        flagged AS (
            SELECT *,
                   CASE WHEN prev_at IS NULL
                         OR julianday(answered_at) - julianday(prev_at) >= ?
                        THEN 1 ELSE 0 END AS is_cold
            FROM marked
        ),
        cold AS (
            SELECT *,
                   ROW_NUMBER() OVER (
                       PARTITION BY question_id ORDER BY answered_at DESC, id DESC
                   ) AS cold_rn
            FROM flagged WHERE is_cold = 1
        )
        {tail}
    """


def cold_params(before: str | None = None) -> tuple:
    """Bind params for `cold_sql(..., before=bool(before))` — order matters."""
    return (before, FRESH_COOLDOWN_DAYS) if before else (FRESH_COOLDOWN_DAYS,)


def depth_tier(pct: float | None) -> str | None:
    """Depth tier from a fresh-accuracy %. None => unrated (needs a diagnostic)."""
    if pct is None:
        return None
    for name, cut in TIER_CUTOFFS:
        if pct >= cut:
            return name
    return "deep"


# back-compat alias (older callers used provisional_tier)
provisional_tier = depth_tier


def tier_css(tier: str | None) -> str:
    return _TIER_CSS.get(tier, "none")


def mastery_band(pct: float | None) -> str | None:
    """S-meter color band for a mastery %. Phase-2 placeholder for the depth-tier
    coloring that Phase 4.5 will drive: ok (≥80 Honours), warn (70–80), low (<70)."""
    if pct is None:
        return None
    if pct >= HONOURS_BAR:
        return "ok"
    if pct >= PASS_BAR:
        return "warn"
    return "low"


def compute_section_mastery(conn, before: str | None = None) -> dict[int, dict]:
    """Return {section: {name, answered, correct, mastery_pct, seen,
    size, coverage_pct, meets_honours}} for every section of the active
    qualification (8 for Basic, 7 for Advanced).

    `before` (ISO-8601 UTC) restricts the log to attempts strictly earlier than
    that instant — "mastery as it stood then". Used by the day digest to compute
    start-of-day deltas; default None = the full log (unchanged behavior)."""
    cond = "WHERE answered_at < ?" if before else ""
    params: tuple = (before,) if before else ()
    sizes = {
        r["section"]: r["n"]
        for r in conn.execute(
            "SELECT section, COUNT(*) n FROM questions GROUP BY section"
        ).fetchall()
    }
    stats = {
        r["section"]: r
        for r in conn.execute(
            f"""
            SELECT section,
                   COUNT(*)                         AS answered,
                   SUM(correct)                     AS correct,
                   COUNT(DISTINCT question_id)      AS seen
            FROM attempts
            {cond}
            GROUP BY section
            """,
            params,
        ).fetchall()
    }
    # FRESH stats: each question's MOST RECENT COLD attempt (see module docstring).
    fresh = {
        r["section"]: r
        for r in conn.execute(
            cold_sql(
                "SELECT section, COUNT(*) AS fa, SUM(correct) AS fc "
                "FROM cold WHERE cold_rn = 1 GROUP BY section",
                before=bool(before),
            ),
            cold_params(before),
        ).fetchall()
    }

    names, shorts = section_names(), section_short_names()
    out: dict[int, dict] = {}
    for section in quals.current().sections:
        size = sizes.get(section, 0)
        s = stats.get(section)
        answered = s["answered"] if s else 0
        correct = (s["correct"] or 0) if s else 0
        seen = s["seen"] if s else 0
        mastery = round(100.0 * correct / answered, 1) if answered else None
        coverage = round(100.0 * seen / size, 1) if size else 0.0

        fr = fresh.get(section)
        fresh_answered = fr["fa"] if fr else 0
        fresh_correct = (fr["fc"] or 0) if fr else 0
        fresh_pct = round(100.0 * fresh_correct / fresh_answered, 1) if fresh_answered else None

        # tier from fresh accuracy (exam-relevant); honours bar also tracks fresh
        tier = depth_tier(fresh_pct)
        out[section] = {
            "section": section,
            "name": names.get(section, f"Section {section}"),
            "short": shorts.get(section, f"Section {section}"),
            "size": size,
            "answered": answered,
            "correct": correct,
            "seen": seen,
            "mastery_pct": mastery,
            "coverage_pct": coverage,
            "fresh_answered": fresh_answered,
            "fresh_correct": fresh_correct,
            "fresh_pct": fresh_pct,
            "meets_honours": fresh_pct is not None and fresh_pct >= HONOURS_BAR,
            "band": mastery_band(fresh_pct),
            "tier": tier,
            "tier_css": tier_css(tier),
        }
    return out


def overall_summary(conn) -> dict:
    """Aggregate readiness snapshot for the dashboard header."""
    by_section = compute_section_mastery(conn)
    answered = sum(s["answered"] for s in by_section.values())
    correct = sum(s["correct"] for s in by_section.values())
    overall = round(100.0 * correct / answered, 1) if answered else None
    sections_meeting = sum(1 for s in by_section.values() if s["meets_honours"])
    return {
        "answered": answered,
        "correct": correct,
        "overall_pct": overall,
        "sections_meeting_honours": sections_meeting,
        # NB: true readiness also needs the §6d.4 coverage guarantee (Phase 4.5/5);
        # this flag is a coarse Phase-2 placeholder, not the terminal signal.
        "all_sections_honours": sections_meeting == quals.current().section_count,
        "pass_bar": PASS_BAR,
        "honours_bar": HONOURS_BAR,
    }

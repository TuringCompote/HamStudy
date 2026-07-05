"""AI-written study journal (spec §6c / §7). Plain Markdown files in JOURNAL_DIR
(QUESTIONS #11 — no special Obsidian integration; point Obsidian at the folder).

The deterministic engine supplies the facts — a full day digest (what was
answered, what was missed and how, deltas) plus the plan — and the AI layer only
narrates them. Falls back to a deterministic summary when AI is unavailable.
Indexed in the `journal` table. Dated YYYY-MM-DD (local, config.TZ); re-running
the same day rewrites.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app import config, timeutil
from app.db.queries import SECTION_SHORT_NAMES
from app.engine import recommend, mastery, diagnostic, day_digest
from app.coaching.ai_provider import get_provider


def _mode_label(mode: str) -> str:
    return {"drill": "drill", "exam": "mock exam", "review": "review",
            "diagnostic": "diagnostic"}.get(mode, mode)


def write_journal(conn, entry_date: str | None = None) -> dict:
    # local day (config.TZ), not container-UTC — an evening entry is still "today"
    entry_date = entry_date or timeutil.today_local().isoformat()
    rec = recommend.build_recommendation(conn)
    by_section = mastery.compute_section_mastery(conn)
    diagnostic.apply_diagnostic_tiers(conn, by_section)

    # the day's facts + the plan + yesterday's thread, for the narrator
    digest = day_digest.build_day_digest(conn, entry_date)
    ns = rec["next_session"]
    digest["plan"] = {
        "focus_section": SECTION_SHORT_NAMES.get(ns.get("focus_section"), None),
        "new_count": ns["new_count"],
        "review_count": ns["review_count"],
        "rationale": ns.get("rationale", ""),
    }
    prev = conn.execute(
        "SELECT entry_date, summary FROM journal WHERE entry_date < ? "
        "ORDER BY entry_date DESC LIMIT 1",
        (entry_date,),
    ).fetchone()
    if prev is not None:
        digest["yesterday"] = {"date": prev["entry_date"], "summary": prev["summary"] or ""}

    narration = get_provider().narrate(digest=digest)

    lines = [f"# Study journal — {entry_date}", ""]
    lines.append(narration.text.strip())
    if digest["answered"]:
        lines.append("")
        lines.append("## Today")
        mode_bits = ", ".join(
            f"{_mode_label(m)} {v['correct']}/{v['answered']}"
            for m, v in digest["by_mode"].items()
        )
        lines.append(f"- **{digest['answered']} answered · {digest['pct']}%** "
                     f"({mode_bits}) · streak {digest['streak']} day"
                     f"{'s' if digest['streak'] != 1 else ''}")
        if digest["fast_wrong"]:
            lines.append(f"- confident-but-wrong (fast misses): {digest['fast_wrong']}")
        if digest["misses"]:
            lines.append("")
            lines.append("### Missed today")
            for m in digest["misses"]:
                times = f" ({m['times']}×)" if m["times"] > 1 else ""
                fast = " · *fast*" if m["fast"] else ""
                lines.append(f"- `{m['question_id']}`{times}{fast} — {m['text']}")
                lines.append(f"  chose “{m['chosen']}” → correct “{m['correct_answer']}”")
            extra = digest["miss_count"] - sum(m["times"] for m in digest["misses"])
            if extra > 0:
                lines.append(f"- …and {extra} more in the review queue")
    lines.append("")
    lines.append("## Per-section (fresh accuracy / tier / trend)")
    for s in by_section.values():
        pct = s["fresh_pct"]
        lines.append(
            f"- **{s['short']}**: "
            f"{pct if pct is not None else '—'}{'%' if pct is not None else ''} "
            f"· {s['tier'] or 'unrated'} · {rec['readiness']['per_section'][s['section']]['trend']}"
        )
    lines.append("")
    rd = rec["readiness"]
    lines.append(f"**Exam-ready:** {'yes — book it' if rd['exam_ready'] else 'not yet'}"
                 + (f" ({'; '.join(rd['blockers'])})" if rd["blockers"] else ""))
    if narration.degraded:
        lines.append("")
        lines.append("_(AI narration unavailable — deterministic summary.)_")
    body = "\n".join(lines) + "\n"

    config.JOURNAL_DIR.mkdir(parents=True, exist_ok=True)
    path = config.JOURNAL_DIR / f"{entry_date}.md"
    path.write_text(body, encoding="utf-8")

    # index it (one row per date; replace on rewrite)
    conn.execute("DELETE FROM journal WHERE entry_date = ?", (entry_date,))
    conn.execute(
        "INSERT INTO journal (entry_date, file_path, summary, created_at) VALUES (?,?,?,?)",
        (entry_date, str(path), (narration.text or "")[:200],
         datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    return {"entry_date": entry_date, "path": str(path),
            "degraded": narration.degraded, "cost_usd": narration.cost_usd}

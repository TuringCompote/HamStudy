"""AI-written study journal (spec §6c / §7). Plain Markdown files in JOURNAL_DIR
(QUESTIONS #11 — no special Obsidian integration; point Obsidian at the folder).

The deterministic engine supplies the facts (scores, plan, deltas); the AI layer
narrates them. Falls back to a deterministic summary when AI is unavailable.
Indexed in the `journal` table. Dated YYYY-MM-DD; re-running the same day rewrites.
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from app import config
from app.engine import recommend, mastery, diagnostic
from app.coaching.ai_provider import get_provider


def write_journal(conn, entry_date: str | None = None) -> dict:
    entry_date = entry_date or date.today().isoformat()
    rec = recommend.build_recommendation(conn)
    by_section = mastery.compute_section_mastery(conn)
    diagnostic.apply_diagnostic_tiers(conn, by_section)

    narration = get_provider().narrate(recommendation=rec)

    lines = [f"# Study journal — {entry_date}", ""]
    lines.append(narration.text.strip() or rec["next_session"]["rationale"])
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

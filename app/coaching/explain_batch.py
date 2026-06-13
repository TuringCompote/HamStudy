"""Batch-generated structured explanation layer (spec §6f).

Pre-generate a RICH, STRUCTURED explanation for every bank question once (via the
Message Batches API, 50% off, cached RIC prefix), store as JSON in `explanations`
keyed by (question_id, bank_version, model). At study time `explain()` is a DB read;
the app reveals depth by the user's §6d tier (adaptive reveal, free). Regenerate
only on a bank revision.

This module holds the request shape + a live `generate_one()` (used for the dry run
and as the fallback). The batch submit/poll/write pipeline is added after sign-off.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import anthropic

from app import config
from app.coaching import prompts, corpus, usage as usage_mod
from app.db.queries import questions_for_ids  # noqa: F401  (kept for callers)

# Structured-output schema for one explanation (spec §6f.2 superset).
LAYER_SCHEMA = {
    "type": "object",
    "properties": {
        "core": {"type": "string"},
        "distractors": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "option": {"type": "string", "enum": ["A", "B", "C", "D"]},
                    "why_wrong": {"type": "string"},
                    "why_tempting": {"type": "string"},
                },
                "required": ["option", "why_wrong", "why_tempting"],
                "additionalProperties": False,
            },
        },
        "concept": {"type": "string"},
        "misconception": {"type": "string"},
        "link": {"anyOf": [{"type": "string"}, {"type": "null"}]},
        "mnemonic": {"type": "string"},
        "edge_cases": {"type": "string"},
    },
    "required": ["core", "distractors", "concept", "misconception", "link"],
    "additionalProperties": False,
}

_LETTERS = ["A", "B", "C", "D"]
MAX_TOKENS = 1200  # rich: room for the full layered superset


def system_blocks(grounding: str = "") -> list[dict]:
    """Shared, cacheable prefix: style prompt + (regs) RIC grounding."""
    blocks = [{"type": "text", "text": prompts.system_prompt("batch_explain")}]
    if grounding:
        blocks.append({
            "type": "text",
            "text": "Reference material (grounding only, do not copy):\n" + grounding,
            "cache_control": {"type": "ephemeral"},
        })
    return blocks


def user_block(question: dict) -> str:
    opts = question["options"]
    lines = [f"Question ({question['id']}, section {question['section']}): {question['text']}",
             "Options:"]
    for i, o in enumerate(opts):
        lines.append(f"  {_LETTERS[i]}. {o}")
    lines.append(f"Correct answer: {_LETTERS[question['correct_index']]}")
    lines.append("Write the structured explanation. In `distractors`, cover each wrong "
                 "option by its letter.")
    return "\n".join(lines)


def generate_one(client, question: dict, grounding: str = "", model: str | None = None):
    """One live structured-output call. Returns (layers_dict, usage)."""
    model = model or config.AI_MODELS.get("explain", config.AI_MODEL)
    resp = client.messages.create(
        model=model,
        max_tokens=MAX_TOKENS,
        system=system_blocks(grounding),
        messages=[{"role": "user", "content": user_block(question)}],
        output_config={"format": {"type": "json_schema", "schema": LAYER_SCHEMA}},
    )
    text = "".join(b.text for b in resp.content if b.type == "text")
    return json.loads(text), resp.usage


# Default reveal depth by §6d depth tier (adaptive reveal, free — spec §6f.5).
DEPTH_LAYERS = {
    "test-out": ["core"],
    "light": ["core", "misconception"],
    "standard": ["core", "distractors", "misconception"],
    "deep": ["core", "distractors", "concept", "misconception", "link", "mnemonic", "edge_cases"],
    None: ["core", "distractors", "concept", "misconception"],  # unrated → generous default
}


# --- batch pipeline ---------------------------------------------------------
def _question_rows(conn):
    return conn.execute(
        "SELECT id, section, subsection, text, options, correct_index, bank_version "
        "FROM questions ORDER BY id"
    ).fetchall()


def build_requests(conn, model: str) -> list[dict]:
    """One Message Batches request per question. Regs sections carry cached RIC/RBR
    grounding; electronics/antenna carry only the (tiny) style prompt."""
    reqs = []
    for r in _question_rows(conn):
        question = {
            "id": r["id"], "section": r["section"], "subsection": r["subsection"],
            "text": r["text"], "options": json.loads(r["options"]),
            "correct_index": r["correct_index"],
        }
        grounding = corpus.ground_for_section(r["section"])
        sys = [{"type": "text", "text": prompts.system_prompt("batch_explain")}]
        if grounding:
            sys.append({
                "type": "text",
                "text": "Reference material (grounding only, do not copy):\n" + grounding,
                "cache_control": {"type": "ephemeral", "ttl": "1h"},
            })
        reqs.append({
            "custom_id": r["id"],
            "params": {
                "model": model,
                "max_tokens": MAX_TOKENS,
                "system": sys,
                "messages": [{"role": "user", "content": user_block(question)}],
                "output_config": {"format": {"type": "json_schema", "schema": LAYER_SCHEMA}},
            },
        })
    return reqs


def submit(conn, model: str | None = None) -> str:
    """Submit the full bank as one batch; record the id in meta. Returns batch id."""
    model = model or config.AI_MODELS.get("explain", config.AI_MODEL)
    client = _client()
    batch = client.messages.batches.create(requests=build_requests(conn, model))
    conn.execute(
        "INSERT INTO meta(key,value) VALUES('explain_batch_id', ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (batch.id,))
    conn.execute(
        "INSERT INTO meta(key,value) VALUES('explain_batch_model', ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (model,))
    conn.commit()
    return batch.id


def status(batch_id: str) -> str:
    return _client().messages.batches.retrieve(batch_id).processing_status


def collect(conn, batch_id: str, model: str) -> dict:
    """Write succeeded results into `explanations`; return coverage + cost stats."""
    client = _client()
    ok = err = 0
    cost = 0.0
    now = datetime.now(timezone.utc).isoformat()
    for res in client.messages.batches.results(batch_id):
        if res.result.type != "succeeded":
            err += 1
            continue
        msg = res.result.message
        bank_version = conn.execute(
            "SELECT bank_version FROM questions WHERE id=?", (res.custom_id,)
        ).fetchone()
        if bank_version is None:
            err += 1
            continue
        bv = bank_version["bank_version"]
        text = "".join(b.text for b in msg.content if b.type == "text")
        try:
            layers = json.loads(text)
        except json.JSONDecodeError:
            err += 1
            continue
        conn.execute(
            "INSERT INTO explanations(question_id,bank_version,model,layers,generated_at) "
            "VALUES (?,?,?,?,?) ON CONFLICT(question_id,bank_version) DO UPDATE SET "
            "model=excluded.model, layers=excluded.layers, generated_at=excluded.generated_at",
            (res.custom_id, bv, model, json.dumps(layers, ensure_ascii=False), now))
        ok += 1
        u = msg.usage
        cost += usage_mod.estimate_cost(
            model,
            getattr(u, "input_tokens", 0) or 0,
            getattr(u, "output_tokens", 0) or 0,
            getattr(u, "cache_read_input_tokens", 0) or 0,
            getattr(u, "cache_creation_input_tokens", 0) or 0,
        ) * 0.5  # Batch API is 50% off
    conn.commit()
    total = conn.execute("SELECT COUNT(*) c FROM questions").fetchone()["c"]
    have = conn.execute("SELECT COUNT(*) c FROM explanations").fetchone()["c"]
    return {"written_ok": ok, "errors": err, "have": have, "total": total,
            "coverage_pct": round(100.0 * have / total, 1) if total else 0.0,
            "est_batch_cost_usd": round(cost, 2)}


def get_explanation(conn, question_id: str, bank_version: str | None = None):
    """Cache-first read of stored layers for a question. None if not generated."""
    if bank_version:
        row = conn.execute(
            "SELECT layers FROM explanations WHERE question_id=? AND bank_version=?",
            (question_id, bank_version)).fetchone()
    else:
        row = conn.execute(
            "SELECT layers FROM explanations WHERE question_id=? ORDER BY generated_at DESC LIMIT 1",
            (question_id,)).fetchone()
    return json.loads(row["layers"]) if row else None


def _client():
    try:
        import truststore
        truststore.inject_into_ssl()
    except Exception:
        pass
    return anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)


# --- portable seed (commit the batch asset so it travels with the repo) ------
def export_explanations(conn, path: Path) -> int:
    """Dump all stored explanations to JSONL — a committable seed so a fresh
    clone/LXC can reconstruct the DB without re-running the paid batch."""
    rows = conn.execute(
        "SELECT question_id, bank_version, model, layers, generated_at "
        "FROM explanations ORDER BY question_id"
    ).fetchall()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps({k: r[k] for k in r.keys()}, ensure_ascii=False) + "\n")
    return len(rows)


def import_explanations(conn, path: Path) -> int:
    """Load explanations from a seed JSONL into the `explanations` table (upsert).
    Run AFTER ingest so question_id foreign keys exist."""
    n = 0
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            conn.execute(
                "INSERT INTO explanations(question_id,bank_version,model,layers,generated_at) "
                "VALUES (?,?,?,?,?) ON CONFLICT(question_id,bank_version) DO UPDATE SET "
                "model=excluded.model, layers=excluded.layers, generated_at=excluded.generated_at",
                (r["question_id"], r["bank_version"], r["model"], r["layers"], r["generated_at"]))
            n += 1
    conn.commit()
    return n


if __name__ == "__main__":
    import argparse
    from app.db.init_db import connect

    ap = argparse.ArgumentParser(description="Explanation batch seed export/import.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    pe = sub.add_parser("export"); pe.add_argument("--path", required=True, type=Path)
    pi = sub.add_parser("import"); pi.add_argument("--path", required=True, type=Path)
    args = ap.parse_args()
    conn = connect()
    if args.cmd == "export":
        print(f"exported {export_explanations(conn, args.path)} explanations -> {args.path}")
    else:
        print(f"imported {import_explanations(conn, args.path)} explanations from {args.path}")

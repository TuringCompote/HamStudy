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

import anthropic

from app import config
from app.coaching import prompts, corpus

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

"""Load externalized, Console-tunable system prompts from prompts/<call_type>.md.

Tune a prompt in the Anthropic Console Workbench, drop the improved text back into
the matching file — no code change. Falls back to a built-in default if a file is
missing, so the AI layer never hard-fails on a missing prompt.
"""
from __future__ import annotations

from functools import lru_cache

from app import config

_DEFAULTS = {
    "explain": "You are Elmer, an amateur-radio exam coach. Explain concisely and "
               "technically in your own words; do not copy any reference prose.",
    "diagnose": "You are Elmer, an amateur-radio exam coach. Diagnose the underlying "
                "misconception concisely, in your own words.",
    "narrate": "You are Elmer, an amateur-radio exam coach. Write a short, plain-language "
               "session note.",
    "condense": "You are Elmer, an amateur-radio exam coach. Condense the lesson to the "
                "requested depth in your own words; do not copy reference prose.",
}


@lru_cache(maxsize=16)
def system_prompt(call_type: str) -> str:
    path = config.PROMPTS_DIR / f"{call_type}.md"
    if path.exists():
        text = path.read_text(encoding="utf-8").strip()
        if text:
            return text
    return _DEFAULTS.get(call_type, _DEFAULTS["explain"])

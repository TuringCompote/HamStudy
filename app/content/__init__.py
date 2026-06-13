"""Original per-section lesson text (constitution §3 — written fresh, never copied
from community courses). Markdown files in `sections/` render to HTML for the
section page's "Learn" panel.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import markdown as _md

_DIR = Path(__file__).resolve().parent / "sections"


@lru_cache(maxsize=16)
def lesson_html(section: int) -> str | None:
    """Rendered HTML for a section's lesson, or None if no lesson file exists."""
    path = _DIR / f"section{section}.md"
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    return _md.markdown(text, extensions=["extra", "sane_lists"])

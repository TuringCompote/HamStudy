"""Original per-section lesson text (constitution §3 — written fresh, never copied
from community courses). Markdown files in `sections/` render to HTML for the
section page's "Learn" panel.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import markdown as _md

from app import quals


def lesson_html(section: int) -> str | None:
    """Rendered HTML for the active qualification's lesson, or None if missing."""
    return _lesson_html(quals.current().code, section)


@lru_cache(maxsize=32)
def _lesson_html(qual_code: str, section: int) -> str | None:
    path = quals.get(qual_code).lessons_dir / f"section{section}.md"
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    return _md.markdown(text, extensions=["extra", "sane_lists"])

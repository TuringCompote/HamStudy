"""Curated local reference corpus for AI grounding (spec §6d.6, QUESTIONS #19).

Extracts the freely-usable Government-of-Canada regulatory docs (RBR-4 PDF, RIC-3 /
RIC-1 HTML) once into `references/_corpus/*.txt`, then serves the relevant text as
GROUNDING for explain/diagnose on the regulation-heavy sections. The AI grounds on
this to stay accurate but writes original prose (constitution §3); the grounding is
passed as a cache_control block so repeat calls hit the prompt cache.

Electronics/antenna sections have no regulatory grounding here — those rely on the
model's own knowledge (we don't ship an electronics reference corpus). This is the
first slice of the §6d.6 corpus; user-added PDFs can extend it later.
"""
from __future__ import annotations

import html
import re
from functools import lru_cache

from app import config

_CORPUS_DIR = config.REFERENCES_DIR / "_corpus"
_GROUND_MAX_CHARS = 20000  # ~5k tokens — bounded cost, above the prompt-cache minimum

# source file -> corpus text file
_SOURCES = {
    "RBR-4-i3-2022-07EN.pdf": "rbr4.txt",
    "RIC-3.html": "ric3.txt",
    "RIC-1.html": "ric1.txt",
}

# section -> corpus files used for grounding (regs-heavy sections only)
_SECTION_GROUNDING = {
    1: ["rbr4.txt", "ric3.txt"],   # Regulations and Policies
    2: ["ric3.txt"],               # Operating and Procedures
}


def _html_to_text(raw: str) -> str:
    raw = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", raw)
    text = re.sub(r"<[^>]+>", " ", raw)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def build_corpus(force: bool = False) -> dict:
    """Extract source docs into references/_corpus/*.txt. Idempotent."""
    _CORPUS_DIR.mkdir(parents=True, exist_ok=True)
    built = {}
    for src, out in _SOURCES.items():
        src_path = config.REFERENCES_DIR / src
        out_path = _CORPUS_DIR / out
        if out_path.exists() and not force:
            built[out] = "cached"
            continue
        if not src_path.exists():
            built[out] = "missing-source"
            continue
        try:
            if src.endswith(".pdf"):
                import pdfplumber
                with pdfplumber.open(src_path) as pdf:
                    text = "\n".join((p.extract_text() or "") for p in pdf.pages)
            else:
                text = _html_to_text(src_path.read_text(encoding="utf-8", errors="replace"))
            out_path.write_text(text, encoding="utf-8")
            built[out] = f"{len(text)} chars"
        except Exception as e:  # noqa: BLE001
            built[out] = f"error: {e}"
    return built


@lru_cache(maxsize=16)
def _load(out_name: str) -> str:
    path = _CORPUS_DIR / out_name
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def ground_for_section(section: int) -> str:
    """Grounding text for a section, or '' if none. Builds the corpus on demand."""
    files = _SECTION_GROUNDING.get(section)
    if not files:
        return ""
    if not _CORPUS_DIR.exists():
        build_corpus()
    parts = [_load(f) for f in files]
    grounding = "\n\n".join(p for p in parts if p).strip()
    return grounding[:_GROUND_MAX_CHARS]

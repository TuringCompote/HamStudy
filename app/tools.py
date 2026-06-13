"""Registry mapping the 8 syllabus sections to their interactive concept tools.

Each tool is a self-contained client-side widget (SVG + vanilla JS) under
`static/tools/<id>.js` that themes from `tokens.css`. The server only needs to
know which tools belong on which section page and what scripts to include; all
the math runs in the browser (constitution §1 — interactive over rote).

Spec §6b: tools matter most for sections 4–8. P0 tools (BACKLOG Phase 3):
Ohm's law, reactance/resonance, decibels, SWR/impedance, wavelength↔frequency.
"""
from __future__ import annotations

# id -> metadata. `js` is the static path included on the section page.
TOOLS: dict[str, dict] = {
    "ohms": {
        "name": "Ohm's Law & Power",
        "blurb": "Enter any two of V, I, R, P — see the other two and the formula used.",
        "js": "/static/tools/ohms.js",
    },
    "reactance": {
        "name": "Reactance & Resonance",
        "blurb": "Sweep L, C and frequency; watch X_L and X_C cross at resonance.",
        "js": "/static/tools/reactance.js",
    },
    "decibel": {
        "name": "Decibel Converter",
        "blurb": "Convert power/voltage ratios ↔ dB, with S-unit (6 dB) examples.",
        "js": "/static/tools/decibel.js",
    },
    "swr": {
        "name": "SWR & Impedance Match",
        "blurb": "See how a load mismatch sets SWR, reflected power and added loss.",
        "js": "/static/tools/swr.js",
    },
    "wavelength": {
        "name": "Wavelength ↔ Frequency",
        "blurb": "Convert f ↔ λ and size a ½λ dipole or ¼λ vertical.",
        "js": "/static/tools/wavelength.js",
    },
}

# section number -> ordered list of tool ids shown on that section's page.
SECTION_TOOLS: dict[int, list[str]] = {
    4: [],                                   # Circuit Components (series/parallel tool later)
    5: ["ohms", "reactance", "decibel"],     # Basic Electronics & Theory
    6: ["swr", "wavelength"],                # Feedlines & Antenna Systems
}


def tools_for_section(section: int) -> list[dict]:
    """Return [{id, name, blurb, js}] for a section (empty if none)."""
    out = []
    for tid in SECTION_TOOLS.get(section, []):
        meta = TOOLS.get(tid)
        if meta:
            out.append({"id": tid, **meta})
    return out

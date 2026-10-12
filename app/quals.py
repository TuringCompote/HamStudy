"""Qualification profiles — Basic and Advanced as separate, fully-tracked tracks.

Phase 7 (README roadmap): the Advanced Qualification reuses the whole engine. The
deterministic engine only ever consumes a `conn` + section scopes, so a second
qualification is a second *profile*: its own bank, its own SQLite file (so
`attempts`, `progress`, `diagnostics`, `explanations`, `recommendation`, `journal`
are all tracked separately — nothing is shared or mixed), its own journal folder,
recommendation.json, seed file, lessons, tool map and grounding.

The active profile is a `ContextVar`, set per request by the ASGI scope wrapper in
`app.main` (Basic is mounted at `/`, Advanced at `/advanced`) and by `activate()`
in the CLI scripts (`--qual advanced`). `connect()` and every path/section lookup
read it, so the engine code never branches on the qualification itself.

Both exams: 70% is a pass. Basic additionally awards **Honours at 80%** (which
unlocks HF). Advanced has no honours grade; we keep the same 80% fresh-accuracy
*training target* for readiness (margin above the pass line) and label it
"target" instead of "Honours" in the UI.
"""
from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass, field
from pathlib import Path

from app import config


@dataclass(frozen=True)
class Qual:
    code: str                      # "basic" | "advanced"
    label: str                     # "Basic" | "Advanced"
    id_prefix: str                 # "B" | "A"  (B-AAA-BBB-CCC / A-AAA-BBB-CCC)
    url_prefix: str                # "" | "/advanced"
    section_names: dict[int, str]
    section_short: dict[int, str]
    exam_size: int                 # real exam length (100 Basic / 50 Advanced)
    expected_total: int            # bank size the validator asserts
    honours: bool                  # does the exam award an Honours grade?
    bank_filename: str             # in references/
    bank_url: str
    seed_filename: str             # seed/<file>.jsonl — committed explanations
    lessons_dirname: str           # app/content/<dir>/section{n}.md
    delim_filename: str = ""       # references/_extracted/<file>: ISED's delimited bank
    tools: dict[int, list[str]] = field(default_factory=dict)      # section -> tool ids
    grounding: dict[int, list[str]] = field(default_factory=dict)  # section -> corpus files
    tagline: str = ""
    # icon/manifest name suffix so the two home-screen apps are distinguishable
    short_name: str = ""

    # --- derived -----------------------------------------------------------
    @property
    def sections(self) -> list[int]:
        return sorted(self.section_names)

    @property
    def section_count(self) -> int:
        return len(self.section_names)

    @property
    def target_label(self) -> str:
        """What the 80% bar is called in this qualification's UI."""
        return "Honours" if self.honours else "target"

    # Paths resolve through `config` at access time (not import time) so the
    # smoke test's config overrides keep working for Basic, and env overrides
    # (HAMSTUDY_DB_ADVANCED, …) apply for Advanced.
    @property
    def db_path(self) -> Path:
        return config.DB_PATH if self.code == "basic" else config.DB_PATH_ADVANCED

    @property
    def recommendation_path(self) -> Path:
        return (config.RECOMMENDATION_PATH if self.code == "basic"
                else config.RECOMMENDATION_PATH_ADVANCED)

    @property
    def journal_dir(self) -> Path:
        return config.JOURNAL_DIR if self.code == "basic" else config.JOURNAL_DIR_ADVANCED

    @property
    def bank_pdf(self) -> Path:
        if self.code == "basic":
            return config.BANK_PDF
        return config.BANK_PDF_ADVANCED

    @property
    def delim_path(self) -> Path:
        return config.REFERENCES_DIR / "_extracted" / self.delim_filename

    @property
    def seed_path(self) -> Path:
        return config.ROOT / "seed" / self.seed_filename

    @property
    def lessons_dir(self) -> Path:
        return Path(__file__).resolve().parent / "content" / self.lessons_dirname


BASIC = Qual(
    code="basic",
    label="Basic",
    id_prefix="B",
    url_prefix="",
    section_names={
        1: "Regulations and Policies",
        2: "Operating and Procedures",
        3: "Station Assembly, Practice and Safety",
        4: "Circuit Components",
        5: "Basic Electronics and Theory",
        6: "Feedlines and Antenna Systems",
        7: "Radio Wave Propagation",
        8: "Interference and Suppression",
    },
    section_short={
        1: "Regulations & policies",
        2: "Operating & procedures",
        3: "Station assembly & safety",
        4: "Circuit components",
        5: "Basic electronics & theory",
        6: "Feedlines & antennas",
        7: "Radio wave propagation",
        8: "Interference & suppression",
    },
    exam_size=100,
    expected_total=984,
    honours=True,
    bank_filename="amateur_basic_questions_en.pdf",
    bank_url="https://apc-cap.ic.gc.ca/datafiles/amateur_basic_questions_en.pdf",
    delim_filename="amat_basic_quest_delim.txt",
    seed_filename="explanations.jsonl",
    lessons_dirname="sections",
    tools={
        1: ["bandplan"],
        4: ["seriesparallel"],
        5: ["ohms", "reactance", "decibel"],
        6: ["swr", "wavelength"],
        7: ["propagation"],
    },
    grounding={1: ["rbr4.txt", "ric3.txt"], 2: ["ric3.txt"]},
    tagline="Canadian Basic — targeting Honours (80%)",
    short_name="Elmer",
)

# Advanced bank sections (ISED, A-001 … A-007). Names are ours (navigation labels).
ADVANCED = Qual(
    code="advanced",
    label="Advanced",
    id_prefix="A",
    url_prefix="/advanced",
    section_names={
        1: "Advanced Theory",
        2: "Advanced Components and Circuits",
        3: "Measurements",
        4: "Power Supplies",
        5: "Transmitters, Modulation and Processing",
        6: "Receivers",
        7: "Feedlines — Matching and Antenna Systems",
    },
    section_short={
        1: "Advanced theory",
        2: "Components & circuits",
        3: "Measurements",
        4: "Power supplies",
        5: "Transmitters & modulation",
        6: "Receivers",
        7: "Feedlines & antennas",
    },
    exam_size=50,
    expected_total=0,     # set by ingest from the PDF; validate reads meta if 0
    honours=False,
    bank_filename="amateur_advanced_questions_en.pdf",
    bank_url="https://apc-cap.ic.gc.ca/datafiles/amateur_advanced_questions_en.pdf",
    delim_filename="amat_adv_quest_delim.txt",
    seed_filename="explanations_advanced.jsonl",
    lessons_dirname="sections_advanced",
    tools={
        1: ["reactance", "decibel", "ohms"],
        2: ["seriesparallel"],
        7: ["swr", "wavelength"],
    },
    grounding={},         # Advanced is technical; RBR-4 power limits live in section 1
    tagline="Canadian Advanced — pass is 70%, training target 80%",
    short_name="Elmer Adv",
)

QUALS: dict[str, Qual] = {q.code: q for q in (BASIC, ADVANCED)}

_active: ContextVar[str] = ContextVar("elmer_qual", default="basic")


def current() -> Qual:
    """The qualification this request / process is operating on."""
    return QUALS[_active.get()]


def get(code: str) -> Qual:
    if code not in QUALS:
        raise KeyError(f"unknown qualification {code!r}; expected one of {sorted(QUALS)}")
    return QUALS[code]


def activate(code: str):
    """Set the active qualification for this context. Returns a token for reset().
    CLI scripts call this once; the app's ASGI wrapper calls it per request."""
    get(code)
    return _active.set(code)


def reset(token) -> None:
    _active.reset(token)


def add_cli_arg(parser) -> None:
    """Shared `--qual {basic,advanced}` for the maintenance scripts."""
    parser.add_argument("--qual", choices=sorted(QUALS), default="basic",
                        help="which qualification's bank/DB to operate on (default: basic)")

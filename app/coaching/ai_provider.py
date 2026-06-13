"""AIProvider — the swappable boundary for all generative work (spec §0.1).

The deterministic engine never calls this; only the generative layer does:
  explain()  — why a specific answer is wrong / a concept, for the user's level
  diagnose() — why a misconception recurs (the "fast + wrong" case)
  narrate()  — phrase "today's session" / journal in plain language
  condense() — compress a lesson to the chosen depth tier, grounded in the corpus

Implementations: StubProvider (deterministic, offline, free — always available)
and AnthropicProvider (Claude, behind this same interface). A local model (Ollama)
can be dropped in later without touching callers. Pick via config.AI_PROVIDER;
callers should fall back to the stub when the budget guard trips.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class AIResult:
    text: str
    model: str = "stub"
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    degraded: bool = False     # True when we fell back to the stub (no key / budget)
    call_type: str = "explain"


class AIProvider(ABC):
    name = "base"

    @abstractmethod
    def explain(self, *, question: dict, chosen_index: int, grounding: str = "") -> AIResult: ...

    @abstractmethod
    def diagnose(self, *, section_name: str, miss_summary: str, grounding: str = "") -> AIResult: ...

    @abstractmethod
    def narrate(self, *, recommendation: dict) -> AIResult: ...

    @abstractmethod
    def condense(self, *, lesson_text: str, tier: str, gaps: str = "", grounding: str = "") -> AIResult: ...


# --- letters helper ---
_LETTERS = ["A", "B", "C", "D"]


class StubProvider(AIProvider):
    """Deterministic, offline fallback. Produces honest, useful (if plain) text
    from the data alone — no model call, no cost. Keeps the app fully functional
    with no API key and when the monthly budget is exhausted (constitution)."""
    name = "stub"

    def explain(self, *, question: dict, chosen_index: int, grounding: str = "") -> AIResult:
        opts = question.get("options", [])
        ci = question.get("correct_index")
        correct_txt = opts[ci] if ci is not None and ci < len(opts) else "(see the bank)"
        chose_txt = opts[chosen_index] if chosen_index < len(opts) else ""
        right = chosen_index == ci
        if right:
            body = f"Correct — “{correct_txt}”. Make sure you can say *why* the others are wrong."
        else:
            body = (
                f"The correct answer is {_LETTERS[ci]}: “{correct_txt}”.\n\n"
                f"You chose {_LETTERS[chosen_index]}: “{chose_txt}”. "
                "Re-read the question stem and compare the two — the distinction is the "
                "thing to learn here. (AI explanations are off; set an API key for a "
                "tailored walk-through.)"
            )
        return AIResult(text=body, degraded=True, call_type="explain")

    def diagnose(self, *, section_name: str, miss_summary: str, grounding: str = "") -> AIResult:
        return AIResult(
            text=(f"In {section_name}, your misses cluster as: {miss_summary}. "
                  "Focus the next session there. (Enable the AI layer for a deeper "
                  "misconception diagnosis.)"),
            degraded=True, call_type="diagnose",
        )

    def narrate(self, *, recommendation: dict) -> AIResult:
        ns = recommendation.get("next_session", {})
        return AIResult(text=ns.get("rationale", "Keep going — drill your weakest section."),
                        degraded=True, call_type="narrate")

    def condense(self, *, lesson_text: str, tier: str, gaps: str = "", grounding: str = "") -> AIResult:
        note = {
            "test-out": "You're testing out here — skim; we'll keep it warm with occasional review.",
            "light": "You're close — focus only on the gaps below.",
            "standard": "Work through the full lesson, then drill.",
            "deep": "Take this slowly — full lesson plus extra practice on each miss.",
        }.get(tier, "")
        return AIResult(text=note, degraded=True, call_type="condense")


def get_provider(force_stub: bool = False) -> AIProvider:
    """Factory: AnthropicProvider when configured + budget allows, else StubProvider."""
    from app import config
    if force_stub or config.AI_PROVIDER != "anthropic" or not config.ANTHROPIC_API_KEY:
        return StubProvider()
    try:
        from app.coaching.anthropic_provider import AnthropicProvider
        return AnthropicProvider()
    except Exception:
        return StubProvider()

"""Anthropic implementation of AIProvider (spec §0.1).

Calls Claude (default Opus 4.8) for the generative layer only — explanations,
misconception diagnosis, session narration, lesson condensation. Original text
only: the system prompt instructs Claude to write fresh explanations grounded in
the supplied reference material, never to reproduce source prose (constitution §3).

Guardrails:
  - Budget guard: before every call, check month-to-date spend (usage table) vs
    the monthly ceiling; if exceeded, fall back to the deterministic stub.
  - Usage logging: every successful call logs tokens + estimated cost.
  - Any API error also falls back to the stub — the core loop never breaks.

Opus 4.8 API notes (per the claude-api reference): adaptive thinking only (we omit
thinking for these short calls), no temperature/top_p, usage on response.usage.
Grounding/reference docs are passed as a cache_control system block.
"""
from __future__ import annotations

import anthropic

from app import config
from app.db.init_db import connect
from app.coaching import usage, prompts
from app.coaching.ai_provider import AIProvider, AIResult, StubProvider


class AnthropicProvider(AIProvider):
    name = "anthropic"

    def __init__(self):
        if not config.ANTHROPIC_API_KEY:
            raise RuntimeError("ANTHROPIC_API_KEY not set")
        # Use the OS trust store for TLS (Windows Python lacks a CA bundle otherwise).
        try:
            import truststore
            truststore.inject_into_ssl()
        except Exception:
            pass
        self.client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        self._stub = StubProvider()

    def _model_for(self, call_type: str) -> str:
        return config.AI_MODELS.get(call_type, config.AI_MODEL)

    # --- core call with budget guard + usage logging + graceful fallback ---
    def _call(self, *, user: str, call_type: str, grounding: str = "",
              max_tokens: int = 700, stub_result: AIResult) -> AIResult:
        model = self._model_for(call_type)
        conn = connect()
        try:
            ok, _mtd = usage.within_budget(conn)
            if not ok:
                r = stub_result
                r.degraded = True
                return r

            system = [{"type": "text", "text": prompts.system_prompt(call_type)}]
            if grounding:
                # prompt-cache the (stable) reference material
                system.append({
                    "type": "text",
                    "text": "Reference material (for grounding only, do not copy):\n" + grounding,
                    "cache_control": {"type": "ephemeral"},
                })

            try:
                resp = self.client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    system=system,
                    messages=[{"role": "user", "content": user}],
                )
            except Exception:
                # network / API error → degrade, never break the loop
                r = stub_result
                r.degraded = True
                return r

            text = "".join(b.text for b in resp.content if b.type == "text").strip()
            u = resp.usage
            cost = usage.log_usage(
                conn, model=model,
                input_tokens=getattr(u, "input_tokens", 0) or 0,
                output_tokens=getattr(u, "output_tokens", 0) or 0,
                cache_read=getattr(u, "cache_read_input_tokens", 0) or 0,
                cache_write=getattr(u, "cache_creation_input_tokens", 0) or 0,
                call_type=call_type,
            )
            return AIResult(
                text=text or stub_result.text,
                model=model,
                input_tokens=getattr(u, "input_tokens", 0) or 0,
                output_tokens=getattr(u, "output_tokens", 0) or 0,
                cost_usd=cost,
                degraded=False,
                call_type=call_type,
            )
        finally:
            conn.close()

    # --- AIProvider methods ---
    def explain(self, *, question: dict, chosen_index: int, grounding: str = "") -> AIResult:
        letters = ["A", "B", "C", "D"]
        opts = question.get("options", [])
        ci = question.get("correct_index")
        lines = [f"Question: {question.get('text','')}", "Options:"]
        for i, o in enumerate(opts):
            lines.append(f"  {letters[i]}. {o}")
        if ci is not None:
            lines.append(f"Correct answer: {letters[ci]}")
        if 0 <= chosen_index < len(opts):
            lines.append(f"The learner chose: {letters[chosen_index]}")
        lines.append("Explain why the correct answer is right and, if they chose wrong, "
                     "why their choice is wrong. 2-4 sentences.")
        return self._call(
            user="\n".join(lines), call_type="explain", grounding=grounding,
            stub_result=self._stub.explain(question=question, chosen_index=chosen_index),
        )

    def diagnose(self, *, section_name: str, miss_summary: str, grounding: str = "") -> AIResult:
        user = (f"Section: {section_name}\nThe learner's recurring misses: {miss_summary}\n"
                "Diagnose the likely underlying misconception and the single most useful "
                "thing to focus on next. 2-4 sentences.")
        return self._call(
            user=user, call_type="diagnose", grounding=grounding,
            stub_result=self._stub.diagnose(section_name=section_name, miss_summary=miss_summary),
        )

    def narrate(self, *, recommendation: dict) -> AIResult:
        import json
        user = ("Write a short, plain-language 'today's session' note (2-3 sentences, "
                "encouraging but specific) from this plan:\n" + json.dumps(recommendation))
        return self._call(
            user=user, call_type="narrate", max_tokens=400,
            stub_result=self._stub.narrate(recommendation=recommendation),
        )

    def condense(self, *, lesson_text: str, tier: str, gaps: str = "", grounding: str = "") -> AIResult:
        user = (f"Depth tier: {tier}. Learner's gaps: {gaps or 'n/a'}.\n"
                "Condense the following lesson to the right depth for this tier "
                "(test-out=quick refresher; deep=full + a worked example). Original wording.\n\n"
                + lesson_text)
        return self._call(
            user=user, call_type="condense", grounding=grounding, max_tokens=900,
            stub_result=self._stub.condense(lesson_text=lesson_text, tier=tier, gaps=gaps),
        )

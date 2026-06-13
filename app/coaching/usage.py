"""AI usage logging + monthly budget guard (spec §0.1 / QUESTIONS #15).

Every Anthropic call is logged to the `usage` table with tokens + estimated cost.
Before a call, `within_budget()` checks month-to-date spend against the ceiling
(~$15); when exceeded, the AI layer degrades to the deterministic stub so the
core loop keeps working (constitution).

Pricing per the claude-api reference (per token): Opus 4.8 $5/$25 per MTok,
Haiku 4.5 $1/$5. Cache reads ≈0.1× input, cache writes ≈1.25× input.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app import config

# (input $/token, output $/token)
PRICING = {
    "claude-opus-4-8": (5.0e-6, 25.0e-6),
    "claude-haiku-4-5": (1.0e-6, 5.0e-6),
}
CACHE_READ_MULT = 0.10
CACHE_WRITE_MULT = 1.25


def estimate_cost(model: str, input_tokens: int, output_tokens: int,
                  cache_read: int = 0, cache_write: int = 0) -> float:
    in_rate, out_rate = PRICING.get(model, PRICING["claude-opus-4-8"])
    return (
        in_rate * input_tokens
        + in_rate * CACHE_WRITE_MULT * cache_write
        + in_rate * CACHE_READ_MULT * cache_read
        + out_rate * output_tokens
    )


def log_usage(conn, *, model: str, input_tokens: int, output_tokens: int,
              cache_read: int, cache_write: int, call_type: str) -> float:
    cost = estimate_cost(model, input_tokens, output_tokens, cache_read, cache_write)
    conn.execute(
        """
        INSERT INTO usage (ts, model, input_tokens, output_tokens, est_cost_usd, call_type)
        VALUES (?,?,?,?,?,?)
        """,
        (datetime.now(timezone.utc).isoformat(), model,
         input_tokens + cache_read + cache_write, output_tokens, cost, call_type),
    )
    conn.commit()
    return cost


def month_to_date_cost(conn, month_prefix: str | None = None) -> float:
    """Sum est_cost_usd for the current calendar month (UTC)."""
    month_prefix = month_prefix or datetime.now(timezone.utc).strftime("%Y-%m")
    row = conn.execute(
        "SELECT COALESCE(SUM(est_cost_usd), 0) c FROM usage WHERE substr(ts,1,7) = ?",
        (month_prefix,),
    ).fetchone()
    return row["c"] or 0.0


def within_budget(conn) -> tuple[bool, float]:
    """(ok, month_to_date_cost). ok=False once the monthly ceiling is reached."""
    mtd = month_to_date_cost(conn)
    return (mtd < config.AI_MONTHLY_BUDGET_USD, mtd)

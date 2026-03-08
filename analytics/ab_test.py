"""A/B Testing engine for paper trading scenario comparison.

Pure functions only — no file I/O, no side effects.

Compares two what-if scenarios (A and B) against the same trade history and
returns a structured result identifying which configuration would have
produced better P&L.

Typical use:
    result = run_ab_test(
        trades,
        scenario_a={"type": "position_sizing", "multiplier": 1.5},
        scenario_b={"type": "stop_loss", "stop_loss_pct": 0.05},
    )
"""
from __future__ import annotations

from dataclasses import dataclass

from analytics.whatif import WhatIfResult, run_what_if

# Treat deltas smaller than this as a tie (avoids noise from floating-point
# rounding on large trade histories).
_TIE_THRESHOLD = 0.01


@dataclass
class ABTestResult:
    """Comparison result for two what-if scenarios run against the same trades."""
    scenario_a: WhatIfResult
    scenario_b: WhatIfResult
    winner: str          # "a" | "b" | "tie" | "unavailable"
    delta_pnl: float     # scenario_b.scenario_pnl - scenario_a.scenario_pnl
    delta_pct: float     # |delta_pnl| / max(|pnl_a|, |pnl_b|) × 100, or 0
    summary: str         # human-readable one-liner


def run_ab_test(
    trades: list[dict],
    scenario_a: dict,
    scenario_b: dict,
) -> ABTestResult:
    """Run two what-if scenarios against the same trade history and compare.

    Args:
        trades: Trade records from AnalyticsStore.load_trades(). Not mutated.
        scenario_a: First scenario dict (same format as run_what_if).
        scenario_b: Second scenario dict.

    Returns:
        ABTestResult with individual WhatIfResults plus winner determination.
        If either scenario is unavailable, winner is "unavailable" and delta
        fields are 0.
    """
    result_a = run_what_if(trades, scenario_a)
    result_b = run_what_if(trades, scenario_b)

    if not result_a.available or not result_b.available:
        reasons = []
        if not result_a.available:
            reasons.append(f"Scenario A: {result_a.unavailable_reason}")
        if not result_b.available:
            reasons.append(f"Scenario B: {result_b.unavailable_reason}")
        return ABTestResult(
            scenario_a=result_a,
            scenario_b=result_b,
            winner="unavailable",
            delta_pnl=0.0,
            delta_pct=0.0,
            summary="Comparison unavailable. " + " ".join(reasons),
        )

    pnl_a = result_a.scenario_pnl
    pnl_b = result_b.scenario_pnl
    delta_pnl = round(pnl_b - pnl_a, 2)

    # Normalise delta against the larger absolute P&L to get a meaningful %.
    denom = max(abs(pnl_a), abs(pnl_b))
    delta_pct = round(abs(delta_pnl) / denom * 100, 2) if denom > 0 else 0.0

    if abs(delta_pnl) < _TIE_THRESHOLD:
        winner = "tie"
        summary = (
            f"Tie — both scenarios produce the same P&L "
            f"(${pnl_a:,.2f} vs ${pnl_b:,.2f})."
        )
    elif pnl_b > pnl_a:
        winner = "b"
        summary = (
            f"Scenario B wins by ${abs(delta_pnl):,.2f} ({delta_pct:.1f}%) "
            f"(A: ${pnl_a:,.2f} → B: ${pnl_b:,.2f})."
        )
    else:
        winner = "a"
        summary = (
            f"Scenario A wins by ${abs(delta_pnl):,.2f} ({delta_pct:.1f}%) "
            f"(A: ${pnl_a:,.2f} → B: ${pnl_b:,.2f})."
        )

    return ABTestResult(
        scenario_a=result_a,
        scenario_b=result_b,
        winner=winner,
        delta_pnl=delta_pnl,
        delta_pct=delta_pct,
        summary=summary,
    )

"""What-If Analysis engine for paper trading scenarios.

Pure functions only — no file I/O, no side effects, no execution paths.

Supported scenario types:
  position_sizing  — scales all trade notionals/P&L by a multiplier
  stop_loss        — simulates an alternative stop-loss threshold
  hold_duration    — requires per-symbol price history (returns unavailable)
"""
from __future__ import annotations

from dataclasses import dataclass, field

from analytics.metrics import compute_round_trip_trades


@dataclass
class WhatIfResult:
    """Result of a what-if scenario analysis."""
    scenario_type: str
    available: bool
    unavailable_reason: str | None
    baseline_pnl: float
    scenario_pnl: float
    delta_pnl: float
    delta_pct: float           # delta as % of |baseline_pnl|
    trade_count: int           # completed round-trip trades considered
    affected_trade_count: int  # trades whose outcome differs under scenario
    trade_by_trade: list[dict] = field(default_factory=list)


def run_what_if(trades: list[dict], scenario: dict) -> WhatIfResult:
    """Compute what-if P&L for a scenario against actual round-trip trade history.

    Args:
        trades: Trade records from AnalyticsStore.load_trades(). Not mutated.
        scenario: Dict with 'type' key plus scenario-specific params.
            position_sizing: {"type": "position_sizing", "multiplier": 1.5}
            stop_loss:       {"type": "stop_loss", "stop_loss_pct": 0.03}
            hold_duration:   {"type": "hold_duration", "extra_days": 2}

    Returns:
        WhatIfResult with baseline vs scenario comparison.
        If available=False, only baseline_pnl and unavailable_reason are meaningful.
    """
    scenario_type = (scenario.get("type") or "").strip()
    pairs = compute_round_trip_trades(trades)

    if scenario_type == "position_sizing":
        return _run_position_sizing(pairs, scenario)
    if scenario_type == "stop_loss":
        return _run_stop_loss(pairs, scenario)
    if scenario_type == "hold_duration":
        return _run_hold_duration(pairs, scenario)

    baseline_total = sum(float(p.get("pnl") or 0) for p in pairs)
    return WhatIfResult(
        scenario_type=scenario_type or "unknown",
        available=False,
        unavailable_reason=(
            f"Unknown scenario type: '{scenario_type}'. "
            "Valid types: position_sizing, stop_loss, hold_duration."
        ),
        baseline_pnl=round(baseline_total, 2),
        scenario_pnl=0.0,
        delta_pnl=0.0,
        delta_pct=0.0,
        trade_count=len(pairs),
        affected_trade_count=0,
    )


# ---------------------------------------------------------------------------
# Scenario implementations
# ---------------------------------------------------------------------------

def _run_position_sizing(pairs: list[dict], scenario: dict) -> WhatIfResult:
    """Scale all P&L proportionally by a position-size multiplier.

    Works purely from round-trip P&L — always available.
    P&L scales linearly because the same price delta applies to a larger notional.
    """
    try:
        multiplier = float(scenario.get("multiplier", 1.0))
    except (TypeError, ValueError):
        multiplier = 1.0

    if multiplier <= 0:
        return WhatIfResult(
            scenario_type="position_sizing",
            available=False,
            unavailable_reason="'multiplier' must be greater than 0 (e.g. 1.5 for 50% larger positions).",
            baseline_pnl=0.0, scenario_pnl=0.0, delta_pnl=0.0, delta_pct=0.0,
            trade_count=0, affected_trade_count=0,
        )

    trade_by_trade = []
    baseline_total = 0.0
    scenario_total = 0.0

    for pair in pairs:
        baseline_pnl = float(pair.get("pnl") or 0.0)
        scenario_pnl = baseline_pnl * multiplier
        delta = scenario_pnl - baseline_pnl
        baseline_total += baseline_pnl
        scenario_total += scenario_pnl
        trade_by_trade.append({
            "symbol": pair.get("symbol", ""),
            "qty": float(pair.get("qty") or 0),
            "entry_price": round(float(pair.get("buy_price") or 0), 4),
            "exit_price": round(float(pair.get("sell_price") or 0), 4),
            "scenario_exit_price": round(float(pair.get("sell_price") or 0), 4),
            "baseline_pnl": round(baseline_pnl, 2),
            "scenario_pnl": round(scenario_pnl, 2),
            "delta": round(delta, 2),
            "affected": multiplier != 1.0,
        })

    delta_pnl = scenario_total - baseline_total
    delta_pct = (delta_pnl / abs(baseline_total) * 100) if baseline_total != 0 else 0.0

    return WhatIfResult(
        scenario_type="position_sizing",
        available=True,
        unavailable_reason=None,
        baseline_pnl=round(baseline_total, 2),
        scenario_pnl=round(scenario_total, 2),
        delta_pnl=round(delta_pnl, 2),
        delta_pct=round(delta_pct, 2),
        trade_count=len(pairs),
        affected_trade_count=len(pairs) if multiplier != 1.0 else 0,
        trade_by_trade=trade_by_trade,
    )


def _run_stop_loss(pairs: list[dict], scenario: dict) -> WhatIfResult:
    """Simulate an alternative stop-loss threshold.

    For each completed round-trip:
      - If actual sell_price < buy_price * (1 - stop_loss_pct), the loss is capped
        at buy_price * (1 - stop_loss_pct), as if the stop had triggered there.
      - If the actual sell was a gain or a loss smaller than the threshold, the
        trade is unaffected.

    Honest approximation: we cannot know the exact intraday moment a stop would
    have triggered. This uses the threshold price as the scenario exit price.
    The scenario is always computable from round-trip pairs.
    """
    try:
        stop_loss_pct = float(scenario.get("stop_loss_pct", 0.05))
    except (TypeError, ValueError):
        stop_loss_pct = 0.05

    if not (0 < stop_loss_pct < 1):
        return WhatIfResult(
            scenario_type="stop_loss",
            available=False,
            unavailable_reason=(
                f"'stop_loss_pct' must be between 0 and 1 exclusive "
                f"(e.g. 0.03 for a 3% stop-loss). Got: {stop_loss_pct}."
            ),
            baseline_pnl=0.0, scenario_pnl=0.0, delta_pnl=0.0, delta_pct=0.0,
            trade_count=0, affected_trade_count=0,
        )

    trade_by_trade = []
    baseline_total = 0.0
    scenario_total = 0.0
    affected = 0

    for pair in pairs:
        buy_price = float(pair.get("buy_price") or 0)
        sell_price = float(pair.get("sell_price") or 0)
        qty = float(pair.get("qty") or 0)
        baseline_pnl = float(pair.get("pnl") or 0.0)

        if buy_price <= 0 or qty <= 0:
            # Cannot compute stop-loss without a valid entry price
            trade_by_trade.append({
                "symbol": pair.get("symbol", ""),
                "qty": qty,
                "entry_price": buy_price,
                "exit_price": sell_price,
                "scenario_exit_price": sell_price,
                "baseline_pnl": round(baseline_pnl, 2),
                "scenario_pnl": round(baseline_pnl, 2),
                "delta": 0.0,
                "affected": False,
            })
            baseline_total += baseline_pnl
            scenario_total += baseline_pnl
            continue

        stop_price = buy_price * (1.0 - stop_loss_pct)

        if sell_price < stop_price:
            # Actual exit was worse than stop price — stop would have triggered
            scenario_exit = stop_price
            scenario_pnl = (scenario_exit - buy_price) * qty
            trade_affected = True
            affected += 1
        else:
            # Actual exit was at or above stop price — trade unaffected
            scenario_exit = sell_price
            scenario_pnl = baseline_pnl
            trade_affected = False

        delta = scenario_pnl - baseline_pnl
        baseline_total += baseline_pnl
        scenario_total += scenario_pnl

        trade_by_trade.append({
            "symbol": pair.get("symbol", ""),
            "qty": qty,
            "entry_price": round(buy_price, 4),
            "exit_price": round(sell_price, 4),
            "scenario_exit_price": round(scenario_exit, 4),
            "baseline_pnl": round(baseline_pnl, 2),
            "scenario_pnl": round(scenario_pnl, 2),
            "delta": round(delta, 2),
            "affected": trade_affected,
        })

    delta_pnl = scenario_total - baseline_total
    delta_pct = (delta_pnl / abs(baseline_total) * 100) if baseline_total != 0 else 0.0

    return WhatIfResult(
        scenario_type="stop_loss",
        available=True,
        unavailable_reason=None,
        baseline_pnl=round(baseline_total, 2),
        scenario_pnl=round(scenario_total, 2),
        delta_pnl=round(delta_pnl, 2),
        delta_pct=round(delta_pct, 2),
        trade_count=len(trade_by_trade),
        affected_trade_count=affected,
        trade_by_trade=trade_by_trade,
    )


def _run_hold_duration(pairs: list[dict], scenario: dict) -> WhatIfResult:
    """Hold-duration scenario — requires per-symbol price history (not available).

    Computing what the P&L would be if positions were held N extra days requires
    knowing the stock price N days after each actual exit date. The analytics store
    only tracks portfolio-level equity, not individual stock prices.

    To run hold-duration sensitivity analysis, use the backtest engine with
    downloaded historical data (backtest/data.py).
    """
    try:
        extra_days = int(scenario.get("extra_days", 2))
    except (TypeError, ValueError):
        extra_days = 2

    baseline_total = round(sum(float(p.get("pnl") or 0) for p in pairs), 2)

    return WhatIfResult(
        scenario_type="hold_duration",
        available=False,
        unavailable_reason=(
            f"Hold-duration analysis (holding {extra_days} extra day(s)) requires "
            "per-symbol price data after each exit date. "
            "The analytics store only tracks portfolio-level equity, not individual stock prices. "
            "Use the backtest engine with historical data for this scenario."
        ),
        baseline_pnl=baseline_total,
        scenario_pnl=0.0,
        delta_pnl=0.0,
        delta_pct=0.0,
        trade_count=len(pairs),
        affected_trade_count=0,
    )

"""Utilities to compute basic performance metrics from equity and trade data."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, date
from math import sqrt
from typing import List, Dict, Optional


@dataclass
class EquityMetrics:
    total_return_pct: float = 0.0
    max_drawdown_pct: float = 0.0
    volatility_pct: float = 0.0
    sharpe_ratio: float = 0.0
    period_days: int = 0


def compute_equity_metrics(equity_points: List[Dict]) -> EquityMetrics:
    """Compute basic metrics from equity snapshots."""
    if not equity_points or len(equity_points) < 2:
        return EquityMetrics()

    # Reduce to last value per calendar day for stability
    daily = _collapse_daily(equity_points)
    if len(daily) < 2:
        return EquityMetrics()

    start_value = daily[0]["equity"]
    end_value = daily[-1]["equity"]
    if start_value <= 0:
        return EquityMetrics(period_days=len(daily))

    total_return = (end_value - start_value) / start_value

    returns = []
    peaks = []
    troughs = []
    max_drawdown = 0.0
    peak = daily[0]["equity"]
    for i in range(1, len(daily)):
        prev = daily[i - 1]["equity"]
        cur = daily[i]["equity"]
        if prev > 0:
            r = (cur - prev) / prev
            returns.append(r)
        peak = max(peak, cur)
        drawdown = (cur - peak) / peak if peak > 0 else 0
        max_drawdown = min(max_drawdown, drawdown)
        peaks.append(peak)
        troughs.append(cur)

    volatility = _stddev(returns)
    sharpe = (avg(returns) / volatility * sqrt(252)) if volatility > 0 else 0.0

    return EquityMetrics(
        total_return_pct=total_return * 100,
        max_drawdown_pct=abs(max_drawdown) * 100,
        volatility_pct=volatility * 100,
        sharpe_ratio=sharpe,
        period_days=len(daily) - 1,
    )


def _collapse_daily(points: List[Dict]) -> List[Dict]:
    by_day: Dict[date, Dict] = {}
    for pt in points:
        ts = pt.get("timestamp")
        equity = pt.get("equity") or pt.get("portfolio_value") or pt.get("account_value")
        if equity is None:
            continue
        if isinstance(ts, str):
            try:
                ts = datetime.fromisoformat(ts)
            except Exception:
                continue
        if not isinstance(ts, datetime):
            continue
        key = ts.date()
        # keep the latest snapshot for the day
        by_day[key] = {"timestamp": ts, "equity": float(equity)}
    return sorted(by_day.values(), key=lambda x: x["timestamp"])


def avg(values: List[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _stddev(values: List[float]) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    mean = avg(values)
    var = sum((x - mean) ** 2 for x in values) / (n - 1)
    return var ** 0.5


@dataclass
class TradeOutcomeStats:
    total: int = 0
    buys: int = 0
    sells: int = 0
    avg_notional: float = 0.0
    realized_pnl: float = 0.0
    win_trades: int = 0
    loss_trades: int = 0
    breakeven_trades: int = 0
    win_rate_pct: float = 0.0


def compute_trade_outcomes(trades: List[Dict]) -> TradeOutcomeStats:
    """Approximate realized P/L and win-rate from a trade stream.

    Uses a simple running-average cost basis per symbol to classify sell trades
    as wins/losses. Assumes long-only flow (buys increase inventory, sells
    reduce it) which matches the current bot behavior.
    """

    if not trades:
        return TradeOutcomeStats()

    # Sort chronologically for correct cost-basis tracking
    def _ts(trade):
        ts = trade.get("timestamp") or trade.get("filled_at") or trade.get("submitted_at")
        if isinstance(ts, datetime):
            return ts
        try:
            return datetime.fromisoformat(str(ts))
        except Exception:
            return None

    ordered = sorted(trades, key=lambda t: _ts(t) or datetime.min)

    holdings: Dict[str, Dict[str, float]] = {}
    notional_vals: List[float] = []
    realized_pnl = 0.0
    wins = losses = breakevens = 0
    buys = sells = 0

    for trade in ordered:
        side = (trade.get("side") or "").lower()
        symbol = trade.get("symbol") or ""
        qty = float(trade.get("qty") or 0)
        price = float(trade.get("filled_avg_price") or 0)

        if not symbol or qty <= 0 or price <= 0:
            continue

        notional = float(trade.get("notional") or (qty * price))
        notional_vals.append(notional)

        if side == "buy":
            buys += 1
            pos = holdings.setdefault(symbol, {"qty": 0.0, "avg_cost": 0.0})
            new_qty = pos["qty"] + qty
            if new_qty <= 0:
                continue
            pos["avg_cost"] = (pos["avg_cost"] * pos["qty"] + price * qty) / new_qty
            pos["qty"] = new_qty
        elif side == "sell":
            sells += 1
            pos = holdings.setdefault(symbol, {"qty": 0.0, "avg_cost": 0.0})
            sell_qty = min(qty, pos["qty"]) if pos["qty"] > 0 else 0.0
            if sell_qty > 0:
                pnl = (price - pos["avg_cost"]) * sell_qty
                realized_pnl += pnl
                pos["qty"] -= sell_qty
                if pnl > 0:
                    wins += 1
                elif pnl < 0:
                    losses += 1
                else:
                    breakevens += 1
            else:
                # No inventory to match; treat as breakeven placeholder
                breakevens += 1
        else:
            continue

    total = buys + sells
    avg_notional = sum(notional_vals) / len(notional_vals) if notional_vals else 0.0
    win_rate = (wins / sells * 100.0) if sells else 0.0

    return TradeOutcomeStats(
        total=total,
        buys=buys,
        sells=sells,
        avg_notional=avg_notional,
        realized_pnl=realized_pnl,
        win_trades=wins,
        loss_trades=losses,
        breakeven_trades=breakevens,
        win_rate_pct=win_rate,
    )

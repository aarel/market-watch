"""Utilities to compute basic performance metrics from equity and trade data."""
from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import UTC, date, datetime
from math import sqrt
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


@dataclass
class EquityMetrics:
    total_return_pct: float = 0.0
    max_drawdown_pct: float = 0.0
    volatility_pct: float = 0.0
    sharpe_ratio: float = 0.0
    period_days: int = 0


def compute_equity_metrics(equity_points: list[dict]) -> EquityMetrics:
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


def _collapse_daily(points: list[dict]) -> list[dict]:
    by_day: dict[date, dict] = {}
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
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        key = ts.date()
        existing = by_day.get(key)
        if existing is None or ts > existing["timestamp"]:
            by_day[key] = {"timestamp": ts, "equity": float(equity)}
    return sorted(by_day.values(), key=lambda x: x["timestamp"])


def avg(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _stddev(values: list[float]) -> float:
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


def compute_trade_outcomes(trades: list[dict]) -> TradeOutcomeStats:
    """Approximate realized P/L and win-rate from a trade stream.

    Uses a simple running-average cost basis per symbol to classify sell trades
    as wins/losses. Assumes long-only flow (buys increase inventory, sells
    reduce it) which matches the current bot behavior.
    """

    if not trades:
        return TradeOutcomeStats()

    # Sort chronologically for correct cost-basis tracking
    ordered = sorted(trades, key=lambda t: _trade_ts(t) or datetime.min)

    holdings: dict[str, dict[str, float]] = {}
    notional_vals: list[float] = []
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


def compute_round_trip_trades(trades: list[dict]) -> list[dict]:
    """Compute realized P&L per completed round-trip trade (buy -> sell)."""
    if not trades:
        return []

    ordered = sorted(trades, key=lambda t: _trade_ts(t) or datetime.min)
    positions: dict[str, dict[str, float | datetime | None]] = {}
    completed: list[dict] = []

    for trade in ordered:
        side = (trade.get("side") or "").lower()
        symbol = trade.get("symbol") or ""
        qty = float(trade.get("qty") or 0)
        price = float(trade.get("filled_avg_price") or 0)

        if not symbol or qty <= 0 or price <= 0:
            continue

        if side == "buy":
            pos = positions.setdefault(symbol, {"qty": 0.0, "avg_cost": 0.0, "last_buy_ts": None})
            new_qty = float(pos["qty"]) + qty
            if new_qty <= 0:
                continue
            pos["avg_cost"] = (float(pos["avg_cost"]) * float(pos["qty"]) + price * qty) / new_qty
            pos["qty"] = new_qty
            pos["last_buy_ts"] = _trade_ts(trade)
        elif side == "sell":
            pos = positions.setdefault(symbol, {"qty": 0.0, "avg_cost": 0.0, "last_buy_ts": None})
            sell_qty = min(qty, float(pos["qty"])) if float(pos["qty"]) > 0 else 0.0
            if sell_qty <= 0:
                continue
            avg_cost = float(pos["avg_cost"]) if float(pos["avg_cost"]) > 0 else 0.0
            pnl = (price - avg_cost) * sell_qty
            pnl_pct = ((price - avg_cost) / avg_cost * 100) if avg_cost > 0 else 0.0
            completed.append({
                "symbol": symbol,
                "qty": sell_qty,
                "buy_price": avg_cost,
                "sell_price": price,
                "pnl": pnl,
                "pnl_pct": pnl_pct,
                "timestamp": _trade_ts(trade).isoformat() if _trade_ts(trade) else None,
                "entry_timestamp": pos.get("last_buy_ts").isoformat() if pos.get("last_buy_ts") else None,
            })
            pos["qty"] = float(pos["qty"]) - sell_qty
            pos["avg_cost"] = avg_cost if float(pos["qty"]) > 0 else 0.0
        else:
            continue

    return completed


def compute_period_returns(
    equity_points: list[dict],
    granularity: str = "daily",
    timezone_name: str = "America/New_York",
) -> list[dict]:
    """Compute period returns (daily/weekly/monthly) from equity snapshots."""
    if not equity_points:
        return []

    tz = _get_timezone(timezone_name)
    buckets: dict[str, dict[str, object]] = {}
    for pt in equity_points:
        ts = _parse_timestamp(pt.get("timestamp"))
        equity = _extract_equity_value(pt)
        if ts is None or equity is None:
            continue
        ts_local = ts.astimezone(tz)
        label, period_start, period_end = _period_bounds(ts_local, granularity)
        if not label:
            continue
        existing = buckets.get(label)
        if existing is None or ts_local > existing["timestamp"]:
            buckets[label] = {
                "timestamp": ts_local,
                "equity": equity,
                "period_start": period_start,
                "period_end": period_end,
                "label": label,
            }

    collapsed = sorted(buckets.values(), key=lambda x: x["timestamp"])
    if len(collapsed) < 2:
        return []

    returns: list[dict] = []
    for idx in range(1, len(collapsed)):
        prev = collapsed[idx - 1]
        cur = collapsed[idx]
        start_equity = float(prev["equity"])
        end_equity = float(cur["equity"])
        if start_equity <= 0:
            continue
        return_pct = (end_equity - start_equity) / start_equity * 100.0
        returns.append({
            "period": cur["label"],
            "period_start": cur["period_start"].isoformat(),
            "period_end": cur["period_end"].isoformat(),
            "start_equity": start_equity,
            "end_equity": end_equity,
            "return_pct": return_pct,
            "start_timestamp": prev["timestamp"].isoformat(),
            "end_timestamp": cur["timestamp"].isoformat(),
        })
    return returns


def _trade_ts(trade: dict) -> datetime | None:
    ts = trade.get("timestamp") or trade.get("filled_at") or trade.get("submitted_at")
    if isinstance(ts, datetime):
        return ts
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except Exception:
        return None


def _parse_timestamp(value) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        ts = value
    else:
        try:
            ts = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except Exception:
            return None
    if ts.tzinfo is None:
        return ts.replace(tzinfo=UTC)
    return ts


def _extract_equity_value(point: dict) -> float | None:
    for key in ("equity", "portfolio_value", "account_value"):
        val = point.get(key)
        if val is not None:
            try:
                return float(val)
            except Exception:
                return None
    return None


def _get_timezone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def _period_bounds(ts_local: datetime, granularity: str) -> tuple[str, date, date]:
    granularity = (granularity or "").lower()
    if granularity == "daily":
        day = ts_local.date()
        return day.isoformat(), day, day
    if granularity == "weekly":
        iso = ts_local.isocalendar()
        start = date.fromisocalendar(iso.year, iso.week, 1)
        end = date.fromisocalendar(iso.year, iso.week, 7)
        label = f"{iso.year}-W{iso.week:02d}"
        return label, start, end
    if granularity == "monthly":
        start = date(ts_local.year, ts_local.month, 1)
        last_day = monthrange(ts_local.year, ts_local.month)[1]
        end = date(ts_local.year, ts_local.month, last_day)
        label = f"{ts_local.year}-{ts_local.month:02d}"
        return label, start, end
    return "", ts_local.date(), ts_local.date()

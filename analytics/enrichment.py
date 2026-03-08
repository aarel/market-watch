"""Subsequent-performance enrichment for trade records.

Pure functions only — no file I/O, no side effects.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any


def _parse_ts(value: Any) -> datetime | None:
    """Parse timestamp value to an aware UTC datetime."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
    except Exception:
        return None


def _first_snapshot_at_or_after(sorted_snaps: list[dict], ts: datetime) -> dict | None:
    """Return the first snapshot whose timestamp >= ts (snapshots must be sorted asc)."""
    for snap in sorted_snaps:
        snap_ts = _parse_ts(snap.get("timestamp"))
        if snap_ts is not None and snap_ts >= ts:
            return snap
    return None


def enrich_with_subsequent_performance(
    trades: list[dict],
    equity_snapshots: list[dict],
    days: list[int] | None = None,
) -> list[dict]:
    """Annotate trade records with portfolio equity performance N days after each trade.

    For each trade and each value in `days`, finds the nearest equity snapshot
    after (trade_timestamp + N days) and computes:

        perf_Nd = (future_equity - baseline_equity) / baseline_equity

    where baseline_equity is the first equity snapshot at or after the trade timestamp.

    Args:
        trades: Trade records from AnalyticsStore.load_trades(). Not mutated.
        equity_snapshots: Equity snapshots from AnalyticsStore.load_equity(). Not mutated.
        days: Forward windows to compute (default: [1, 5, 10]).

    Returns:
        New list of trade dicts with perf_1d / perf_5d / perf_10d fields added.
        Each perf field is a float or None if data is unavailable.
    """
    if days is None:
        days = [1, 5, 10]

    _min_dt = datetime.min.replace(tzinfo=UTC)

    # Sort snapshots chronologically once; exclude records with no equity value
    sorted_snaps = sorted(
        [s for s in equity_snapshots if s.get("equity") is not None],
        key=lambda s: _parse_ts(s.get("timestamp")) or _min_dt,
    )

    result: list[dict] = []
    for trade in trades:
        enriched = dict(trade)
        trade_ts = _parse_ts(trade.get("timestamp"))

        if trade_ts is None:
            for d in days:
                enriched[f"perf_{d}d"] = None
            result.append(enriched)
            continue

        # Baseline: first snapshot at or after the trade timestamp
        baseline_snap = _first_snapshot_at_or_after(sorted_snaps, trade_ts)
        try:
            baseline_equity = float(baseline_snap["equity"]) if baseline_snap else None
        except Exception:
            baseline_equity = None

        for d in days:
            if not baseline_equity:
                enriched[f"perf_{d}d"] = None
                continue
            future_snap = _first_snapshot_at_or_after(sorted_snaps, trade_ts + timedelta(days=d))
            if future_snap is None:
                enriched[f"perf_{d}d"] = None
                continue
            try:
                future_equity = float(future_snap["equity"])
                enriched[f"perf_{d}d"] = (future_equity - baseline_equity) / baseline_equity
            except Exception:
                enriched[f"perf_{d}d"] = None

        result.append(enriched)

    return result

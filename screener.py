"""Screener utilities for dynamic watchlists."""
from typing import Any


def _snapshot_price(snapshot) -> float | None:
    if snapshot is None:
        return None
    latest_trade = getattr(snapshot, "latest_trade", None)
    if latest_trade and getattr(latest_trade, "price", None):
        return float(latest_trade.price)
    daily_bar = getattr(snapshot, "daily_bar", None)
    if daily_bar and getattr(daily_bar, "c", None):
        return float(daily_bar.c)
    minute_bar = getattr(snapshot, "minute_bar", None)
    if minute_bar and getattr(minute_bar, "c", None):
        return float(minute_bar.c)
    return None


def _snapshot_prev_close(snapshot) -> float | None:
    if snapshot is None:
        return None
    prev_bar = getattr(snapshot, "prev_daily_bar", None)
    if prev_bar and getattr(prev_bar, "c", None):
        return float(prev_bar.c)
    return None


def _snapshot_volume(snapshot) -> int:
    if snapshot is None:
        return 0
    volumes = []
    daily_bar = getattr(snapshot, "daily_bar", None)
    if daily_bar and getattr(daily_bar, "v", None):
        volumes.append(int(daily_bar.v))
    prev_bar = getattr(snapshot, "prev_daily_bar", None)
    if prev_bar and getattr(prev_bar, "v", None):
        volumes.append(int(prev_bar.v))
    return max(volumes) if volumes else 0


def compute_top_gainers(
    snapshots: dict[str, Any],
    min_price: float,
    min_volume: int,
    limit: int,
) -> list[dict[str, float]]:
    """Compute top gainers from snapshot data."""
    entries = []
    low_volume_entries = []
    for symbol, snapshot in snapshots.items():
        price = _snapshot_price(snapshot)
        prev_close = _snapshot_prev_close(snapshot)
        if price is None or prev_close is None or prev_close <= 0:
            continue

        if price < min_price:
            continue

        volume = _snapshot_volume(snapshot)
        change_pct = (price - prev_close) / prev_close
        entry = {
            "symbol": symbol,
            "price": price,
            "prev_close": prev_close,
            "change_pct": change_pct,
            "volume": float(volume),
        }
        if volume >= min_volume:
            entries.append(entry)
        else:
            low_volume_entries.append(entry)

    entries.sort(key=lambda item: item["change_pct"], reverse=True)
    if len(entries) < limit and low_volume_entries:
        low_volume_entries.sort(key=lambda item: item["change_pct"], reverse=True)
        needed = limit - len(entries)
        entries.extend(low_volume_entries[:needed])
    return entries[:limit]

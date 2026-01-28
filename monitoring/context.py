"""Market context extraction and annotation utilities."""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from agents.events import MarketDataReady


@dataclass
class MarketContext:
    market_open: bool = False
    symbol_count: int = 0
    priced_symbols: int = 0
    bars_symbols: int = 0
    top_gainers_count: int = 0
    avg_volatility: Optional[float] = None
    volatility_regime: str = "unknown"
    direction_bias: str = "unknown"  # bullish, bearish, mixed, unknown
    last_updated: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "market_open": self.market_open,
            "symbol_count": self.symbol_count,
            "priced_symbols": self.priced_symbols,
            "bars_symbols": self.bars_symbols,
            "top_gainers_count": self.top_gainers_count,
            "avg_volatility": self.avg_volatility,
            "volatility_regime": self.volatility_regime,
            "direction_bias": self.direction_bias,
            "last_updated": self.last_updated,
        }


class MarketContextTracker:
    """Tracks and updates market context from MarketDataReady events."""

    def __init__(self):
        self._context = MarketContext()

    def update(self, event: MarketDataReady) -> MarketContext:
        symbol_count = len(event.symbols)
        price_count = len(event.prices or {})
        bars_count = len(event.bars or {})
        top_gainers_count = len(event.top_gainers or [])

        avg_volatility, direction_bias = _summarize_bars(event.bars or {})
        volatility_regime = _categorize_volatility(avg_volatility)

        self._context = MarketContext(
            market_open=event.market_open,
            symbol_count=symbol_count,
            priced_symbols=price_count,
            bars_symbols=bars_count,
            top_gainers_count=top_gainers_count,
            avg_volatility=avg_volatility,
            volatility_regime=volatility_regime,
            direction_bias=direction_bias,
            last_updated=datetime.now().isoformat(),
        )
        return self._context

    def get(self) -> MarketContext:
        return self._context


def _summarize_bars(bars: dict[str, Any]) -> tuple[Optional[float], str]:
    volatilities = []
    directions = []

    for symbol, bar_data in bars.items():
        close_dict = (bar_data or {}).get("close", {})
        if not close_dict:
            continue
        closes = [close_dict[i] for i in sorted(close_dict.keys())]
        if len(closes) < 3:
            continue

        returns = []
        for idx in range(1, len(closes)):
            prev = closes[idx - 1]
            if prev:
                returns.append((closes[idx] - prev) / prev)
        if len(returns) < 2:
            continue

        volatilities.append(statistics.stdev(returns))

        trend = (closes[-1] - closes[0]) / closes[0] if closes[0] else 0.0
        directions.append(trend)

    avg_volatility = statistics.mean(volatilities) if volatilities else None
    direction_bias = _categorize_direction(directions)

    return avg_volatility, direction_bias


def _categorize_volatility(avg_volatility: Optional[float]) -> str:
    if avg_volatility is None:
        return "unknown"
    if avg_volatility < 0.01:
        return "low"
    if avg_volatility < 0.02:
        return "normal"
    return "high"


def _categorize_direction(directions: list[float]) -> str:
    if not directions:
        return "unknown"
    positive = sum(1 for d in directions if d > 0)
    negative = sum(1 for d in directions if d < 0)
    if positive >= len(directions) * 0.7:
        return "bullish"
    if negative >= len(directions) * 0.7:
        return "bearish"
    return "mixed"

"""Analytics package for market-watch trading system.

This package provides analytics storage and metrics tracking
across different trading universes (LIVE, PAPER, SIMULATION).
"""

from analytics.store import AnalyticsStore

__all__ = ["AnalyticsStore"]

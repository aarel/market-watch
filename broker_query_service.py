"""Broker Query Service - Centralized broker API calls with caching and rate limiting.

This service wraps the broker interface to provide:
- TTL-based caching to reduce redundant API calls
- Thread-safe cache operations
- Per-universe cache isolation
- Cache hit rate metrics

Priority caches (from architecture audit):
1. Account data (portfolio_value, buying_power) - 30s TTL
2. Positions list - 1s TTL
3. Market open status - 5min TTL
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from threading import RLock
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from broker import AlpacaBroker


@dataclass
class CacheEntry:
    """Cache entry with value and expiration timestamp."""
    value: Any
    expires_at: float


@dataclass
class CacheStats:
    """Statistics for a specific cache."""
    hits: int = 0
    misses: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate as percentage."""
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0.0


class BrokerQueryService:
    """Centralized broker query service with intelligent caching.

    Wraps AlpacaBroker to provide:
    - Automatic caching with TTL for frequently accessed data
    - Thread-safe operations with RLock
    - Cache statistics tracking
    - Per-universe isolation

    Cache TTLs (based on data volatility):
    - Account data: 30 seconds (buying power changes with trades)
    - Positions: 1 second (tight for intra-cycle consistency)
    - Market open status: 5 minutes (only changes at market hours)

    Usage:
        service = BrokerQueryService(broker)
        account = service.get_account()  # Cached for 30s
        positions = service.get_positions()  # Cached for 1s
    """

    def __init__(
        self,
        broker: AlpacaBroker,
        account_ttl_seconds: float = 30.0,
        positions_ttl_seconds: float = 1.0,
        market_open_ttl_seconds: float = 300.0,  # 5 minutes
    ):
        """Initialize broker query service.

        Args:
            broker: The broker instance to wrap
            account_ttl_seconds: TTL for account data cache
            positions_ttl_seconds: TTL for positions cache
            market_open_ttl_seconds: TTL for market open status cache
        """
        self.broker = broker
        self.account_ttl = account_ttl_seconds
        self.positions_ttl = positions_ttl_seconds
        self.market_open_ttl = market_open_ttl_seconds

        # Thread-safe caches (RLock allows reentrant locking)
        self._lock = RLock()
        self._account_cache: CacheEntry | None = None
        self._positions_cache: CacheEntry | None = None
        self._market_open_cache: CacheEntry | None = None

        # Cache statistics
        self._account_stats = CacheStats()
        self._positions_stats = CacheStats()
        self._market_open_stats = CacheStats()

    def _is_expired(self, entry: CacheEntry | None) -> bool:
        """Check if cache entry is expired."""
        if entry is None:
            return True
        return time.time() >= entry.expires_at

    def _set_cache(self, cache_attr: str, value: Any, ttl: float) -> None:
        """Set cache entry with TTL."""
        expires_at = time.time() + ttl
        setattr(self, cache_attr, CacheEntry(value=value, expires_at=expires_at))

    # ===== CACHED METHODS =====

    def get_account(self):
        """Get account data with caching (TTL: 30s).

        Returns account object with:
        - portfolio_value
        - buying_power
        - cash
        - equity

        This consolidates get_portfolio_value() and get_buying_power() calls.
        """
        with self._lock:
            if not self._is_expired(self._account_cache):
                self._account_stats.hits += 1
                return self._account_cache.value

            self._account_stats.misses += 1
            account = self.broker.get_account()
            self._set_cache('_account_cache', account, self.account_ttl)
            return account

    def get_positions(self):
        """Get all positions with caching (TTL: 1s).

        Short TTL ensures consistency within single event cycle while
        avoiding redundant calls from multiple agents.

        Returns:
            List of position objects
        """
        with self._lock:
            if not self._is_expired(self._positions_cache):
                self._positions_stats.hits += 1
                return self._positions_cache.value

            self._positions_stats.misses += 1
            positions = self.broker.get_positions()
            self._set_cache('_positions_cache', positions, self.positions_ttl)
            return positions

    def get_position(self, symbol: str):
        """Get single position, using cached positions list when available.

        Args:
            symbol: Stock symbol

        Returns:
            Position object or None if no position exists
        """
        # Try cache first
        with self._lock:
            if not self._is_expired(self._positions_cache):
                positions = self._positions_cache.value
                return next((p for p in positions if p.symbol == symbol), None)

        # Cache miss - fetch directly
        return self.broker.get_position(symbol)

    def is_market_open(self) -> bool:
        """Check if market is open with caching (TTL: 5 min).

        Market hours only change at 9:30 AM / 4:00 PM EST, so long TTL
        is safe and avoids unnecessary API calls.

        Returns:
            True if market is open, False otherwise
        """
        with self._lock:
            if not self._is_expired(self._market_open_cache):
                self._market_open_stats.hits += 1
                return self._market_open_cache.value

            self._market_open_stats.misses += 1
            is_open = self.broker.is_market_open()
            self._set_cache('_market_open_cache', is_open, self.market_open_ttl)
            return is_open

    # ===== DERIVED METHODS (use account cache) =====

    def get_portfolio_value(self) -> float:
        """Get portfolio value from cached account data.

        Previously this called get_account() internally each time.
        Now consolidates through shared account cache.
        """
        account = self.get_account()
        return float(account.portfolio_value)

    def get_buying_power(self) -> float:
        """Get buying power from cached account data.

        Previously this called get_account() internally each time.
        Now consolidates through shared account cache.
        """
        account = self.get_account()
        return float(account.buying_power)

    # ===== PASSTHROUGH METHODS (no caching yet) =====

    def get_current_price(self, symbol: str):
        """Get current price for symbol (passthrough, no caching yet)."""
        return self.broker.get_current_price(symbol)

    def get_bars(self, symbol: str, days: int = 20):
        """Get historical bars (passthrough, no caching yet)."""
        return self.broker.get_bars(symbol, days=days)

    def get_snapshots(self, symbols):
        """Get snapshots for multiple symbols (passthrough, no caching yet)."""
        return self.broker.get_snapshots(symbols)

    def submit_order(self, **kwargs):
        """Submit order (passthrough, never cached)."""
        # Invalidate account and positions cache on order submission
        with self._lock:
            self._account_cache = None
            self._positions_cache = None
        return self.broker.submit_order(**kwargs)

    def get_order(self, order_id: str):
        """Get order by ID (passthrough, never cached)."""
        return self.broker.get_order(order_id)

    # ===== CACHE MANAGEMENT =====

    def clear_cache(self) -> None:
        """Clear all caches."""
        with self._lock:
            self._account_cache = None
            self._positions_cache = None
            self._market_open_cache = None

    def invalidate_account(self) -> None:
        """Invalidate account cache (call after trades)."""
        with self._lock:
            self._account_cache = None

    def invalidate_positions(self) -> None:
        """Invalidate positions cache (call after trades)."""
        with self._lock:
            self._positions_cache = None

    def get_cache_stats(self) -> dict:
        """Get cache hit rate statistics.

        Returns:
            Dict with cache stats for each cached method
        """
        with self._lock:
            return {
                'account': {
                    'hits': self._account_stats.hits,
                    'misses': self._account_stats.misses,
                    'hit_rate': self._account_stats.hit_rate,
                    'ttl_seconds': self.account_ttl,
                },
                'positions': {
                    'hits': self._positions_stats.hits,
                    'misses': self._positions_stats.misses,
                    'hit_rate': self._positions_stats.hit_rate,
                    'ttl_seconds': self.positions_ttl,
                },
                'market_open': {
                    'hits': self._market_open_stats.hits,
                    'misses': self._market_open_stats.misses,
                    'hit_rate': self._market_open_stats.hit_rate,
                    'ttl_seconds': self.market_open_ttl,
                },
            }

    # ===== ASYNC WRAPPERS =====

    async def get_account_async(self):
        """Async wrapper for get_account()."""
        return await asyncio.to_thread(self.get_account)

    async def get_positions_async(self):
        """Async wrapper for get_positions()."""
        return await asyncio.to_thread(self.get_positions)

    async def get_position_async(self, symbol: str):
        """Async wrapper for get_position()."""
        return await asyncio.to_thread(self.get_position, symbol)

    async def is_market_open_async(self) -> bool:
        """Async wrapper for is_market_open()."""
        return await asyncio.to_thread(self.is_market_open)

    async def get_current_price_async(self, symbol: str):
        """Async wrapper for get_current_price()."""
        return await asyncio.to_thread(self.get_current_price, symbol)

    async def get_bars_async(self, symbol: str, days: int = 20):
        """Async wrapper for get_bars()."""
        return await asyncio.to_thread(self.get_bars, symbol, days)

    async def get_portfolio_value_async(self) -> float:
        """Async wrapper for get_portfolio_value()."""
        return await asyncio.to_thread(self.get_portfolio_value)

    async def get_buying_power_async(self) -> float:
        """Async wrapper for get_buying_power()."""
        return await asyncio.to_thread(self.get_buying_power)

    async def submit_order_async(self, **kwargs):
        """Async wrapper for submit_order()."""
        return await asyncio.to_thread(self.submit_order, **kwargs)

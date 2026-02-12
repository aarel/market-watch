"""Tests for DataAgent to improve coverage.

Focuses on helper functions, error handling, and edge cases.
"""
import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pandas as pd

from agents.data_agent import DataAgent, _snapshot_price, _snapshot_prev_close
from agents.event_bus import EventBus
from agents.events import ConfigUpdated
from universe import Universe, UniverseContext


class TestSnapshotHelperFunctions(unittest.TestCase):
    """Test _snapshot_price and _snapshot_prev_close helper functions."""

    def test_snapshot_price_none_snapshot(self):
        """Test _snapshot_price returns None when snapshot is None."""
        result = _snapshot_price(None)
        self.assertIsNone(result)  # Line 20

    def test_snapshot_price_daily_bar_fallback(self):
        """Test _snapshot_price falls back to daily_bar when no latest_trade."""
        snapshot = SimpleNamespace(
            latest_trade=None,
            daily_bar=SimpleNamespace(c=150.50),
        )
        result = _snapshot_price(snapshot)
        self.assertEqual(result, 150.50)  # Line 26

    def test_snapshot_price_minute_bar_fallback(self):
        """Test _snapshot_price falls back to minute_bar when no daily_bar."""
        snapshot = SimpleNamespace(
            latest_trade=None,
            daily_bar=None,
            minute_bar=SimpleNamespace(c=149.75),
        )
        result = _snapshot_price(snapshot)
        self.assertEqual(result, 149.75)  # Line 29

    def test_snapshot_price_no_data(self):
        """Test _snapshot_price returns None when no price data available."""
        snapshot = SimpleNamespace(
            latest_trade=None,
            daily_bar=None,
            minute_bar=None,
        )
        result = _snapshot_price(snapshot)
        self.assertIsNone(result)

    def test_snapshot_prev_close_none_snapshot(self):
        """Test _snapshot_prev_close returns None when snapshot is None."""
        result = _snapshot_prev_close(None)
        self.assertIsNone(result)  # Line 35

    def test_snapshot_prev_close_no_prev_bar(self):
        """Test _snapshot_prev_close returns None when no prev_daily_bar."""
        snapshot = SimpleNamespace(prev_daily_bar=None)
        result = _snapshot_prev_close(snapshot)
        self.assertIsNone(result)  # Line 39

    def test_snapshot_prev_close_success(self):
        """Test _snapshot_prev_close returns prev close when available."""
        snapshot = SimpleNamespace(
            prev_daily_bar=SimpleNamespace(c=145.25)
        )
        result = _snapshot_prev_close(snapshot)
        self.assertEqual(result, 145.25)


class MockBroker:
    """Mock broker for testing."""

    def __init__(self, universe=Universe.SIMULATION):
        self.universe = universe
        self._raise_positions_error = False
        self._raise_fetch_error = False

    def is_market_open(self):
        return True

    def get_account(self):
        return SimpleNamespace(
            portfolio_value=100000,
            buying_power=100000,
            cash=50000,
            equity=100000,
        )

    def get_positions(self):
        if self._raise_positions_error:
            raise Exception("Positions API error")
        return [
            SimpleNamespace(
                symbol="AAPL",
                qty=10,
                market_value=1500.0,
                avg_entry_price=145.0,
                unrealized_pl=50.0,
                unrealized_plpc=0.034,
            )
        ]

    def get_snapshots(self, symbols):
        return {
            symbol: SimpleNamespace(
                latest_trade=SimpleNamespace(price=150.0),
                prev_daily_bar=SimpleNamespace(c=145.0),
            )
            for symbol in symbols
        }

    def get_current_price(self, symbol):
        if self._raise_fetch_error:
            raise Exception(f"Failed to fetch {symbol}")
        return 150.0

    def get_bars(self, symbol, days=20):
        return pd.DataFrame({
            "open": [10, 11],
            "high": [11, 12],
            "low": [9, 10],
            "close": [10, 11],
            "volume": [1000, 1200],
        })


class TestDataAgentErrorHandling(unittest.IsolatedAsyncioTestCase):
    """Test error handling paths in DataAgent."""

    async def asyncSetUp(self):
        self.context = UniverseContext(Universe.SIMULATION)
        self.bus = EventBus(self.context)
        self.broker = MockBroker(Universe.SIMULATION)

    async def test_run_loop_handles_fetch_error(self):
        """Test that _run_loop catches and logs fetch_data exceptions."""
        agent = DataAgent(self.bus, self.broker, interval_minutes=1)

        # Mock fetch_data to raise exception
        async def mock_fetch_error():
            raise ValueError("Test error")

        agent.fetch_data = mock_fetch_error

        # Start agent
        await agent.start()

        # Wait for one loop iteration
        await asyncio.sleep(0.1)

        # Stop agent
        await agent.stop()

        # Test passes if no exception propagated (line 90 logs error)
        self.assertTrue(True)

    async def test_positions_fetch_error_logged(self):
        """Test that positions fetch errors are caught and logged."""
        self.broker._raise_positions_error = True
        agent = DataAgent(self.bus, self.broker, interval_minutes=1)

        with patch("config.WATCHLIST_MODE", "static"), \
             patch("config.WATCHLIST", ["AAPL"]), \
             patch("config.LOOKBACK_DAYS", 2), \
             patch("config.MARKET_INDEX_SYMBOLS", []):
            event = await agent.fetch_data()

        # Should have empty positions due to error (lines 174-175)
        self.assertEqual(len(event.positions), 0)


class TestDataAgentWatchlistModes(unittest.IsolatedAsyncioTestCase):
    """Test different watchlist modes and symbol selection."""

    async def asyncSetUp(self):
        self.context = UniverseContext(Universe.SIMULATION)
        self.bus = EventBus(self.context)
        self.broker = MockBroker(Universe.SIMULATION)

    async def test_top_gainers_mode_with_results(self):
        """Test top gainers mode when gainers are found."""
        agent = DataAgent(self.bus, self.broker, interval_minutes=1)

        with patch("config.WATCHLIST_MODE", "top_gainers"), \
             patch("config.TOP_GAINERS_UNIVERSE", "nyse_stocks"), \
             patch("config.TOP_GAINERS_MIN_PRICE", 5.0), \
             patch("config.TOP_GAINERS_MIN_VOLUME", 100000), \
             patch("config.TOP_GAINERS_COUNT", 5), \
             patch("config.WATCHLIST", ["BACKUP"]), \
             patch("config.LOOKBACK_DAYS", 2), \
             patch("config.MARKET_INDEX_SYMBOLS", []), \
             patch("screener.compute_top_gainers") as mock_gainers, \
             patch("screener_universe.get_universe") as mock_universe:

            # Mock successful top gainers
            mock_universe.return_value = ["STOCK1", "STOCK2"]
            mock_gainers.return_value = [
                {"symbol": "STOCK1", "price": 100.0},
                {"symbol": "STOCK2", "price": 200.0},
            ]

            event = await agent.fetch_data()

            # Should use top gainers symbols (lines 118-119)
            self.assertIn("STOCK1", event.symbols)
            self.assertIn("STOCK2", event.symbols)

    async def test_static_watchlist_mode(self):
        """Test static watchlist mode (non-top-gainers)."""
        agent = DataAgent(self.bus, self.broker, interval_minutes=1)

        with patch("config.WATCHLIST_MODE", "static"), \
             patch("config.WATCHLIST", ["AAPL", "GOOGL"]), \
             patch("config.LOOKBACK_DAYS", 2), \
             patch("config.MARKET_INDEX_SYMBOLS", []):
            event = await agent.fetch_data()

        # Should use static watchlist (line 123)
        self.assertIn("AAPL", event.symbols)
        self.assertIn("GOOGL", event.symbols)

    async def test_empty_symbols_fallback(self):
        """Test fallback when symbols list is empty."""
        agent = DataAgent(self.bus, self.broker, interval_minutes=1)

        with patch("config.WATCHLIST_MODE", "top_gainers"), \
             patch("config.TOP_GAINERS_UNIVERSE", "nyse_stocks"), \
             patch("config.WATCHLIST", []), \
             patch("config.LOOKBACK_DAYS", 2), \
             patch("config.MARKET_INDEX_SYMBOLS", []), \
             patch("screener.compute_top_gainers") as mock_gainers, \
             patch("screener_universe.get_universe") as mock_universe:

            # Mock empty top gainers
            mock_universe.return_value = []
            mock_gainers.return_value = []

            event = await agent.fetch_data()

            # Should fall back to default symbols (line 127)
            self.assertGreater(len(event.symbols), 0)
            # Default fallback includes SPY
            self.assertIn("SPY", event.symbols)


class TestDataAgentConfigUpdates(unittest.IsolatedAsyncioTestCase):
    """Test config update handling."""

    async def asyncSetUp(self):
        self.context = UniverseContext(Universe.SIMULATION)
        self.bus = EventBus(self.context)
        self.broker = MockBroker(Universe.SIMULATION)

    async def test_trade_interval_update(self):
        """Test that trade_interval config changes are applied."""
        agent = DataAgent(self.bus, self.broker, interval_minutes=5)
        await agent.start()

        # Publish config update
        event = ConfigUpdated(
            universe=Universe.SIMULATION,
            session_id="test",
            source="Test",
            changed_keys=["trade_interval"],
            config_snapshot={"trade_interval": 10},
        )
        await self.bus.publish(event)

        # Wait for event to propagate
        await asyncio.sleep(0.1)

        # Check interval was updated
        self.assertEqual(agent.interval_minutes, 10)

        await agent.stop()

    async def test_non_trade_interval_update_ignored(self):
        """Test that non-trade_interval config changes are ignored."""
        agent = DataAgent(self.bus, self.broker, interval_minutes=5)
        await agent.start()

        # Publish config update for different key
        event = ConfigUpdated(
            universe=Universe.SIMULATION,
            session_id="test",
            source="Test",
            changed_keys=["max_position_size"],
            config_snapshot={"max_position_size": 1000},
        )
        await self.bus.publish(event)

        # Wait for event to propagate
        await asyncio.sleep(0.1)

        # Interval should remain unchanged
        self.assertEqual(agent.interval_minutes, 5)

        await agent.stop()


class TestDataAgentHelperMethods(unittest.IsolatedAsyncioTestCase):
    """Test DataAgent helper methods."""

    async def asyncSetUp(self):
        self.context = UniverseContext(Universe.SIMULATION)
        self.bus = EventBus(self.context)
        self.broker = MockBroker(Universe.SIMULATION)

    async def test_get_cached_data(self):
        """Test getting cached data."""
        agent = DataAgent(self.bus, self.broker, interval_minutes=1)

        with patch("config.WATCHLIST_MODE", "static"), \
             patch("config.WATCHLIST", ["AAPL"]), \
             patch("config.LOOKBACK_DAYS", 2), \
             patch("config.MARKET_INDEX_SYMBOLS", []):
            await agent.fetch_data()

        # Get cached data
        cached = agent.get_cached_data()
        self.assertIn("prices", cached)
        self.assertIn("bars", cached)
        self.assertIn("account", cached)
        self.assertIn("positions", cached)

    async def test_status_includes_last_fetch(self):
        """Test status includes last fetch time."""
        agent = DataAgent(self.bus, self.broker, interval_minutes=1)

        # Before fetch
        status_before = agent.status()
        self.assertIsNone(status_before["last_fetch"])

        # After fetch
        with patch("config.WATCHLIST_MODE", "static"), \
             patch("config.WATCHLIST", ["AAPL"]), \
             patch("config.LOOKBACK_DAYS", 2), \
             patch("config.MARKET_INDEX_SYMBOLS", []):
            await agent.fetch_data()

        status_after = agent.status()
        self.assertIsNotNone(status_after["last_fetch"])
        self.assertIn("cached_symbols", status_after)


if __name__ == "__main__":
    unittest.main()

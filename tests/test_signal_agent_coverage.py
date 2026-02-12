"""Tests for SignalAgent to improve coverage.

Focuses on error handling, edge cases, and helper methods.
"""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pandas as pd

from agents.event_bus import EventBus
from agents.events import MarketDataReady
from agents.signal_agent import SignalAgent
from strategies import MomentumStrategy
from universe import Universe, UniverseContext


class MockBroker:
    """Mock broker for testing."""

    def __init__(self, universe=Universe.SIMULATION):
        self.universe = universe
        self._position = None

    async def get_position_async(self, symbol):
        """Return mock position or None."""
        return self._position


class TestSignalAgentErrorHandling(unittest.IsolatedAsyncioTestCase):
    """Test error handling in SignalAgent."""

    async def asyncSetUp(self):
        self.context = UniverseContext(Universe.SIMULATION)
        self.bus = EventBus(self.context)
        self.broker = MockBroker(Universe.SIMULATION)
        self.agent = SignalAgent(self.bus, self.broker)
        await self.agent.start()

    async def asyncTearDown(self):
        await self.agent.stop()

    async def test_strategy_analyze_exception_creates_hold_signal(self):
        """Test that exceptions in strategy.analyze() create hold signals."""
        # Mock strategy that raises exception
        mock_strategy = Mock()
        mock_strategy.name = "TestStrategy"
        mock_strategy.required_history = 5
        mock_strategy.analyze.side_effect = ValueError("Strategy error")

        self.agent.strategy = mock_strategy

        # Capture published events
        events = []
        self.bus.subscribe_all(lambda e: events.append(e))

        # Create market data event with valid data
        event = MarketDataReady(
            universe=Universe.SIMULATION,
            session_id="test",
            source="Test",
            symbols=["AAPL"],
            prices={"AAPL": 150.0},
            bars={"AAPL": {
                "close": {0: 145.0, 1: 146.0, 2: 147.0, 3: 148.0, 4: 149.0, 5: 150.0},
                "open": {0: 144.0, 1: 145.0, 2: 146.0, 3: 147.0, 4: 148.0, 5: 149.0},
                "high": {0: 146.0, 1: 147.0, 2: 148.0, 3: 149.0, 4: 150.0, 5: 151.0},
                "low": {0: 143.0, 1: 144.0, 2: 145.0, 3: 146.0, 4: 147.0, 5: 148.0},
                "volume": {0: 1000, 1: 1100, 2: 1200, 3: 1300, 4: 1400, 5: 1500},
            }},
            account={},
            positions=[],
            top_gainers=[],
            market_indices=[],
            market_open=True,
        )

        await self.agent._handle_market_data(event)

        # Should have created hold signal due to exception (lines 145-147)
        from agents.events import SignalsUpdated
        signal_updates = [e for e in events if isinstance(e, SignalsUpdated)]
        self.assertGreater(len(signal_updates), 0)

        signals = signal_updates[0].signals
        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0]["symbol"], "AAPL")
        self.assertEqual(signals[0]["action"], "hold")
        self.assertIn("error", signals[0]["reason"].lower())


class TestSignalAgentBarsConversion(unittest.IsolatedAsyncioTestCase):
    """Test _convert_bars_to_dataframe edge cases."""

    async def asyncSetUp(self):
        self.context = UniverseContext(Universe.SIMULATION)
        self.bus = EventBus(self.context)
        self.broker = MockBroker(Universe.SIMULATION)
        self.agent = SignalAgent(self.bus, self.broker)

    async def test_convert_bars_empty_data(self):
        """Test _convert_bars_to_dataframe with empty data."""
        result = self.agent._convert_bars_to_dataframe({})
        self.assertIsNone(result)  # Line 189

    async def test_convert_bars_no_close_key(self):
        """Test _convert_bars_to_dataframe with no 'close' key."""
        bars_data = {"open": {0: 100.0}, "high": {0: 101.0}}
        result = self.agent._convert_bars_to_dataframe(bars_data)
        self.assertIsNone(result)  # Line 189

    async def test_convert_bars_empty_close_dict(self):
        """Test _convert_bars_to_dataframe with empty close dict."""
        bars_data = {"close": {}}
        result = self.agent._convert_bars_to_dataframe(bars_data)
        self.assertIsNone(result)  # Line 199

    async def test_convert_bars_exception_handling(self):
        """Test _convert_bars_to_dataframe exception handling."""
        # Create malformed data that will cause an exception
        bars_data = {"close": "not a dict"}  # Invalid type
        result = self.agent._convert_bars_to_dataframe(bars_data)
        self.assertIsNone(result)  # Lines 220-222

    async def test_convert_bars_valid_data(self):
        """Test _convert_bars_to_dataframe with valid data."""
        bars_data = {
            "close": {0: 100.0, 1: 101.0, 2: 102.0},
            "open": {0: 99.0, 1: 100.0, 2: 101.0},
            "high": {0: 101.0, 1: 102.0, 2: 103.0},
            "low": {0: 98.0, 1: 99.0, 2: 100.0},
            "volume": {0: 1000, 1: 1100, 2: 1200},
        }
        result = self.agent._convert_bars_to_dataframe(bars_data)
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 3)
        self.assertListEqual(list(result.columns), ["open", "high", "low", "close", "volume"])


class TestSignalAgentPositionInfo(unittest.IsolatedAsyncioTestCase):
    """Test _get_position_info method."""

    async def asyncSetUp(self):
        self.context = UniverseContext(Universe.SIMULATION)
        self.bus = EventBus(self.context)
        self.broker = MockBroker(Universe.SIMULATION)
        self.agent = SignalAgent(self.bus, self.broker)

    async def test_get_position_info_with_valid_position(self):
        """Test _get_position_info with valid position data."""
        # Set up mock position
        self.broker._position = SimpleNamespace(
            avg_entry_price=145.0,
            qty=10,
            current_price=150.0,
            market_value=1500.0,
            unrealized_pl=50.0,
        )

        result = await self.agent._get_position_info("AAPL")

        # Lines 239-244, 246
        self.assertIsNotNone(result)
        self.assertEqual(result["quantity"], 10.0)
        self.assertEqual(result["entry_price"], 145.0)
        self.assertEqual(result["current_price"], 150.0)
        self.assertEqual(result["market_value"], 1500.0)
        self.assertEqual(result["unrealized_pnl"], 50.0)
        self.assertAlmostEqual(result["unrealized_pnl_pct"], 50.0 / 1450.0, places=4)

    async def test_get_position_info_no_position(self):
        """Test _get_position_info when no position exists."""
        self.broker._position = None
        result = await self.agent._get_position_info("AAPL")
        self.assertIsNone(result)

    async def test_get_position_info_exception_handling(self):
        """Test _get_position_info exception handling."""
        # Make get_position_async raise an exception
        async def raise_error(symbol):
            raise Exception("API error")

        self.broker.get_position_async = raise_error

        result = await self.agent._get_position_info("AAPL")
        self.assertIsNone(result)  # Exception caught, returns None


class TestSignalAgentStrategyManagement(unittest.IsolatedAsyncioTestCase):
    """Test strategy getter/setter methods."""

    async def asyncSetUp(self):
        self.context = UniverseContext(Universe.SIMULATION)
        self.bus = EventBus(self.context)
        self.broker = MockBroker(Universe.SIMULATION)
        self.agent = SignalAgent(self.bus, self.broker)

    async def test_set_strategy(self):
        """Test set_strategy method."""
        from strategies import MeanReversionStrategy

        new_strategy = MeanReversionStrategy()
        self.agent.set_strategy(new_strategy)

        # Lines 266-267
        self.assertEqual(self.agent.strategy, new_strategy)
        self.assertEqual(self.agent.strategy.name, "Mean Reversion Strategy")

    async def test_get_strategy(self):
        """Test get_strategy method."""
        strategy = self.agent.get_strategy()

        # Line 271
        self.assertIsInstance(strategy, MomentumStrategy)
        self.assertEqual(strategy.name, "Momentum Strategy")

    async def test_default_strategy_is_momentum(self):
        """Test that default strategy is MomentumStrategy."""
        agent = SignalAgent(self.bus, self.broker)
        self.assertIsInstance(agent.strategy, MomentumStrategy)


class TestSignalAgentConfigUpdates(unittest.IsolatedAsyncioTestCase):
    """Test config update handling."""

    async def asyncSetUp(self):
        self.context = UniverseContext(Universe.SIMULATION)
        self.bus = EventBus(self.context)
        self.broker = MockBroker(Universe.SIMULATION)
        self.agent = SignalAgent(self.bus, self.broker)
        await self.agent.start()

    async def asyncTearDown(self):
        await self.agent.stop()

    async def test_strategy_params_updated_on_config_change(self):
        """Test that strategy parameters are updated when config changes."""
        from agents.events import ConfigUpdated

        with patch("config.MOMENTUM_THRESHOLD", 0.05), \
             patch("config.SELL_THRESHOLD", -0.04), \
             patch("config.STOP_LOSS_PCT", 0.12):

            event = ConfigUpdated(
                universe=Universe.SIMULATION,
                session_id="test",
                source="Test",
                changed_keys=["momentum_threshold", "sell_threshold"],
                config_snapshot={},
            )

            await self.agent._handle_config_updated(event)

            # Strategy params should be updated
            self.assertEqual(self.agent.strategy.momentum_threshold, 0.05)
            self.assertEqual(self.agent.strategy.sell_threshold, -0.04)
            self.assertEqual(self.agent.strategy.stop_loss_pct, 0.12)

    async def test_non_strategy_config_ignored(self):
        """Test that non-strategy config changes are ignored."""
        from agents.events import ConfigUpdated

        original_threshold = self.agent.strategy.momentum_threshold

        event = ConfigUpdated(
            universe=Universe.SIMULATION,
            session_id="test",
            source="Test",
            changed_keys=["trade_interval"],  # Not a strategy parameter
            config_snapshot={},
        )

        await self.agent._handle_config_updated(event)

        # Strategy params should remain unchanged
        self.assertEqual(self.agent.strategy.momentum_threshold, original_threshold)


class TestSignalAgentHelperMethods(unittest.IsolatedAsyncioTestCase):
    """Test helper methods."""

    async def asyncSetUp(self):
        self.context = UniverseContext(Universe.SIMULATION)
        self.bus = EventBus(self.context)
        self.broker = MockBroker(Universe.SIMULATION)
        self.agent = SignalAgent(self.bus, self.broker)

    async def test_get_signals(self):
        """Test get_signals method."""
        signals = self.agent.get_signals()
        self.assertIsInstance(signals, list)

    async def test_status_includes_strategy_info(self):
        """Test status includes strategy information."""
        status = self.agent.status()
        self.assertIn("strategy", status)
        self.assertIn("strategy_params", status)
        self.assertIn("signal_count", status)
        self.assertIn("actionable", status)


if __name__ == "__main__":
    unittest.main()

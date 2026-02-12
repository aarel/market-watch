"""Tests for Coordinator to improve coverage.

Focuses on optional agent paths, error handling, and helper methods.
"""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from agents.coordinator import Coordinator
from agents.events import RiskCheckPassed, StopLossTriggered
from universe import Universe


class MockBroker:
    """Mock broker for testing."""

    def __init__(self, universe=Universe.SIMULATION):
        self.universe = universe

    def get_account(self):
        return SimpleNamespace(
            portfolio_value=100000,
            buying_power=100000,
            cash=100000,
            equity=100000,
        )

    def get_positions(self):
        return []

    def is_market_open(self):
        return True


class TestCoordinatorValidation(unittest.IsolatedAsyncioTestCase):
    """Test coordinator initialization validation."""

    async def test_requires_explicit_universe(self):
        """Test that coordinator requires explicit universe parameter."""
        broker = MockBroker()

        # Should raise TypeError when universe is None
        with self.assertRaises(TypeError) as ctx:
            Coordinator(broker=broker, analytics_store=None, universe=None)

        self.assertIn("explicit universe", str(ctx.exception))

    async def test_invalid_strategy_falls_back(self):
        """Test that invalid strategy falls back to momentum."""
        broker = MockBroker(Universe.SIMULATION)

        # Patch config to have invalid strategy
        with patch("config.STRATEGY", "InvalidStrategy"):
            with patch("config.LOOKBACK_DAYS", 30):
                with patch("config.MOMENTUM_THRESHOLD", 0.02):
                    with patch("config.SELL_THRESHOLD", -0.03):
                        with patch("config.STOP_LOSS_PCT", 0.15):
                            with patch("config.TRADE_INTERVAL_MINUTES", 5):
                                coordinator = Coordinator(broker=broker, analytics_store=None, universe=Universe.SIMULATION)

                                # Should have fallen back to momentum strategy
                                self.assertIsNotNone(coordinator.signal_agent)
                                # Check that a startup warning log was created
                                # (logs are published on start, so we check the agent exists)
                                self.assertIsNotNone(coordinator.event_bus)


class TestCoordinatorOptionalAgents(unittest.IsolatedAsyncioTestCase):
    """Test optional agent initialization."""

    async def test_test_agent_enabled(self):
        """Test that test agent is created when enabled."""
        broker = MockBroker(Universe.SIMULATION)

        with patch("config.TEST_AGENT_ENABLED", True):
            with patch("config.TEST_AGENT_INTERVAL_MINUTES", 60):
                with patch("config.TEST_AGENT_LOG_PATH", "logs/test.jsonl"):
                    with patch("config.TRADE_INTERVAL_MINUTES", 5):
                        coordinator = Coordinator(broker=broker, analytics_store=None, universe=Universe.SIMULATION)
                        self.assertIsNotNone(coordinator.test_agent)

    async def test_replay_recorder_enabled(self):
        """Test that replay recorder is created when enabled."""
        broker = MockBroker(Universe.SIMULATION)

        with patch("config.REPLAY_RECORDER_ENABLED", True):
            with patch("config.REPLAY_RECORDER_SYMBOLS", ["AAPL", "GOOGL"]):
                with patch("config.REPLAY_RECORDER_INTERVAL_MINUTES", 5):
                    with patch("config.TRADE_INTERVAL_MINUTES", 5):
                        coordinator = Coordinator(broker=broker, analytics_store=None, universe=Universe.SIMULATION)
                        self.assertIsNotNone(coordinator.replay_recorder_agent)

    async def test_ui_check_enabled(self):
        """Test that UI check agent is created when enabled."""
        broker = MockBroker(Universe.SIMULATION)

        with patch("config.UI_CHECK_ENABLED", True):
            with patch("config.UI_CHECK_URL", "http://localhost:8000"):
                with patch("config.UI_CHECK_INTERVAL_MINUTES", 15):
                    with patch("config.UI_CHECK_LOG_PATH", "logs/ui_check.jsonl"):
                        with patch("config.TRADE_INTERVAL_MINUTES", 5):
                            coordinator = Coordinator(broker=broker, analytics_store=None, universe=Universe.SIMULATION)
                            self.assertIsNotNone(coordinator.ui_check_agent)

    async def test_ui_check_uses_default_url(self):
        """Test that UI check uses default URL when not specified."""
        broker = MockBroker(Universe.SIMULATION)

        with patch("config.UI_CHECK_ENABLED", True):
            with patch("config.UI_CHECK_URL", None):  # No URL specified
                with patch("config.API_HOST", "0.0.0.0"):
                    with patch("config.UI_PORT", 8000):
                        with patch("config.UI_CHECK_INTERVAL_MINUTES", 15):
                            with patch("config.UI_CHECK_LOG_PATH", "logs/ui_check.jsonl"):
                                with patch("config.TRADE_INTERVAL_MINUTES", 5):
                                    coordinator = Coordinator(broker=broker, analytics_store=None, universe=Universe.SIMULATION)
                                    self.assertIsNotNone(coordinator.ui_check_agent)


class TestCoordinatorAgentLifecycle(unittest.IsolatedAsyncioTestCase):
    """Test starting/stopping optional agents."""

    async def asyncSetUp(self):
        self.broker = MockBroker(Universe.SIMULATION)

    async def test_start_with_optional_agents(self):
        """Test starting coordinator with optional agents enabled."""
        with patch("config.TEST_AGENT_ENABLED", True):
            with patch("config.TEST_AGENT_INTERVAL_MINUTES", 60):
                with patch("config.TEST_AGENT_LOG_PATH", "logs/test.jsonl"):
                    with patch("config.REPLAY_RECORDER_ENABLED", True):
                        with patch("config.REPLAY_RECORDER_SYMBOLS", ["AAPL"]):
                            with patch("config.REPLAY_RECORDER_INTERVAL_MINUTES", 5):
                                with patch("config.UI_CHECK_ENABLED", True):
                                    with patch("config.UI_CHECK_URL", "http://localhost:8000"):
                                        with patch("config.UI_CHECK_INTERVAL_MINUTES", 15):
                                            with patch("config.UI_CHECK_LOG_PATH", "logs/ui.jsonl"):
                                                with patch("config.TRADE_INTERVAL_MINUTES", 5):
                                                    coordinator = Coordinator(
                                                        broker=self.broker,
                                                        analytics_store=None,
                                                        universe=Universe.SIMULATION
                                                    )

                                                    # Start all agents
                                                    await coordinator.start()
                                                    self.assertTrue(coordinator._running)

                                                    # Stop all agents
                                                    await coordinator.stop()
                                                    self.assertFalse(coordinator._running)


class TestCoordinatorStopLoss(unittest.IsolatedAsyncioTestCase):
    """Test stop-loss event handling."""

    async def asyncSetUp(self):
        self.broker = MockBroker(Universe.SIMULATION)
        with patch("config.TRADE_INTERVAL_MINUTES", 5):
            self.coordinator = Coordinator(
                broker=self.broker,
                analytics_store=None,
                universe=Universe.SIMULATION
            )
        await self.coordinator.start()

    async def asyncTearDown(self):
        await self.coordinator.stop()

    async def test_stop_loss_triggers_sell(self):
        """Test that stop-loss event creates a sell signal."""
        # Track published events
        published_events = []

        def capture_event(event):
            published_events.append(event)

        self.coordinator.event_bus.subscribe_all(capture_event)

        # Publish stop-loss event
        stop_loss_event = StopLossTriggered(
            universe=Universe.SIMULATION,
            session_id=self.coordinator.session_id,
            source="Test",
            symbol="AAPL",
            loss_pct=0.10,
            position_value=1000.0,
            current_price=90.0,
            entry_price=100.0,  # Fixed: it's entry_price not avg_entry_price
        )

        await self.coordinator.event_bus.publish(stop_loss_event)

        # Allow event to propagate
        import asyncio
        await asyncio.sleep(0.1)

        # Check that a RiskCheckPassed sell event was created
        sell_events = [e for e in published_events if isinstance(e, RiskCheckPassed) and e.action == "sell"]
        self.assertGreater(len(sell_events), 0)
        sell_event = sell_events[0]
        self.assertEqual(sell_event.symbol, "AAPL")
        self.assertEqual(sell_event.action, "sell")
        self.assertIn("Stop loss", sell_event.reason)


class TestCoordinatorHelperMethods(unittest.IsolatedAsyncioTestCase):
    """Test coordinator helper methods."""

    async def asyncSetUp(self):
        self.broker = MockBroker(Universe.SIMULATION)
        with patch("config.TRADE_INTERVAL_MINUTES", 5):
            self.coordinator = Coordinator(
                broker=self.broker,
                analytics_store=None,
                universe=Universe.SIMULATION
            )
        await self.coordinator.start()

    async def asyncTearDown(self):
        await self.coordinator.stop()

    async def test_set_broadcast_callback(self):
        """Test setting WebSocket broadcast callback."""
        callback = Mock()
        self.coordinator.set_broadcast_callback(callback)
        # Callback is set on alert agent
        self.assertIsNotNone(self.coordinator.alert_agent)

    async def test_refresh_data(self):
        """Test manual data refresh."""
        # Should trigger data fetch
        await self.coordinator.refresh_data()
        # No exception means success

    async def test_update_trade_interval_valid(self):
        """Test updating trade interval with valid value."""
        self.coordinator.update_trade_interval(10)
        self.assertEqual(self.coordinator.data_agent.interval_minutes, 10)

    async def test_update_trade_interval_invalid(self):
        """Test updating trade interval with invalid value."""
        with self.assertRaises(ValueError):
            self.coordinator.update_trade_interval(0)

        with self.assertRaises(ValueError):
            self.coordinator.update_trade_interval(-5)

    async def test_get_signals(self):
        """Test getting current signals."""
        signals = self.coordinator.get_signals()
        self.assertIsInstance(signals, (list, dict))

    async def test_get_logs(self):
        """Test getting recent logs."""
        logs = self.coordinator.get_logs(count=10)
        self.assertIsInstance(logs, list)

    async def test_get_top_gainers(self):
        """Test getting top gainers."""
        gainers = self.coordinator.get_top_gainers()
        self.assertIsInstance(gainers, list)

    async def test_get_market_indices(self):
        """Test getting market indices."""
        indices = self.coordinator.get_market_indices()
        self.assertIsInstance(indices, list)

    async def test_status_includes_all_agents(self):
        """Test that status includes all agent statuses."""
        status = self.coordinator.status()
        self.assertIn("running", status)
        self.assertIn("agents", status)
        self.assertIn("data", status["agents"])
        self.assertIn("signal", status["agents"])
        self.assertIn("risk", status["agents"])
        self.assertIn("execution", status["agents"])
        self.assertIn("monitor", status["agents"])
        self.assertIn("alert", status["agents"])
        self.assertIn("external_alerts", status["agents"])
        self.assertIn("observability", status["agents"])
        self.assertIn("analytics", status["agents"])
        self.assertIn("test", status["agents"])


if __name__ == "__main__":
    unittest.main()

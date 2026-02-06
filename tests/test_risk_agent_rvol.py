import unittest
import pandas as pd
from types import SimpleNamespace
from unittest.mock import patch

from agents.event_bus import EventBus
from agents.events import SignalGenerated, RiskCheckFailed, RiskCheckPassed
from agents.risk_agent import RiskAgent
from universe import Universe, UniverseContext


class DummyBroker:
    def __init__(self, bars_data=None):
        self._bars_data = bars_data

    def get_portfolio_value(self):
        return 100000.0

    def get_buying_power(self):
        return 100000.0

    def get_positions(self):
        return []

    def get_position(self, symbol):
        return None

    def get_bars(self, symbol, days=30):
        if self._bars_data is None:
            # Default: volume above threshold (RVOL = 2.5)
            return pd.DataFrame({
                "close": [100.0] * 30,
                "volume": [1000000] * 29 + [2500000]  # Last bar has 2.5x avg volume
            })
        return self._bars_data


class DummyBreaker:
    def update(self, equity):
        return False, None

    def status(self):
        return {"active": False}


class TestRiskAgentRVOL(unittest.IsolatedAsyncioTestCase):
    async def test_rvol_above_threshold_passes(self):
        """High relative volume should pass the check."""
        bars = pd.DataFrame({
            "close": [100.0] * 30,
            "volume": [1000000] * 29 + [2500000]  # RVOL = 2.5
        })
        broker = DummyBroker(bars_data=bars)
        context = UniverseContext(Universe.SIMULATION)
        bus = EventBus(context)
        agent = RiskAgent(bus, broker, circuit_breaker=DummyBreaker())

        passed = []
        failed = []

        def handle_pass(event: RiskCheckPassed):
            passed.append(event)

        def handle_fail(event: RiskCheckFailed):
            failed.append(event)

        bus.subscribe(RiskCheckPassed, handle_pass)
        bus.subscribe(RiskCheckFailed, handle_fail)

        signal = SignalGenerated(
            universe=context.universe,
            session_id=context.session_id,
            source="SignalAgent",
            symbol="AAPL",
            action="buy",
            strength=0.5,
            reason="test",
            current_price=100.0,
            momentum=0.1,
        )

        with patch("config.MAX_DAILY_TRADES", 5), \
            patch("config.MAX_OPEN_POSITIONS", 20), \
            patch("config.MIN_TRADE_VALUE", 1.0), \
            patch("config.MAX_POSITION_PCT", 0.5), \
            patch("config.MAX_SECTOR_EXPOSURE_PCT", 1.0), \
            patch("config.MAX_CORRELATED_EXPOSURE_PCT", 1.0), \
            patch("config.RVOL_THRESHOLD", 2.0), \
            patch("config.LOOKBACK_DAYS", 30):
            await agent._handle_signal(signal)

        self.assertEqual(len(passed), 1)
        self.assertEqual(len(failed), 0)

    async def test_rvol_below_threshold_fails(self):
        """Low relative volume should fail the check."""
        bars = pd.DataFrame({
            "close": [100.0] * 30,
            "volume": [1000000] * 29 + [500000]  # RVOL = 0.5
        })
        broker = DummyBroker(bars_data=bars)
        context = UniverseContext(Universe.SIMULATION)
        bus = EventBus(context)
        agent = RiskAgent(bus, broker, circuit_breaker=DummyBreaker())

        passed = []
        failed = []

        def handle_pass(event: RiskCheckPassed):
            passed.append(event)

        def handle_fail(event: RiskCheckFailed):
            failed.append(event)

        bus.subscribe(RiskCheckPassed, handle_pass)
        bus.subscribe(RiskCheckFailed, handle_fail)

        signal = SignalGenerated(
            universe=context.universe,
            session_id=context.session_id,
            source="SignalAgent",
            symbol="AAPL",
            action="buy",
            strength=0.5,
            reason="test",
            current_price=100.0,
            momentum=0.1,
        )

        with patch("config.MAX_DAILY_TRADES", 5), \
            patch("config.MAX_OPEN_POSITIONS", 20), \
            patch("config.MIN_TRADE_VALUE", 1.0), \
            patch("config.MAX_POSITION_PCT", 0.5), \
            patch("config.MAX_SECTOR_EXPOSURE_PCT", 1.0), \
            patch("config.MAX_CORRELATED_EXPOSURE_PCT", 1.0), \
            patch("config.RVOL_THRESHOLD", 2.0), \
            patch("config.LOOKBACK_DAYS", 30):
            await agent._handle_signal(signal)

        self.assertEqual(len(passed), 0)
        self.assertEqual(len(failed), 1)
        self.assertIn("Relative volume", failed[0].reason)

    async def test_rvol_missing_data_passes(self):
        """Missing volume data should fail-open and allow the trade."""
        bars = pd.DataFrame({
            "close": [100.0] * 30,
        })  # No volume column
        broker = DummyBroker(bars_data=bars)
        context = UniverseContext(Universe.SIMULATION)
        bus = EventBus(context)
        agent = RiskAgent(bus, broker, circuit_breaker=DummyBreaker())

        passed = []
        failed = []

        def handle_pass(event: RiskCheckPassed):
            passed.append(event)

        def handle_fail(event: RiskCheckFailed):
            failed.append(event)

        bus.subscribe(RiskCheckPassed, handle_pass)
        bus.subscribe(RiskCheckFailed, handle_fail)

        signal = SignalGenerated(
            universe=context.universe,
            session_id=context.session_id,
            source="SignalAgent",
            symbol="AAPL",
            action="buy",
            strength=0.5,
            reason="test",
            current_price=100.0,
            momentum=0.1,
        )

        with patch("config.MAX_DAILY_TRADES", 5), \
            patch("config.MAX_OPEN_POSITIONS", 20), \
            patch("config.MIN_TRADE_VALUE", 1.0), \
            patch("config.MAX_POSITION_PCT", 0.5), \
            patch("config.MAX_SECTOR_EXPOSURE_PCT", 1.0), \
            patch("config.MAX_CORRELATED_EXPOSURE_PCT", 1.0), \
            patch("config.RVOL_THRESHOLD", 2.0), \
            patch("config.LOOKBACK_DAYS", 30):
            await agent._handle_signal(signal)

        # Should pass - fail-open when data is unavailable
        self.assertEqual(len(passed), 1)
        self.assertEqual(len(failed), 0)


if __name__ == "__main__":
    unittest.main()

import unittest
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd

from agents.event_bus import EventBus
from agents.events import SignalGenerated, RiskCheckFailed, RiskCheckPassed
from agents.risk_agent import RiskAgent
from universe import Universe, UniverseContext


class DummySizer:
    def __init__(self, trade_value):
        self.trade_value = trade_value

    def calculate_trade_value(self, **kwargs):
        return self.trade_value


class DummyBroker:
    def __init__(self, positions=None, bars_map=None):
        self._positions = positions or []
        self._bars_map = bars_map or {}

    def get_portfolio_value(self):
        return 100000.0

    def get_buying_power(self):
        return 100000.0

    def get_positions(self):
        return self._positions

    def get_position(self, symbol):
        return None

    def get_bars(self, symbol, days=20):
        return self._bars_map.get(symbol)


class DummyBreaker:
    def update(self, equity):
        return False, None

    def status(self):
        return {"active": False}


def make_bars(prices):
    return pd.DataFrame(
        {"close": prices},
        index=pd.date_range(end="2024-01-05", periods=len(prices)),
    )


class TestRiskAgentExposure(unittest.IsolatedAsyncioTestCase):
    async def test_sector_exposure_blocks_buy(self):
        positions = [
            SimpleNamespace(symbol="BBB", market_value=20000.0),
            SimpleNamespace(symbol="CCC", market_value=20000.0),
        ]
        broker = DummyBroker(positions=positions)
        context = UniverseContext(Universe.SIMULATION)
        bus = EventBus(context)
        agent = RiskAgent(bus, broker, position_sizer=DummySizer(15000.0), circuit_breaker=DummyBreaker())

        failures = []
        bus.subscribe(RiskCheckFailed, failures.append)

        signal = SignalGenerated(
            universe=context.universe,
            session_id=context.session_id,
            source="SignalAgent",
            symbol="AAA",
            action="buy",
            strength=0.9,
            reason="test",
            current_price=10.0,
            momentum=0.1,
        )

        with patch("config.MAX_DAILY_TRADES", 5), \
            patch("config.MAX_OPEN_POSITIONS", 10), \
            patch("config.MIN_TRADE_VALUE", 1.0), \
            patch("config.MAX_POSITION_PCT", 0.5), \
            patch("config.SECTOR_MAP_JSON", "{\"AAA\": \"Tech\", \"BBB\": \"Tech\", \"CCC\": \"Tech\"}"), \
            patch("config.SECTOR_MAP_PATH", ""), \
            patch("config.MAX_SECTOR_EXPOSURE_PCT", 0.30), \
            patch("config.MAX_CORRELATED_EXPOSURE_PCT", 1.0):
            await agent._handle_signal(signal)

        self.assertEqual(len(failures), 1)
        self.assertIn("Sector exposure", failures[0].reason)

    async def test_correlation_exposure_blocks_buy(self):
        positions = [SimpleNamespace(symbol="BBB", market_value=30000.0)]
        bars_map = {
            "AAA": make_bars([100, 110, 120, 130, 140]),
            "BBB": make_bars([50, 55, 60, 65, 70]),
        }
        broker = DummyBroker(positions=positions, bars_map=bars_map)
        context = UniverseContext(Universe.SIMULATION)
        bus = EventBus(context)
        agent = RiskAgent(bus, broker, position_sizer=DummySizer(20000.0), circuit_breaker=DummyBreaker())

        failures = []
        bus.subscribe(RiskCheckFailed, failures.append)

        signal = SignalGenerated(
            universe=context.universe,
            session_id=context.session_id,
            source="SignalAgent",
            symbol="AAA",
            action="buy",
            strength=0.9,
            reason="test",
            current_price=10.0,
            momentum=0.1,
        )

        with patch("config.MAX_DAILY_TRADES", 5), \
            patch("config.MAX_OPEN_POSITIONS", 10), \
            patch("config.MIN_TRADE_VALUE", 1.0), \
            patch("config.MAX_POSITION_PCT", 0.5), \
            patch("config.SECTOR_MAP_JSON", ""), \
            patch("config.SECTOR_MAP_PATH", ""), \
            patch("config.MAX_SECTOR_EXPOSURE_PCT", 1.0), \
            patch("config.MAX_CORRELATED_EXPOSURE_PCT", 0.40), \
            patch("config.CORRELATION_THRESHOLD", 0.8), \
            patch("config.CORRELATION_LOOKBACK_DAYS", 5):
            await agent._handle_signal(signal)

        self.assertEqual(len(failures), 1)
        self.assertIn("Correlation exposure", failures[0].reason)

    async def test_correlation_exposure_allows_when_below_threshold(self):
        positions = [SimpleNamespace(symbol="BBB", market_value=10000.0)]
        bars_map = {
            "AAA": make_bars([100, 101, 100, 101, 100]),
            "BBB": make_bars([200, 199, 200, 199, 200]),
        }
        broker = DummyBroker(positions=positions, bars_map=bars_map)
        context = UniverseContext(Universe.SIMULATION)
        bus = EventBus(context)
        agent = RiskAgent(bus, broker, position_sizer=DummySizer(10000.0), circuit_breaker=DummyBreaker())

        passes = []
        bus.subscribe(RiskCheckPassed, passes.append)

        signal = SignalGenerated(
            universe=context.universe,
            session_id=context.session_id,
            source="SignalAgent",
            symbol="AAA",
            action="buy",
            strength=0.9,
            reason="test",
            current_price=10.0,
            momentum=0.1,
        )

        with patch("config.MAX_DAILY_TRADES", 5), \
            patch("config.MAX_OPEN_POSITIONS", 10), \
            patch("config.MIN_TRADE_VALUE", 1.0), \
            patch("config.MAX_POSITION_PCT", 0.5), \
            patch("config.SECTOR_MAP_JSON", ""), \
            patch("config.SECTOR_MAP_PATH", ""), \
            patch("config.MAX_SECTOR_EXPOSURE_PCT", 1.0), \
            patch("config.MAX_CORRELATED_EXPOSURE_PCT", 0.40), \
            patch("config.CORRELATION_THRESHOLD", 0.8), \
            patch("config.CORRELATION_LOOKBACK_DAYS", 5):
            await agent._handle_signal(signal)

        self.assertEqual(len(passes), 1)


if __name__ == "__main__":
    unittest.main()

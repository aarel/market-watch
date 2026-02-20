import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch
from zoneinfo import ZoneInfo

from agents.event_bus import EventBus
from agents.events import RiskCheckFailed, RiskCheckPassed, SignalGenerated
from agents.risk_agent import RiskAgent
from universe import Universe, UniverseContext


class DummyBroker:
    def __init__(
        self,
        portfolio_value=100000.0,
        buying_power=100000.0,
        positions=None,
        position=None,
        raise_get_position=False,
        raise_get_positions=False,
    ):
        self._portfolio_value = portfolio_value
        self._buying_power = buying_power
        self._positions = positions
        self._position = position
        self._raise_get_position = raise_get_position
        self._raise_get_positions = raise_get_positions

    def get_portfolio_value(self):
        return self._portfolio_value

    def get_buying_power(self):
        return self._buying_power

    def get_positions(self):
        if self._raise_get_positions:
            raise Exception("positions error")
        return self._positions

    def get_position(self, symbol):
        return self._position

    async def get_portfolio_value_async(self):
        return self.get_portfolio_value()

    async def get_buying_power_async(self):
        return self.get_buying_power()

    async def get_position_async(self, symbol):
        if self._raise_get_position:
            raise Exception("position error")
        return self.get_position(symbol)

    def get_bars(self, symbol, timeframe=None, limit=None, start=None, end=None, days=None, **kwargs):
        """Mock get_bars for RVOL/exposure checks. Returns empty list."""
        return []


class DummySizer:
    def __init__(self, value):
        self.value = value

    def calculate_trade_value(self, **kwargs):
        return self.value


class DummyBreaker:
    def update(self, equity):
        return False, None

    def status(self):
        return {"active": False}


class TestRiskAgentAdditionalCoverage(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        context = UniverseContext(Universe.SIMULATION)
        self.bus = EventBus(context)

    def _make_signal(self, action="buy"):
        return SignalGenerated(
            universe=self.bus._context.universe,
            session_id=self.bus._context.session_id,
            source="SignalAgent",
            symbol="AAA",
            action=action,
            strength=0.5,
            reason="test",
            current_price=10.0,
            momentum=0.1,
        )

    async def test_hold_signal_is_ignored(self):
        broker = DummyBroker()
        agent = RiskAgent(self.bus, broker, circuit_breaker=DummyBreaker())

        passed = []
        failed = []
        self.bus.subscribe(RiskCheckPassed, passed.append)
        self.bus.subscribe(RiskCheckFailed, failed.append)

        await agent._handle_signal(self._make_signal(action="hold"))

        self.assertEqual(passed, [])
        self.assertEqual(failed, [])

    async def test_daily_trade_limit_blocks_signal(self):
        import config
        broker = DummyBroker()
        agent = RiskAgent(self.bus, broker, circuit_breaker=DummyBreaker())
        agent.daily_trades = 5
        # Use same timezone as RiskAgent._reset_daily_limits()
        try:
            agent.last_trade_date = datetime.now(ZoneInfo(config.MARKET_TIMEZONE)).date()
        except Exception:
            agent.last_trade_date = datetime.now().date()

        failed = []
        self.bus.subscribe(RiskCheckFailed, failed.append)

        with patch("config.MAX_DAILY_TRADES", 5):
            await agent._handle_signal(self._make_signal(action="buy"))

        self.assertEqual(len(failed), 1)
        self.assertIn("Daily trade limit", failed[0].reason)

    async def test_invalid_portfolio_value_fails(self):
        broker = DummyBroker(portfolio_value=0.0)
        agent = RiskAgent(self.bus, broker, circuit_breaker=DummyBreaker())

        failed = []
        self.bus.subscribe(RiskCheckFailed, failed.append)

        with patch("config.MAX_DAILY_TRADES", 5):
            await agent._handle_signal(self._make_signal(action="buy"))

        self.assertEqual(len(failed), 1)
        self.assertIn("Invalid portfolio value", failed[0].reason)

    async def test_insufficient_buying_power_fails(self):
        broker = DummyBroker(buying_power=10.0, positions=None)
        agent = RiskAgent(self.bus, broker, position_sizer=DummySizer(1000.0), circuit_breaker=DummyBreaker())

        failed = []
        self.bus.subscribe(RiskCheckFailed, failed.append)

        with patch("config.MAX_DAILY_TRADES", 5), \
            patch("config.MIN_TRADE_VALUE", 100.0), \
            patch("config.MAX_POSITION_PCT", 0.5):
            await agent._handle_signal(self._make_signal(action="buy"))

        self.assertEqual(len(failed), 1)
        self.assertIn("Insufficient buying power", failed[0].reason)

    async def test_sell_position_lookup_exception(self):
        broker = DummyBroker(raise_get_position=True)
        agent = RiskAgent(self.bus, broker, circuit_breaker=DummyBreaker())

        failed = []
        self.bus.subscribe(RiskCheckFailed, failed.append)

        with patch("config.MAX_DAILY_TRADES", 5):
            await agent._handle_signal(self._make_signal(action="sell"))

        self.assertEqual(len(failed), 1)
        self.assertIn("Position lookup failed", failed[0].reason)

    async def test_sell_no_position_fails(self):
        broker = DummyBroker(position=None)
        agent = RiskAgent(self.bus, broker, circuit_breaker=DummyBreaker())

        failed = []
        self.bus.subscribe(RiskCheckFailed, failed.append)

        with patch("config.MAX_DAILY_TRADES", 5):
            await agent._handle_signal(self._make_signal(action="sell"))

        self.assertEqual(len(failed), 1)
        self.assertIn("No position", failed[0].reason)

    async def test_sell_with_position_passes(self):
        position = SimpleNamespace(market_value=5000.0)
        broker = DummyBroker(position=position)
        agent = RiskAgent(self.bus, broker, circuit_breaker=DummyBreaker())

        passed = []
        self.bus.subscribe(RiskCheckPassed, passed.append)

        with patch("config.MAX_DAILY_TRADES", 5):
            await agent._handle_signal(self._make_signal(action="sell"))

        self.assertEqual(len(passed), 1)
        self.assertAlmostEqual(passed[0].trade_value, 5000.0)
        self.assertGreater(passed[0].position_pct, 0.0)


class TestRiskAgentHelpers(unittest.TestCase):
    def setUp(self):
        context = UniverseContext(Universe.SIMULATION)
        self.bus = EventBus(context)

    def test_reset_daily_limits_fallback_timezone(self):
        broker = DummyBroker()
        agent = RiskAgent(self.bus, broker, circuit_breaker=DummyBreaker())
        agent.daily_trades = 5
        agent.last_trade_date = datetime(2000, 1, 1).date()

        today = datetime.now().date()
        with patch("config.MARKET_TIMEZONE", "Invalid/Zone"):
            agent._reset_daily_limits()

        self.assertEqual(agent.daily_trades, 0)
        self.assertEqual(agent.last_trade_date, today)

    def test_get_positions_safe_logs_and_returns_none(self):
        broker = DummyBroker(raise_get_positions=True)
        agent = RiskAgent(self.bus, broker, circuit_breaker=DummyBreaker())

        with patch("agents.risk_agent.logger") as mocked_logger:
            result = agent._get_positions_safe()

        self.assertIsNone(result)
        mocked_logger.error.assert_called()


if __name__ == "__main__":
    unittest.main()

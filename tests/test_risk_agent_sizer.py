import unittest
from types import SimpleNamespace
from unittest.mock import patch

from agents.event_bus import EventBus
from agents.events import SignalGenerated, RiskCheckPassed, RiskCheckFailed
from agents.risk_agent import RiskAgent
from universe import Universe, UniverseContext


class DummyBroker:
    def get_portfolio_value(self):
        return 100000.0

    def get_buying_power(self):
        return 100000.0

    def get_positions(self):
        return []

    def get_position(self, symbol):
        return None


class DummySizer:
    def __init__(self, value):
        self.value = value

    def calculate_trade_value(self, **kwargs):
        return self.value


class TestRiskAgentPositionSizer(unittest.IsolatedAsyncioTestCase):
    async def test_risk_agent_uses_sizer_value(self):
        context = UniverseContext(Universe.SIMULATION)
        bus = EventBus(context)
        broker = DummyBroker()
        sizer = DummySizer(4200.0)
        agent = RiskAgent(bus, broker, position_sizer=sizer)

        captured = []

        def handle_pass(event: RiskCheckPassed):
            captured.append(event)

        bus.subscribe(RiskCheckPassed, handle_pass)

        signal = SignalGenerated(
            universe=context.universe,
            session_id=context.session_id,
            source="SignalAgent",
            symbol="AAA",
            action="buy",
            strength=0.5,
            reason="test",
            current_price=10.0,
            momentum=0.1,
        )

        with patch("config.MAX_DAILY_TRADES", 5), \
            patch("config.MIN_TRADE_VALUE", 1.0), \
            patch("config.MAX_POSITION_PCT", 0.5):
            await agent._handle_signal(signal)

        self.assertEqual(len(captured), 1)
        self.assertAlmostEqual(captured[0].trade_value, 4200.0)

    async def test_risk_agent_rejects_below_min(self):
        context = UniverseContext(Universe.SIMULATION)
        bus = EventBus(context)
        broker = DummyBroker()
        sizer = DummySizer(0.5)
        agent = RiskAgent(bus, broker, position_sizer=sizer)

        captured = []

        def handle_fail(event: RiskCheckFailed):
            captured.append(event)

        bus.subscribe(RiskCheckFailed, handle_fail)

        signal = SignalGenerated(
            universe=context.universe,
            session_id=context.session_id,
            source="SignalAgent",
            symbol="AAA",
            action="buy",
            strength=0.1,
            reason="test",
            current_price=10.0,
            momentum=0.1,
        )

        with patch("config.MAX_DAILY_TRADES", 5), \
            patch("config.MIN_TRADE_VALUE", 1.0), \
            patch("config.MAX_POSITION_PCT", 0.5):
            await agent._handle_signal(signal)

        self.assertEqual(len(captured), 1)
        self.assertIn("below minimum", captured[0].reason)


if __name__ == "__main__":
    unittest.main()

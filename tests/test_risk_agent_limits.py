import unittest
from types import SimpleNamespace
from unittest.mock import patch

from agents.event_bus import EventBus
from agents.events import SignalGenerated, RiskCheckFailed
from agents.risk_agent import RiskAgent
from universe import Universe, UniverseContext


class DummyBroker:
    def __init__(self, positions_count=0):
        self._positions_count = positions_count

    def get_portfolio_value(self):
        return 100000.0

    def get_buying_power(self):
        return 100000.0

    def get_positions(self):
        return [SimpleNamespace(symbol=f"SYM{i}") for i in range(self._positions_count)]

    def get_position(self, symbol):
        return None


class DummyBreaker:
    def update(self, equity):
        return False, None

    def status(self):
        return {"active": False}


class TestRiskAgentLimits(unittest.IsolatedAsyncioTestCase):
    async def test_max_open_positions_blocks_buy(self):
        broker = DummyBroker(positions_count=3)
        context = UniverseContext(Universe.SIMULATION)
        bus = EventBus(context)
        agent = RiskAgent(bus, broker, circuit_breaker=DummyBreaker())

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
            strength=0.5,
            reason="test",
            current_price=10.0,
            momentum=0.1,
        )

        with patch("config.MAX_DAILY_TRADES", 5), \
            patch("config.MAX_OPEN_POSITIONS", 3), \
            patch("config.MIN_TRADE_VALUE", 1.0), \
            patch("config.MAX_POSITION_PCT", 0.5):
            await agent._handle_signal(signal)

        self.assertEqual(len(captured), 1)
        self.assertIn("Max open positions", captured[0].reason)


if __name__ == "__main__":
    unittest.main()

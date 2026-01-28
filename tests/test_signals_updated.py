import unittest

from agents.event_bus import EventBus
from agents.events import MarketDataReady, SignalsUpdated
from agents.signal_agent import SignalAgent
from strategies.momentum import MomentumStrategy
from universe import Universe, UniverseContext


class DummyBroker:
    def get_position(self, symbol):
        return None


class TestSignalsUpdated(unittest.IsolatedAsyncioTestCase):
    async def test_signals_updated_emitted(self):
        context = UniverseContext(Universe.SIMULATION)
        event_bus = EventBus(context)
        broker = DummyBroker()

        # Create a custom strategy with low requirements for testing
        strategy = MomentumStrategy(
            lookback_days=2,  # Only require 2 bars of history
            momentum_threshold=0.01,  # 1% threshold
            sell_threshold=-0.01,
            stop_loss_pct=0.05
        )

        agent = SignalAgent(event_bus, broker, strategy=strategy)

        captured = []

        def handle_signals(event: SignalsUpdated):
            captured.append(event)

        event_bus.subscribe(SignalsUpdated, handle_signals)

        event = MarketDataReady(
            universe=context.universe,
            session_id=context.session_id,
            source="test",
            symbols=["AAA"],
            prices={"AAA": 105.0},
            bars={"AAA": {"close": {0: 100.0, 1: 105.0}}},
            account={},
            positions=[],
            market_open=True,
        )

        await agent._handle_market_data(event)

        self.assertEqual(len(captured), 1)
        self.assertEqual(len(captured[0].signals), 1)
        self.assertEqual(captured[0].signals[0]["action"], "buy")
        self.assertEqual(captured[0].signals[0]["symbol"], "AAA")


if __name__ == "__main__":
    unittest.main()

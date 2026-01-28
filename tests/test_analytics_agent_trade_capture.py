import types
import unittest
from datetime import datetime

from agents.analytics_agent import AnalyticsAgent
from agents.events import OrderExecuted
from universe import Universe, UniverseContext


class InMemoryStore:
    def __init__(self):
        self.trades = []
        self.equity = []

    def record_trade(self, trade):
        self.trades.append(trade)

    def record_equity(self, snap):
        self.equity.append(snap)


class DummyEventBus:
    def __init__(self):
        self._context = UniverseContext(Universe.SIMULATION)
        self.subs = []

    def subscribe(self, event_type, cb):
        self.subs.append((event_type, cb))

    def unsubscribe(self, event_type, cb):
        self.subs = [s for s in self.subs if s != (event_type, cb)]


class TestAnalyticsAgentTradeCapture(unittest.IsolatedAsyncioTestCase):
    async def test_records_trade_with_price_and_backfills_notional(self):
        store = InMemoryStore()
        bus = DummyEventBus()
        agent = AnalyticsAgent(bus, broker=None, store=store)
        await agent.start()

        evt = OrderExecuted(
            universe=bus._context.universe,
            session_id=bus._context.session_id,
            timestamp=datetime.now(),
            symbol="AAPL",
            action="buy",
            qty=2,
            filled_avg_price=5.5,
            notional=None,
            order_id="abc",
        )
        await agent._handle_order_executed(evt)
        self.assertEqual(len(store.trades), 1)
        trade = store.trades[0]
        self.assertEqual(trade["symbol"], "AAPL")
        self.assertEqual(trade["side"], "buy")
        self.assertAlmostEqual(trade["filled_avg_price"], 5.5)
        self.assertAlmostEqual(trade["notional"], 11.0)
        self.assertEqual(trade["order_id"], "abc")

        await agent.stop()


if __name__ == "__main__":
    unittest.main()

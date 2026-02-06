"""Test that AnalyticsAgent only records filled orders."""
import unittest
from datetime import datetime, timezone

from agents.analytics_agent import AnalyticsAgent
from agents.events import OrderExecuted
from universe import Universe, UniverseContext


class InMemoryStore:
    """Mock store that holds trades in memory."""
    def __init__(self):
        self.trades = []
        self.equity = []

    def record_trade(self, trade):
        self.trades.append(trade)

    def record_equity(self, snap):
        self.equity.append(snap)


class DummyEventBus:
    """Mock EventBus for testing."""
    def __init__(self):
        self._context = UniverseContext(Universe.SIMULATION)

    def subscribe(self, *args, **kwargs):
        pass

    def unsubscribe(self, *args, **kwargs):
        pass

    async def publish(self, *args, **kwargs):
        pass


class TestAnalyticsFilledFilter(unittest.IsolatedAsyncioTestCase):
    """Test AnalyticsAgent filters unfilled orders."""

    def setUp(self):
        self.event_bus = DummyEventBus()
        self.store = InMemoryStore()
        self.agent = AnalyticsAgent(
            event_bus=self.event_bus,
            broker=None,
            store=self.store
        )

    async def test_records_filled_order(self):
        """Filled orders should be recorded."""
        event = OrderExecuted(
            universe=Universe.PAPER,
            session_id="test_session",
            symbol="AAPL",
            action="buy",
            qty=10.0,
            filled_avg_price=150.50,
            notional=1505.0,
            order_id="filled_order_1",
            status="filled",
            filled_at=datetime.now(timezone.utc).isoformat(),
        )

        await self.agent._handle_order_executed(event)

        # Should be recorded
        self.assertEqual(len(self.store.trades), 1)
        self.assertEqual(self.store.trades[0]["symbol"], "AAPL")
        self.assertEqual(self.store.trades[0]["filled_avg_price"], 150.50)

    async def test_records_partially_filled_order(self):
        """Partially filled orders should be recorded."""
        event = OrderExecuted(
            universe=Universe.PAPER,
            session_id="test_session",
            symbol="TSLA",
            action="buy",
            qty=5.0,
            filled_avg_price=200.00,
            notional=1000.0,
            order_id="partial_order_1",
            status="partially_filled",
            filled_at=datetime.now(timezone.utc).isoformat(),
        )

        await self.agent._handle_order_executed(event)

        # Should be recorded
        self.assertEqual(len(self.store.trades), 1)
        self.assertEqual(self.store.trades[0]["status"], "partially_filled")

    async def test_skips_pending_new_order(self):
        """Pending_new orders should NOT be recorded."""
        event = OrderExecuted(
            universe=Universe.PAPER,
            session_id="test_session",
            symbol="GOOGL",
            action="buy",
            qty=None,
            filled_avg_price=None,
            notional=1000.0,
            order_id="pending_order_1",
            status="pending_new",
            filled_at=None,
        )

        await self.agent._handle_order_executed(event)

        # Should NOT be recorded
        self.assertEqual(len(self.store.trades), 0)

    async def test_skips_new_order(self):
        """New orders should NOT be recorded."""
        event = OrderExecuted(
            universe=Universe.PAPER,
            session_id="test_session",
            symbol="MSFT",
            action="sell",
            qty=20.0,
            filled_avg_price=None,
            order_id="new_order_1",
            status="new",
        )

        await self.agent._handle_order_executed(event)

        # Should NOT be recorded
        self.assertEqual(len(self.store.trades), 0)

    async def test_skips_accepted_order(self):
        """Accepted orders should NOT be recorded."""
        event = OrderExecuted(
            universe=Universe.PAPER,
            session_id="test_session",
            symbol="NVDA",
            action="buy",
            qty=None,
            filled_avg_price=None,
            notional=500.0,
            order_id="accepted_order_1",
            status="accepted",
        )

        await self.agent._handle_order_executed(event)

        # Should NOT be recorded
        self.assertEqual(len(self.store.trades), 0)

    async def test_skips_order_with_null_price(self):
        """Orders with null filled_avg_price should NOT be recorded."""
        event = OrderExecuted(
            universe=Universe.PAPER,
            session_id="test_session",
            symbol="AMZN",
            action="buy",
            qty=10.0,
            filled_avg_price=None,  # Price is null
            notional=1000.0,
            order_id="null_price_1",
            status="filled",  # Status says filled but price is null
        )

        await self.agent._handle_order_executed(event)

        # Should NOT be recorded (invalid data)
        self.assertEqual(len(self.store.trades), 0)

    async def test_skips_order_with_zero_price(self):
        """Orders with zero filled_avg_price should NOT be recorded."""
        event = OrderExecuted(
            universe=Universe.PAPER,
            session_id="test_session",
            symbol="META",
            action="buy",
            qty=10.0,
            filled_avg_price=0.0,  # Price is zero
            notional=1000.0,
            order_id="zero_price_1",
            status="filled",
        )

        await self.agent._handle_order_executed(event)

        # Should NOT be recorded (invalid price)
        self.assertEqual(len(self.store.trades), 0)

    async def test_backfills_notional_for_filled_order(self):
        """Notional should be backfilled from qty * filled_avg_price."""
        event = OrderExecuted(
            universe=Universe.PAPER,
            session_id="test_session",
            symbol="NFLX",
            action="buy",
            qty=10.0,
            filled_avg_price=300.00,
            notional=None,  # Missing notional
            order_id="backfill_1",
            status="filled",
        )

        await self.agent._handle_order_executed(event)

        # Should be recorded with backfilled notional
        self.assertEqual(len(self.store.trades), 1)
        self.assertEqual(self.store.trades[0]["notional"], 3000.0)

    async def test_mixed_orders_only_records_filled(self):
        """Multiple orders: only filled ones should be recorded."""
        events = [
            # Pending - should be skipped
            OrderExecuted(
                universe=Universe.PAPER,
                session_id="test_session",
                symbol="AAPL",
                action="buy",
                filled_avg_price=None,
                order_id="pending_1",
                status="pending_new",
            ),
            # Filled - should be recorded
            OrderExecuted(
                universe=Universe.PAPER,
                session_id="test_session",
                symbol="TSLA",
                action="buy",
                qty=5.0,
                filled_avg_price=200.0,
                order_id="filled_1",
                status="filled",
            ),
            # New - should be skipped
            OrderExecuted(
                universe=Universe.PAPER,
                session_id="test_session",
                symbol="GOOGL",
                action="sell",
                filled_avg_price=None,
                order_id="new_1",
                status="new",
            ),
            # Filled - should be recorded
            OrderExecuted(
                universe=Universe.PAPER,
                session_id="test_session",
                symbol="MSFT",
                action="sell",
                qty=10.0,
                filled_avg_price=350.0,
                order_id="filled_2",
                status="filled",
            ),
        ]

        for event in events:
            await self.agent._handle_order_executed(event)

        # Only 2 filled orders should be recorded
        self.assertEqual(len(self.store.trades), 2)
        symbols = [t["symbol"] for t in self.store.trades]
        self.assertIn("TSLA", symbols)
        self.assertIn("MSFT", symbols)
        self.assertNotIn("AAPL", symbols)
        self.assertNotIn("GOOGL", symbols)


if __name__ == "__main__":
    unittest.main()

"""Test ExecutionAgent._await_fill polling behavior."""
import unittest
from unittest.mock import MagicMock, AsyncMock
from types import SimpleNamespace

from agents.execution_agent import ExecutionAgent
from universe import Universe, UniverseContext


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


class TestExecutionAwaitFill(unittest.IsolatedAsyncioTestCase):
    """Test _await_fill polling and retry logic."""

    def setUp(self):
        self.event_bus = DummyEventBus()
        self.broker = MagicMock()
        self.agent = ExecutionAgent(
            event_bus=self.event_bus,
            broker=self.broker,
            risk_agent=None,
        )

    async def test_returns_filled_order_on_first_attempt(self):
        """If order is filled on first poll, return immediately."""
        # Initial order (pending)
        order = SimpleNamespace(id="order_123", status="pending_new")

        # First poll returns filled order
        filled_order = SimpleNamespace(id="order_123", status="filled", filled_avg_price=150.50)
        self.broker.get_order = MagicMock(return_value=filled_order)

        result = await self.agent._await_fill(order)

        # Should return filled order after first poll
        self.assertEqual(result.status, "filled")
        self.assertEqual(result.filled_avg_price, 150.50)
        # Should have called get_order at least once
        self.broker.get_order.assert_called()

    async def test_polls_multiple_times_until_filled(self):
        """Should poll up to 5 times until order is filled."""
        order = SimpleNamespace(id="order_456", status="pending_new")

        # Simulate: pending -> pending -> filled
        call_count = 0

        def mock_get_order(order_id):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return SimpleNamespace(id=order_id, status="pending_new")
            else:
                return SimpleNamespace(id=order_id, status="filled", filled_avg_price=200.0)

        self.broker.get_order = MagicMock(side_effect=mock_get_order)

        result = await self.agent._await_fill(order)

        # Should return filled order
        self.assertEqual(result.status, "filled")
        self.assertEqual(result.filled_avg_price, 200.0)
        # Should have called get_order 3 times
        self.assertEqual(call_count, 3)

    async def test_stops_polling_on_partially_filled(self):
        """Should stop polling when status is partially_filled."""
        order = SimpleNamespace(id="order_789", status="pending_new")

        # First poll returns partially_filled
        partial_order = SimpleNamespace(
            id="order_789",
            status="partially_filled",
            filled_avg_price=100.0
        )
        self.broker.get_order = MagicMock(return_value=partial_order)

        result = await self.agent._await_fill(order)

        # Should return partially filled order
        self.assertEqual(result.status, "partially_filled")
        self.assertEqual(result.filled_avg_price, 100.0)

    async def test_stops_polling_on_canceled(self):
        """Should stop polling when order is canceled."""
        order = SimpleNamespace(id="order_canceled", status="pending_new")

        call_count = 0

        def mock_get_order(order_id):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return SimpleNamespace(id=order_id, status="pending_new")
            else:
                return SimpleNamespace(id=order_id, status="canceled")

        self.broker.get_order = MagicMock(side_effect=mock_get_order)

        result = await self.agent._await_fill(order)

        # Should return canceled order and stop polling
        self.assertEqual(result.status, "canceled")
        # Should have stopped after 2 attempts (not all 5)
        self.assertLessEqual(call_count, 2)

    async def test_stops_polling_on_rejected(self):
        """Should stop polling when order is rejected."""
        order = SimpleNamespace(id="order_rejected", status="pending_new")

        rejected_order = SimpleNamespace(id="order_rejected", status="rejected")
        self.broker.get_order = MagicMock(return_value=rejected_order)

        result = await self.agent._await_fill(order)

        # Should return rejected order
        self.assertEqual(result.status, "rejected")

    async def test_returns_last_state_after_max_attempts(self):
        """If order never fills, return last known state after 5 attempts."""
        order = SimpleNamespace(id="order_stuck", status="pending_new")

        # Always return pending
        pending_order = SimpleNamespace(id="order_stuck", status="pending_new")
        self.broker.get_order = MagicMock(return_value=pending_order)

        result = await self.agent._await_fill(order)

        # Should return last known state (still pending)
        self.assertEqual(result.status, "pending_new")
        # Should have tried all 5 attempts
        self.assertEqual(self.broker.get_order.call_count, 5)

    async def test_handles_broker_without_get_order(self):
        """If broker doesn't support get_order, return original order."""
        order = SimpleNamespace(id="order_no_support", status="pending_new")

        # Remove get_order method
        if hasattr(self.broker, 'get_order'):
            delattr(self.broker, 'get_order')

        result = await self.agent._await_fill(order)

        # Should return original order unchanged
        self.assertEqual(result, order)

    async def test_handles_get_order_exception(self):
        """If get_order raises exception, continue polling."""
        order = SimpleNamespace(id="order_error", status="pending_new")

        call_count = 0

        def mock_get_order(order_id):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("API error")
            else:
                return SimpleNamespace(id=order_id, status="filled", filled_avg_price=250.0)

        self.broker.get_order = MagicMock(side_effect=mock_get_order)

        result = await self.agent._await_fill(order)

        # Should eventually return filled order despite earlier errors
        self.assertEqual(result.status, "filled")
        self.assertEqual(result.filled_avg_price, 250.0)
        # Should have tried 3 times
        self.assertEqual(call_count, 3)

    async def test_exponential_backoff_timing(self):
        """Verify exponential backoff delays (not strict timing, just structure)."""
        order = SimpleNamespace(id="order_timing", status="pending_new")

        # Track when get_order is called
        call_times = []

        def mock_get_order(order_id):
            import time
            call_times.append(time.time())
            # Keep returning pending to force all 5 attempts
            return SimpleNamespace(id=order_id, status="pending_new")

        self.broker.get_order = MagicMock(side_effect=mock_get_order)

        await self.agent._await_fill(order)

        # Should have made 5 calls
        self.assertEqual(len(call_times), 5)

        # Each delay should be approximately double the previous
        # (0.5s, 1s, 2s, 4s, 8s) but we won't check exact timing
        # Just verify calls were made and spread out
        if len(call_times) >= 2:
            # At least some delay between first and last call
            time_span = call_times[-1] - call_times[0]
            # With exponential backoff, should be at least 10 seconds
            # (but be generous in test to avoid flakiness)
            self.assertGreater(time_span, 5.0)


if __name__ == "__main__":
    unittest.main()

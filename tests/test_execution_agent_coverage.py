"""Comprehensive tests for ExecutionAgent to improve coverage.

Focuses on untested paths:
- Sell order execution
- Manual trades (notional and qty modes)
- Error handling
- Edge cases
"""
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from agents.event_bus import EventBus
from agents.events import OrderExecuted, OrderFailed, RiskCheckPassed
from agents.execution_agent import ExecutionAgent
from universe import Universe, UniverseContext


class MockBroker:
    """Mock broker for testing."""

    def __init__(self, universe=Universe.SIMULATION):
        self.universe = universe
        self._positions = {}
        self._order_counter = 0

    def get_position(self, symbol):
        return self._positions.get(symbol)

    async def get_position_async(self, symbol):
        return self.get_position(symbol)

    async def submit_order_async(self, **kwargs):
        self._order_counter += 1
        return SimpleNamespace(
            id=f"order_{self._order_counter}",
            symbol=kwargs.get("symbol", "TEST"),
            qty=kwargs.get("qty", 10),
            notional=kwargs.get("notional"),
            side=kwargs.get("side", "buy"),
            filled_avg_price=150.0,
            status="filled",
            submitted_at="2026-01-01T10:00:00Z",
            filled_at="2026-01-01T10:00:01Z",
            time_in_force="day",
            type="market",
        )

    def get_order(self, order_id):
        # Simulate immediate fill
        return SimpleNamespace(
            id=order_id,
            status="filled",
            filled_avg_price=150.0,
        )

    def add_position(self, symbol, qty):
        """Helper to add a mock position."""
        self._positions[symbol] = SimpleNamespace(
            symbol=symbol,
            qty=qty,
            avg_entry_price=150.0,
            current_price=155.0,
        )


class TestExecutionAgentApprovedTrades(unittest.IsolatedAsyncioTestCase):
    """Test approved trade execution paths."""

    async def asyncSetUp(self):
        self.universe = Universe.SIMULATION
        self.context = UniverseContext(self.universe)
        self.broker = MockBroker(self.universe)
        self.event_bus = EventBus(self.context)
        self.agent = ExecutionAgent(self.event_bus, self.broker, risk_agent=None)
        await self.agent.start()

    async def asyncTearDown(self):
        await self.agent.stop()

    async def test_buy_order_success(self):
        """Test successful buy order execution."""
        event = RiskCheckPassed(
            universe=self.universe,
            session_id=self.context.session_id,
            source="Test",
            symbol="AAPL",
            action="buy",
            trade_value=1000.0,
            reason="Test buy",
        )

        # Enable auto trading
        with patch("config.AUTO_TRADE", True):
            await self.agent._handle_approved_trade(event)

        self.assertEqual(self.agent._orders_executed, 1)
        self.assertEqual(self.agent._orders_failed, 0)

    async def test_sell_order_with_position(self):
        """Test successful sell order when position exists."""
        # Add position first
        self.broker.add_position("AAPL", "10")

        event = RiskCheckPassed(
            universe=self.universe,
            session_id=self.context.session_id,
            source="Test",
            symbol="AAPL",
            action="sell",
            trade_value=1500.0,
            reason="Test sell",
        )

        with patch("config.AUTO_TRADE", True):
            await self.agent._handle_approved_trade(event)

        self.assertEqual(self.agent._orders_executed, 1)
        self.assertEqual(self.agent._orders_failed, 0)

    async def test_sell_order_without_position(self):
        """Test sell order fails when position doesn't exist."""
        event = RiskCheckPassed(
            universe=self.universe,
            session_id=self.context.session_id,
            source="Test",
            symbol="AAPL",
            action="sell",
            trade_value=1500.0,
            reason="Test sell",
        )

        with patch("config.AUTO_TRADE", True):
            await self.agent._handle_approved_trade(event)

        self.assertEqual(self.agent._orders_executed, 0)
        self.assertEqual(self.agent._orders_failed, 1)

    async def test_auto_trade_disabled(self):
        """Test that trades are skipped when AUTO_TRADE is False."""
        event = RiskCheckPassed(
            universe=self.universe,
            session_id=self.context.session_id,
            source="Test",
            symbol="AAPL",
            action="buy",
            trade_value=1000.0,
            reason="Test",
        )

        with patch("config.AUTO_TRADE", False):
            await self.agent._handle_approved_trade(event)

        self.assertEqual(self.agent._orders_executed, 0)
        self.assertEqual(self.agent._orders_failed, 0)

    async def test_exception_handling(self):
        """Test exception handling in trade execution."""
        # Make broker raise exception
        self.broker.submit_order_async = AsyncMock(side_effect=Exception("Broker error"))

        event = RiskCheckPassed(
            universe=self.universe,
            session_id=self.context.session_id,
            source="Test",
            symbol="AAPL",
            action="buy",
            trade_value=1000.0,
            reason="Test",
        )

        with patch("config.AUTO_TRADE", True):
            await self.agent._handle_approved_trade(event)

        self.assertEqual(self.agent._orders_executed, 0)
        self.assertEqual(self.agent._orders_failed, 1)


class TestExecutionAgentManualTrades(unittest.IsolatedAsyncioTestCase):
    """Test manual trade execution paths."""

    async def asyncSetUp(self):
        self.universe = Universe.SIMULATION
        self.context = UniverseContext(self.universe)
        self.broker = MockBroker(self.universe)
        self.event_bus = EventBus(self.context)
        self.agent = ExecutionAgent(self.event_bus, self.broker, risk_agent=None)
        await self.agent.start()

    async def asyncTearDown(self):
        await self.agent.stop()

    async def test_manual_buy_notional(self):
        """Test manual buy with notional amount."""
        result = await self.agent.execute_manual_trade(
            symbol="AAPL",
            action="buy",
            amount=1000.0,
            mode="notional"
        )

        self.assertTrue(result["success"])
        self.assertIn("order_id", result)
        self.assertEqual(self.agent._orders_executed, 1)

    async def test_manual_buy_qty(self):
        """Test manual buy with share quantity."""
        result = await self.agent.execute_manual_trade(
            symbol="AAPL",
            action="buy",
            qty=10,
            mode="qty"
        )

        self.assertTrue(result["success"])
        self.assertIn("order_id", result)

    async def test_manual_buy_qty_invalid(self):
        """Test manual buy fails with invalid qty."""
        result = await self.agent.execute_manual_trade(
            symbol="AAPL",
            action="buy",
            qty=0,
            mode="qty"
        )

        self.assertFalse(result["success"])
        self.assertIn("Shares required", result["error"])

    async def test_manual_buy_notional_invalid(self):
        """Test manual buy fails with invalid amount."""
        result = await self.agent.execute_manual_trade(
            symbol="AAPL",
            action="buy",
            amount=0,
            mode="notional"
        )

        self.assertFalse(result["success"])
        self.assertIn("Amount required", result["error"])

    async def test_manual_sell_with_position(self):
        """Test manual sell when position exists."""
        self.broker.add_position("AAPL", "10")

        result = await self.agent.execute_manual_trade(
            symbol="AAPL",
            action="sell"
        )

        self.assertTrue(result["success"])
        self.assertIn("order_id", result)

    async def test_manual_sell_without_position(self):
        """Test manual sell fails when no position."""
        result = await self.agent.execute_manual_trade(
            symbol="AAPL",
            action="sell"
        )

        self.assertFalse(result["success"])
        self.assertIn("No position", result["error"])

    async def test_manual_sell_partial_qty(self):
        """Test manual sell with specified quantity."""
        self.broker.add_position("AAPL", "10")

        result = await self.agent.execute_manual_trade(
            symbol="AAPL",
            action="sell",
            qty=5,
            mode="qty"
        )

        self.assertTrue(result["success"])

    async def test_manual_sell_by_amount(self):
        """Test manual sell by dollar amount (converts to qty)."""
        position = SimpleNamespace(
            symbol="AAPL",
            qty=10,  # Numeric, not string
            avg_entry_price=150.0,
            current_price=155.0,
        )
        self.broker._positions["AAPL"] = position

        result = await self.agent.execute_manual_trade(
            symbol="AAPL",
            action="sell",
            amount=500.0,  # Should convert to ~3.2 shares at $155
            mode="notional"
        )

        self.assertTrue(result["success"])

    async def test_manual_invalid_action(self):
        """Test manual trade fails with invalid action."""
        result = await self.agent.execute_manual_trade(
            symbol="AAPL",
            action="hold",  # Invalid
            amount=1000.0
        )

        self.assertFalse(result["success"])
        self.assertIn("must be 'buy' or 'sell'", result["error"])

    async def test_manual_trade_exception(self):
        """Test manual trade exception handling."""
        self.broker.submit_order_async = AsyncMock(side_effect=Exception("Error"))

        result = await self.agent.execute_manual_trade(
            symbol="AAPL",
            action="buy",
            amount=1000.0
        )

        self.assertFalse(result["success"])
        self.assertIn("Error", result["error"])


class TestExecutionAgentHelpers(unittest.IsolatedAsyncioTestCase):
    """Test helper methods and edge cases."""

    async def asyncSetUp(self):
        self.universe = Universe.SIMULATION
        self.context = UniverseContext(self.universe)
        self.broker = MockBroker(self.universe)
        self.event_bus = EventBus(self.context)
        self.agent = ExecutionAgent(self.event_bus, self.broker, risk_agent=None)

    async def test_build_client_order_id(self):
        """Test client order ID generation."""
        order_id = self.agent._build_client_order_id("test", "AAPL")
        self.assertIn("test", order_id)
        self.assertIn("AAPL", order_id)

    async def test_round_notional(self):
        """Test notional rounding."""
        self.assertEqual(self.agent._round_notional(1000.567), 1000.57)
        self.assertEqual(self.agent._round_notional(None), 0.0)

    async def test_extract_order_id_fallback(self):
        """Test order-id extraction fallback for broker objects without id."""
        order = SimpleNamespace(order_id="broker_order_123")
        extracted = self.agent._extract_order_id(order, fallback="manual-AAPL-1")
        self.assertEqual(extracted, "broker_order_123")

        no_id_order = SimpleNamespace(status="filled")
        fallback_only = self.agent._extract_order_id(no_id_order, fallback="manual-AAPL-2")
        self.assertEqual(fallback_only, "manual-AAPL-2")

    async def test_status(self):
        """Test status reporting."""
        status = self.agent.status()
        self.assertIn("orders_executed", status)
        self.assertIn("orders_failed", status)
        self.assertIn("recent_orders", status)

    async def test_recent_orders_limit(self):
        """Test that recent orders are limited to 50."""
        # Simulate 60 orders
        for i in range(60):
            self.agent._recent_orders.append({"order_id": f"order_{i}"})

        # Trigger the limit check by executing a successful order
        self.broker.add_position("AAPL", "10")
        event = RiskCheckPassed(
            universe=self.universe,
            session_id=self.context.session_id,
            source="Test",
            symbol="AAPL",
            action="buy",
            trade_value=1000.0,
            reason="Test",
        )

        with patch("config.AUTO_TRADE", True):
            await self.agent._handle_approved_trade(event)

        # Should be trimmed to 50
        self.assertEqual(len(self.agent._recent_orders), 50)


class TestExecutionAgentRiskIntegration(unittest.IsolatedAsyncioTestCase):
    """Test integration with RiskAgent."""

    async def asyncSetUp(self):
        self.universe = Universe.SIMULATION
        self.context = UniverseContext(self.universe)
        self.broker = MockBroker(self.universe)
        self.event_bus = EventBus(self.context)
        self.risk_agent = Mock()
        self.risk_agent.increment_trade_count = Mock()
        self.agent = ExecutionAgent(self.event_bus, self.broker, self.risk_agent)
        await self.agent.start()

    async def asyncTearDown(self):
        await self.agent.stop()

    async def test_risk_agent_notified_on_success(self):
        """Test that risk agent is notified when trade succeeds."""
        event = RiskCheckPassed(
            universe=self.universe,
            session_id=self.context.session_id,
            source="Test",
            symbol="AAPL",
            action="buy",
            trade_value=1000.0,
            reason="Test",
        )

        with patch("config.AUTO_TRADE", True):
            await self.agent._handle_approved_trade(event)

        self.risk_agent.increment_trade_count.assert_called_once()

    async def test_risk_agent_notified_on_manual_trade(self):
        """Test that risk agent is notified on manual trades."""
        result = await self.agent.execute_manual_trade(
            symbol="AAPL",
            action="buy",
            amount=1000.0
        )

        self.assertTrue(result["success"])
        self.risk_agent.increment_trade_count.assert_called_once()


if __name__ == "__main__":
    unittest.main()

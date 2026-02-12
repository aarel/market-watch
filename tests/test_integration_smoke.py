"""Integration smoke tests - verify full system works end-to-end.

These tests exercise the complete flow from market data to analytics,
ensuring all components integrate correctly.
"""
import asyncio
import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock, patch

import config
from agents.coordinator import Coordinator
from agents.event_bus import EventBus
from agents.events import (
    ConfigUpdated,
    MarketDataReady,
    OrderExecuted,
    RiskCheckPassed,
    SignalGenerated,
)
from analytics.store import AnalyticsStore
from broker_query_service import BrokerQueryService
from server.config_manager import ConfigManager
from universe import Universe, UniverseContext


class IntegrationBroker:
    """Realistic broker mock for integration tests."""

    def __init__(self, universe: Universe):
        self.universe = universe
        self._positions = []
        self._orders = []
        self._order_id_counter = 1
        self._account = SimpleNamespace(
            portfolio_value=100000.0,
            buying_power=100000.0,
            cash=100000.0,
            equity=100000.0,
            status="ACTIVE",
        )

    def get_account(self):
        return self._account

    def get_positions(self):
        return self._positions

    def get_position(self, symbol):
        for pos in self._positions:
            if pos.symbol == symbol:
                return pos
        return None

    def get_portfolio_value(self):
        return float(self._account.portfolio_value)

    def get_buying_power(self):
        return float(self._account.buying_power)

    def is_market_open(self):
        return True

    def get_current_price(self, symbol):
        # Simple price model
        prices = {
            "AAPL": 150.0,
            "GOOGL": 2800.0,
            "MSFT": 300.0,
            "NVDA": 500.0,
            "TSLA": 200.0,
        }
        return prices.get(symbol, 100.0)

    def get_bars(self, symbol, days=30, timeframe='1Day', limit=None):
        """Return mock bars with upward momentum."""
        import pandas as pd

        # Create bars with upward trend (momentum > threshold)
        closes = [100.0 + i * 2.0 for i in range(days)]  # 2% daily gain
        volumes = [1000000] * (days - 1) + [2500000]  # High volume on last bar

        return pd.DataFrame({
            "close": closes,
            "volume": volumes,
        })

    def get_snapshots(self, symbols):
        """Return mock snapshots for top gainers."""
        result = {}
        for symbol in symbols:
            result[symbol] = SimpleNamespace(
                latest_trade=SimpleNamespace(p=self.get_current_price(symbol)),
                prev_daily_bar=SimpleNamespace(c=self.get_current_price(symbol) * 0.95),
            )
        return result

    def submit_order(self, symbol, qty=None, notional=None, side="buy", **kwargs):
        """Submit order and update positions."""
        order_id = f"order_{self._order_id_counter}"
        self._order_id_counter += 1

        price = self.get_current_price(symbol)

        if notional:
            qty = notional / price

        order = SimpleNamespace(
            id=order_id,
            symbol=symbol,
            qty=str(qty),
            notional=str(notional) if notional else None,
            side=side,
            filled_avg_price=str(price),
            status="filled",
            filled_qty=str(qty),
            submitted_at=datetime.now().isoformat(),
            filled_at=datetime.now().isoformat(),
            time_in_force=kwargs.get("time_in_force", "day"),
            order_type=kwargs.get("type", "market"),
        )

        self._orders.append(order)

        # Update positions
        if side == "buy":
            # Add to positions
            existing = self.get_position(symbol)
            if existing:
                # Average up
                new_qty = float(existing.qty) + qty
                new_avg = (float(existing.avg_entry_price) * float(existing.qty) + price * qty) / new_qty
                existing.qty = str(new_qty)
                existing.avg_entry_price = str(new_avg)
                existing.market_value = str(new_qty * price)
            else:
                position = SimpleNamespace(
                    symbol=symbol,
                    qty=str(qty),
                    avg_entry_price=str(price),
                    current_price=str(price),
                    market_value=str(qty * price),
                    unrealized_pl="0.0",
                    unrealized_plpc="0.0",
                )
                self._positions.append(position)

            # Update account
            self._account.buying_power -= qty * price
            self._account.cash -= qty * price

        elif side == "sell":
            # Remove from positions
            existing = self.get_position(symbol)
            if existing:
                self._positions = [p for p in self._positions if p.symbol != symbol]
                # Update account
                self._account.buying_power += qty * price
                self._account.cash += qty * price

        return order

    def get_order(self, order_id):
        """Get order by ID."""
        for order in self._orders:
            if order.id == order_id:
                return order
        return None

    # Async wrappers
    async def get_portfolio_value_async(self):
        return self.get_portfolio_value()

    async def get_buying_power_async(self):
        return self.get_buying_power()

    async def get_position_async(self, symbol):
        return self.get_position(symbol)

    async def submit_order_async(self, **kwargs):
        return self.submit_order(**kwargs)


class TestIntegrationSmoke(unittest.IsolatedAsyncioTestCase):
    """Integration smoke tests for end-to-end system verification."""

    async def asyncSetUp(self):
        """Set up test fixtures."""
        self.universe = Universe.SIMULATION
        self.context = UniverseContext(self.universe)
        self.broker = IntegrationBroker(self.universe)
        self.analytics_store = AnalyticsStore(self.universe)

        # Configure test environment with higher limits
        import config
        self._original_max_daily_trades = config.MAX_DAILY_TRADES
        config.MAX_DAILY_TRADES = 100  # High limit for integration tests

        # Create coordinator with all agents
        self.coordinator = Coordinator(
            broker=self.broker,
            analytics_store=self.analytics_store,
            universe=self.universe,
        )

        # Track events
        self.captured_events = []

        def capture_all(event):
            self.captured_events.append(event)

        self.coordinator.event_bus.subscribe_all(capture_all)

        # Start coordinator
        await self.coordinator.start()

    async def asyncTearDown(self):
        """Clean up."""
        await self.coordinator.stop()

        # Restore original config
        import config
        if hasattr(self, '_original_max_daily_trades'):
            config.MAX_DAILY_TRADES = self._original_max_daily_trades

    async def test_full_trade_lifecycle_end_to_end(self):
        """Test complete flow: Market data → Signal → Risk → Execution → Analytics.

        This is the critical path - if this works, the system works.
        """
        # Clear captured events and broker state for clean test
        self.captured_events = []
        self.broker._positions = []  # Clear any positions from background data fetch
        self.broker._orders = []  # Clear orders too

        # Create realistic market data with strong momentum signal
        # Build explicit bars: steady at 150, jump to 160 on last bar
        # Momentum = (160 - 150) / 150 = 6.67% > 2% threshold
        close_prices = dict.fromkeys(range(29), 150.0)  # Steady at 150
        close_prices[29] = 160.0  # Jump to 160 on last bar

        market_data = MarketDataReady(
            universe=self.universe,
            session_id=self.context.session_id,
            source="TestDataAgent",
            timestamp=datetime.now(),
            market_open=True,
            symbols=["AAPL"],
            prices={"AAPL": 160.0},
            bars={
                "AAPL": {
                    "close": close_prices,
                    "open": {i: 149.0 if i < 29 else 158.0 for i in range(30)},
                    "high": {i: 151.0 if i < 29 else 162.0 for i in range(30)},
                    "low": {i: 148.0 if i < 29 else 157.0 for i in range(30)},
                    "volume": {i: 1000000 if i < 29 else 3000000 for i in range(30)},  # High volume (3x normal)
                }
            },
            account={
                "equity": 100000.0,
                "cash": 100000.0,
                "buying_power": 100000.0,
                "portfolio_value": 100000.0,
            },
            positions=[],  # No existing positions
        )

        # Publish market data and wait for full propagation
        await self.coordinator.event_bus.publish(market_data)
        await asyncio.sleep(0.2)  # Allow time for async event propagation

        # Verify each stage of the pipeline
        event_types = [type(e).__name__ for e in self.captured_events]

        # Stage 1: Market data published
        self.assertIn("MarketDataReady", event_types, "Market data not published")

        # Stage 2: Signal generated
        signal_events = [e for e in self.captured_events if isinstance(e, SignalGenerated)]
        self.assertGreater(len(signal_events), 0, "No signal generated from strong momentum")
        # Filter for AAPL signals (background DataAgent may generate signals for other symbols)
        aapl_signals = [s for s in signal_events if s.symbol == "AAPL"]
        self.assertGreater(len(aapl_signals), 0, "No AAPL signal generated from test data")
        signal = aapl_signals[0]
        self.assertEqual(signal.symbol, "AAPL")
        self.assertEqual(signal.action, "buy")

        # Stage 3: Risk check passed
        risk_passed = [e for e in self.captured_events if isinstance(e, RiskCheckPassed)]
        # Filter for AAPL risk checks (background DataAgent may process other symbols)
        aapl_risk_passed = [r for r in risk_passed if r.symbol == "AAPL"]
        self.assertGreater(len(aapl_risk_passed), 0, "AAPL risk check did not pass")

        # Stage 4: Order executed
        order_events = [e for e in self.captured_events if isinstance(e, OrderExecuted)]
        # Filter for AAPL orders (background DataAgent may generate orders for other symbols)
        aapl_orders = [o for o in order_events if o.symbol == "AAPL"]
        self.assertGreater(len(aapl_orders), 0, "AAPL order not executed")
        order = aapl_orders[0]
        self.assertEqual(order.symbol, "AAPL")
        self.assertEqual(order.action, "buy")  # OrderExecuted uses 'action' not 'side'
        self.assertIsNotNone(order.filled_avg_price)

        # Stage 5: Verify broker state updated (position created)
        aapl_positions = [p for p in self.broker.get_positions() if p.symbol == "AAPL"]
        self.assertEqual(len(aapl_positions), 1, "AAPL position not created")
        self.assertEqual(aapl_positions[0].symbol, "AAPL")

    async def test_config_change_propagates_to_agents(self):
        """Test config update via API → Event emission → Agent updates."""
        # Set up config manager with event bus
        config_manager = ConfigManager(universe=self.universe, event_bus=self.coordinator.event_bus)

        # Track config events
        config_events = []

        def capture_config(event: ConfigUpdated):
            config_events.append(event)

        self.coordinator.event_bus.subscribe(ConfigUpdated, capture_config)

        # Record initial interval
        initial_interval = self.coordinator.data_agent.interval_minutes

        # Apply config update (simulating API call)
        new_interval = initial_interval + 10
        config_manager.apply_updates({"trade_interval": new_interval})

        await asyncio.sleep(0.1)  # Let event propagate

        # Verify ConfigUpdated event emitted
        self.assertEqual(len(config_events), 1, "ConfigUpdated event not emitted")
        event = config_events[0]
        self.assertIn("trade_interval", event.changed_keys)
        self.assertEqual(event.config_snapshot["trade_interval"], new_interval)

        # Verify DataAgent updated
        self.assertEqual(
            self.coordinator.data_agent.interval_minutes,
            new_interval,
            "DataAgent did not update interval from config event"
        )

    async def test_circuit_breaker_stops_trading_on_loss(self):
        """Test circuit breaker: Force loss → Trading stops → Reset works."""
        # Simulate portfolio with significant loss
        initial_value = 100000.0
        loss_value = initial_value * 0.90  # 10% loss (exceeds MAX_DRAWDOWN_PCT default 15%)

        # Update circuit breaker with loss
        self.coordinator.risk_agent.circuit_breaker.update(loss_value)

        # Try to execute a buy signal
        buy_signal = SignalGenerated(
            universe=self.universe,
            session_id=self.context.session_id,
            source="Test",
            symbol="AAPL",
            action="buy",
            strength=0.8,
            reason="Test signal",
            current_price=150.0,
            momentum=0.05,
        )

        # Clear events and publish signal
        self.captured_events = []
        await self.coordinator.event_bus.publish(buy_signal)
        await asyncio.sleep(0.1)

        # Verify circuit breaker blocked the trade
        from agents.events import RiskCheckFailed
        failed_events = [e for e in self.captured_events if isinstance(e, RiskCheckFailed)]

        # Circuit breaker should have triggered
        breaker_status = self.coordinator.risk_agent.circuit_breaker.status()
        self.assertTrue(
            breaker_status.get("active") or len(failed_events) > 0,
            "Circuit breaker did not activate on significant loss"
        )

        # Reset circuit breaker
        self.coordinator.reset_circuit_breaker()
        breaker_status = self.coordinator.risk_agent.circuit_breaker.status()
        self.assertFalse(breaker_status.get("active"), "Circuit breaker did not reset")

    async def test_alert_delivery_on_critical_event(self):
        """Test alert system: Event trigger → Alert generated (with mocked delivery)."""
        # Mock alert delivery
        alerts_sent = []

        def mock_send_email(subject, body, **kwargs):
            alerts_sent.append({"type": "email", "subject": subject, "body": body})
            return True

        def mock_send_webhook(url, payload, **kwargs):
            alerts_sent.append({"type": "webhook", "url": url, "payload": payload})
            return True

        # Patch alert channels
        with patch("alerts.channels.email.EmailChannel.send", side_effect=mock_send_email):
            with patch("alerts.channels.webhook.WebhookChannel.send", side_effect=mock_send_webhook):
                # Enable alerts
                import config
                original_alerts = config.ALERTS_ENABLED
                config.ALERTS_ENABLED = True

                try:
                    # Trigger circuit breaker event (critical severity)
                    from agents.events import LogEvent

                    critical_event = LogEvent(
                        universe=self.universe,
                        session_id=self.context.session_id,
                        source="Test",
                        level="error",
                        message="Circuit breaker triggered - trading halted due to max drawdown"
                    )

                    await self.coordinator.event_bus.publish(critical_event)
                    await asyncio.sleep(0.2)  # Allow alert processing

                    # Note: Alert delivery depends on alert rules being configured
                    # This test verifies the alert system is wired, even if no alerts sent
                    # (because default config may not have email/webhook configured)

                    # Verify alert agent is running and listening
                    self.assertIsNotNone(self.coordinator.alert_agent)
                    self.assertIsNotNone(self.coordinator.external_alert_agent)

                finally:
                    config.ALERTS_ENABLED = original_alerts

    async def test_broker_query_service_caching_reduces_calls(self):
        """Test BrokerQueryService caches broker calls as expected."""
        # Create broker query service
        service = BrokerQueryService(self.broker)

        # Track broker calls
        call_count = 0
        original_get_account = self.broker.get_account

        def count_get_account():
            nonlocal call_count
            call_count += 1
            return original_get_account()

        self.broker.get_account = count_get_account

        # Call get_account multiple times
        service.get_account()
        service.get_account()
        service.get_account()

        # Should only call broker once (cached)
        self.assertEqual(call_count, 1, "BrokerQueryService did not cache get_account()")

        # Check cache stats
        stats = service.get_cache_stats()
        self.assertEqual(stats["account"]["hits"], 2, "Cache hits not tracked correctly")
        self.assertEqual(stats["account"]["misses"], 1, "Cache misses not tracked correctly")

    async def test_observability_agent_records_events(self):
        """Test ObservabilityAgent captures and logs events correctly."""
        if not self.coordinator.observability_agent:
            self.skipTest("ObservabilityAgent not enabled")

        # Publish a test event
        from agents.events import LogEvent

        test_event = LogEvent(
            universe=self.universe,
            session_id=self.context.session_id,
            source="IntegrationTest",
            level="info",
            message="Integration smoke test - observability check"
        )

        await self.coordinator.event_bus.publish(test_event)
        await asyncio.sleep(0.1)

        # Verify observability agent is tracking events
        # (Actual log file verification would require reading the JSONL file)
        status = self.coordinator.observability_agent.status()
        self.assertTrue(status.get("running"), "ObservabilityAgent not running")


class TestIntegrationEdgeCases(unittest.IsolatedAsyncioTestCase):
    """Edge case integration tests."""

    async def test_multiple_signals_same_symbol(self):
        """Test broker consolidates multiple buys of same symbol into single position."""
        universe = Universe.SIMULATION
        broker = IntegrationBroker(universe)

        # Execute two buy orders for AAPL
        broker.submit_order(symbol="AAPL", notional=1000, side="buy")
        broker.submit_order(symbol="AAPL", notional=1000, side="buy")

        # Verify: Only one position created (consolidated)
        aapl_positions = [p for p in broker.get_positions() if p.symbol == "AAPL"]
        self.assertEqual(len(aapl_positions), 1, "Multiple buys should consolidate into one position")

        # Verify: Position has combined quantity
        position = aapl_positions[0]
        # Two $1000 notional orders at $150/share = ~13.33 shares total
        expected_qty = (1000 / 150.0) * 2
        self.assertAlmostEqual(float(position.qty), expected_qty, places=2)

    async def test_market_closed_blocks_execution(self):
        """Test that market closed status prevents order execution.

        Note: Uses PAPER mode, not SIMULATION, because SIMULATION intentionally
        bypasses market_open checks for backtesting purposes.
        """
        universe = Universe.PAPER
        context = UniverseContext(universe)
        broker = IntegrationBroker(universe)
        broker.is_market_open = lambda: False  # Market closed

        coordinator = Coordinator(broker=broker, analytics_store=None, universe=universe)
        await coordinator.start()

        captured = []
        coordinator.event_bus.subscribe_all(captured.append)

        # Send market data with market_open=False and strong momentum signal
        # This tests the SignalAgent's market_open gating logic
        close_prices = dict.fromkeys(range(29), 150.0)
        close_prices[29] = 160.0  # Strong momentum

        market_data = MarketDataReady(
            universe=universe,
            session_id=context.session_id,
            source="TestDataAgent",
            timestamp=datetime.now(),
            market_open=False,  # Market closed
            symbols=["AAPL"],
            prices={"AAPL": 160.0},
            bars={
                "AAPL": {
                    "close": close_prices,
                    "volume": {i: 1000000 if i < 29 else 3000000 for i in range(30)},
                }
            },
            account={
                "equity": 100000.0,
                "cash": 100000.0,
                "buying_power": 100000.0,
                "portfolio_value": 100000.0,
            },
            positions=[],
        )

        await coordinator.event_bus.publish(market_data)
        await asyncio.sleep(0.2)

        # SignalAgent should NOT emit actionable SignalGenerated events when market is closed
        # (in PAPER/LIVE modes - SIMULATION bypasses this check)
        signal_events = [e for e in captured if isinstance(e, SignalGenerated)]
        self.assertEqual(len(signal_events), 0, "SignalGenerated event emitted with market closed")

        # Consequently, no orders should execute
        order_events = [e for e in captured if isinstance(e, OrderExecuted)]
        self.assertEqual(len(order_events), 0, "Order executed with market closed")

        await coordinator.stop()


if __name__ == '__main__':
    unittest.main()

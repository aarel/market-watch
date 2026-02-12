"""
Integration test for full trade lifecycle.

Tests the complete flow:
1. MarketDataReady event published
2. SignalAgent generates signals
3. RiskAgent checks risk
4. ExecutionAgent executes order
5. AnalyticsAgent captures trade
6. All events flow through EventBus correctly
"""
import unittest
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from agents.analytics_agent import AnalyticsAgent
from agents.event_bus import EventBus
from agents.events import (
    MarketDataReady,
    OrderExecuted,
    RiskCheckFailed,
    RiskCheckPassed,
    SignalGenerated,
)
from agents.execution_agent import ExecutionAgent
from agents.risk_agent import RiskAgent
from agents.signal_agent import SignalAgent
from strategies.momentum import MomentumStrategy
from universe import Universe, UniverseContext

pytestmark = [pytest.mark.integration, pytest.mark.whitebox]


class InMemoryAnalyticsStore:
    """In-memory store for testing."""
    def __init__(self):
        self.trades = []
        self.equity = []

    def record_trade(self, trade):
        self.trades.append(trade)

    def record_equity(self, snapshot):
        self.equity.append(snapshot)


class MockBroker:
    """Mock broker for testing trade flow."""
    def __init__(self, universe: Universe):
        self.universe = universe
        self._positions = []
        self._orders = []
        self._next_order_id = 1

    def get_account(self):
        """Return mock account with sufficient funds."""
        return type('Account', (), {
            'equity': '100000.0',
            'portfolio_value': '100000.0',
            'cash': '100000.0',
            'buying_power': '100000.0',
        })()

    def get_positions(self):
        """Return current positions."""
        return self._positions

    def get_position(self, symbol):
        """Get position for symbol."""
        for pos in self._positions:
            if pos.symbol == symbol:
                return pos
        return None

    def get_portfolio_value(self):
        """Get total portfolio value."""
        return 100000.0

    def get_buying_power(self):
        """Get available buying power."""
        return 100000.0

    def get_bars(self, symbol, timeframe='1Day', limit=30, days=None):
        """Get historical bars for RVOL calculation (returns empty for mock)."""
        return []

    # Async wrappers (for non-blocking agent calls)
    async def get_portfolio_value_async(self):
        return self.get_portfolio_value()

    async def get_buying_power_async(self):
        return self.get_buying_power()

    async def get_position_async(self, symbol):
        return self.get_position(symbol)

    async def submit_order_async(self, **kwargs):
        return self.submit_order(**kwargs)

    def submit_order(self, symbol, qty=None, notional=None, side='buy', **kwargs):
        """Submit order and return mock order object."""
        order_id = f"order_{self._next_order_id}"
        self._next_order_id += 1

        # Create mock order object
        order = type('Order', (), {
            'id': order_id,
            'symbol': symbol,
            'qty': str(qty) if qty else None,
            'notional': str(notional) if notional else None,
            'side': side,
            'filled_avg_price': '150.50',  # Mock fill price
            'status': 'filled',
            'submitted_at': datetime.now().isoformat(),
            'filled_at': datetime.now().isoformat(),
            'time_in_force': kwargs.get('time_in_force', 'day'),
            'order_type': kwargs.get('type', 'market'),
        })()

        self._orders.append(order)
        return order


class TestTradeLifecycleIntegration(unittest.IsolatedAsyncioTestCase):
    """Integration tests for complete trade lifecycle."""

    async def asyncSetUp(self):
        """Set up test environment with all agents."""
        self.universe = Universe.SIMULATION
        self.context = UniverseContext(self.universe)
        self.event_bus = EventBus(self.context)
        self.broker = MockBroker(self.universe)
        self.analytics_store = InMemoryAnalyticsStore()

        # Track published events
        self.published_events = []

        # Subscribe to all events for verification
        def track_event(event):
            self.published_events.append(event)

        self.event_bus.subscribe_all(track_event)

        # Create strategy with low threshold to ensure signal generation
        self.strategy = MomentumStrategy(
            lookback_days=1,
            momentum_threshold=0.01,  # Very low threshold
            sell_threshold=-0.01,
            stop_loss_pct=5.0,
        )

        # Create agents (they get universe from event_bus.context)
        self.signal_agent = SignalAgent(
            self.event_bus,
            self.broker,
            strategy=self.strategy,
        )

        self.risk_agent = RiskAgent(
            self.event_bus,
            self.broker,
        )

        self.execution_agent = ExecutionAgent(
            self.event_bus,
            self.broker,
            risk_agent=self.risk_agent,
        )

        self.analytics_agent = AnalyticsAgent(
            self.event_bus,
            self.broker,
            self.analytics_store,
        )

        # Start all agents
        await self.signal_agent.start()
        await self.risk_agent.start()
        await self.execution_agent.start()
        await self.analytics_agent.start()

    async def asyncTearDown(self):
        """Clean up agents."""
        await self.signal_agent.stop()
        await self.risk_agent.stop()
        await self.execution_agent.stop()
        await self.analytics_agent.stop()

    async def test_full_trade_lifecycle_buy_signal(self):
        """Test complete flow from market data to analytics capture (buy signal)."""
        # Create market data with strong momentum signal
        # Note: MarketDataReady expects symbols as list of strings, not dicts
        market_data_event = MarketDataReady(
            universe=self.universe,
            session_id=self.context.session_id,
            timestamp=datetime.now(),
            source="TestDataAgent",
            market_open=True,
            symbols=['AAPL'],  # List of symbol strings
            prices={'AAPL': 160.0},  # Symbol -> price mapping
            bars={
                'AAPL': {  # Historical bars for strategy (index -> value mapping)
                    'close': {0: 150.0, 1: 152.0, 2: 155.0, 3: 160.0},  # Upward trend
                    'volume': {0: 1000000, 1: 1100000, 2: 1200000, 3: 1300000},
                }
            },
            account={
                'equity': 100000.0,
                'cash': 100000.0,
                'buying_power': 100000.0,
                'portfolio_value': 100000.0,
            }
        )

        # Clear tracked events
        self.published_events = []

        # Publish market data event
        await self.event_bus.publish(market_data_event)

        # Wait for event propagation (all agents are async)
        import asyncio
        await asyncio.sleep(0.1)

        # Verify the complete event flow
        event_types = [type(e).__name__ for e in self.published_events]

        # 1. MarketDataReady should be published
        self.assertIn('MarketDataReady', event_types)

        # 2. SignalGenerated should be published (SignalAgent processes market data)
        signal_events = [e for e in self.published_events if isinstance(e, SignalGenerated)]
        self.assertGreater(len(signal_events), 0, "No signal generated from market data")

        signal_event = signal_events[0]
        self.assertEqual(signal_event.symbol, 'AAPL')
        self.assertEqual(signal_event.action, 'buy')

        # 3. RiskCheckPassed should be published (RiskAgent approves signal)
        risk_passed_events = [e for e in self.published_events if isinstance(e, RiskCheckPassed)]
        self.assertGreater(len(risk_passed_events), 0, "Risk check did not pass")

        # 4. OrderExecuted should be published (ExecutionAgent executes)
        order_executed_events = [e for e in self.published_events if isinstance(e, OrderExecuted)]
        self.assertGreater(len(order_executed_events), 0, "Order was not executed")

        order_event = order_executed_events[0]
        self.assertEqual(order_event.symbol, 'AAPL')
        self.assertEqual(order_event.action, 'buy')
        self.assertIsNotNone(order_event.filled_avg_price)

        # 5. AnalyticsAgent should have captured the trade
        self.assertEqual(len(self.analytics_store.trades), 1)

        trade = self.analytics_store.trades[0]
        self.assertEqual(trade['symbol'], 'AAPL')
        self.assertEqual(trade['side'], 'buy')
        self.assertIsNotNone(trade['filled_avg_price'])
        self.assertIsNotNone(trade['order_id'])

        # 6. AnalyticsAgent should have captured equity snapshot
        self.assertGreater(len(self.analytics_store.equity), 0)
        equity_snapshot = self.analytics_store.equity[0]
        self.assertIn('equity', equity_snapshot)
        self.assertIn('cash', equity_snapshot)

    async def test_risk_check_failure_blocks_execution(self):
        """Test that failed risk check prevents execution and analytics capture."""
        import config
        # Force risk rejection by hitting max open positions limit
        self.broker._positions = [object() for _ in range(config.MAX_OPEN_POSITIONS)]

        # Create market data with signal
        market_data_event = MarketDataReady(
            universe=self.universe,
            session_id=self.context.session_id,
            timestamp=datetime.now(),
            source="TestDataAgent",
            market_open=True,
            symbols=['TSLA'],
            prices={'TSLA': 200.0},
            bars={
                'TSLA': {
                    'close': {0: 190.0, 1: 195.0, 2: 198.0, 3: 200.0},
                    'volume': {0: 1000000, 1: 1100000, 2: 1200000, 3: 1300000},
                }
            },
            account={
                'equity': 100000.0,
                'cash': 100000.0,
                'buying_power': 100000.0,
                'portfolio_value': 100000.0,
            }
        )

        # Clear tracked events
        self.published_events = []
        initial_trade_count = len(self.analytics_store.trades)

        # Publish market data event
        await self.event_bus.publish(market_data_event)

        # Wait for event propagation
        import asyncio
        await asyncio.sleep(0.1)

        # Debug: print what events we got
        event_types = [type(e).__name__ for e in self.published_events]

        # Check if signal was generated
        signal_events = [e for e in self.published_events if isinstance(e, SignalGenerated)]
        self.assertGreater(len(signal_events), 0, "Signal should be generated for risk rejection test")

        # Verify risk check failed
        risk_failed_events = [e for e in self.published_events if isinstance(e, RiskCheckFailed)]
        self.assertGreater(len(risk_failed_events), 0,
                          f"Risk check should have failed. Got events: {event_types}")

        # Verify NO order was executed
        order_executed_events = [e for e in self.published_events if isinstance(e, OrderExecuted)]
        self.assertEqual(len(order_executed_events), 0, "Order should not have been executed")

        # Verify NO new trade in analytics
        self.assertEqual(len(self.analytics_store.trades), initial_trade_count,
                        "No trade should be recorded when risk check fails")

    async def test_event_bus_delivers_to_all_agents(self):
        """Test that EventBus delivers events to all subscribed agents."""
        # Create a simple event
        test_event = MarketDataReady(
            universe=self.universe,
            session_id=self.context.session_id,
            timestamp=datetime.now(),
            source="TestAgent",
            market_open=True,
            symbols=[],
            account={'equity': 100000.0}
        )

        # Clear tracked events
        self.published_events = []

        # Publish event
        await self.event_bus.publish(test_event)

        # Wait for propagation
        import asyncio
        await asyncio.sleep(0.05)

        # Verify all agents received it (all subscribe to MarketDataReady)
        # At minimum, the event should be in our tracked list
        self.assertGreater(len(self.published_events), 0)

        # Find the MarketDataReady event
        market_data_events = [e for e in self.published_events if isinstance(e, MarketDataReady)]
        self.assertGreater(len(market_data_events), 0)


class TestTradeLifecycleEdgeCases(unittest.IsolatedAsyncioTestCase):
    """Edge case tests for trade lifecycle."""

    async def test_no_signal_when_market_closed(self):
        """Test that no signals are generated when market is closed."""
        universe = Universe.SIMULATION
        context = UniverseContext(universe)
        event_bus = EventBus(context)
        broker = MockBroker(universe)

        strategy = MomentumStrategy(momentum_threshold=0.01)
        signal_agent = SignalAgent(event_bus, broker, strategy=strategy)

        await signal_agent.start()

        # Track signals
        signals_generated = []
        def track_signal(event):
            signals_generated.append(event)
        event_bus.subscribe(SignalGenerated, track_signal)

        # Publish market data with market_open=False
        market_data_event = MarketDataReady(
            universe=universe,
            session_id=context.session_id,
            timestamp=datetime.now(),
            source="TestAgent",
            market_open=False,  # Market closed
            symbols=['AAPL'],
            prices={'AAPL': 150.0},
            bars={'AAPL': {'close': {0: 140, 1: 145, 2: 148, 3: 150}, 'volume': {0: 1000000, 1: 1000000, 2: 1000000, 3: 1000000}}},
            account={'equity': 100000.0}
        )

        await event_bus.publish(market_data_event)

        import asyncio
        await asyncio.sleep(0.05)

        # Verify no signals generated
        self.assertEqual(len(signals_generated), 0, "No signals should be generated when market is closed")

        await signal_agent.stop()


if __name__ == "__main__":
    unittest.main()

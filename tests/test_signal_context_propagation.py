"""Tests for signal context propagation through the auto-trade pipeline.

Verifies that signal_reason, signal_strength, and signal_momentum flow from
SignalGenerated → RiskCheckPassed → OrderExecuted → trade record.
"""
import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from agents.event_bus import EventBus
from agents.events import MarketDataReady, OrderExecuted, RiskCheckPassed, SignalGenerated
from agents.risk_agent import RiskAgent
from universe import Universe, UniverseContext

# Import AnalyticsAgent last — it pulls in server.domain which triggers a
# server → agents → server circular import when agents/__init__.py hasn't
# finished loading. Importing after event_bus/events/risk_agent avoids this
# because agents/__init__.py will have already re-exported those names.
from agents.analytics_agent import AnalyticsAgent  # noqa: E402


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

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


class DummyBroker:
    def get_positions(self):
        return []

    async def get_portfolio_value_async(self):
        return 100_000.0

    async def get_buying_power_async(self):
        return 100_000.0

    async def get_position_async(self, symbol):
        return None

    def get_bars(self, symbol, *args, **kwargs):
        return []


class DummyCircuitBreaker:
    def update(self, equity):
        return False, None

    def status(self):
        return {"active": False}


# ---------------------------------------------------------------------------
# AnalyticsAgent: signal fields persist to trade record
# ---------------------------------------------------------------------------

class TestSignalContextInTradeRecord(unittest.IsolatedAsyncioTestCase):
    """AnalyticsAgent must write signal fields into the trade record."""

    async def _make_agent(self):
        store = InMemoryStore()
        bus = DummyEventBus()
        agent = AnalyticsAgent(bus, broker=None, store=store)
        await agent.start()
        return agent, store

    async def test_auto_trade_signal_fields_persisted(self):
        agent, store = await self._make_agent()

        evt = OrderExecuted(
            universe=Universe.SIMULATION,
            session_id="sess-1",
            symbol="AAPL",
            action="buy",
            qty=10,
            filled_avg_price=150.0,
            notional=1500.0,
            order_id="ord-1",
            status="filled",
            signal_reason="Momentum crossed 2.3%, above 2.0% threshold",
            signal_strength=0.75,
            signal_momentum=0.023,
        )
        await agent._handle_order_executed(evt)

        self.assertEqual(len(store.trades), 1)
        trade = store.trades[0]
        self.assertEqual(trade["signal_reason"], "Momentum crossed 2.3%, above 2.0% threshold")
        self.assertAlmostEqual(trade["signal_strength"], 0.75)
        self.assertAlmostEqual(trade["signal_momentum"], 0.023)

    async def test_manual_trade_signal_fields_default_to_empty(self):
        """Manual trades emit OrderExecuted without signal context — fields default to empty."""
        agent, store = await self._make_agent()

        evt = OrderExecuted(
            universe=Universe.SIMULATION,
            session_id="sess-2",
            symbol="TSLA",
            action="buy",
            qty=5,
            filled_avg_price=200.0,
            notional=1000.0,
            order_id="ord-2",
            status="filled",
            # No signal fields supplied — must default cleanly
        )
        await agent._handle_order_executed(evt)

        self.assertEqual(len(store.trades), 1)
        trade = store.trades[0]
        self.assertEqual(trade["signal_reason"], "")
        self.assertAlmostEqual(trade["signal_strength"], 0.0)
        self.assertAlmostEqual(trade["signal_momentum"], 0.0)

    async def test_market_context_populated_after_market_data_event(self):
        """Trade record contains market_context when MarketDataReady fired first."""
        agent, store = await self._make_agent()

        market_evt = MarketDataReady(
            universe=Universe.SIMULATION,
            session_id="sess-mc-1",
            market_open=True,
            market_indices=[{"symbol": "SPY", "price": 500.0}],
            top_gainers=[{"symbol": "AAPL"}, {"symbol": "TSLA"}],
            account={"cash": 10000, "equity": 10000,
                     "portfolio_value": 10000, "buying_power": 10000},
        )
        await agent._handle_market_data(market_evt)

        order_evt = OrderExecuted(
            universe=Universe.SIMULATION,
            session_id="sess-mc-1",
            symbol="AAPL",
            action="buy",
            qty=5,
            filled_avg_price=150.0,
            notional=750.0,
            order_id="ord-mc-1",
            status="filled",
        )
        await agent._handle_order_executed(order_evt)

        self.assertEqual(len(store.trades), 1)
        ctx = store.trades[0]["market_context"]
        self.assertTrue(ctx["market_open"])
        self.assertEqual(ctx["top_gainer_count"], 2)
        self.assertEqual(len(ctx["index_levels"]), 1)
        self.assertEqual(ctx["index_levels"][0]["symbol"], "SPY")
        self.assertIn("snapshot_timestamp", ctx)

    async def test_market_context_empty_when_no_market_data_fired(self):
        """Trade record has market_context={} when no MarketDataReady has fired yet."""
        agent, store = await self._make_agent()

        order_evt = OrderExecuted(
            universe=Universe.SIMULATION,
            session_id="sess-mc-2",
            symbol="MSFT",
            action="buy",
            qty=3,
            filled_avg_price=400.0,
            notional=1200.0,
            order_id="ord-mc-2",
            status="filled",
        )
        await agent._handle_order_executed(order_evt)

        self.assertEqual(len(store.trades), 1)
        self.assertEqual(store.trades[0]["market_context"], {})


# ---------------------------------------------------------------------------
# RiskCheckPassed carries signal context from SignalGenerated
# ---------------------------------------------------------------------------

class AlwaysPassChecker:
    """Stub checker that always approves."""
    def check(self, *args, **kwargs):
        return True


class TestRiskAgentSignalContextPassThrough(unittest.IsolatedAsyncioTestCase):
    """RiskAgent._pass() must copy signal fields onto RiskCheckPassed."""

    async def test_risk_check_passed_carries_signal_fields(self):
        context = UniverseContext(Universe.SIMULATION)
        bus = EventBus(context)
        broker = DummyBroker()

        captured = []
        bus.subscribe(RiskCheckPassed, lambda e: captured.append(e))

        agent = RiskAgent(
            bus,
            broker,
            circuit_breaker=DummyCircuitBreaker(),
            sector_exposure_checker=AlwaysPassChecker(),
            correlation_exposure_checker=AlwaysPassChecker(),
            rvol_checker=AlwaysPassChecker(),
        )

        signal = SignalGenerated(
            universe=context.universe,
            session_id=context.session_id,
            source="SignalAgent",
            symbol="AAPL",
            action="buy",
            strength=0.8,
            reason="RSI oversold at 28.5",
            current_price=150.0,
            momentum=0.031,
        )

        with patch("config.MAX_DAILY_TRADES", 10), \
             patch("config.MAX_POSITION_PCT", 0.1), \
             patch("config.MIN_TRADE_VALUE", 1.0), \
             patch("config.MAX_OPEN_POSITIONS", 10):
            await agent._handle_signal(signal)

        self.assertEqual(len(captured), 1)
        passed = captured[0]
        self.assertEqual(passed.signal_reason, "RSI oversold at 28.5")
        self.assertAlmostEqual(passed.signal_strength, 0.8)
        self.assertAlmostEqual(passed.signal_momentum, 0.031)


# ---------------------------------------------------------------------------
# OrderExecuted event: new fields have correct defaults
# ---------------------------------------------------------------------------

class TestOrderExecutedDefaults(unittest.TestCase):
    """OrderExecuted signal fields must default to empty/zero (no KeyError)."""

    def test_defaults_present(self):
        evt = OrderExecuted(
            universe=Universe.SIMULATION,
            session_id="sess-3",
            symbol="MSFT",
            action="sell",
            order_id="ord-3",
            status="filled",
        )
        self.assertEqual(evt.signal_reason, "")
        self.assertAlmostEqual(evt.signal_strength, 0.0)
        self.assertAlmostEqual(evt.signal_momentum, 0.0)

    def test_fields_set_when_provided(self):
        evt = OrderExecuted(
            universe=Universe.SIMULATION,
            session_id="sess-4",
            symbol="MSFT",
            action="buy",
            order_id="ord-4",
            status="filled",
            signal_reason="Breakout above 20-day high",
            signal_strength=0.6,
            signal_momentum=0.015,
        )
        self.assertEqual(evt.signal_reason, "Breakout above 20-day high")
        self.assertAlmostEqual(evt.signal_strength, 0.6)
        self.assertAlmostEqual(evt.signal_momentum, 0.015)

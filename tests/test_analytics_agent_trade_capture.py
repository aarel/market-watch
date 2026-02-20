import types
import unittest
from datetime import datetime
from unittest.mock import Mock, patch

import config
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
        # PHASE R2: Pipeline is now mandatory - toggle removed
        # PHASE R2: ENABLE_REALISM_PIPELINE toggle removed (always True)
        try:
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
                status="filled",  # Required for analytics filtering
            )
            await agent._handle_order_executed(evt)
            self.assertEqual(len(store.trades), 1)
            trade = store.trades[0]
            self.assertEqual(trade["symbol"], "AAPL")
            self.assertEqual(trade["side"], "buy")
            self.assertAlmostEqual(trade["filled_avg_price"], 5.5)
            self.assertAlmostEqual(trade["notional"], 11.0)
            self.assertEqual(trade["order_id"], "abc")
            # PHASE R2: Pipeline is now mandatory - all trades have realism fields
            self.assertIn("realism_pipeline_enabled", trade)
            self.assertTrue(trade["realism_pipeline_enabled"])
            self.assertIn("gross_pnl", trade)
            self.assertIn("net_pnl", trade)
            self.assertIn("after_tax_pnl", trade)
            self.assertIn("realized_gain", trade)
            self.assertIn("tax_estimate", trade)
            self.assertIn("settlement_date", trade)
            self.assertIn("fee_breakdown", trade)
            await agent.stop()
        finally:
            pass  # PHASE R2: No cleanup needed

    async def test_realism_pipeline_fields_are_attached(self):
        store = InMemoryStore()
        bus = DummyEventBus()
        # PHASE R2: Pipeline is now mandatory - toggle removed
        # PHASE R2: ENABLE_REALISM_PIPELINE toggle removed (always True)
        try:
            agent = AnalyticsAgent(bus, broker=None, store=store)
            await agent.start()
            buy_evt = OrderExecuted(
                universe=bus._context.universe,
                session_id=bus._context.session_id,
                timestamp=datetime.now(),
                symbol="MSFT",
                action="buy",
                qty=10,
                filled_avg_price=100,
                notional=1000.0,
                order_id="b1",
                status="filled",
            )
            sell_evt = OrderExecuted(
                universe=bus._context.universe,
                session_id=bus._context.session_id,
                timestamp=datetime.now(),
                symbol="MSFT",
                action="sell",
                qty=10,
                filled_avg_price=110,
                notional=1100.0,
                order_id="s1",
                status="filled",
            )
            await agent._handle_order_executed(buy_evt)
            await agent._handle_order_executed(sell_evt)
            self.assertEqual(len(store.trades), 2)
            sell_trade = store.trades[-1]
            self.assertTrue(sell_trade["realism_pipeline_enabled"])
            self.assertIn("gross_pnl", sell_trade)
            self.assertIn("net_pnl", sell_trade)
            self.assertIn("after_tax_pnl", sell_trade)
            self.assertIn("realized_gain", sell_trade)
            self.assertIn("tax_estimate", sell_trade)
            self.assertIn("settlement_date", sell_trade)
            self.assertIn("fee_breakdown", sell_trade)
            await agent.stop()
        finally:
            pass  # PHASE R2: No cleanup needed

    async def test_realism_gate_on_is_deterministic_for_same_event_stream(self):
        store_a = InMemoryStore()
        store_b = InMemoryStore()
        bus = DummyEventBus()
        # PHASE R2: Pipeline is now mandatory - toggle removed
        # PHASE R2: ENABLE_REALISM_PIPELINE toggle removed (always True)
        try:
            fixed_ts = datetime(2026, 1, 7, 10, 0, 0)
            buy_evt = OrderExecuted(
                universe=bus._context.universe,
                session_id=bus._context.session_id,
                timestamp=fixed_ts,
                symbol="MSFT",
                action="buy",
                qty=10,
                filled_avg_price=100,
                notional=1000.0,
                order_id="b1",
                status="filled",
            )
            sell_evt = OrderExecuted(
                universe=bus._context.universe,
                session_id=bus._context.session_id,
                timestamp=fixed_ts,
                symbol="MSFT",
                action="sell",
                qty=10,
                filled_avg_price=110,
                notional=1100.0,
                order_id="s1",
                status="filled",
            )

            agent_a = AnalyticsAgent(bus, broker=None, store=store_a)
            await agent_a.start()
            await agent_a._handle_order_executed(buy_evt)
            await agent_a._handle_order_executed(sell_evt)
            await agent_a.stop()

            agent_b = AnalyticsAgent(bus, broker=None, store=store_b)
            await agent_b.start()
            await agent_b._handle_order_executed(buy_evt)
            await agent_b._handle_order_executed(sell_evt)
            await agent_b.stop()

            a = store_a.trades[-1]
            b = store_b.trades[-1]
            keys = [
                "gross_pnl",
                "net_pnl",
                "after_tax_pnl",
                "realized_gain",
                "tax_estimate",
                "settlement_date",
                "fee_breakdown",
                "fees_total",
                "realism_pipeline_enabled",
            ]
            for key in keys:
                self.assertEqual(a[key], b[key])
        finally:
            pass  # PHASE R2: No cleanup needed

    async def test_realism_processing_exception_persists_trade_and_sets_error_flag(self):
        store = InMemoryStore()
        bus = DummyEventBus()
        # PHASE R2: Pipeline is now mandatory - toggle removed
        # PHASE R2: ENABLE_REALISM_PIPELINE toggle removed (always True)
        try:
            agent = AnalyticsAgent(bus, broker=None, store=store)
            await agent.start()
            agent._performance_engine.process_trade = Mock(side_effect=RuntimeError("boom"))

            evt = OrderExecuted(
                universe=bus._context.universe,
                session_id=bus._context.session_id,
                timestamp=datetime(2026, 1, 7, 10, 0, 0),
                symbol="AAPL",
                action="buy",
                qty=1,
                filled_avg_price=100,
                notional=100.0,
                order_id="err1",
                status="filled",
            )
            await agent._handle_order_executed(evt)
            self.assertEqual(len(store.trades), 1)
            trade = store.trades[0]
            self.assertFalse(trade["realism_pipeline_enabled"])
            self.assertIn("realism_processing_error", trade)
            await agent.stop()
        finally:
            pass  # PHASE R2: No cleanup needed

    async def test_gate_on_uses_single_realism_pnl_source(self):
        store = InMemoryStore()
        bus = DummyEventBus()
        # PHASE R2: Pipeline is now mandatory - toggle removed
        # PHASE R2: ENABLE_REALISM_PIPELINE toggle removed (always True)
        try:
            agent = AnalyticsAgent(bus, broker=None, store=store)
            await agent.start()

            breakdown = types.SimpleNamespace(
                gross_pnl=123.0,
                net_pnl=120.0,
                after_tax_pnl=118.0,
                realized_gain=130.0,
                tax_estimate=2.0,
                settlement_date="2026-01-08",
                fee_breakdown={"total_cost": 3.0, "margin_interest": 0.0},
            )
            mock_proc = Mock(return_value=breakdown)
            agent._performance_engine.process_trade = mock_proc

            evt = OrderExecuted(
                universe=bus._context.universe,
                session_id=bus._context.session_id,
                timestamp=datetime(2026, 1, 7, 10, 0, 0),
                symbol="AAPL",
                action="sell",
                qty=1,
                filled_avg_price=100,
                notional=100.0,
                order_id="pnl1",
                status="filled",
            )
            await agent._handle_order_executed(evt)
            self.assertEqual(mock_proc.call_count, 1)
            trade = store.trades[0]
            self.assertEqual(trade["gross_pnl"], 123.0)
            self.assertEqual(trade["net_pnl"], 120.0)
            self.assertEqual(trade["after_tax_pnl"], 118.0)
            self.assertTrue(trade["realism_pipeline_enabled"])
            await agent.stop()
        finally:
            pass  # PHASE R2: No cleanup needed

    async def test_gate_on_does_not_call_analytics_metrics_pnl_helpers(self):
        store = InMemoryStore()
        bus = DummyEventBus()
        # PHASE R2: Pipeline is now mandatory - toggle removed
        # PHASE R2: ENABLE_REALISM_PIPELINE toggle removed (always True)
        try:
            agent = AnalyticsAgent(bus, broker=None, store=store)
            await agent.start()
            buy_evt = OrderExecuted(
                universe=bus._context.universe,
                session_id=bus._context.session_id,
                timestamp=datetime(2026, 1, 7, 10, 0, 0),
                symbol="MSFT",
                action="buy",
                qty=10,
                filled_avg_price=100,
                notional=1000.0,
                order_id="b1",
                status="filled",
            )
            sell_evt = OrderExecuted(
                universe=bus._context.universe,
                session_id=bus._context.session_id,
                timestamp=datetime(2026, 1, 7, 10, 0, 1),
                symbol="MSFT",
                action="sell",
                qty=10,
                filled_avg_price=110,
                notional=1100.0,
                order_id="s1",
                status="filled",
            )
            with patch("analytics.metrics.compute_trade_outcomes", side_effect=AssertionError("legacy helper used")):
                with patch("analytics.metrics.compute_round_trip_trades", side_effect=AssertionError("legacy helper used")):
                    await agent._handle_order_executed(buy_evt)
                    await agent._handle_order_executed(sell_evt)
            self.assertEqual(len(store.trades), 2)
            self.assertTrue(store.trades[-1]["realism_pipeline_enabled"])
            await agent.stop()
        finally:
            pass  # PHASE R2: No cleanup needed

    async def test_fail_fast_guard_raises_on_unauthorized_pnl_input(self):
        store = InMemoryStore()
        bus = DummyEventBus()
        prior_gate = config.ENABLE_REALISM_PIPELINE
        prior_guard = config.REALISM_FAIL_FAST_PNL_GUARD
        # PHASE R2: ENABLE_REALISM_PIPELINE toggle removed (always True)
        config.REALISM_FAIL_FAST_PNL_GUARD = True
        try:
            agent = AnalyticsAgent(bus, broker=None, store=store)
            with self.assertRaises(RuntimeError) as ctx:
                agent._assert_no_unauthorized_pnl_inputs(
                    {
                        "symbol": "AAPL",
                        "gross_pnl": 1.0,
                    }
                )
            self.assertIn("Unauthorized PnL computation path", str(ctx.exception))
        finally:
            config.ENABLE_REALISM_PIPELINE = prior_gate
            config.REALISM_FAIL_FAST_PNL_GUARD = prior_guard


if __name__ == "__main__":
    unittest.main()

"""Unit tests for analytics.whatif — What-If Analysis engine.

Covers all three scenario types and edge cases:
  - position_sizing: P&L scaling, multiplier=1 (no-op), invalid multiplier
  - stop_loss: loss capping, unaffected wins, invalid pct, missing entry price
  - hold_duration: always-unavailable with clear reason
  - run_what_if: routing, unknown type guard
"""
import unittest

from analytics.whatif import WhatIfResult, run_what_if


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pair(symbol: str = "AAPL", buy_price: float = 100.0,
          sell_price: float = 110.0, qty: float = 10.0,
          pnl: float | None = None) -> dict:
    """Build a minimal round-trip trade pair dict."""
    if pnl is None:
        pnl = (sell_price - buy_price) * qty
    return {
        "symbol": symbol,
        "buy_price": buy_price,
        "sell_price": sell_price,
        "qty": qty,
        "pnl": pnl,
        "timestamp": "2026-01-10T14:00:00+00:00",
    }


def _trade(symbol: str = "AAPL", side: str = "buy",
           filled_avg_price: float = 100.0) -> dict:
    """Build a minimal raw trade dict (pre-pairing)."""
    return {
        "symbol": symbol,
        "side": side,
        "filled_avg_price": filled_avg_price,
        "qty": 10.0,
        "timestamp": "2026-01-10T14:00:00+00:00",
    }


# ---------------------------------------------------------------------------
# position_sizing
# ---------------------------------------------------------------------------

class TestPositionSizing(unittest.TestCase):

    def _run(self, pairs, multiplier):
        """Invoke run_what_if with pre-built pairs by going directly to the
        position_sizing path so we don't have to construct raw trades that will
        be re-paired by compute_round_trip_trades."""
        from analytics.whatif import _run_position_sizing
        return _run_position_sizing(pairs, {"type": "position_sizing", "multiplier": multiplier})

    def test_multiplier_increases_profit(self):
        """A multiplier > 1 scales up a winning trade's P&L."""
        pairs = [_pair(pnl=100.0)]
        result = self._run(pairs, multiplier=2.0)
        self.assertTrue(result.available)
        self.assertAlmostEqual(result.baseline_pnl, 100.0)
        self.assertAlmostEqual(result.scenario_pnl, 200.0)
        self.assertAlmostEqual(result.delta_pnl, 100.0)
        self.assertAlmostEqual(result.delta_pct, 100.0)
        self.assertEqual(result.affected_trade_count, 1)

    def test_multiplier_increases_loss(self):
        """A multiplier > 1 also amplifies a losing trade's P&L magnitude."""
        pairs = [_pair(buy_price=100.0, sell_price=90.0, qty=10.0, pnl=-100.0)]
        result = self._run(pairs, multiplier=2.0)
        self.assertAlmostEqual(result.scenario_pnl, -200.0)
        self.assertAlmostEqual(result.delta_pnl, -100.0)

    def test_multiplier_one_is_noop(self):
        """Multiplier = 1.0 produces zero delta and zero affected trades."""
        pairs = [_pair(pnl=50.0), _pair(pnl=-30.0)]
        result = self._run(pairs, multiplier=1.0)
        self.assertAlmostEqual(result.delta_pnl, 0.0)
        self.assertEqual(result.affected_trade_count, 0)

    def test_fractional_multiplier(self):
        """Multiplier < 1 reduces P&L magnitude proportionally."""
        pairs = [_pair(pnl=200.0)]
        result = self._run(pairs, multiplier=0.5)
        self.assertAlmostEqual(result.scenario_pnl, 100.0)
        self.assertAlmostEqual(result.delta_pnl, -100.0)

    def test_invalid_zero_multiplier(self):
        """Multiplier = 0 returns available=False."""
        pairs = [_pair(pnl=100.0)]
        result = self._run(pairs, multiplier=0)
        self.assertFalse(result.available)
        self.assertIsNotNone(result.unavailable_reason)

    def test_invalid_negative_multiplier(self):
        """Negative multiplier returns available=False."""
        pairs = [_pair(pnl=100.0)]
        result = self._run(pairs, multiplier=-1.5)
        self.assertFalse(result.available)

    def test_multiple_trades_summed(self):
        """baseline_pnl and scenario_pnl are summed across all pairs."""
        pairs = [_pair(pnl=100.0), _pair(pnl=200.0), _pair(pnl=-50.0)]
        result = self._run(pairs, multiplier=2.0)
        self.assertAlmostEqual(result.baseline_pnl, 250.0)
        self.assertAlmostEqual(result.scenario_pnl, 500.0)
        self.assertEqual(result.trade_count, 3)

    def test_empty_trade_list(self):
        """Empty pairs list returns available=True with zero P&L."""
        result = self._run([], multiplier=2.0)
        self.assertTrue(result.available)
        self.assertAlmostEqual(result.baseline_pnl, 0.0)
        self.assertAlmostEqual(result.scenario_pnl, 0.0)
        self.assertEqual(result.trade_count, 0)

    def test_trade_by_trade_length_matches(self):
        """trade_by_trade has one entry per pair."""
        pairs = [_pair(pnl=100.0), _pair(pnl=-20.0)]
        result = self._run(pairs, multiplier=1.5)
        self.assertEqual(len(result.trade_by_trade), 2)

    def test_trade_by_trade_fields(self):
        """Each trade_by_trade entry has the required fields."""
        pairs = [_pair(buy_price=100.0, sell_price=110.0, qty=5.0, pnl=50.0)]
        result = self._run(pairs, multiplier=2.0)
        entry = result.trade_by_trade[0]
        for field in ("symbol", "qty", "entry_price", "exit_price",
                      "scenario_exit_price", "baseline_pnl", "scenario_pnl",
                      "delta", "affected"):
            self.assertIn(field, entry, f"Missing field: {field}")

    def test_delta_pct_when_baseline_zero(self):
        """delta_pct is 0.0 when baseline_pnl is 0 (avoid division by zero)."""
        pairs = [_pair(pnl=0.0)]
        result = self._run(pairs, multiplier=2.0)
        self.assertAlmostEqual(result.delta_pct, 0.0)


# ---------------------------------------------------------------------------
# stop_loss
# ---------------------------------------------------------------------------

class TestStopLoss(unittest.TestCase):

    def _run(self, pairs, stop_loss_pct):
        from analytics.whatif import _run_stop_loss
        return _run_stop_loss(pairs, {"type": "stop_loss", "stop_loss_pct": stop_loss_pct})

    def test_loss_worse_than_stop_is_capped(self):
        """When actual loss exceeds stop threshold, P&L is capped at stop price."""
        # buy=100, sell=90 → 10% loss. 5% stop → stop price = 95.
        # scenario_pnl = (95 - 100) * 10 = -50 (better than -100 actual)
        pairs = [_pair(buy_price=100.0, sell_price=90.0, qty=10.0, pnl=-100.0)]
        result = self._run(pairs, stop_loss_pct=0.05)
        self.assertTrue(result.available)
        self.assertAlmostEqual(result.baseline_pnl, -100.0)
        self.assertAlmostEqual(result.scenario_pnl, -50.0)
        self.assertGreater(result.delta_pnl, 0.0, "Stop-loss should reduce loss")
        self.assertEqual(result.affected_trade_count, 1)

    def test_winning_trade_unaffected(self):
        """A trade that closed above stop price is not modified."""
        pairs = [_pair(buy_price=100.0, sell_price=110.0, qty=10.0, pnl=100.0)]
        result = self._run(pairs, stop_loss_pct=0.05)
        self.assertAlmostEqual(result.scenario_pnl, 100.0)
        self.assertEqual(result.affected_trade_count, 0)

    def test_loss_at_exact_stop_threshold_unaffected(self):
        """A trade that exited exactly at stop price is not considered affected."""
        # stop_price = 100 * (1 - 0.05) = 95
        pairs = [_pair(buy_price=100.0, sell_price=95.0, qty=10.0, pnl=-50.0)]
        result = self._run(pairs, stop_loss_pct=0.05)
        # sell_price == stop_price → not < stop_price → unaffected
        self.assertEqual(result.affected_trade_count, 0)
        self.assertAlmostEqual(result.scenario_pnl, -50.0)

    def test_small_loss_below_stop_unaffected(self):
        """A loss smaller than the stop threshold is not modified."""
        # 2% loss, 5% stop → below threshold → unaffected
        pairs = [_pair(buy_price=100.0, sell_price=98.0, qty=10.0, pnl=-20.0)]
        result = self._run(pairs, stop_loss_pct=0.05)
        self.assertEqual(result.affected_trade_count, 0)

    def test_invalid_stop_loss_zero(self):
        """stop_loss_pct = 0 returns available=False."""
        pairs = [_pair()]
        result = self._run(pairs, stop_loss_pct=0)
        self.assertFalse(result.available)

    def test_invalid_stop_loss_one(self):
        """stop_loss_pct = 1.0 returns available=False."""
        pairs = [_pair()]
        result = self._run(pairs, stop_loss_pct=1.0)
        self.assertFalse(result.available)

    def test_invalid_stop_loss_above_one(self):
        """stop_loss_pct > 1 returns available=False."""
        pairs = [_pair()]
        result = self._run(pairs, stop_loss_pct=1.5)
        self.assertFalse(result.available)

    def test_missing_buy_price_not_affected(self):
        """Trade with buy_price=0 cannot compute stop; P&L passes through unchanged."""
        pairs = [{
            "symbol": "AAPL", "buy_price": 0.0,
            "sell_price": 90.0, "qty": 10.0, "pnl": -100.0,
        }]
        result = self._run(pairs, stop_loss_pct=0.05)
        self.assertAlmostEqual(result.scenario_pnl, -100.0)
        self.assertEqual(result.affected_trade_count, 0)

    def test_multiple_trades_mixed(self):
        """Mix of affected and unaffected trades; counts and totals are correct."""
        pairs = [
            _pair(buy_price=100.0, sell_price=80.0, qty=10.0, pnl=-200.0),  # affected
            _pair(buy_price=100.0, sell_price=110.0, qty=10.0, pnl=100.0),   # unaffected (win)
            _pair(buy_price=100.0, sell_price=98.0, qty=10.0, pnl=-20.0),    # unaffected (small loss)
        ]
        result = self._run(pairs, stop_loss_pct=0.10)
        self.assertEqual(result.affected_trade_count, 1)
        self.assertEqual(result.trade_count, 3)

    def test_empty_trade_list(self):
        """Empty pairs list returns available=True with zero P&L."""
        result = self._run([], stop_loss_pct=0.05)
        self.assertTrue(result.available)
        self.assertAlmostEqual(result.baseline_pnl, 0.0)
        self.assertEqual(result.affected_trade_count, 0)

    def test_large_stop_loss_prevents_no_capping(self):
        """A very large stop-loss (e.g. 99%) means almost no trade is affected."""
        # sell_price would have to be below 1% of buy_price to trigger
        pairs = [_pair(buy_price=100.0, sell_price=90.0, qty=10.0, pnl=-100.0)]
        result = self._run(pairs, stop_loss_pct=0.99)
        # stop_price = 100 * 0.01 = 1.0 → sell 90 > 1.0 → unaffected
        self.assertEqual(result.affected_trade_count, 0)

    def test_trade_by_trade_scenario_exit_price_is_stop_price(self):
        """For an affected trade, scenario_exit_price equals the stop price."""
        pairs = [_pair(buy_price=100.0, sell_price=90.0, qty=10.0, pnl=-100.0)]
        result = self._run(pairs, stop_loss_pct=0.05)
        entry = result.trade_by_trade[0]
        expected_stop = 100.0 * (1.0 - 0.05)  # 95.0
        self.assertAlmostEqual(entry["scenario_exit_price"], expected_stop, places=4)

    def test_delta_pct_relative_to_baseline(self):
        """delta_pct = delta_pnl / abs(baseline_pnl) * 100."""
        pairs = [_pair(buy_price=100.0, sell_price=90.0, qty=10.0, pnl=-100.0)]
        result = self._run(pairs, stop_loss_pct=0.05)
        expected_pct = (result.delta_pnl / abs(result.baseline_pnl)) * 100
        self.assertAlmostEqual(result.delta_pct, expected_pct, places=2)


# ---------------------------------------------------------------------------
# hold_duration
# ---------------------------------------------------------------------------

class TestHoldDuration(unittest.TestCase):

    def _run(self, pairs, extra_days=2):
        from analytics.whatif import _run_hold_duration
        return _run_hold_duration(pairs, {"type": "hold_duration", "extra_days": extra_days})

    def test_always_unavailable(self):
        """hold_duration always returns available=False."""
        pairs = [_pair(pnl=100.0)]
        result = self._run(pairs, extra_days=3)
        self.assertFalse(result.available)

    def test_unavailable_reason_mentions_price_data(self):
        """unavailable_reason explains the data gap."""
        result = self._run([_pair()], extra_days=2)
        self.assertIsNotNone(result.unavailable_reason)
        reason_lower = result.unavailable_reason.lower()
        self.assertIn("price", reason_lower)

    def test_baseline_pnl_is_computed(self):
        """Even when unavailable, baseline_pnl is the sum of actual P&L."""
        pairs = [_pair(pnl=100.0), _pair(pnl=-30.0)]
        result = self._run(pairs, extra_days=1)
        self.assertAlmostEqual(result.baseline_pnl, 70.0)

    def test_scenario_pnl_is_zero(self):
        """scenario_pnl is 0 when unavailable."""
        result = self._run([_pair(pnl=200.0)], extra_days=5)
        self.assertAlmostEqual(result.scenario_pnl, 0.0)

    def test_trade_count_populated(self):
        """trade_count reflects number of pairs passed in."""
        pairs = [_pair(), _pair(), _pair()]
        result = self._run(pairs)
        self.assertEqual(result.trade_count, 3)

    def test_empty_trades(self):
        """Empty pairs list returns available=False with zero baseline."""
        result = self._run([])
        self.assertFalse(result.available)
        self.assertAlmostEqual(result.baseline_pnl, 0.0)
        self.assertEqual(result.trade_count, 0)


# ---------------------------------------------------------------------------
# run_what_if routing + raw trade input
# ---------------------------------------------------------------------------

class TestRunWhatIfRouting(unittest.TestCase):
    """Test the top-level run_what_if dispatcher with raw trade input
    (trades go through compute_round_trip_trades internally)."""

    def _make_round_trip_trades(self):
        """Two raw trades that form a complete buy→sell round trip."""
        return [
            {
                "symbol": "AAPL", "side": "buy", "qty": 10.0,
                "filled_avg_price": 100.0,
                "timestamp": "2026-01-10T14:00:00+00:00",
            },
            {
                "symbol": "AAPL", "side": "sell", "qty": 10.0,
                "filled_avg_price": 110.0,
                "timestamp": "2026-01-11T14:00:00+00:00",
            },
        ]

    def test_position_sizing_route(self):
        """run_what_if routes position_sizing correctly and returns result."""
        trades = self._make_round_trip_trades()
        result = run_what_if(trades, {"type": "position_sizing", "multiplier": 2.0})
        self.assertEqual(result.scenario_type, "position_sizing")
        self.assertTrue(result.available)

    def test_stop_loss_route(self):
        """run_what_if routes stop_loss correctly and returns result."""
        trades = self._make_round_trip_trades()
        result = run_what_if(trades, {"type": "stop_loss", "stop_loss_pct": 0.05})
        self.assertEqual(result.scenario_type, "stop_loss")
        self.assertTrue(result.available)

    def test_hold_duration_route(self):
        """run_what_if routes hold_duration correctly."""
        trades = self._make_round_trip_trades()
        result = run_what_if(trades, {"type": "hold_duration", "extra_days": 3})
        self.assertEqual(result.scenario_type, "hold_duration")
        self.assertFalse(result.available)

    def test_unknown_type_returns_unavailable(self):
        """Unknown scenario type returns available=False with clear message."""
        result = run_what_if([], {"type": "magic_profits"})
        self.assertFalse(result.available)
        self.assertEqual(result.scenario_type, "magic_profits")
        self.assertIn("magic_profits", result.unavailable_reason)

    def test_empty_type_returns_unavailable(self):
        """Empty type string is handled gracefully."""
        result = run_what_if([], {"type": ""})
        self.assertFalse(result.available)

    def test_result_is_whatif_result_instance(self):
        """run_what_if always returns a WhatIfResult instance."""
        result = run_what_if([], {"type": "position_sizing", "multiplier": 1.0})
        self.assertIsInstance(result, WhatIfResult)

    def test_empty_trades_no_crash(self):
        """All scenario types handle empty trade list without error."""
        for scenario in [
            {"type": "position_sizing", "multiplier": 1.5},
            {"type": "stop_loss", "stop_loss_pct": 0.05},
            {"type": "hold_duration", "extra_days": 2},
        ]:
            with self.subTest(scenario=scenario["type"]):
                result = run_what_if([], scenario)
                self.assertIsInstance(result, WhatIfResult)

    def test_position_sizing_baseline_pnl_matches_round_trips(self):
        """baseline_pnl matches the sum of round-trip P&L from raw trades."""
        trades = self._make_round_trip_trades()
        # buy=100, sell=110, qty=10 → P&L=100
        result = run_what_if(trades, {"type": "position_sizing", "multiplier": 1.0})
        self.assertAlmostEqual(result.baseline_pnl, 100.0)


# ---------------------------------------------------------------------------
# WhatIfResult dataclass
# ---------------------------------------------------------------------------

class TestWhatIfResultDataclass(unittest.TestCase):

    def test_default_trade_by_trade_is_empty_list(self):
        """trade_by_trade defaults to an empty list (not a shared mutable default)."""
        r1 = WhatIfResult("test", False, None, 0, 0, 0, 0, 0, 0)
        r2 = WhatIfResult("test", False, None, 0, 0, 0, 0, 0, 0)
        r1.trade_by_trade.append({"x": 1})
        self.assertEqual(r2.trade_by_trade, [],
                         "trade_by_trade must not share state between instances")

    def test_all_fields_accessible(self):
        """All documented fields are accessible on the dataclass."""
        r = WhatIfResult(
            scenario_type="position_sizing",
            available=True,
            unavailable_reason=None,
            baseline_pnl=100.0,
            scenario_pnl=200.0,
            delta_pnl=100.0,
            delta_pct=100.0,
            trade_count=5,
            affected_trade_count=5,
            trade_by_trade=[{"symbol": "AAPL"}],
        )
        self.assertEqual(r.scenario_type, "position_sizing")
        self.assertTrue(r.available)
        self.assertIsNone(r.unavailable_reason)
        self.assertAlmostEqual(r.baseline_pnl, 100.0)
        self.assertEqual(len(r.trade_by_trade), 1)


if __name__ == "__main__":
    unittest.main()

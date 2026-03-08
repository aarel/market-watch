"""Unit tests for analytics.ab_test — A/B Testing engine.

Covers:
  - Winner determination: a, b, tie, unavailable
  - delta_pnl / delta_pct computation
  - Summary string content
  - Edge cases: empty trades, zero P&L, both unavailable, one unavailable
  - Panel highlight: winner field reflects correct side
  - Tie threshold: near-identical P&L reported as tie
"""
import unittest
from unittest.mock import patch

from analytics.ab_test import ABTestResult, run_ab_test, _TIE_THRESHOLD
from analytics.whatif import WhatIfResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _round_trip(buy_price=100.0, sell_price=110.0, qty=10.0):
    """Two raw trades that form a complete buy→sell round trip."""
    return [
        {
            "symbol": "AAPL", "side": "buy", "qty": qty,
            "filled_avg_price": buy_price,
            "timestamp": "2026-01-10T14:00:00+00:00",
        },
        {
            "symbol": "AAPL", "side": "sell", "qty": qty,
            "filled_avg_price": sell_price,
            "timestamp": "2026-01-11T14:00:00+00:00",
        },
    ]


def _whatif_result(scenario_type="position_sizing", available=True,
                   scenario_pnl=100.0, baseline_pnl=80.0,
                   delta_pnl=20.0, delta_pct=25.0,
                   trade_count=1, affected_trade_count=1,
                   unavailable_reason=None):
    return WhatIfResult(
        scenario_type=scenario_type,
        available=available,
        unavailable_reason=unavailable_reason,
        baseline_pnl=baseline_pnl,
        scenario_pnl=scenario_pnl,
        delta_pnl=delta_pnl,
        delta_pct=delta_pct,
        trade_count=trade_count,
        affected_trade_count=affected_trade_count,
    )


# ---------------------------------------------------------------------------
# Winner determination
# ---------------------------------------------------------------------------

class TestWinnerDetermination(unittest.TestCase):

    def _run_patched(self, pnl_a, pnl_b, avail_a=True, avail_b=True,
                     reason_a=None, reason_b=None):
        """Patch run_what_if to return controlled WhatIfResults."""
        result_a = _whatif_result(scenario_pnl=pnl_a, available=avail_a,
                                  unavailable_reason=reason_a)
        result_b = _whatif_result(scenario_pnl=pnl_b, available=avail_b,
                                  unavailable_reason=reason_b)
        with patch("analytics.ab_test.run_what_if", side_effect=[result_a, result_b]):
            return run_ab_test([], {"type": "position_sizing"}, {"type": "position_sizing"})

    def test_b_wins_when_pnl_b_greater(self):
        result = self._run_patched(pnl_a=100.0, pnl_b=200.0)
        self.assertEqual(result.winner, "b")

    def test_a_wins_when_pnl_a_greater(self):
        result = self._run_patched(pnl_a=300.0, pnl_b=150.0)
        self.assertEqual(result.winner, "a")

    def test_tie_when_equal(self):
        result = self._run_patched(pnl_a=100.0, pnl_b=100.0)
        self.assertEqual(result.winner, "tie")

    def test_tie_within_threshold(self):
        """P&L difference below TIE_THRESHOLD is treated as a tie."""
        epsilon = _TIE_THRESHOLD * 0.5
        result = self._run_patched(pnl_a=100.0, pnl_b=100.0 + epsilon)
        self.assertEqual(result.winner, "tie")

    def test_not_tie_just_above_threshold(self):
        """P&L difference above TIE_THRESHOLD is decisive."""
        epsilon = _TIE_THRESHOLD * 2
        result = self._run_patched(pnl_a=100.0, pnl_b=100.0 + epsilon)
        self.assertEqual(result.winner, "b")

    def test_unavailable_when_a_unavailable(self):
        result = self._run_patched(pnl_a=0, pnl_b=100.0, avail_a=False,
                                   reason_a="Hold-duration requires price data.")
        self.assertEqual(result.winner, "unavailable")

    def test_unavailable_when_b_unavailable(self):
        result = self._run_patched(pnl_a=100.0, pnl_b=0, avail_b=False,
                                   reason_b="Hold-duration requires price data.")
        self.assertEqual(result.winner, "unavailable")

    def test_unavailable_when_both_unavailable(self):
        result = self._run_patched(pnl_a=0, pnl_b=0, avail_a=False, avail_b=False,
                                   reason_a="A bad.", reason_b="B bad.")
        self.assertEqual(result.winner, "unavailable")

    def test_negative_pnl_b_still_wins_if_less_negative(self):
        """A: -200, B: -50 → B is better (less negative)."""
        result = self._run_patched(pnl_a=-200.0, pnl_b=-50.0)
        self.assertEqual(result.winner, "b")


# ---------------------------------------------------------------------------
# Delta computation
# ---------------------------------------------------------------------------

class TestDeltaComputation(unittest.TestCase):

    def _run_patched(self, pnl_a, pnl_b):
        result_a = _whatif_result(scenario_pnl=pnl_a, baseline_pnl=pnl_a)
        result_b = _whatif_result(scenario_pnl=pnl_b, baseline_pnl=pnl_b)
        with patch("analytics.ab_test.run_what_if", side_effect=[result_a, result_b]):
            return run_ab_test([], {"type": "position_sizing"}, {"type": "position_sizing"})

    def test_delta_pnl_is_b_minus_a(self):
        result = self._run_patched(pnl_a=100.0, pnl_b=150.0)
        self.assertAlmostEqual(result.delta_pnl, 50.0)

    def test_delta_pnl_negative_when_a_wins(self):
        result = self._run_patched(pnl_a=200.0, pnl_b=100.0)
        self.assertAlmostEqual(result.delta_pnl, -100.0)

    def test_delta_pct_normalised_to_max(self):
        """delta_pct = |delta_pnl| / max(|pnl_a|, |pnl_b|) * 100."""
        result = self._run_patched(pnl_a=100.0, pnl_b=200.0)
        expected = abs(100.0) / max(abs(100.0), abs(200.0)) * 100
        self.assertAlmostEqual(result.delta_pct, expected, places=2)

    def test_delta_pct_zero_when_both_zero(self):
        result = self._run_patched(pnl_a=0.0, pnl_b=0.0)
        self.assertAlmostEqual(result.delta_pct, 0.0)

    def test_delta_zero_when_unavailable(self):
        result_a = _whatif_result(available=False, scenario_pnl=0, unavailable_reason="x")
        result_b = _whatif_result(scenario_pnl=100.0)
        with patch("analytics.ab_test.run_what_if", side_effect=[result_a, result_b]):
            r = run_ab_test([], {}, {})
        self.assertAlmostEqual(r.delta_pnl, 0.0)
        self.assertAlmostEqual(r.delta_pct, 0.0)


# ---------------------------------------------------------------------------
# Summary string
# ---------------------------------------------------------------------------

class TestSummaryString(unittest.TestCase):

    def _run(self, pnl_a, pnl_b, avail_a=True, avail_b=True,
             reason_a="not available", reason_b="not available"):
        ra = _whatif_result(scenario_pnl=pnl_a, available=avail_a, unavailable_reason=reason_a)
        rb = _whatif_result(scenario_pnl=pnl_b, available=avail_b, unavailable_reason=reason_b)
        with patch("analytics.ab_test.run_what_if", side_effect=[ra, rb]):
            return run_ab_test([], {}, {})

    def test_summary_mentions_winner_a(self):
        result = self._run(300.0, 100.0)
        self.assertIn("A", result.summary)
        self.assertIn("wins", result.summary.lower())

    def test_summary_mentions_winner_b(self):
        result = self._run(100.0, 300.0)
        self.assertIn("B", result.summary)

    def test_summary_mentions_tie(self):
        result = self._run(100.0, 100.0)
        self.assertIn("Tie", result.summary)

    def test_summary_mentions_unavailable(self):
        result = self._run(0, 0, avail_a=False)
        self.assertIn("unavailable", result.summary.lower())

    def test_summary_includes_reason_when_unavailable(self):
        result = self._run(0, 0, avail_b=False, reason_b="Hold-duration needs prices.")
        self.assertIn("Hold-duration needs prices.", result.summary)

    def test_summary_is_nonempty_string(self):
        result = self._run(100.0, 200.0)
        self.assertIsInstance(result.summary, str)
        self.assertGreater(len(result.summary), 0)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

class TestABTestResult(unittest.TestCase):

    def test_result_is_abtestresult_instance(self):
        ra = _whatif_result(scenario_pnl=100.0)
        rb = _whatif_result(scenario_pnl=200.0)
        with patch("analytics.ab_test.run_what_if", side_effect=[ra, rb]):
            result = run_ab_test([], {}, {})
        self.assertIsInstance(result, ABTestResult)

    def test_scenario_a_and_b_preserved(self):
        ra = _whatif_result(scenario_pnl=100.0, scenario_type="position_sizing")
        rb = _whatif_result(scenario_pnl=200.0, scenario_type="stop_loss")
        with patch("analytics.ab_test.run_what_if", side_effect=[ra, rb]):
            result = run_ab_test([], {}, {})
        self.assertEqual(result.scenario_a.scenario_type, "position_sizing")
        self.assertEqual(result.scenario_b.scenario_type, "stop_loss")

    def test_all_fields_present(self):
        ra = _whatif_result(scenario_pnl=50.0)
        rb = _whatif_result(scenario_pnl=75.0)
        with patch("analytics.ab_test.run_what_if", side_effect=[ra, rb]):
            result = run_ab_test([], {}, {})
        for attr in ("scenario_a", "scenario_b", "winner", "delta_pnl",
                     "delta_pct", "summary"):
            self.assertTrue(hasattr(result, attr), f"Missing field: {attr}")


# ---------------------------------------------------------------------------
# Integration: real trades through real what-if engine
# ---------------------------------------------------------------------------

class TestIntegration(unittest.TestCase):
    """End-to-end: raw trade list → run_ab_test → ABTestResult."""

    def test_position_sizing_vs_stop_loss(self):
        """Comparing position sizing and stop-loss on a winning trade."""
        trades = _round_trip(buy_price=100.0, sell_price=110.0, qty=10.0)
        result = run_ab_test(
            trades,
            {"type": "position_sizing", "multiplier": 1.5},
            {"type": "stop_loss", "stop_loss_pct": 0.05},
        )
        self.assertIsInstance(result, ABTestResult)
        self.assertIn(result.winner, {"a", "b", "tie", "unavailable"})
        # Both should be available for this trade set
        self.assertTrue(result.scenario_a.available)
        self.assertTrue(result.scenario_b.available)

    def test_hold_duration_makes_unavailable(self):
        """hold_duration always marks that scenario unavailable."""
        trades = _round_trip()
        result = run_ab_test(
            trades,
            {"type": "position_sizing", "multiplier": 2.0},
            {"type": "hold_duration", "extra_days": 3},
        )
        self.assertEqual(result.winner, "unavailable")
        self.assertFalse(result.scenario_b.available)

    def test_empty_trades(self):
        """Empty trade list: both scenarios available, P&L zero, tie."""
        result = run_ab_test(
            [],
            {"type": "position_sizing", "multiplier": 2.0},
            {"type": "position_sizing", "multiplier": 3.0},
        )
        # With no trades there's nothing to affect — P&L is 0 for both → tie
        self.assertAlmostEqual(result.scenario_a.scenario_pnl, 0.0)
        self.assertAlmostEqual(result.scenario_b.scenario_pnl, 0.0)
        self.assertEqual(result.winner, "tie")

    def test_same_scenario_both_sides_is_tie(self):
        """Identical scenarios produce tie regardless of trade history."""
        trades = _round_trip()
        result = run_ab_test(
            trades,
            {"type": "position_sizing", "multiplier": 1.5},
            {"type": "position_sizing", "multiplier": 1.5},
        )
        self.assertEqual(result.winner, "tie")
        self.assertAlmostEqual(result.delta_pnl, 0.0)

    def test_baseline_pnl_consistent(self):
        """Both scenarios share the same underlying round-trip trades,
        so their baseline P&L should be identical."""
        trades = _round_trip(buy_price=100.0, sell_price=110.0, qty=10.0)
        result = run_ab_test(
            trades,
            {"type": "position_sizing", "multiplier": 2.0},
            {"type": "stop_loss", "stop_loss_pct": 0.05},
        )
        self.assertAlmostEqual(
            result.scenario_a.baseline_pnl,
            result.scenario_b.baseline_pnl,
            places=2,
        )


if __name__ == "__main__":
    unittest.main()

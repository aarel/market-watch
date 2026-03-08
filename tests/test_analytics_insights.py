"""Unit tests for analytics.insights — Paper Trading Insights engine.

Tests cover:
  - All five insight categories: signal_quality, timing, symbol_performance,
    risk, portfolio
  - MIN_SAMPLES graceful degradation (< 3 data points → insight omitted)
  - Direction assignment (positive / negative / neutral)
  - Insight field completeness
  - Empty trade list → empty insights (no crash)
  - compute_insights top-level dispatcher
"""
import unittest
from datetime import UTC, datetime, timedelta

from analytics.insights import (
    MIN_SAMPLES,
    Insight,
    _max_consecutive,
    _portfolio_insights,
    _risk_insights,
    _signal_quality_insights,
    _symbol_performance_insights,
    _timing_insights,
    compute_insights,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pair(symbol="AAPL", pnl=100.0, buy_price=100.0, sell_price=110.0, qty=10.0) -> dict:
    return {
        "symbol": symbol,
        "pnl": pnl,
        "buy_price": buy_price,
        "sell_price": sell_price,
        "qty": qty,
        "timestamp": "2026-01-10T14:00:00+00:00",
    }


def _trade(symbol="AAPL", side="buy", signal_reason="momentum",
           signal_strength=0.8, market_open=True, gainer_count=15,
           perf_1d=None) -> dict:
    t = {
        "symbol": symbol,
        "side": side,
        "signal_reason": signal_reason,
        "signal_strength": signal_strength,
        "filled_avg_price": 100.0,
        "qty": 10.0,
        "timestamp": "2026-01-10T14:00:00+00:00",
        "market_context": {
            "market_open": market_open,
            "top_gainer_count": gainer_count,
        },
    }
    if perf_1d is not None:
        t["perf_1d"] = perf_1d
    return t


def _snap(days_offset=0, equity=100_000.0) -> dict:
    base = datetime(2026, 1, 1, tzinfo=UTC)
    ts = (base + timedelta(days=days_offset)).isoformat()
    return {"timestamp": ts, "equity": equity}


def _insight_list_has_category(insights, category):
    return any(i.category == category for i in insights)


# ---------------------------------------------------------------------------
# Insight dataclass
# ---------------------------------------------------------------------------

class TestInsightDataclass(unittest.TestCase):

    def test_all_fields_accessible(self):
        i = Insight(
            category="risk",
            headline="Test headline",
            detail="Test detail sentence.",
            value=42.0,
            direction="positive",
        )
        self.assertEqual(i.category, "risk")
        self.assertEqual(i.headline, "Test headline")
        self.assertEqual(i.detail, "Test detail sentence.")
        self.assertAlmostEqual(i.value, 42.0)
        self.assertEqual(i.direction, "positive")

    def test_none_value_allowed(self):
        i = Insight("portfolio", "h", "d", None, "neutral")
        self.assertIsNone(i.value)


# ---------------------------------------------------------------------------
# _max_consecutive helper
# ---------------------------------------------------------------------------

class TestMaxConsecutive(unittest.TestCase):

    def test_all_matching(self):
        self.assertEqual(_max_consecutive([-1, -2, -3, -4], lambda p: p < 0), 4)

    def test_none_matching(self):
        self.assertEqual(_max_consecutive([1, 2, 3], lambda p: p < 0), 0)

    def test_interleaved(self):
        self.assertEqual(_max_consecutive([-1, 1, -1, -1, 1], lambda p: p < 0), 2)

    def test_empty(self):
        self.assertEqual(_max_consecutive([], lambda p: p < 0), 0)

    def test_single_element_match(self):
        self.assertEqual(_max_consecutive([-5], lambda p: p < 0), 1)


# ---------------------------------------------------------------------------
# Signal quality
# ---------------------------------------------------------------------------

class TestSignalQualityInsights(unittest.TestCase):

    def _run(self, trades, pairs):
        return _signal_quality_insights(trades, pairs)

    def test_overall_win_rate_computed(self):
        """Win rate insight emitted when >= MIN_SAMPLES pairs."""
        pairs = [_pair(pnl=p) for p in [100.0, -50.0, 80.0, 60.0]]
        insights = self._run([], pairs)
        win_rate_insights = [i for i in insights if "win rate" in i.headline.lower() and "overall" in i.headline.lower()]
        self.assertEqual(len(win_rate_insights), 1)
        # 3 wins out of 4 = 75%
        self.assertAlmostEqual(win_rate_insights[0].value, 75.0)

    def test_win_rate_positive_direction_when_above_55(self):
        pairs = [_pair(pnl=p) for p in [100.0, 80.0, 60.0, 40.0]]  # 100% win
        insights = self._run([], pairs)
        wr = [i for i in insights if "overall" in i.headline.lower()][0]
        self.assertEqual(wr.direction, "positive")

    def test_win_rate_negative_direction_when_below_45(self):
        pairs = [_pair(pnl=p) for p in [-100.0, -80.0, -60.0, -40.0]]  # 0% win
        insights = self._run([], pairs)
        wr = [i for i in insights if "overall" in i.headline.lower()][0]
        self.assertEqual(wr.direction, "negative")

    def test_win_rate_omitted_when_below_min_samples(self):
        pairs = [_pair(pnl=100.0), _pair(pnl=-50.0)]  # only 2
        insights = self._run([], pairs)
        win_rate_insights = [i for i in insights if "overall" in i.headline.lower()]
        self.assertEqual(len(win_rate_insights), 0)

    def test_perf_1d_insight_emitted_when_sufficient(self):
        trades = [
            _trade(perf_1d=0.02), _trade(perf_1d=0.01), _trade(perf_1d=0.03),
        ]
        insights = self._run(trades, [])
        perf_insights = [i for i in insights if "1 day" in i.headline.lower()]
        self.assertEqual(len(perf_insights), 1)
        self.assertAlmostEqual(perf_insights[0].value, 2.0, places=1)  # avg 2%

    def test_perf_1d_omitted_when_below_min_samples(self):
        trades = [_trade(perf_1d=0.02), _trade(perf_1d=0.01)]
        insights = self._run(trades, [])
        perf_insights = [i for i in insights if "1 day" in i.headline.lower()]
        self.assertEqual(len(perf_insights), 0)

    def test_perf_1d_negative_direction_when_negative(self):
        trades = [
            _trade(perf_1d=-0.03), _trade(perf_1d=-0.02), _trade(perf_1d=-0.01),
        ]
        insights = self._run(trades, [])
        perf_insights = [i for i in insights if "1 day" in i.headline.lower()]
        self.assertEqual(perf_insights[0].direction, "negative")

    def test_empty_trades_and_pairs_no_crash(self):
        insights = self._run([], [])
        self.assertIsInstance(insights, list)


# ---------------------------------------------------------------------------
# Timing
# ---------------------------------------------------------------------------

class TestTimingInsights(unittest.TestCase):

    def _run(self, trades, pairs=None):
        if pairs is None:
            # Build pairs from trades so symbol_pnl is populated
            pairs = [_pair(symbol=t["symbol"], pnl=100.0) for t in trades if t["side"] == "buy"]
        return _timing_insights(trades, pairs)

    def _make_market_trades(self, open_wins, open_losses, closed_wins, closed_losses):
        """Build buy trades with known market_open and a pair for each."""
        trades = []
        pairs = []
        sym_counter = [0]
        def add(market_open, pnl):
            sym_counter[0] += 1
            sym = f"SYM{sym_counter[0]}"
            t = _trade(symbol=sym, market_open=market_open)
            trades.append(t)
            pairs.append(_pair(symbol=sym, pnl=pnl))
        for _ in range(open_wins):    add(True,  100.0)
        for _ in range(open_losses):  add(True,  -50.0)
        for _ in range(closed_wins):  add(False, 100.0)
        for _ in range(closed_losses):add(False, -50.0)
        return trades, pairs

    def test_market_open_insight_emitted_when_sufficient(self):
        trades, pairs = self._make_market_trades(3, 0, 0, 3)
        insights = _timing_insights(trades, pairs)
        timing = [i for i in insights if "market" in i.headline.lower() or "hours" in i.headline.lower()]
        self.assertEqual(len(timing), 1)

    def test_market_open_omitted_when_below_min_samples_one_side(self):
        trades, pairs = self._make_market_trades(3, 0, 1, 0)  # closed only 1
        insights = _timing_insights(trades, pairs)
        timing = [i for i in insights if "hours" in i.headline.lower()]
        self.assertEqual(len(timing), 0)

    def test_empty_trades_no_crash(self):
        insights = _timing_insights([], [])
        self.assertIsInstance(insights, list)


# ---------------------------------------------------------------------------
# Symbol performance
# ---------------------------------------------------------------------------

class TestSymbolPerformanceInsights(unittest.TestCase):

    def test_best_symbol_emitted(self):
        pairs = [_pair("AAPL", 100.0)] * 3 + [_pair("TSLA", -50.0)] * 3
        insights = _symbol_performance_insights(pairs)
        best = [i for i in insights if "best" in i.headline.lower()]
        self.assertEqual(len(best), 1)
        self.assertIn("AAPL", best[0].headline)

    def test_worst_symbol_emitted(self):
        pairs = [_pair("AAPL", 100.0)] * 3 + [_pair("TSLA", -50.0)] * 3
        insights = _symbol_performance_insights(pairs)
        worst = [i for i in insights if "worst" in i.headline.lower()]
        self.assertEqual(len(worst), 1)
        self.assertIn("TSLA", worst[0].headline)

    def test_omitted_when_below_min_samples(self):
        """Only 1 trade per symbol → qualified is empty → no best/worst insight."""
        pairs = [_pair("AAPL", 100.0), _pair("TSLA", -50.0)]
        insights = _symbol_performance_insights(pairs)
        best = [i for i in insights if "best" in i.headline.lower()]
        self.assertEqual(len(best), 0)

    def test_positive_direction_for_best(self):
        pairs = [_pair("AAPL", 200.0)] * 3
        insights = _symbol_performance_insights(pairs)
        best = [i for i in insights if "best" in i.headline.lower()]
        self.assertEqual(best[0].direction, "positive")

    def test_negative_direction_for_worst(self):
        pairs = [_pair("AAPL", 100.0)] * 3 + [_pair("TSLA", -200.0)] * 3
        insights = _symbol_performance_insights(pairs)
        worst = [i for i in insights if "worst" in i.headline.lower()]
        self.assertEqual(worst[0].direction, "negative")

    def test_single_trade_symbols_summary(self):
        """3+ symbols with only 1 trade each get a summary insight."""
        pairs = [_pair("A", 10.0), _pair("B", -5.0), _pair("C", 20.0)]
        insights = _symbol_performance_insights(pairs)
        single = [i for i in insights if "once" in i.headline.lower()]
        self.assertEqual(len(single), 1)

    def test_empty_pairs_no_crash(self):
        insights = _symbol_performance_insights([])
        self.assertEqual(insights, [])


# ---------------------------------------------------------------------------
# Risk
# ---------------------------------------------------------------------------

class TestRiskInsights(unittest.TestCase):

    def test_win_loss_ratio_emitted(self):
        pairs = [_pair(pnl=p) for p in [100.0, 80.0, 60.0, -30.0, -20.0, -10.0]]
        insights = _risk_insights(pairs)
        ratio = [i for i in insights if "ratio" in i.headline.lower()]
        self.assertEqual(len(ratio), 1)
        self.assertGreater(ratio[0].value, 0)

    def test_win_loss_ratio_omitted_when_below_min_samples(self):
        pairs = [_pair(pnl=100.0), _pair(pnl=-50.0)]  # only 2 pairs total
        insights = _risk_insights(pairs)
        ratio = [i for i in insights if "ratio" in i.headline.lower()]
        self.assertEqual(len(ratio), 0)

    def test_largest_loss_emitted(self):
        pairs = [_pair(pnl=p) for p in [100.0, -200.0, -50.0]]
        insights = _risk_insights(pairs)
        loss_ins = [i for i in insights if "largest" in i.headline.lower()]
        self.assertEqual(len(loss_ins), 1)
        self.assertAlmostEqual(loss_ins[0].value, -200.0)
        self.assertEqual(loss_ins[0].direction, "negative")

    def test_losing_streak_emitted_when_3_or_more(self):
        pairs = [_pair(pnl=p) for p in [-1, -2, -3, 100.0, 50.0]]
        insights = _risk_insights(pairs)
        streak = [i for i in insights if "losing streak" in i.headline.lower()]
        self.assertEqual(len(streak), 1)
        self.assertEqual(streak[0].value, 3.0)

    def test_losing_streak_omitted_when_less_than_3(self):
        pairs = [_pair(pnl=p) for p in [-1, -2, 100.0, 50.0, 80.0]]
        insights = _risk_insights(pairs)
        streak = [i for i in insights if "losing streak" in i.headline.lower()]
        self.assertEqual(len(streak), 0)

    def test_empty_pairs_no_crash(self):
        insights = _risk_insights([])
        self.assertEqual(insights, [])


# ---------------------------------------------------------------------------
# Portfolio
# ---------------------------------------------------------------------------

class TestPortfolioInsights(unittest.TestCase):

    def test_total_return_emitted(self):
        equity = [_snap(i, 100_000 + i * 1000) for i in range(5)]
        insights = _portfolio_insights(equity, [])
        returns = [i for i in insights if "return" in i.headline.lower()]
        self.assertEqual(len(returns), 1)
        self.assertGreater(returns[0].value, 0)
        self.assertEqual(returns[0].direction, "positive")

    def test_total_return_negative_direction(self):
        equity = [_snap(0, 100_000), _snap(1, 95_000), _snap(2, 90_000)]
        insights = _portfolio_insights(equity, [])
        returns = [i for i in insights if "return" in i.headline.lower()]
        self.assertEqual(returns[0].direction, "negative")

    def test_total_return_omitted_when_below_min_samples(self):
        equity = [_snap(0, 100_000), _snap(1, 101_000)]  # only 2
        insights = _portfolio_insights(equity, [])
        returns = [i for i in insights if "return" in i.headline.lower()]
        self.assertEqual(len(returns), 0)

    def test_realised_pnl_emitted(self):
        pairs = [_pair(pnl=p) for p in [100.0, -50.0, 200.0]]
        insights = _portfolio_insights([_snap(i) for i in range(5)], pairs)
        pnl_ins = [i for i in insights if "realised" in i.headline.lower()]
        self.assertEqual(len(pnl_ins), 1)
        self.assertAlmostEqual(pnl_ins[0].value, 250.0)

    def test_realised_pnl_omitted_when_below_min_samples(self):
        pairs = [_pair(pnl=100.0), _pair(pnl=-50.0)]
        equity = [_snap(i) for i in range(5)]
        insights = _portfolio_insights(equity, pairs)
        pnl_ins = [i for i in insights if "realised" in i.headline.lower()]
        self.assertEqual(len(pnl_ins), 0)

    def test_empty_equity_no_crash(self):
        insights = _portfolio_insights([], [])
        self.assertIsInstance(insights, list)


# ---------------------------------------------------------------------------
# compute_insights (top-level)
# ---------------------------------------------------------------------------

class TestComputeInsights(unittest.TestCase):

    def test_returns_list(self):
        result = compute_insights([])
        self.assertIsInstance(result, list)

    def test_empty_everything_returns_empty(self):
        result = compute_insights([], [])
        self.assertEqual(result, [])

    def test_all_insights_are_insight_instances(self):
        pairs = [_pair(pnl=p) for p in [100.0, -50.0, 80.0, 60.0, -30.0, 120.0]]
        equity = [_snap(i, 100_000 + i * 500) for i in range(5)]
        result = compute_insights(pairs, equity)
        for item in result:
            self.assertIsInstance(item, Insight, f"Expected Insight, got {type(item)}")

    def test_insight_directions_are_valid(self):
        pairs = [_pair(pnl=p) for p in [100.0, 50.0, -30.0, 80.0]]
        result = compute_insights(pairs)
        for i in result:
            self.assertIn(i.direction, {"positive", "negative", "neutral"},
                          f"Invalid direction: {i.direction}")

    def test_insight_categories_are_valid(self):
        pairs = [_pair(pnl=p) for p in [100.0, 50.0, -30.0, 80.0]]
        result = compute_insights(pairs)
        valid = {"signal_quality", "timing", "symbol_performance", "risk", "portfolio"}
        for i in result:
            self.assertIn(i.category, valid, f"Invalid category: {i.category}")

    def test_headlines_within_length_limit(self):
        pairs = [_pair(pnl=p) for p in [100.0, 50.0, -30.0, 80.0]]
        result = compute_insights(pairs)
        for i in result:
            self.assertLessEqual(len(i.headline), 100,
                                 f"Headline too long: {i.headline}")

    def test_portfolio_insights_included_when_equity_provided(self):
        equity = [_snap(i, 100_000 + i * 1000) for i in range(5)]
        pairs = [_pair(pnl=p) for p in [100.0, 50.0, -30.0]]
        result = compute_insights(pairs, equity)
        self.assertTrue(_insight_list_has_category(result, "portfolio"))

    def test_portfolio_insights_absent_when_no_equity(self):
        pairs = [_pair(pnl=p) for p in [100.0, 50.0, -30.0]]
        result = compute_insights(pairs)  # no equity arg
        self.assertFalse(_insight_list_has_category(result, "portfolio"))


if __name__ == "__main__":
    unittest.main()

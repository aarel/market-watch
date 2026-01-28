"""
Enhanced tests for analytics/metrics.py

Tests performance metric calculations and trade outcome analysis.
"""
import unittest
from datetime import datetime, timedelta

from analytics.metrics import compute_equity_metrics, compute_trade_outcomes


class TestEquityMetrics(unittest.TestCase):
    """Test equity curve performance metrics."""

    def test_compute_equity_metrics_basic(self):
        """Test basic equity metrics calculation."""
        now = datetime.now()
        points = [
            {"timestamp": now - timedelta(days=2), "equity": 100000},
            {"timestamp": now - timedelta(days=1), "equity": 101000},
            {"timestamp": now, "equity": 99000},
        ]
        metrics = compute_equity_metrics(points)
        self.assertGreater(metrics.period_days, 0)
        self.assertNotEqual(metrics.total_return_pct, 0)
        self.assertGreaterEqual(metrics.max_drawdown_pct, 0)

    def test_compute_equity_metrics_empty(self):
        """Test empty equity data returns zeros."""
        metrics = compute_equity_metrics([])
        self.assertEqual(metrics.total_return_pct, 0)
        self.assertEqual(metrics.period_days, 0)

    def test_compute_equity_metrics_single_point(self):
        """Test single data point returns zeros."""
        metrics = compute_equity_metrics([{"timestamp": datetime.now(), "equity": 100000}])
        self.assertEqual(metrics.total_return_pct, 0)
        self.assertEqual(metrics.period_days, 0)

    def test_compute_equity_metrics_positive_return(self):
        """Test positive return calculation."""
        now = datetime.now()
        points = [
            {"timestamp": now - timedelta(days=10), "equity": 100000},
            {"timestamp": now, "equity": 110000},
        ]
        metrics = compute_equity_metrics(points)
        # 10% return
        self.assertAlmostEqual(metrics.total_return_pct, 10.0, places=1)

    def test_compute_equity_metrics_negative_return(self):
        """Test negative return calculation."""
        now = datetime.now()
        points = [
            {"timestamp": now - timedelta(days=10), "equity": 100000},
            {"timestamp": now, "equity": 95000},
        ]
        metrics = compute_equity_metrics(points)
        # -5% return
        self.assertAlmostEqual(metrics.total_return_pct, -5.0, places=1)

    def test_compute_equity_metrics_drawdown_calculation(self):
        """Test max drawdown is calculated correctly."""
        now = datetime.now()
        points = [
            {"timestamp": now - timedelta(days=5), "equity": 100000},
            {"timestamp": now - timedelta(days=4), "equity": 110000},  # Peak
            {"timestamp": now - timedelta(days=3), "equity": 105000},
            {"timestamp": now - timedelta(days=2), "equity": 99000},   # Trough (-10% from peak)
            {"timestamp": now - timedelta(days=1), "equity": 102000},
            {"timestamp": now, "equity": 108000},
        ]
        metrics = compute_equity_metrics(points)
        # Max drawdown should be ~10% (110k to 99k)
        self.assertGreater(metrics.max_drawdown_pct, 9.0)
        self.assertLess(metrics.max_drawdown_pct, 11.0)

    def test_compute_equity_metrics_multiple_same_day(self):
        """Test daily collapsing keeps last snapshot per day."""
        now = datetime.now()
        yesterday = now - timedelta(days=1)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        points = [
            {"timestamp": yesterday, "equity": 100000},  # Previous day
            {"timestamp": today_start + timedelta(hours=9), "equity": 101000},
            {"timestamp": today_start + timedelta(hours=12), "equity": 101500},
            {"timestamp": today_start + timedelta(hours=15), "equity": 102000},  # Last one for today
        ]
        metrics = compute_equity_metrics(points)
        # Should use 100000 as start, 102000 as end (last snapshot of today)
        self.assertAlmostEqual(metrics.total_return_pct, 2.0, places=1)

    def test_compute_equity_metrics_zero_start_value(self):
        """Test zero starting equity is handled gracefully."""
        now = datetime.now()
        points = [
            {"timestamp": now - timedelta(days=1), "equity": 0},
            {"timestamp": now, "equity": 100000},
        ]
        metrics = compute_equity_metrics(points)
        # Can't calculate return with zero start
        self.assertEqual(metrics.total_return_pct, 0)

    def test_compute_equity_metrics_alternative_field_names(self):
        """Test using portfolio_value and account_value fields."""
        now = datetime.now()
        points = [
            {"timestamp": now - timedelta(days=2), "portfolio_value": 100000},
            {"timestamp": now - timedelta(days=1), "account_value": 105000},
            {"timestamp": now, "equity": 110000},
        ]
        metrics = compute_equity_metrics(points)
        self.assertAlmostEqual(metrics.total_return_pct, 10.0, places=1)


class TestTradeOutcomes(unittest.TestCase):
    """Test trade outcome and P&L analysis."""

    def test_compute_trade_outcomes_basic(self):
        """Test basic win/loss calculation."""
        now = datetime.now()
        trades = [
            {"timestamp": now, "symbol": "ABC", "side": "buy", "qty": 10, "filled_avg_price": 10},
            {"timestamp": now, "symbol": "ABC", "side": "sell", "qty": 5, "filled_avg_price": 12},
            {"timestamp": now, "symbol": "ABC", "side": "sell", "qty": 5, "filled_avg_price": 8},
        ]
        stats = compute_trade_outcomes(trades)
        self.assertEqual(stats.total, 3)
        self.assertEqual(stats.buys, 1)
        self.assertEqual(stats.sells, 2)
        self.assertEqual(stats.win_trades, 1)
        self.assertEqual(stats.loss_trades, 1)
        self.assertEqual(stats.breakeven_trades, 0)
        self.assertAlmostEqual(stats.win_rate_pct, 50.0)

    def test_compute_trade_outcomes_empty(self):
        """Test empty trade list returns zeros."""
        stats = compute_trade_outcomes([])
        self.assertEqual(stats.total, 0)
        self.assertEqual(stats.win_rate_pct, 0)

    def test_compute_trade_outcomes_chronological_sorting(self):
        """Test trades are sorted chronologically before processing."""
        # Trades provided out of order
        now = datetime.now()
        trades = [
            {"timestamp": now + timedelta(hours=2), "symbol": "ABC", "side": "sell", "qty": 10, "filled_avg_price": 12},
            {"timestamp": now, "symbol": "ABC", "side": "buy", "qty": 10, "filled_avg_price": 10},
        ]
        stats = compute_trade_outcomes(trades)
        # Should match buy with sell correctly
        self.assertEqual(stats.win_trades, 1)
        self.assertAlmostEqual(stats.realized_pnl, 20.0)  # (12-10) * 10

    def test_compute_trade_outcomes_missing_price_skipped(self):
        """Test trades without filled_avg_price are skipped (current behavior)."""
        now = datetime.now()
        trades = [
            {"timestamp": now, "symbol": "ABC", "side": "buy", "qty": 10, "notional": 1000},
            {"timestamp": now + timedelta(hours=1), "symbol": "ABC", "side": "sell", "qty": 10, "notional": 1200},
        ]
        stats = compute_trade_outcomes(trades)
        # Current implementation skips trades without filled_avg_price
        # even if notional is available
        # TODO: Enhancement - calculate price from notional/qty when filled_avg_price is missing
        self.assertEqual(stats.total, 0)  # Both skipped
        self.assertEqual(stats.win_trades, 0)

    def test_compute_trade_outcomes_sell_without_inventory(self):
        """Test sell without prior buy is treated as breakeven."""
        now = datetime.now()
        trades = [
            {"timestamp": now, "symbol": "ABC", "side": "sell", "qty": 10, "filled_avg_price": 100},
        ]
        stats = compute_trade_outcomes(trades)
        self.assertEqual(stats.sells, 1)
        self.assertEqual(stats.breakeven_trades, 1)
        self.assertEqual(stats.realized_pnl, 0)

    def test_compute_trade_outcomes_partial_sells(self):
        """Test multiple partial sells from one buy."""
        now = datetime.now()
        trades = [
            {"timestamp": now, "symbol": "ABC", "side": "buy", "qty": 100, "filled_avg_price": 10},
            {"timestamp": now + timedelta(hours=1), "symbol": "ABC", "side": "sell", "qty": 30, "filled_avg_price": 11},
            {"timestamp": now + timedelta(hours=2), "symbol": "ABC", "side": "sell", "qty": 40, "filled_avg_price": 12},
            {"timestamp": now + timedelta(hours=3), "symbol": "ABC", "side": "sell", "qty": 30, "filled_avg_price": 9},
        ]
        stats = compute_trade_outcomes(trades)
        self.assertEqual(stats.buys, 1)
        self.assertEqual(stats.sells, 3)
        self.assertEqual(stats.win_trades, 2)
        self.assertEqual(stats.loss_trades, 1)
        # P&L: (11-10)*30 + (12-10)*40 + (9-10)*30 = 30 + 80 - 30 = 80
        self.assertAlmostEqual(stats.realized_pnl, 80.0)

    def test_compute_trade_outcomes_multiple_symbols(self):
        """Test tracking multiple symbols independently."""
        now = datetime.now()
        trades = [
            {"timestamp": now, "symbol": "AAPL", "side": "buy", "qty": 10, "filled_avg_price": 100},
            {"timestamp": now, "symbol": "GOOGL", "side": "buy", "qty": 5, "filled_avg_price": 200},
            {"timestamp": now + timedelta(hours=1), "symbol": "AAPL", "side": "sell", "qty": 10, "filled_avg_price": 110},
            {"timestamp": now + timedelta(hours=2), "symbol": "GOOGL", "side": "sell", "qty": 5, "filled_avg_price": 190},
        ]
        stats = compute_trade_outcomes(trades)
        self.assertEqual(stats.total, 4)
        self.assertEqual(stats.win_trades, 1)  # AAPL won
        self.assertEqual(stats.loss_trades, 1)  # GOOGL lost
        # P&L: (110-100)*10 + (190-200)*5 = 100 - 50 = 50
        self.assertAlmostEqual(stats.realized_pnl, 50.0)

    def test_compute_trade_outcomes_average_cost_basis(self):
        """Test average cost basis calculation with multiple buys."""
        now = datetime.now()
        trades = [
            {"timestamp": now, "symbol": "ABC", "side": "buy", "qty": 10, "filled_avg_price": 100},
            {"timestamp": now + timedelta(hours=1), "symbol": "ABC", "side": "buy", "qty": 10, "filled_avg_price": 110},
            {"timestamp": now + timedelta(hours=2), "symbol": "ABC", "side": "sell", "qty": 20, "filled_avg_price": 120},
        ]
        stats = compute_trade_outcomes(trades)
        # Average cost: (100*10 + 110*10) / 20 = 105
        # P&L: (120 - 105) * 20 = 300
        self.assertAlmostEqual(stats.realized_pnl, 300.0)
        self.assertEqual(stats.win_trades, 1)

    def test_compute_trade_outcomes_breakeven_trade(self):
        """Test exact breakeven trade (P&L = 0)."""
        now = datetime.now()
        trades = [
            {"timestamp": now, "symbol": "ABC", "side": "buy", "qty": 10, "filled_avg_price": 100},
            {"timestamp": now + timedelta(hours=1), "symbol": "ABC", "side": "sell", "qty": 10, "filled_avg_price": 100},
        ]
        stats = compute_trade_outcomes(trades)
        self.assertEqual(stats.breakeven_trades, 1)
        self.assertAlmostEqual(stats.realized_pnl, 0.0)

    def test_compute_trade_outcomes_invalid_trades_skipped(self):
        """Test trades with missing data are skipped."""
        now = datetime.now()
        trades = [
            {"timestamp": now, "symbol": "ABC", "side": "buy", "qty": 10, "filled_avg_price": 100},
            {"timestamp": now, "symbol": "", "side": "buy", "qty": 10, "filled_avg_price": 100},  # No symbol
            {"timestamp": now, "symbol": "DEF", "side": "buy", "qty": 0, "filled_avg_price": 100},  # Zero qty
            {"timestamp": now, "symbol": "GHI", "side": "buy", "qty": 10, "filled_avg_price": 0},  # Zero price
            {"timestamp": now + timedelta(hours=1), "symbol": "ABC", "side": "sell", "qty": 10, "filled_avg_price": 110},
        ]
        stats = compute_trade_outcomes(trades)
        # Should only count valid ABC trades
        self.assertEqual(stats.total, 2)
        self.assertEqual(stats.win_trades, 1)

    def test_compute_trade_outcomes_win_rate_calculation(self):
        """Test win rate percentage calculation."""
        now = datetime.now()
        trades = [
            {"timestamp": now, "symbol": "A", "side": "buy", "qty": 10, "filled_avg_price": 100},
            {"timestamp": now, "symbol": "B", "side": "buy", "qty": 10, "filled_avg_price": 100},
            {"timestamp": now, "symbol": "C", "side": "buy", "qty": 10, "filled_avg_price": 100},
            {"timestamp": now, "symbol": "D", "side": "buy", "qty": 10, "filled_avg_price": 100},
            {"timestamp": now + timedelta(hours=1), "symbol": "A", "side": "sell", "qty": 10, "filled_avg_price": 110},  # Win
            {"timestamp": now + timedelta(hours=1), "symbol": "B", "side": "sell", "qty": 10, "filled_avg_price": 110},  # Win
            {"timestamp": now + timedelta(hours=1), "symbol": "C", "side": "sell", "qty": 10, "filled_avg_price": 110},  # Win
            {"timestamp": now + timedelta(hours=1), "symbol": "D", "side": "sell", "qty": 10, "filled_avg_price": 90},   # Loss
        ]
        stats = compute_trade_outcomes(trades)
        # 3 wins out of 4 sells = 75%
        self.assertAlmostEqual(stats.win_rate_pct, 75.0)

    def test_compute_trade_outcomes_no_sells(self):
        """Test win rate is 0 when no sells (all buys)."""
        now = datetime.now()
        trades = [
            {"timestamp": now, "symbol": "ABC", "side": "buy", "qty": 10, "filled_avg_price": 100},
            {"timestamp": now, "symbol": "DEF", "side": "buy", "qty": 10, "filled_avg_price": 100},
        ]
        stats = compute_trade_outcomes(trades)
        self.assertEqual(stats.sells, 0)
        self.assertEqual(stats.win_rate_pct, 0.0)


if __name__ == "__main__":
    unittest.main()

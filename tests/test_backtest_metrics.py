"""Tests for backtest/metrics.py - Performance calculations."""

import unittest
import pandas as pd
import numpy as np
from datetime import datetime

from backtest.metrics import (
    calculate_sharpe_ratio,
    calculate_max_drawdown,
    calculate_sortino_ratio,
    calculate_metrics,
    calculate_trade_statistics
)


class TestMetricCalculations(unittest.TestCase):
    """Test performance metric calculations."""

    def test_sharpe_ratio_positive_returns(self):
        """Test Sharpe ratio with positive returns."""
        # Create returns with mean > 0
        returns = pd.Series([0.01, 0.02, -0.005, 0.015, 0.01])
        sharpe = calculate_sharpe_ratio(returns, risk_free_rate=0.0)

        # Sharpe should be positive for positive mean returns
        self.assertGreater(sharpe, 0)

    def test_sharpe_ratio_negative_returns(self):
        """Test Sharpe ratio with negative returns."""
        # Create returns with mean < 0
        returns = pd.Series([-0.01, -0.02, 0.005, -0.015, -0.01])
        sharpe = calculate_sharpe_ratio(returns, risk_free_rate=0.0)

        # Sharpe should be negative for negative mean returns
        self.assertLess(sharpe, 0)

    def test_sharpe_ratio_with_risk_free_rate(self):
        """Test Sharpe ratio accounts for risk-free rate."""
        returns = pd.Series([0.01, 0.02, 0.015, 0.01, 0.02])
        sharpe_no_rf = calculate_sharpe_ratio(returns, risk_free_rate=0.0)
        sharpe_with_rf = calculate_sharpe_ratio(returns, risk_free_rate=0.05)

        # Sharpe with risk-free rate should be lower
        self.assertLess(sharpe_with_rf, sharpe_no_rf)

    def test_max_drawdown_declining_equity(self):
        """Test max drawdown with continuously declining equity."""
        # Equity drops from 100 to 50
        dates = pd.date_range('2023-01-01', periods=6, freq='D')
        equity_curve = pd.Series([100, 90, 80, 70, 60, 50], index=dates)
        max_dd, duration = calculate_max_drawdown(equity_curve)

        # Max drawdown should be 50% (from 100 to 50)
        self.assertAlmostEqual(max_dd, 0.5, places=2)

    def test_max_drawdown_with_recovery(self):
        """Test max drawdown with drawdown and recovery."""
        # Equity: 100 -> 70 -> 100 -> 60
        dates = pd.date_range('2023-01-01', periods=8, freq='D')
        equity_curve = pd.Series([100, 90, 80, 70, 85, 100, 80, 60], index=dates)
        max_dd, duration = calculate_max_drawdown(equity_curve)

        # Max drawdown is 40% (from 100 to 60)
        self.assertAlmostEqual(max_dd, 0.4, places=2)

    def test_max_drawdown_always_rising(self):
        """Test max drawdown with always rising equity."""
        dates = pd.date_range('2023-01-01', periods=5, freq='D')
        equity_curve = pd.Series([100, 110, 120, 130, 140], index=dates)
        max_dd, duration = calculate_max_drawdown(equity_curve)

        # No drawdown
        self.assertEqual(max_dd, 0.0)

    def test_sortino_ratio_positive_returns(self):
        """Test Sortino ratio with mixed returns."""
        # Mix of positive and negative returns
        returns = pd.Series([0.02, -0.01, 0.03, -0.005, 0.015])
        sortino = calculate_sortino_ratio(returns, risk_free_rate=0.0)

        # Should be positive with overall positive returns
        self.assertGreater(sortino, 0)

    def test_trade_statistics(self):
        """Test trade statistics calculation."""
        trades = [
            {'pnl': 100, 'pnl_pct': 0.10},
            {'pnl': -50, 'pnl_pct': -0.05},
            {'pnl': 75, 'pnl_pct': 0.075},
            {'pnl': -25, 'pnl_pct': -0.025},
        ]

        stats = calculate_trade_statistics(trades)

        # Check that basic stats are calculated
        self.assertEqual(stats['total_trades'], 4)
        self.assertEqual(stats['winning_trades'], 2)
        self.assertEqual(stats['losing_trades'], 2)
        self.assertEqual(stats['win_rate'], 0.5)  # 50%

        # Profit factor = total wins / total losses
        # (100 + 75) / (50 + 25) = 175 / 75 = 2.33
        self.assertAlmostEqual(stats['profit_factor'], 2.33, places=1)

    def test_calculate_metrics_integration(self):
        """Test calculate_metrics with full dataset."""
        # Create realistic backtest data
        dates = pd.date_range('2023-01-01', periods=10, freq='D')
        equity_curve = pd.Series([
            10000, 10100, 10050, 10200, 10150,
            10300, 10250, 10400, 10350, 10500
        ], index=dates)

        position_series = pd.Series([
            0, 1000, 1000, 0, 2000,
            2000, 0, 1500, 1500, 0
        ], index=dates)

        trades = [
            {'symbol': 'AAPL', 'pnl': 100, 'pnl_pct': 0.01, 'duration_days': 1},
            {'symbol': 'GOOGL', 'pnl': -50, 'pnl_pct': -0.005, 'duration_days': 1},
            {'symbol': 'MSFT', 'pnl': 150, 'pnl_pct': 0.015, 'duration_days': 1},
            {'symbol': 'TSLA', 'pnl': -50, 'pnl_pct': -0.005, 'duration_days': 1},
            {'symbol': 'NVDA', 'pnl': 150, 'pnl_pct': 0.015, 'duration_days': 1},
        ]

        metrics = calculate_metrics(
            equity_curve=equity_curve,
            trades=trades,
            position_series=position_series,
            initial_capital=10000
        )

        # Verify metrics object is returned
        self.assertIsNotNone(metrics)

        # Verify all expected attributes are present
        self.assertTrue(hasattr(metrics, 'total_return'))
        self.assertTrue(hasattr(metrics, 'sharpe_ratio'))
        self.assertTrue(hasattr(metrics, 'max_drawdown'))
        self.assertTrue(hasattr(metrics, 'win_rate'))
        self.assertTrue(hasattr(metrics, 'profit_factor'))
        self.assertTrue(hasattr(metrics, 'total_trades'))

        # Verify reasonable values
        self.assertGreater(metrics.total_return, 0)  # Made money
        self.assertEqual(metrics.total_trades, 5)
        self.assertGreaterEqual(metrics.win_rate, 0)
        self.assertLessEqual(metrics.win_rate, 1)

    def test_daily_loss_and_drawdown_limits(self):
        """Test daily loss limit hits and drawdown limit flag."""
        dates = pd.date_range('2023-01-01', periods=5, freq='D')
        equity_curve = pd.Series([10000, 9800, 9700, 9900, 9500], index=dates)
        position_series = pd.Series([0, 0, 0, 0, 0], index=dates)

        metrics = calculate_metrics(
            equity_curve=equity_curve,
            trades=[],
            position_series=position_series,
            initial_capital=10000,
            daily_loss_limit_pct=0.01,
            max_drawdown_limit_pct=0.05,
        )

        self.assertGreaterEqual(metrics.daily_loss_limit_hits, 1)
        self.assertTrue(metrics.drawdown_limit_hit)

    def test_trade_statistics_empty_trades(self):
        """Test trade statistics with no trades."""
        trades = []
        stats = calculate_trade_statistics(trades)

        self.assertEqual(stats['total_trades'], 0)
        self.assertEqual(stats['win_rate'], 0.0)


if __name__ == '__main__':
    unittest.main()

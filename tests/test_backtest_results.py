"""Tests for backtest/results.py - Results formatting and export."""

import unittest
import pandas as pd
import json
import tempfile
import os
from datetime import datetime

from backtest.results import BacktestResults, PerformanceMetrics, Trade


class TestPerformanceMetrics(unittest.TestCase):
    """Test PerformanceMetrics dataclass."""

    def test_performance_metrics_creation(self):
        """Test creating performance metrics object."""
        metrics = PerformanceMetrics(
            total_return=0.25,
            total_return_pct=0.25,
            annualized_return=0.15,
            sharpe_ratio=1.5,
            sortino_ratio=2.0,
            max_drawdown=0.10,
            max_drawdown_duration=10,
            win_rate=0.60,
            profit_factor=2.5,
            total_trades=50,
            winning_trades=30,
            losing_trades=20,
            avg_win=150.0,
            avg_loss=-75.0,
            avg_trade=50.0,
            largest_win=500.0,
            largest_loss=-200.0,
            exposure_time=0.75,
            avg_position_duration=5.5,
            benchmark_return=0.12,
            alpha=0.03,
            beta=1.2,
            volatility=0.18
        )

        self.assertEqual(metrics.total_return, 0.25)
        self.assertEqual(metrics.sharpe_ratio, 1.5)
        self.assertEqual(metrics.total_trades, 50)
        self.assertEqual(metrics.win_rate, 0.60)

    def test_performance_metrics_to_dict(self):
        """Test converting metrics to dictionary."""
        metrics = PerformanceMetrics(
            total_return=0.25,
            total_return_pct=0.25,
            annualized_return=0.15,
            sharpe_ratio=1.5,
            sortino_ratio=2.0,
            max_drawdown=0.10,
            max_drawdown_duration=10,
            win_rate=0.60,
            profit_factor=2.5,
            total_trades=50,
            winning_trades=30,
            losing_trades=20,
            avg_win=150.0,
            avg_loss=-75.0,
            avg_trade=50.0,
            largest_win=500.0,
            largest_loss=-200.0,
            exposure_time=0.75,
            avg_position_duration=5.5,
            volatility=0.18
        )

        metrics_dict = metrics.__dict__

        self.assertIn('total_return', metrics_dict)
        self.assertIn('sharpe_ratio', metrics_dict)
        self.assertEqual(metrics_dict['total_return'], 0.25)


class TestBacktestResults(unittest.TestCase):
    """Test BacktestResults class."""

    def setUp(self):
        """Set up test fixtures."""
        self.metrics = PerformanceMetrics(
            total_return=0.25,
            total_return_pct=0.25,
            annualized_return=0.15,
            sharpe_ratio=1.5,
            sortino_ratio=2.0,
            max_drawdown=0.10,
            max_drawdown_duration=10,
            win_rate=0.60,
            profit_factor=2.5,
            total_trades=10,
            winning_trades=6,
            losing_trades=4,
            avg_win=150.0,
            avg_loss=-75.0,
            avg_trade=50.0,
            largest_win=500.0,
            largest_loss=-200.0,
            exposure_time=0.75,
            avg_position_duration=5.5,
            volatility=0.18
        )

        dates = pd.date_range('2023-01-01', periods=10, freq='D')
        self.equity_curve = pd.Series([
            10000, 10100, 10050, 10200, 10150,
            10300, 10250, 10400, 10350, 10500
        ], index=dates)

        self.trades = [
            Trade(
                symbol='AAPL',
                side='buy',
                entry_date=datetime(2023, 1, 5),
                entry_price=150.0,
                exit_date=datetime(2023, 1, 10),
                exit_price=160.0,
                quantity=10,
                pnl=100.0,
                pnl_pct=0.0667,
                duration_days=5,
                reason='Test trade'
            )
        ]

        self.position_history = pd.DataFrame({
            'value': [0, 1500, 1550, 1600, 0]
        })

    def test_backtest_results_creation(self):
        """Test creating BacktestResults object."""
        results = BacktestResults(
            symbols=['AAPL'],
            start_date='2023-01-01',
            end_date='2023-12-31',
            initial_capital=10000,
            strategy_name='TestStrategy',
            strategy_params={'param1': 0.5},
            metrics=self.metrics,
            equity_curve=self.equity_curve,
            trades=self.trades,
            position_history=self.position_history
        )

        self.assertEqual(results.metrics, self.metrics)
        self.assertTrue(results.equity_curve.equals(self.equity_curve))
        self.assertEqual(len(results.trades), 1)

    def test_to_dict(self):
        """Test converting results to dictionary."""
        results = BacktestResults(
            symbols=['AAPL'],
            start_date='2023-01-01',
            end_date='2023-12-31',
            initial_capital=10000,
            strategy_name='TestStrategy',
            strategy_params={'param1': 0.5},
            metrics=self.metrics,
            equity_curve=self.equity_curve,
            trades=self.trades,
            position_history=self.position_history
        )

        results_dict = results.to_dict()

        self.assertIn('metrics', results_dict)
        self.assertIn('trades', results_dict)
        self.assertEqual(results_dict['metrics']['total_return'], 0.25)
        self.assertEqual(len(results_dict['trades']), 1)

    def test_to_json_file(self):
        """Test exporting results to JSON file."""
        results = BacktestResults(
            symbols=['AAPL'],
            start_date='2023-01-01',
            end_date='2023-12-31',
            initial_capital=10000,
            strategy_name='TestStrategy',
            strategy_params={'param1': 0.5},
            metrics=self.metrics,
            equity_curve=self.equity_curve,
            trades=self.trades,
            position_history=self.position_history
        )

        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json_path = f.name

        try:
            results.to_json(json_path)

            # Verify file was created
            self.assertTrue(os.path.exists(json_path))

            # Load and verify contents
            with open(json_path, 'r') as f:
                data = json.load(f)

            self.assertIn('metrics', data)
            self.assertIn('equity_curve', data)
            self.assertIn('trades', data)
            self.assertEqual(data['metrics']['total_return'], 0.25)

        finally:
            # Clean up
            if os.path.exists(json_path):
                os.remove(json_path)

    def test_to_csv_file(self):
        """Test exporting equity curve to CSV file."""
        results = BacktestResults(
            symbols=['AAPL'],
            start_date='2023-01-01',
            end_date='2023-12-31',
            initial_capital=10000,
            strategy_name='TestStrategy',
            strategy_params={'param1': 0.5},
            metrics=self.metrics,
            equity_curve=self.equity_curve,
            trades=self.trades,
            position_history=self.position_history
        )

        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            csv_path = f.name

        try:
            results.to_csv(csv_path)

            # Verify file was created
            self.assertTrue(os.path.exists(csv_path))

            # Load and verify contents
            df = pd.read_csv(csv_path)

            self.assertGreater(len(df), 0)
            self.assertIn('portfolio_value', df.columns)

        finally:
            # Clean up
            if os.path.exists(csv_path):
                os.remove(csv_path)

    def test_summary_string(self):
        """Test summary string generation."""
        results = BacktestResults(
            symbols=['AAPL'],
            start_date='2023-01-01',
            end_date='2023-12-31',
            initial_capital=10000,
            strategy_name='TestStrategy',
            strategy_params={'param1': 0.5},
            metrics=self.metrics,
            equity_curve=self.equity_curve,
            trades=self.trades,
            position_history=self.position_history,
            benchmark_symbol='SPY'
        )

        summary = results.summary()

        # Verify key information is in summary
        self.assertIn('BACKTEST RESULTS', summary)
        self.assertIn('AAPL', summary)
        self.assertIn('TestStrategy', summary)

    def test_summary_with_benchmark(self):
        """Test summary includes benchmark when provided."""
        results = BacktestResults(
            symbols=['AAPL'],
            start_date='2023-01-01',
            end_date='2023-12-31',
            initial_capital=10000,
            strategy_name='TestStrategy',
            strategy_params={'param1': 0.5},
            metrics=self.metrics,
            equity_curve=self.equity_curve,
            trades=self.trades,
            position_history=self.position_history,
            benchmark_symbol='SPY'
        )

        summary = results.summary()

        self.assertIn('BACKTEST RESULTS', summary)

    def test_empty_trades_list(self):
        """Test results with no trades."""
        metrics = PerformanceMetrics(
            total_return=0.0,
            total_return_pct=0.0,
            annualized_return=0.0,
            sharpe_ratio=0.0,
            sortino_ratio=0.0,
            max_drawdown=0.0,
            max_drawdown_duration=0,
            win_rate=0.0,
            profit_factor=0.0,
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            avg_win=0.0,
            avg_loss=0.0,
            avg_trade=0.0,
            largest_win=0.0,
            largest_loss=0.0,
            exposure_time=0.0,
            avg_position_duration=0.0,
            volatility=0.0
        )

        dates = pd.date_range('2023-01-01', periods=10, freq='D')
        equity_curve = pd.Series([10000] * 10, index=dates)
        position_history = pd.DataFrame({'value': [0] * 10}, index=dates)

        results = BacktestResults(
            symbols=['TEST'],
            start_date='2023-01-01',
            end_date='2023-12-31',
            initial_capital=10000,
            strategy_name='TestStrategy',
            strategy_params={},
            metrics=metrics,
            equity_curve=equity_curve,
            trades=[],
            position_history=position_history
        )

        self.assertEqual(len(results.trades), 0)
        self.assertEqual(results.metrics.total_trades, 0)

        # Should still generate summary without errors
        summary = results.summary()
        self.assertIn('BACKTEST RESULTS', summary)


if __name__ == '__main__':
    unittest.main()

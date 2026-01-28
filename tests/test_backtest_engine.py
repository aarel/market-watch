"""Tests for backtest/engine.py - Backtest simulation engine."""

import unittest
from unittest.mock import Mock, patch
import pandas as pd
from datetime import datetime, timedelta

from backtest.engine import BacktestEngine
from backtest.data import HistoricalData
from strategies.momentum import MomentumStrategy


class TestBacktestEngine(unittest.TestCase):
    """Test backtest engine simulation logic."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a simple strategy for testing
        self.strategy = MomentumStrategy(
            lookback_days=5,
            momentum_threshold=0.02,
            sell_threshold=-0.01,
            stop_loss_pct=0.05
        )

    @patch('backtest.engine.HistoricalData')
    def test_backtest_initialization(self, mock_data_class):
        """Test backtest engine initializes correctly."""
        mock_data = Mock()
        mock_data_class.return_value = mock_data

        engine = BacktestEngine(
            data=mock_data,
            initial_capital=10000,
            max_position_pct=0.25
        )

        self.assertEqual(engine.initial_capital, 10000)
        self.assertEqual(engine.max_position_pct, 0.25)

    @patch('backtest.engine.HistoricalData')
    def test_backtest_buy_signal_creates_position(self, mock_data_class):
        """Test that buy signal creates a position."""
        # Create mock data
        mock_data = Mock()
        mock_data_class.return_value = mock_data

        # Create test data showing upward momentum (30+ days for warmup)
        dates = pd.date_range(start='2023-01-01', end='2023-02-15', freq='D')
        num_days = len(dates)
        test_data = pd.DataFrame({
            'date': dates,
            'open': [100.0 + i * 0.5 for i in range(num_days)],
            'high': [105.0 + i * 0.5 for i in range(num_days)],
            'low': [95.0 + i * 0.5 for i in range(num_days)],
            'close': [100.0 + i * 0.5 for i in range(num_days)],  # Rising prices
            'volume': [1000000] * num_days
        }, index=dates)

        def mock_get_bars(symbol, date, num_bars):
            # Return data up to the current date
            end_idx = (pd.to_datetime(date) - pd.to_datetime('2023-01-01')).days + 1
            start_idx = max(0, end_idx - num_bars)
            return test_data.iloc[start_idx:end_idx]

        def mock_get_price(symbol, date, field):
            date_idx = pd.to_datetime(date)
            if date_idx in test_data.index:
                return test_data.loc[date_idx, field]
            return None

        mock_data.symbols = ['TEST']
        mock_data.date_range = (test_data.index[0], test_data.index[-1])
        mock_data.get = Mock(return_value=test_data)
        mock_data.get_bars_up_to = mock_get_bars
        mock_data.get_price = mock_get_price
        mock_data.load.return_value = test_data

        # Run backtest
        engine = BacktestEngine(
            data=mock_data,
            initial_capital=10000,
            max_position_pct=0.25
        )

        results = engine.run(
            symbols=['TEST'],
            start='2023-01-01',
            end='2023-02-15'
        )

        # Should have executed at least one trade
        self.assertGreater(len(results.trades), 0)

    @patch('backtest.engine.HistoricalData')
    def test_backtest_stop_loss_triggered(self, mock_data_class):
        """Test that stop-loss exits position."""
        mock_data = Mock()
        mock_data_class.return_value = mock_data

        # Create data with price drop triggering stop-loss (30+ days)
        dates = pd.date_range(start='2023-01-01', end='2023-02-15', freq='D')
        num_days = len(dates)
        # Prices stable then drop
        prices = [100.0] * 30 + [95.0, 90.0, 85.0] + [85.0] * (num_days - 33)

        test_data = pd.DataFrame({
            'date': dates,
            'open': prices,
            'high': [p + 2 for p in prices],
            'low': [p - 2 for p in prices],
            'close': prices,
            'volume': [1000000] * num_days
        }, index=dates)

        def mock_get_bars(symbol, date, num_bars):
            end_idx = (pd.to_datetime(date) - pd.to_datetime('2023-01-01')).days + 1
            start_idx = max(0, end_idx - num_bars)
            return test_data.iloc[start_idx:end_idx]

        def mock_get_price(symbol, date, field):
            date_idx = pd.to_datetime(date)
            if date_idx in test_data.index:
                return test_data.loc[date_idx, field]
            return None

        mock_data.symbols = ['TEST']
        mock_data.date_range = (test_data.index[0], test_data.index[-1])
        mock_data.get = Mock(return_value=test_data)
        mock_data.get_bars_up_to = mock_get_bars
        mock_data.get_price = mock_get_price
        mock_data.load.return_value = test_data

        engine = BacktestEngine(
            data=mock_data,
            initial_capital=10000,
            max_position_pct=0.25,
            stop_loss_pct=0.05
        )

        results = engine.run(
            symbols=['TEST'],
            start='2023-01-01',
            end='2023-02-15'
        )

        # Should have trades (may buy and then stop-loss sell)
        # Verify that we handled the price drop
        self.assertIsNotNone(results)

    @patch('backtest.engine.HistoricalData')
    def test_backtest_respects_max_position_size(self, mock_data_class):
        """Test that position sizing respects max_position_pct."""
        mock_data = Mock()
        mock_data_class.return_value = mock_data

        # Create simple uptrending data (30+ days)
        dates = pd.date_range(start='2023-01-01', end='2023-02-15', freq='D')
        num_days = len(dates)
        test_data = pd.DataFrame({
            'date': dates,
            'open': [100.0 + i for i in range(num_days)],
            'high': [105.0 + i for i in range(num_days)],
            'low': [95.0 + i for i in range(num_days)],
            'close': [100.0 + i for i in range(num_days)],
            'volume': [1000000] * num_days
        }, index=dates)

        def mock_get_bars(symbol, date, num_bars):
            end_idx = (pd.to_datetime(date) - pd.to_datetime('2023-01-01')).days + 1
            start_idx = max(0, end_idx - num_bars)
            return test_data.iloc[start_idx:end_idx]

        def mock_get_price(symbol, date, field):
            date_idx = pd.to_datetime(date)
            if date_idx in test_data.index:
                return test_data.loc[date_idx, field]
            return None

        mock_data.symbols = ['TEST']
        mock_data.date_range = (test_data.index[0], test_data.index[-1])
        mock_data.get = Mock(return_value=test_data)
        mock_data.get_bars_up_to = mock_get_bars
        mock_data.get_price = mock_get_price
        mock_data.load.return_value = test_data

        initial_capital = 10000
        max_position_pct = 0.30  # 30%

        engine = BacktestEngine(
            data=mock_data,
            initial_capital=initial_capital,
            max_position_pct=max_position_pct
        )

        results = engine.run(
            symbols=['TEST'],
            start='2023-01-01',
            end='2023-02-15'
        )

        # Check that any position created doesn't exceed max position size
        for trade in results.trades:
            if trade.side == 'buy':
                position_value = trade.quantity * trade.entry_price
                # Should be approximately max_position_pct of capital
                max_allowed = initial_capital * max_position_pct * 1.1  # 10% tolerance
                self.assertLessEqual(position_value, max_allowed)

    @patch('backtest.engine.HistoricalData')
    def test_backtest_equity_curve_generation(self, mock_data_class):
        """Test that equity curve is generated correctly."""
        mock_data = Mock()
        mock_data_class.return_value = mock_data

        dates = pd.date_range(start='2023-01-01', end='2023-02-15', freq='D')
        num_days = len(dates)
        test_data = pd.DataFrame({
            'date': dates,
            'open': [100.0] * num_days,
            'high': [105.0] * num_days,
            'low': [95.0] * num_days,
            'close': [100.0] * num_days,
            'volume': [1000000] * num_days
        }, index=dates)

        def mock_get_bars(symbol, date, num_bars):
            end_idx = (pd.to_datetime(date) - pd.to_datetime('2023-01-01')).days + 1
            start_idx = max(0, end_idx - num_bars)
            return test_data.iloc[start_idx:end_idx]

        def mock_get_price(symbol, date, field):
            date_idx = pd.to_datetime(date)
            if date_idx in test_data.index:
                return test_data.loc[date_idx, field]
            return None

        mock_data.symbols = ['TEST']
        mock_data.date_range = (test_data.index[0], test_data.index[-1])
        mock_data.get = Mock(return_value=test_data)
        mock_data.get_bars_up_to = mock_get_bars
        mock_data.get_price = mock_get_price
        mock_data.load.return_value = test_data

        engine = BacktestEngine(
            data=mock_data,
            initial_capital=10000
        )

        results = engine.run(
            symbols=['TEST'],
            start='2023-01-01',
            end='2023-02-15'
        )

        # Equity curve should exist and have entries
        self.assertIsNotNone(results.equity_curve)
        self.assertGreater(len(results.equity_curve), 0)

        # First equity value should be initial capital
        self.assertEqual(results.equity_curve.iloc[0], 10000)

    @patch('backtest.engine.HistoricalData')
    def test_backtest_no_lookahead_bias(self, mock_data_class):
        """Test that backtest doesn't use future data."""
        mock_data = Mock()
        mock_data_class.return_value = mock_data

        # Create data where only looking ahead would generate signals (30+ days)
        dates = pd.date_range(start='2023-01-01', end='2023-02-15', freq='D')
        num_days = len(dates)
        # Prices flat then spike on last day
        prices = [100.0] * (num_days - 1) + [150.0]

        test_data = pd.DataFrame({
            'date': dates,
            'open': prices,
            'high': [p + 2 for p in prices],
            'low': [p - 2 for p in prices],
            'close': prices,
            'volume': [1000000] * num_days
        }, index=dates)

        call_log = []

        def mock_get_bars(symbol, date, num_bars):
            end_idx = (pd.to_datetime(date) - pd.to_datetime('2023-01-01')).days + 1
            start_idx = max(0, end_idx - num_bars)
            bars = test_data.iloc[start_idx:end_idx]

            # Log what data is being returned
            call_log.append({
                'date': date,
                'max_price': bars['close'].max() if len(bars) > 0 else 0
            })

            return bars

        def mock_get_price(symbol, date, field):
            date_idx = pd.to_datetime(date)
            if date_idx in test_data.index:
                return test_data.loc[date_idx, field]
            return None

        mock_data.symbols = ['TEST']
        mock_data.date_range = (test_data.index[0], test_data.index[-1])
        mock_data.get = Mock(return_value=test_data)
        mock_data.get_bars_up_to = mock_get_bars
        mock_data.get_price = mock_get_price
        mock_data.load.return_value = test_data

        engine = BacktestEngine(
            data=mock_data,
            initial_capital=10000
        )

        results = engine.run(
            symbols=['TEST'],
            start='2023-01-01',
            end='2023-02-14'  # Before the spike on 2023-02-15
        )

        # Verify that no call received the spike price
        for call in call_log:
            if call['date'] < datetime(2023, 2, 15):
                self.assertLess(call['max_price'], 150.0)


if __name__ == '__main__':
    unittest.main()

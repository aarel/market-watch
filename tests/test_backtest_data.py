"""Tests for backtest/data.py - Historical data management."""

import unittest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
from datetime import datetime, timedelta
import os
import tempfile
import shutil

from backtest.data import HistoricalData


class TestHistoricalData(unittest.TestCase):
    """Test historical data download and caching."""

    def setUp(self):
        """Create temporary directory for test data."""
        self.test_dir = tempfile.mkdtemp()
        self.data_manager = HistoricalData(data_dir=self.test_dir)

    def tearDown(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.test_dir)

    def test_init_creates_directory(self):
        """Test that initialization creates data directory."""
        self.assertTrue(os.path.exists(self.test_dir))

    @patch('backtest.data.tradeapi')
    def test_download_creates_csv(self, mock_tradeapi):
        """Test that download creates CSV files."""
        # Create mock DataFrame to return from get_bars().df
        dates = pd.date_range(start='2023-01-01', end='2023-01-10', freq='D')
        mock_df = pd.DataFrame({
            'open': [100.0 + i for i in range(len(dates))],
            'high': [105.0 + i for i in range(len(dates))],
            'low': [95.0 + i for i in range(len(dates))],
            'close': [102.0 + i for i in range(len(dates))],
            'volume': [1000000] * len(dates)
        }, index=dates)
        mock_df.index.name = 'timestamp'  # Set index name for CSV compatibility

        # Mock the API get_bars to return object with .df attribute
        mock_bars_result = Mock()
        mock_bars_result.df = mock_df

        mock_api = Mock()
        mock_api.get_bars.return_value = mock_bars_result
        mock_tradeapi.REST.return_value = mock_api

        # Download data
        self.data_manager.download(
            symbols=['AAPL'],
            start='2023-01-01',
            end='2023-01-10'
        )

        # Verify CSV was created
        csv_path = os.path.join(self.test_dir, 'AAPL_daily.csv')
        self.assertTrue(os.path.exists(csv_path))

        # Verify data in CSV (timestamp as index)
        df = pd.read_csv(csv_path, index_col='timestamp', parse_dates=True)
        self.assertEqual(len(df), len(dates))
        self.assertIn('open', df.columns)
        self.assertIn('high', df.columns)
        self.assertIn('low', df.columns)
        self.assertIn('close', df.columns)
        self.assertIn('volume', df.columns)

    def test_load_from_cache(self):
        """Test loading data from cached CSV."""
        # Create a test CSV with proper format (timestamp as index)
        test_data = pd.DataFrame({
            'open': [100.0 + i for i in range(10)],
            'high': [105.0 + i for i in range(10)],
            'low': [95.0 + i for i in range(10)],
            'close': [102.0 + i for i in range(10)],
            'volume': [1000000] * 10
        }, index=pd.date_range(start='2023-01-01', end='2023-01-10', freq='D'))
        test_data.index.name = 'timestamp'
        csv_path = os.path.join(self.test_dir, 'TEST_daily.csv')
        test_data.to_csv(csv_path)

        # Load from cache - load() expects a list of symbols
        loaded_data_dict = self.data_manager.load(['TEST'])

        self.assertIsNotNone(loaded_data_dict)
        self.assertIn('TEST', loaded_data_dict)
        loaded_data = loaded_data_dict['TEST']
        self.assertEqual(len(loaded_data), 10)
        self.assertIn('close', loaded_data.columns)

    def test_get_bars_up_to_no_lookahead(self):
        """Test that get_bars_up_to prevents lookahead bias."""
        # Create test data spanning 30 days with proper format
        test_data = pd.DataFrame({
            'open': [100.0 + i for i in range(30)],
            'high': [105.0 + i for i in range(30)],
            'low': [95.0 + i for i in range(30)],
            'close': [102.0 + i for i in range(30)],
            'volume': [1000000] * 30
        }, index=pd.date_range(start='2023-01-01', end='2023-01-30', freq='D'))
        test_data.index.name = 'timestamp'
        csv_path = os.path.join(self.test_dir, 'LOOK_daily.csv')
        test_data.to_csv(csv_path)

        # Load data first
        self.data_manager.load(['LOOK'])

        # Request 10 bars up to Jan 25 (we have 25 days available)
        target_date = pd.Timestamp('2023-01-25')
        bars = self.data_manager.get_bars_up_to('LOOK', target_date, num_bars=10)

        # Should get exactly 10 bars
        self.assertIsNotNone(bars)
        self.assertEqual(len(bars), 10)

        # Verify no data after target date (test for lookahead bias)
        last_date = bars.index[-1]
        self.assertLessEqual(last_date, target_date)

        # Verify we can't get future data
        future_bars = self.data_manager.get_bars_up_to('LOOK', pd.Timestamp('2023-01-10'), num_bars=20)
        # Should be None because we only have 10 days of data up to Jan 10
        self.assertIsNone(future_bars)

    def test_get_bars_up_to_returns_requested_amount(self):
        """Test that get_bars_up_to returns requested number when available."""
        # Create 30 days of data with proper format
        test_data = pd.DataFrame({
            'open': [100.0] * 30,
            'high': [105.0] * 30,
            'low': [95.0] * 30,
            'close': [102.0] * 30,
            'volume': [1000000] * 30
        }, index=pd.date_range(start='2023-01-01', end='2023-01-30', freq='D'))
        test_data.index.name = 'timestamp'
        csv_path = os.path.join(self.test_dir, 'COUNT_daily.csv')
        test_data.to_csv(csv_path)

        # Load data first
        self.data_manager.load(['COUNT'])

        # Request 10 bars up to Jan 25
        target_date = pd.Timestamp('2023-01-25')
        bars = self.data_manager.get_bars_up_to('COUNT', target_date, num_bars=10)

        # Should get exactly 10 bars ending on or before Jan 25
        self.assertEqual(len(bars), 10)

        # Verify last bar is on or before target date
        last_date = bars.index[-1]
        self.assertLessEqual(last_date, target_date)

    def test_load_nonexistent_symbol_returns_none(self):
        """Test that loading non-existent symbol returns empty dict."""
        result = self.data_manager.load(['NONEXISTENT'])
        # load() returns a dict, empty if symbol not found
        self.assertIsInstance(result, dict)
        self.assertEqual(len(result), 0)

    def test_get_bars_up_to_nonexistent_symbol_returns_none(self):
        """Test that get_bars_up_to for non-existent symbol returns None."""
        result = self.data_manager.get_bars_up_to(
            'NONEXISTENT',
            datetime(2023, 1, 15),
            num_bars=20
        )
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()

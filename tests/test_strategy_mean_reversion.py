"""Tests for strategies/mean_reversion.py - Mean reversion strategy."""

import unittest
import pandas as pd

from strategies.mean_reversion import MeanReversionStrategy
from strategies.base import SignalType


class TestMeanReversionStrategy(unittest.TestCase):
    """Test mean reversion strategy signal generation."""

    def setUp(self):
        """Set up test fixtures."""
        self.strategy = MeanReversionStrategy(
            ma_period=20,
            deviation_threshold=0.03,  # 3%
            return_threshold=0.01,  # 1%
            stop_loss_pct=0.05  # 5%
        )

    def test_buy_signal_price_below_ma(self):
        """Test buy signal when price is significantly below moving average."""
        # Create data where price is stable then drops (30 bars for ma_period=20)
        closes = [100.0] * 25 + [99.0, 98.0, 97.0, 96.0, 95.0]
        bars = pd.DataFrame({
            'open': closes,
            'high': [c + 1.0 for c in closes],
            'low': [c - 1.0 for c in closes],
            'close': closes,
            'volume': [1000000] * 30
        })

        # MA ~99.0, current price 93 is ~6% below (exceeds 3% threshold)
        signal = self.strategy.analyze(
            symbol='AAPL',
            bars=bars,
            current_price=93.0,  # Significantly below MA
            current_position=None
        )

        self.assertEqual(signal.action, SignalType.BUY)
        self.assertIn('oversold', signal.reason.lower())

    def test_hold_signal_price_near_ma(self):
        """Test hold signal when price is close to moving average."""
        bars = pd.DataFrame({
            'open': [100.0, 101.0, 102.0, 101.0, 100.0],
            'high': [101.0, 102.0, 103.0, 102.0, 101.0],
            'low': [99.0, 100.0, 101.0, 100.0, 99.0],
            'close': [100.0, 101.0, 102.0, 101.0, 100.0],
            'volume': [1000000] * 5
        })

        # Current price near MA (only 1% below)
        signal = self.strategy.analyze(
            symbol='AAPL',
            bars=bars,
            current_price=100.0,
            current_position=None
        )

        self.assertEqual(signal.action, SignalType.HOLD)
        self.assertIn('near ma', signal.reason.lower())

    def test_sell_signal_price_above_ma(self):
        """Test sell signal when holding position and price above MA."""
        # Create stable data with 30 bars
        closes = [95.0] * 30
        bars = pd.DataFrame({
            'open': closes,
            'high': [c + 1.0 for c in closes],
            'low': [c - 1.0 for c in closes],
            'close': closes,
            'volume': [1000000] * 30
        })

        position = {
            'quantity': 10,
            'entry_price': 93.0,
            'current_price': 96.0,
            'market_value': 960.0,
            'unrealized_pnl': 30.0,
            'unrealized_pnl_pct': 0.0323  # 3.23% profit
        }

        # MA = 95, current price 96 is ~1.05% above MA (exceeds return_threshold of 1%)
        signal = self.strategy.analyze(
            symbol='AAPL',
            bars=bars,
            current_price=96.0,
            current_position=position
        )

        self.assertEqual(signal.action, SignalType.SELL)
        self.assertIn('returned to ma', signal.reason.lower())

    def test_sell_signal_stop_loss(self):
        """Test sell signal when stop-loss is triggered."""
        bars = pd.DataFrame({
            'open': [100.0] * 5,
            'high': [101.0] * 5,
            'low': [99.0] * 5,
            'close': [100.0] * 5,
            'volume': [1000000] * 5
        })

        # Position with >5% loss
        position = {
            'quantity': 10,
            'entry_price': 105.0,
            'current_price': 99.0,
            'market_value': 990.0,
            'unrealized_pnl': -60.0,
            'unrealized_pnl_pct': -0.0571  # -5.71%
        }

        signal = self.strategy.analyze(
            symbol='AAPL',
            bars=bars,
            current_price=99.0,
            current_position=position
        )

        self.assertEqual(signal.action, SignalType.SELL)
        self.assertIn('stop loss', signal.reason.lower())

    def test_hold_with_position_near_ma(self):
        """Test hold signal when holding position and price near MA."""
        bars = pd.DataFrame({
            'open': [100.0] * 5,
            'high': [101.0] * 5,
            'low': [99.0] * 5,
            'close': [100.0] * 5,
            'volume': [1000000] * 5
        })

        position = {
            'quantity': 10,
            'entry_price': 99.0,
            'current_price': 100.0,
            'market_value': 1000.0,
            'unrealized_pnl': 10.0,
            'unrealized_pnl_pct': 0.0101  # 1.01% (below sell threshold)
        }

        signal = self.strategy.analyze(
            symbol='AAPL',
            bars=bars,
            current_price=100.0,
            current_position=position
        )

        # Should hold since price is near MA and below sell threshold
        self.assertEqual(signal.action, SignalType.HOLD)

    def test_insufficient_data_for_ma(self):
        """Test behavior with insufficient data for moving average."""
        # Only 2 bars, but strategy requires 20
        bars = pd.DataFrame({
            'open': [100.0, 101.0],
            'high': [101.0, 102.0],
            'low': [99.0, 100.0],
            'close': [100.0, 101.0],
            'volume': [1000000, 1000000]
        })

        signal = self.strategy.analyze(
            symbol='AAPL',
            bars=bars,
            current_price=101.0,
            current_position=None
        )

        # Should still calculate MA with available data
        self.assertIsNotNone(signal)

    def test_get_parameters(self):
        """Test retrieving strategy parameters."""
        params = self.strategy.get_parameters()

        self.assertEqual(params['ma_period'], 20)
        self.assertEqual(params['deviation_threshold'], 0.03)
        self.assertEqual(params['return_threshold'], 0.01)
        self.assertEqual(params['stop_loss_pct'], 0.05)

    def test_strategy_metadata(self):
        """Test strategy name and description."""
        self.assertEqual(self.strategy.name, "Mean Reversion Strategy")
        self.assertIn('ma', self.strategy.description.lower())
        self.assertEqual(self.strategy.required_history, 25)  # ma_period (20) + 5

    def test_signal_metadata_includes_ma_and_deviation(self):
        """Test that signal metadata includes MA and deviation."""
        bars = pd.DataFrame({
            'open': [100.0, 101.0, 102.0, 103.0, 104.0],
            'high': [101.0, 102.0, 103.0, 104.0, 105.0],
            'low': [99.0, 100.0, 101.0, 102.0, 103.0],
            'close': [100.0, 101.0, 102.0, 103.0, 104.0],
            'volume': [1000000] * 5
        })

        signal = self.strategy.analyze(
            symbol='AAPL',
            bars=bars,
            current_price=98.0,
            current_position=None
        )

        self.assertIn('ma', signal.metadata)
        self.assertIn('deviation', signal.metadata)
        self.assertIsInstance(signal.metadata['ma'], float)
        self.assertIsInstance(signal.metadata['deviation'], float)


if __name__ == '__main__':
    unittest.main()

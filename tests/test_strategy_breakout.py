"""Tests for strategies/breakout.py - Breakout trading strategy."""

import unittest
import pandas as pd

from strategies.breakout import BreakoutStrategy
from strategies.base import SignalType


class TestBreakoutStrategy(unittest.TestCase):
    """Test breakout strategy signal generation."""

    def setUp(self):
        """Set up test fixtures."""
        self.strategy = BreakoutStrategy(
            lookback_days=20,
            breakout_threshold=0.01,  # 1% above high
            breakdown_threshold=0.01,  # 1% below low
            stop_loss_pct=0.05  # 5%
        )

    def test_buy_signal_breakout_above_high(self):
        """Test buy signal when price breaks above period high."""
        # Create consolidation then breakout (30 bars for lookback_days=20)
        closes = [100.0 + (i % 5) * 0.5 for i in range(30)]  # Consolidating pattern
        bars = pd.DataFrame({
            'open': closes,
            'high': [c + 2.0 for c in closes],  # Period high will be around 106.5
            'low': [c - 1.0 for c in closes],
            'close': closes,
            'volume': [1000000] * 30
        })

        # Current price 108.0 breaks above period high ~106.5 + 1% = 107.565
        signal = self.strategy.analyze(
            symbol='AAPL',
            bars=bars,
            current_price=108.0,
            current_position=None
        )

        self.assertEqual(signal.action, SignalType.BUY)
        self.assertIn('breakout', signal.reason.lower())

    def test_hold_signal_no_breakout(self):
        """Test hold signal when price hasn't broken out."""
        bars = pd.DataFrame({
            'open': [100.0, 101.0, 100.5, 101.0, 100.0],
            'high': [102.0, 102.5, 102.0, 102.5, 102.0],
            'low': [99.0, 99.5, 99.0, 99.5, 99.0],
            'close': [100.0, 101.0, 100.5, 101.0, 100.5],
            'volume': [1000000] * 5
        })

        # Current price 101.0 is well below breakout level
        signal = self.strategy.analyze(
            symbol='AAPL',
            bars=bars,
            current_price=101.0,
            current_position=None
        )

        self.assertEqual(signal.action, SignalType.HOLD)
        self.assertIn('channel', signal.reason.lower())

    def test_sell_signal_breakdown_below_low(self):
        """Test sell signal when holding position and price breaks down."""
        # Create consolidation pattern with 30 bars
        closes = [102.0 - (i % 5) * 0.5 for i in range(30)]
        bars = pd.DataFrame({
            'open': closes,
            'high': [c + 1.0 for c in closes],
            'low': [c - 2.0 for c in closes],  # Period low will be around 98.0
            'close': closes,
            'volume': [1000000] * 30
        })

        # Position with entry at 100.0, current at 96.0 = -4% (within 5% stop loss)
        position = {
            'quantity': 10,
            'entry_price': 100.0,
            'current_price': 96.0,
            'market_value': 960.0,
            'unrealized_pnl': -40.0,
            'unrealized_pnl_pct': -0.04  # -4% (doesn't trigger 5% stop loss)
        }

        # Current price 96.0 breaks below period low ~98.0 - 1% = 97.02
        signal = self.strategy.analyze(
            symbol='AAPL',
            bars=bars,
            current_price=96.0,
            current_position=position
        )

        self.assertEqual(signal.action, SignalType.SELL)
        self.assertIn('breakdown', signal.reason.lower())

    def test_sell_signal_stop_loss(self):
        """Test sell signal when stop-loss is triggered."""
        bars = pd.DataFrame({
            'open': [100.0] * 5,
            'high': [102.0] * 5,
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

    def test_period_high_calculation(self):
        """Test that period high is calculated correctly."""
        bars = pd.DataFrame({
            'open': [100.0, 102.0, 101.0, 103.0, 102.0],
            'high': [101.0, 105.0, 103.0, 107.0, 104.0],  # Max high = 107.0
            'low': [99.0, 100.0, 99.0, 101.0, 100.0],
            'close': [100.0, 102.0, 101.0, 103.0, 102.0],
            'volume': [1000000] * 5
        })

        period_high = bars['high'].max()
        self.assertEqual(period_high, 107.0)

    def test_period_low_calculation(self):
        """Test that period low is calculated correctly."""
        bars = pd.DataFrame({
            'open': [100.0, 102.0, 101.0, 103.0, 102.0],
            'high': [101.0, 105.0, 103.0, 107.0, 104.0],
            'low': [99.0, 100.0, 97.0, 101.0, 100.0],  # Min low = 97.0
            'close': [100.0, 102.0, 101.0, 103.0, 102.0],
            'volume': [1000000] * 5
        })

        period_low = bars['low'].min()
        self.assertEqual(period_low, 97.0)

    def test_hold_with_position_in_range(self):
        """Test hold signal when holding position and price in range."""
        bars = pd.DataFrame({
            'open': [100.0, 101.0, 100.5, 101.0, 100.0],
            'high': [102.0, 102.5, 102.0, 102.5, 102.0],
            'low': [99.0, 99.5, 99.0, 99.5, 99.0],
            'close': [100.0, 101.0, 100.5, 101.0, 100.5],
            'volume': [1000000] * 5
        })

        position = {
            'quantity': 10,
            'entry_price': 100.0,
            'current_price': 101.0,
            'market_value': 1010.0,
            'unrealized_pnl': 10.0,
            'unrealized_pnl_pct': 0.01  # 1% profit
        }

        # Price 101.0 is within range (not breakout or breakdown)
        signal = self.strategy.analyze(
            symbol='AAPL',
            bars=bars,
            current_price=101.0,
            current_position=position
        )

        self.assertEqual(signal.action, SignalType.HOLD)

    def test_breakout_threshold_calculation(self):
        """Test breakout level calculation."""
        period_high = 100.0
        threshold = 0.02  # 2%
        breakout_level = period_high * (1 + threshold)

        self.assertEqual(breakout_level, 102.0)

    def test_breakdown_threshold_calculation(self):
        """Test breakdown level calculation."""
        period_low = 100.0
        threshold = 0.02  # 2%
        breakdown_level = period_low * (1 - threshold)

        self.assertEqual(breakdown_level, 98.0)

    def test_narrow_range_no_breakout(self):
        """Test that narrow consolidation doesn't trigger false breakouts."""
        # Tight consolidation
        bars = pd.DataFrame({
            'open': [100.0, 100.1, 100.2, 100.1, 100.0],
            'high': [100.2, 100.3, 100.4, 100.3, 100.2],
            'low': [99.8, 99.9, 100.0, 99.9, 99.8],
            'close': [100.0, 100.1, 100.2, 100.1, 100.0],
            'volume': [1000000] * 5
        })

        # Price at 100.3 (just at high, not breaking out)
        signal = self.strategy.analyze(
            symbol='AAPL',
            bars=bars,
            current_price=100.3,
            current_position=None
        )

        # Should not buy unless price exceeds high + threshold
        # High = 100.4, breakout = 100.4 * 1.01 = 101.404
        self.assertEqual(signal.action, SignalType.HOLD)

    def test_get_parameters(self):
        """Test retrieving strategy parameters."""
        params = self.strategy.get_parameters()

        self.assertEqual(params['lookback_days'], 20)
        self.assertEqual(params['breakout_threshold'], 0.01)
        self.assertEqual(params['breakdown_threshold'], 0.01)
        self.assertEqual(params['stop_loss_pct'], 0.05)

    def test_strategy_metadata(self):
        """Test strategy name and description."""
        self.assertEqual(self.strategy.name, "Breakout Strategy")
        self.assertIn('breakout', self.strategy.description.lower())
        self.assertEqual(self.strategy.required_history, 25)

    def test_signal_metadata_includes_levels(self):
        """Test that signal metadata includes breakout/breakdown levels."""
        # Create consolidation pattern with 30 bars
        closes = [100.0 + (i % 5) * 0.5 for i in range(30)]
        bars = pd.DataFrame({
            'open': closes,
            'high': [c + 2.0 for c in closes],
            'low': [c - 1.0 for c in closes],
            'close': closes,
            'volume': [1000000] * 30
        })

        # Test BUY signal metadata (includes breakout_level)
        buy_signal = self.strategy.analyze(
            symbol='AAPL',
            bars=bars,
            current_price=108.0,
            current_position=None
        )

        self.assertEqual(buy_signal.action, SignalType.BUY)
        self.assertIn('period_high', buy_signal.metadata)
        self.assertIn('period_low', buy_signal.metadata)
        self.assertIn('breakout_level', buy_signal.metadata)


if __name__ == '__main__':
    unittest.main()

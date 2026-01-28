"""Tests for strategies/momentum.py - Momentum trading strategy."""

import unittest
import pandas as pd

from strategies.momentum import MomentumStrategy
from strategies.base import SignalType


class TestMomentumStrategy(unittest.TestCase):
    """Test momentum strategy signal generation."""

    def setUp(self):
        """Set up test fixtures."""
        self.strategy = MomentumStrategy(
            lookback_days=20,
            momentum_threshold=0.02,  # 2%
            sell_threshold=-0.01,  # -1%
            stop_loss_pct=0.05  # 5%
        )

    def test_buy_signal_strong_momentum(self):
        """Test buy signal when momentum exceeds threshold."""
        # Create data with 3% upward momentum
        bars = pd.DataFrame({
            'open': [100.0, 101.0, 102.0, 103.0],
            'high': [101.0, 102.0, 103.0, 104.0],
            'low': [99.0, 100.0, 101.0, 102.0],
            'close': [100.0, 101.0, 102.0, 103.0],
            'volume': [1000000] * 4
        })

        signal = self.strategy.analyze(
            symbol='AAPL',
            bars=bars,
            current_price=103.0,
            current_position=None
        )

        self.assertEqual(signal.action, SignalType.BUY)
        self.assertGreater(signal.strength, 0.02)
        self.assertIn('momentum', signal.reason.lower())

    def test_hold_signal_weak_momentum(self):
        """Test hold signal when momentum below threshold."""
        # Create data with only 1% momentum (below 2% threshold)
        bars = pd.DataFrame({
            'open': [100.0, 100.0, 100.5, 100.5],
            'high': [101.0, 101.0, 101.5, 101.5],
            'low': [99.0, 99.0, 99.5, 99.5],
            'close': [100.0, 100.0, 100.5, 101.0],
            'volume': [1000000] * 4
        })

        signal = self.strategy.analyze(
            symbol='AAPL',
            bars=bars,
            current_price=101.0,
            current_position=None
        )

        self.assertEqual(signal.action, SignalType.HOLD)
        self.assertIn('below threshold', signal.reason.lower())

    def test_sell_signal_momentum_reversal(self):
        """Test sell signal when momentum reverses while holding position."""
        # Create declining price data
        bars = pd.DataFrame({
            'open': [105.0, 104.0, 103.0, 102.0],
            'high': [106.0, 105.0, 104.0, 103.0],
            'low': [104.0, 103.0, 102.0, 101.0],
            'close': [105.0, 104.0, 103.0, 102.0],
            'volume': [1000000] * 4
        })

        position = {
            'quantity': 10,
            'entry_price': 105.0,
            'current_price': 102.0,
            'market_value': 1020.0,
            'unrealized_pnl': -30.0,
            'unrealized_pnl_pct': -0.0286  # -2.86%
        }

        signal = self.strategy.analyze(
            symbol='AAPL',
            bars=bars,
            current_price=102.0,
            current_position=position
        )

        self.assertEqual(signal.action, SignalType.SELL)
        self.assertIn('negative', signal.reason.lower())

    def test_sell_signal_stop_loss_triggered(self):
        """Test sell signal when stop-loss is triggered."""
        # Price data doesn't matter much here, focus on position P/L
        bars = pd.DataFrame({
            'open': [100.0] * 4,
            'high': [101.0] * 4,
            'low': [99.0] * 4,
            'close': [100.0] * 4,
            'volume': [1000000] * 4
        })

        # Position with >5% loss (stop-loss threshold)
        position = {
            'quantity': 10,
            'entry_price': 105.0,
            'current_price': 99.0,
            'market_value': 990.0,
            'unrealized_pnl': -60.0,
            'unrealized_pnl_pct': -0.0571  # -5.71% (exceeds 5% stop-loss)
        }

        signal = self.strategy.analyze(
            symbol='AAPL',
            bars=bars,
            current_price=99.0,
            current_position=position
        )

        self.assertEqual(signal.action, SignalType.SELL)
        self.assertIn('stop loss', signal.reason.lower())
        self.assertEqual(signal.strength, 1.0)  # High urgency

    def test_hold_signal_with_position_positive_momentum(self):
        """Test hold signal when holding position with positive momentum."""
        # Upward trending data
        bars = pd.DataFrame({
            'open': [100.0, 101.0, 102.0, 103.0],
            'high': [101.0, 102.0, 103.0, 104.0],
            'low': [99.0, 100.0, 101.0, 102.0],
            'close': [100.0, 101.0, 102.0, 103.0],
            'volume': [1000000] * 4
        })

        # Position in profit
        position = {
            'quantity': 10,
            'entry_price': 100.0,
            'current_price': 103.0,
            'market_value': 1030.0,
            'unrealized_pnl': 30.0,
            'unrealized_pnl_pct': 0.03  # 3% profit
        }

        signal = self.strategy.analyze(
            symbol='AAPL',
            bars=bars,
            current_price=103.0,
            current_position=position
        )

        self.assertEqual(signal.action, SignalType.HOLD)
        self.assertIn('holding', signal.reason.lower())

    def test_momentum_calculation_accuracy(self):
        """Test that momentum is calculated correctly."""
        bars = pd.DataFrame({
            'open': [100.0, 102.0, 104.0, 106.0, 108.0],
            'high': [102.0, 104.0, 106.0, 108.0, 110.0],
            'low': [98.0, 100.0, 102.0, 104.0, 106.0],
            'close': [100.0, 102.0, 104.0, 106.0, 108.0],
            'volume': [1000000] * 5
        })

        # Momentum = (108 - 100) / 100 = 0.08 = 8%
        momentum = self.strategy._calculate_momentum(bars)

        self.assertAlmostEqual(momentum, 0.08, places=4)

    def test_negative_momentum_calculation(self):
        """Test momentum calculation with declining prices."""
        bars = pd.DataFrame({
            'open': [110.0, 108.0, 106.0, 104.0, 102.0],
            'high': [112.0, 110.0, 108.0, 106.0, 104.0],
            'low': [108.0, 106.0, 104.0, 102.0, 100.0],
            'close': [110.0, 108.0, 106.0, 104.0, 102.0],
            'volume': [1000000] * 5
        })

        # Momentum = (102 - 110) / 110 = -0.0727 = -7.27%
        momentum = self.strategy._calculate_momentum(bars)

        self.assertAlmostEqual(momentum, -0.0727, places=3)

    def test_insufficient_data_returns_hold(self):
        """Test that insufficient bars returns hold signal."""
        # Only 1 bar (need at least 2 for momentum calculation)
        bars = pd.DataFrame({
            'open': [100.0],
            'high': [101.0],
            'low': [99.0],
            'close': [100.0],
            'volume': [1000000]
        })

        signal = self.strategy.analyze(
            symbol='AAPL',
            bars=bars,
            current_price=100.0,
            current_position=None
        )

        # Should still return a signal (momentum will be 0)
        self.assertEqual(signal.action, SignalType.HOLD)

    def test_get_parameters(self):
        """Test retrieving strategy parameters."""
        params = self.strategy.get_parameters()

        self.assertEqual(params['lookback_days'], 20)
        self.assertEqual(params['momentum_threshold'], 0.02)
        self.assertEqual(params['sell_threshold'], -0.01)
        self.assertEqual(params['stop_loss_pct'], 0.05)

    def test_strategy_metadata(self):
        """Test strategy name and description."""
        self.assertEqual(self.strategy.name, "Momentum Strategy")
        self.assertIn('momentum', self.strategy.description.lower())
        self.assertEqual(self.strategy.required_history, 20)

    def test_signal_metadata_includes_momentum(self):
        """Test that signal metadata includes momentum value."""
        bars = pd.DataFrame({
            'open': [100.0, 101.0, 102.0, 103.0],
            'high': [101.0, 102.0, 103.0, 104.0],
            'low': [99.0, 100.0, 101.0, 102.0],
            'close': [100.0, 101.0, 102.0, 103.0],
            'volume': [1000000] * 4
        })

        signal = self.strategy.analyze(
            symbol='AAPL',
            bars=bars,
            current_price=103.0,
            current_position=None
        )

        self.assertIn('momentum', signal.metadata)
        self.assertIsInstance(signal.metadata['momentum'], float)


if __name__ == '__main__':
    unittest.main()

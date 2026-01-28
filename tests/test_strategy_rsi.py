"""Tests for strategies/rsi.py - RSI trading strategy."""

import unittest
import pandas as pd
import numpy as np

from strategies.rsi import RSIStrategy
from strategies.base import SignalType


class TestRSIStrategy(unittest.TestCase):
    """Test RSI strategy signal generation."""

    def setUp(self):
        """Set up test fixtures."""
        self.strategy = RSIStrategy(
            rsi_period=14,
            oversold_level=30,
            overbought_level=70,
            stop_loss_pct=0.05  # 5%
        )

    def test_buy_signal_rsi_oversold(self):
        """Test buy signal when RSI is oversold."""
        # Create declining price data to get low RSI
        # Need at least 15 bars for RSI calculation with period 14
        closes = [100] + [100 - i for i in range(1, 20)]  # Declining prices
        bars = pd.DataFrame({
            'open': closes,
            'high': [c + 1 for c in closes],
            'low': [c - 1 for c in closes],
            'close': closes,
            'volume': [1000000] * 20
        })

        signal = self.strategy.analyze(
            symbol='AAPL',
            bars=bars,
            current_price=closes[-1],
            current_position=None
        )

        # With declining prices, RSI should be low (oversold)
        self.assertEqual(signal.action, SignalType.BUY)
        self.assertIn('oversold', signal.reason.lower())
        self.assertIn('rsi', signal.metadata)
        self.assertLess(signal.metadata['rsi'], 30)

    def test_hold_signal_rsi_neutral(self):
        """Test hold signal when RSI is in neutral zone."""
        # Create stable/slightly varying prices
        bars = pd.DataFrame({
            'open': [100.0 + (i % 2) for i in range(20)],
            'high': [101.0 + (i % 2) for i in range(20)],
            'low': [99.0 + (i % 2) for i in range(20)],
            'close': [100.0 + (i % 2) for i in range(20)],
            'volume': [1000000] * 20
        })

        signal = self.strategy.analyze(
            symbol='AAPL',
            bars=bars,
            current_price=100.0,
            current_position=None
        )

        # RSI should be around 50 (neutral)
        self.assertEqual(signal.action, SignalType.HOLD)
        self.assertIn('neutral', signal.reason.lower())
        rsi = signal.metadata['rsi']
        self.assertGreater(rsi, 30)
        self.assertLess(rsi, 70)

    def test_sell_signal_rsi_overbought(self):
        """Test sell signal when holding position and RSI is overbought."""
        # Create rising price data to get high RSI
        closes = [100 + i for i in range(20)]  # Rising prices
        bars = pd.DataFrame({
            'open': closes,
            'high': [c + 1 for c in closes],
            'low': [c - 1 for c in closes],
            'close': closes,
            'volume': [1000000] * 20
        })

        position = {
            'quantity': 10,
            'entry_price': 100.0,
            'current_price': closes[-1],
            'market_value': closes[-1] * 10,
            'unrealized_pnl': (closes[-1] - 100.0) * 10,
            'unrealized_pnl_pct': (closes[-1] - 100.0) / 100.0
        }

        signal = self.strategy.analyze(
            symbol='AAPL',
            bars=bars,
            current_price=closes[-1],
            current_position=position
        )

        # With rising prices, RSI should be high (overbought)
        self.assertEqual(signal.action, SignalType.SELL)
        self.assertIn('overbought', signal.reason.lower())
        self.assertIn('rsi', signal.metadata)
        self.assertGreater(signal.metadata['rsi'], 70)

    def test_sell_signal_stop_loss(self):
        """Test sell signal when stop-loss is triggered."""
        # Create some price data
        bars = pd.DataFrame({
            'open': [100.0] * 20,
            'high': [101.0] * 20,
            'low': [99.0] * 20,
            'close': [100.0] * 20,
            'volume': [1000000] * 20
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

    def test_hold_with_position_neutral_rsi(self):
        """Test hold signal when holding position with neutral RSI."""
        # Mixed price movements
        closes = [100 + ((-1) ** i) * (i % 3) for i in range(20)]
        bars = pd.DataFrame({
            'open': closes,
            'high': [c + 1 for c in closes],
            'low': [c - 1 for c in closes],
            'close': closes,
            'volume': [1000000] * 20
        })

        position = {
            'quantity': 10,
            'entry_price': 100.0,
            'current_price': closes[-1],
            'market_value': closes[-1] * 10,
            'unrealized_pnl': (closes[-1] - 100.0) * 10,
            'unrealized_pnl_pct': (closes[-1] - 100.0) / 100.0
        }

        signal = self.strategy.analyze(
            symbol='AAPL',
            bars=bars,
            current_price=closes[-1],
            current_position=position
        )

        # With neutral RSI, should hold
        rsi = signal.metadata['rsi']
        if 30 < rsi < 70:
            self.assertEqual(signal.action, SignalType.HOLD)

    def test_insufficient_data_returns_hold(self):
        """Test that insufficient bars returns hold signal."""
        # Only 5 bars (need 15+ for RSI with period 14)
        bars = pd.DataFrame({
            'open': [100.0] * 5,
            'high': [101.0] * 5,
            'low': [99.0] * 5,
            'close': [100.0] * 5,
            'volume': [1000000] * 5
        })

        signal = self.strategy.analyze(
            symbol='AAPL',
            bars=bars,
            current_price=100.0,
            current_position=None
        )

        # Should return HOLD when insufficient data (RSI will be NaN)
        self.assertEqual(signal.action, SignalType.HOLD)

    def test_get_parameters(self):
        """Test retrieving strategy parameters."""
        params = self.strategy.get_parameters()

        self.assertEqual(params['rsi_period'], 14)
        self.assertEqual(params['oversold_level'], 30)
        self.assertEqual(params['overbought_level'], 70)
        self.assertEqual(params['stop_loss_pct'], 0.05)

    def test_strategy_metadata(self):
        """Test strategy name and description."""
        self.assertEqual(self.strategy.name, "RSI Strategy")
        self.assertIn('rsi', self.strategy.description.lower())
        self.assertEqual(self.strategy.required_history, 24)  # RSI period (14) + 10

    def test_signal_metadata_includes_rsi(self):
        """Test that signal metadata includes RSI value."""
        closes = [100 + (i % 3) for i in range(20)]
        bars = pd.DataFrame({
            'open': closes,
            'high': [c + 1 for c in closes],
            'low': [c - 1 for c in closes],
            'close': closes,
            'volume': [1000000] * 20
        })

        signal = self.strategy.analyze(
            symbol='AAPL',
            bars=bars,
            current_price=closes[-1],
            current_position=None
        )

        self.assertIn('rsi', signal.metadata)
        self.assertIsInstance(signal.metadata['rsi'], (int, float))
        self.assertGreaterEqual(signal.metadata['rsi'], 0)
        self.assertLessEqual(signal.metadata['rsi'], 100)


if __name__ == '__main__':
    unittest.main()

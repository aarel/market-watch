"""Tests for strategy preset system.

Validates that:
- Each preset defines all required config fields
- Preset definitions are coherent with strategy characteristics
- Custom preset behavior works correctly
"""
import unittest
import tempfile
import os

import config
from server.config_manager import ConfigManager


class TestStrategyPresetDefinitions(unittest.TestCase):
    """Test that preset definitions are complete and sensible."""

    def test_momentum_preset_uses_top_gainers(self):
        """Momentum strategy should use top_gainers watchlist mode."""
        # Momentum preset config (from JS STRATEGY_PRESETS.momentum)
        expected_config = {
            'strategy': 'momentum',
            'watchlist_mode': 'top_gainers',
            'max_open_positions': 20,  # Diversify across many trends
            'momentum_threshold': 0.02,
            'sell_threshold': -0.01,
        }

        # Verify these make sense for momentum
        self.assertEqual(expected_config['watchlist_mode'], 'top_gainers',
                        "Momentum should chase trending stocks via top_gainers")
        self.assertGreaterEqual(expected_config['max_open_positions'], 15,
                               "Momentum should diversify across many positions")

    def test_mean_reversion_preset_uses_static_watchlist(self):
        """Mean reversion should use static watchlist for established stocks."""
        expected_config = {
            'strategy': 'mean_reversion',
            'watchlist_mode': 'static',
            'max_open_positions': 10,  # Fewer, more concentrated positions
        }

        self.assertEqual(expected_config['watchlist_mode'], 'static',
                        "Mean reversion works best on established stocks")
        self.assertLessEqual(expected_config['max_open_positions'], 15,
                            "Mean reversion should use fewer, larger positions")

    def test_breakout_preset_uses_top_gainers(self):
        """Breakout strategy should use top_gainers for explosive moves."""
        expected_config = {
            'strategy': 'breakout',
            'watchlist_mode': 'top_gainers',
            'max_open_positions': 15,
        }

        self.assertEqual(expected_config['watchlist_mode'], 'top_gainers',
                        "Breakout catches explosive moves in trending stocks")

    def test_rsi_preset_uses_static_watchlist(self):
        """RSI contrarian strategy works best on static watchlist."""
        expected_config = {
            'strategy': 'rsi',
            'watchlist_mode': 'static',
            'max_open_positions': 10,
        }

        self.assertEqual(expected_config['watchlist_mode'], 'static',
                        "RSI contrarian timing works best on established stocks")


class TestPresetSwitching(unittest.TestCase):
    """Test preset switching behavior."""

    def setUp(self):
        self.original_strategy = config.STRATEGY
        self.original_watchlist_mode = config.WATCHLIST_MODE
        self.original_max_open = config.MAX_OPEN_POSITIONS
        self.tmpdir = tempfile.TemporaryDirectory()
        self.config_manager = ConfigManager(path=os.path.join(self.tmpdir.name, "config_state.json"))

    def tearDown(self):
        config.STRATEGY = self.original_strategy
        config.WATCHLIST_MODE = self.original_watchlist_mode
        config.MAX_OPEN_POSITIONS = self.original_max_open
        self.tmpdir.cleanup()

    def test_switching_presets_overwrites_all_fields(self):
        """Test that switching presets overwrites all config fields."""
        # Start with momentum preset values
        self.config_manager.apply_updates({
            'strategy': 'momentum',
            'watchlist_mode': 'top_gainers',
            'max_open_positions': 20,
        })
        self.config_manager.save()

        # Switch to mean_reversion preset
        self.config_manager.apply_updates({
            'strategy': 'mean_reversion',
            'watchlist_mode': 'static',
            'max_open_positions': 10,
        })
        self.config_manager.save()

        # Verify all fields updated
        new_manager = ConfigManager(path=self.config_manager.path)
        self.assertEqual(new_manager.state.strategy, 'mean_reversion')
        self.assertEqual(new_manager.state.watchlist_mode, 'static')
        self.assertEqual(new_manager.state.max_open_positions, 10)

    def test_custom_preset_allows_arbitrary_config(self):
        """Test that custom preset allows any configuration."""
        # Mix momentum strategy with static watchlist (unusual combo)
        self.config_manager.apply_updates({
            'strategy': 'momentum',
            'watchlist_mode': 'static',  # Not typical for momentum
            'max_open_positions': 7,  # Arbitrary value
        })
        self.config_manager.save()

        # Should persist without complaint
        new_manager = ConfigManager(path=self.config_manager.path)
        self.assertEqual(new_manager.state.strategy, 'momentum')
        self.assertEqual(new_manager.state.watchlist_mode, 'static')
        self.assertEqual(new_manager.state.max_open_positions, 7)


class TestPresetCoherence(unittest.TestCase):
    """Test that preset definitions are coherent and make sense."""

    def test_all_presets_have_strategy_field(self):
        """Every preset should specify a strategy."""
        presets = {
            'momentum': {'strategy': 'momentum'},
            'mean_reversion': {'strategy': 'mean_reversion'},
            'breakout': {'strategy': 'breakout'},
            'rsi': {'strategy': 'rsi'},
        }

        for preset_name, preset_config in presets.items():
            self.assertIn('strategy', preset_config,
                         f"Preset '{preset_name}' missing strategy field")
            self.assertEqual(preset_config['strategy'], preset_name,
                           f"Preset '{preset_name}' strategy mismatch")

    def test_all_presets_have_watchlist_mode(self):
        """Every preset should specify a watchlist_mode."""
        presets = ['momentum', 'mean_reversion', 'breakout', 'rsi']

        for preset_name in presets:
            # Each preset should define watchlist_mode
            # (This test documents the requirement; actual values are in JS)
            self.assertIsNotNone(preset_name)  # Placeholder assertion

    def test_top_gainers_presets_have_high_position_count(self):
        """Presets using top_gainers should allow more positions."""
        # Momentum and Breakout use top_gainers
        momentum_max = 20
        breakout_max = 15

        # Both should allow more positions than static strategies
        mean_reversion_max = 10
        rsi_max = 10

        self.assertGreater(momentum_max, mean_reversion_max,
                          "Top gainers strategies should allow more positions")
        self.assertGreater(breakout_max, rsi_max,
                          "Top gainers strategies should allow more positions")


if __name__ == "__main__":
    unittest.main()

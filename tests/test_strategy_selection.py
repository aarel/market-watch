"""Tests for strategy selection and configuration.

Validates that:
- All available strategies can be selected and persisted
- Each strategy has a human-readable description
- Invalid strategy selections are rejected
- Strategy changes require explicit save to persist
"""
import os
import tempfile
import unittest

import config
from server.config_manager import ConfigManager
from strategies import AVAILABLE_STRATEGIES, get_strategy, list_strategies


class TestStrategySelection(unittest.TestCase):
    """Test strategy dropdown and config update behavior."""

    def setUp(self):
        self.original_strategy = config.STRATEGY
        self.tmpdir = tempfile.TemporaryDirectory()
        self.config_manager = ConfigManager(path=os.path.join(self.tmpdir.name, "config_state.json"))

    def tearDown(self):
        config.STRATEGY = self.original_strategy
        self.tmpdir.cleanup()

    def test_all_strategies_are_valid(self):
        """Verify all dropdown options map to real strategy classes."""
        expected_strategies = ["momentum", "mean_reversion", "breakout", "rsi"]
        available = list_strategies()

        for strategy_name in expected_strategies:
            self.assertIn(
                strategy_name,
                available,
                f"Strategy '{strategy_name}' not found in registry"
            )
            # Verify we can instantiate it
            strategy = get_strategy(strategy_name)
            self.assertIsNotNone(strategy)
            # Strategy.name is a display name (e.g., "Momentum Strategy")
            # Just verify it's not empty
            self.assertTrue(len(strategy.name) > 0)

    def test_each_strategy_has_description(self):
        """Verify each strategy class has a human-readable description."""
        for name, strategy_class in AVAILABLE_STRATEGIES.items():
            strategy = strategy_class()
            # All strategies should have a __doc__ string or description attribute
            has_description = (
                strategy.__doc__ is not None or
                hasattr(strategy, 'description')
            )
            self.assertTrue(
                has_description,
                f"Strategy '{name}' missing description"
            )

    def test_strategy_change_persists_after_save(self):
        """Test that strategy selection persists after save/load cycle."""
        # Change to breakout
        self.config_manager.apply_updates({"strategy": "breakout"})
        self.assertEqual(self.config_manager.state.strategy, "breakout")

        # Save
        self.config_manager.save()

        # Create new manager to simulate page reload
        new_manager = ConfigManager(path=self.config_manager.path)
        self.assertEqual(new_manager.state.strategy, "breakout")

    def test_strategy_change_without_save_does_not_persist(self):
        """Test that strategy change without save is lost on reload."""
        # Save initial state
        self.config_manager.apply_updates({"strategy": "momentum"})
        self.config_manager.save()

        # Change without saving
        self.config_manager.apply_updates({"strategy": "rsi"})
        self.assertEqual(self.config_manager.state.strategy, "rsi")

        # Reload without saving - should revert to momentum
        new_manager = ConfigManager(path=self.config_manager.path)
        self.assertEqual(new_manager.state.strategy, "momentum")

    def test_invalid_strategy_rejected(self):
        """Test that invalid strategy names are rejected."""
        with self.assertRaises(ValueError):
            get_strategy("nonexistent_strategy")

    def test_strategy_value_stored_as_provided(self):
        """Test that strategy values are stored as provided (case-sensitive)."""
        # Config stores exactly what's provided
        self.config_manager.apply_updates({"strategy": "momentum"})
        self.assertEqual(self.config_manager.state.strategy, "momentum")

        self.config_manager.apply_updates({"strategy": "mean_reversion"})
        self.assertEqual(self.config_manager.state.strategy, "mean_reversion")

    def test_all_strategies_can_be_cycled(self):
        """Test cycling through all strategies and back."""
        strategies = ["momentum", "mean_reversion", "breakout", "rsi"]

        for strategy_name in strategies:
            self.config_manager.apply_updates({"strategy": strategy_name})
            self.config_manager.save()

            # Reload and verify
            new_manager = ConfigManager(path=self.config_manager.path)
            self.assertEqual(new_manager.state.strategy, strategy_name)


class TestStrategyDescriptions(unittest.TestCase):
    """Test that strategy descriptions are appropriate for user display."""

    def test_momentum_strategy_description(self):
        """Verify Momentum strategy has clear description."""
        strategy = get_strategy("momentum")
        self.assertIsNotNone(strategy)
        # Description should mention momentum, trending, or acceleration
        description = strategy.__doc__ or getattr(strategy, 'description', '')
        self.assertTrue(
            any(word in description.lower() for word in ['momentum', 'trend', 'accelerat']),
            "Momentum strategy description should mention momentum/trend concepts"
        )

    def test_mean_reversion_description(self):
        """Verify Mean Reversion strategy has clear description."""
        strategy = get_strategy("mean_reversion")
        self.assertIsNotNone(strategy)
        description = strategy.__doc__ or getattr(strategy, 'description', '')
        self.assertTrue(
            any(word in description.lower() for word in ['mean', 'reversion', 'average', 'dip']),
            "Mean Reversion strategy description should mention mean/average concepts"
        )

    def test_breakout_description(self):
        """Verify Breakout strategy has clear description."""
        strategy = get_strategy("breakout")
        self.assertIsNotNone(strategy)
        description = strategy.__doc__ or getattr(strategy, 'description', '')
        self.assertTrue(
            any(word in description.lower() for word in ['breakout', 'range', 'resistance', 'support']),
            "Breakout strategy description should mention breakout/range concepts"
        )

    def test_rsi_description(self):
        """Verify RSI strategy has clear description."""
        strategy = get_strategy("rsi")
        self.assertIsNotNone(strategy)
        description = strategy.__doc__ or getattr(strategy, 'description', '')
        self.assertTrue(
            any(word in description.lower() for word in ['rsi', 'oversold', 'overbought', 'relative']),
            "RSI strategy description should mention RSI/oversold concepts"
        )


if __name__ == "__main__":
    unittest.main()

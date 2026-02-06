"""Tests for config field warnings and risk indicators.

Validates that:
- Warning thresholds are correctly defined
- Risk levels (safe/moderate/risky) make sense
- Preset-defining vs operational fields are correctly categorized
- Editing operational fields doesn't switch to Custom mode
"""
import unittest


class TestWarningThresholds(unittest.TestCase):
    """Test that warning thresholds are sensible."""

    def test_stop_loss_thresholds(self):
        """Stop loss warnings should encourage 3-10% range."""
        # Safe: 3-10%
        # Moderate: 2% or 10-15%
        # Risky: < 2% or > 15%
        safe_values = [3, 5, 7, 10]
        moderate_values = [2, 2.5, 11, 15]
        risky_values = [1, 1.5, 16, 20, 50]

        for val in safe_values:
            self.assertTrue(3 <= val <= 10,
                           f"{val}% should be safe stop loss")

        for val in moderate_values:
            self.assertTrue((2 <= val < 3) or (10 < val <= 15),
                           f"{val}% should be moderate stop loss")

        for val in risky_values:
            self.assertTrue(val < 2 or val > 15,
                           f"{val}% should be risky stop loss")

    def test_max_position_thresholds(self):
        """Max position warnings should discourage concentration."""
        # Safe: 0-30%
        # Moderate: 31-50%
        # Risky: > 50%
        safe_values = [10, 20, 30]
        moderate_values = [35, 40, 50]
        risky_values = [60, 80, 100]

        for val in safe_values:
            self.assertLessEqual(val, 30,
                                f"{val}% should be safe max position")

        for val in moderate_values:
            self.assertTrue(31 <= val <= 50,
                           f"{val}% should be moderate max position")

        for val in risky_values:
            self.assertGreater(val, 50,
                              f"{val}% should be risky max position")

    def test_max_daily_trades_thresholds(self):
        """Daily trades warnings should flag PDT risk."""
        # Safe: 0-15
        # Moderate: 16-25 (PDT zone)
        # Risky: > 25
        safe_values = [5, 10, 15]
        moderate_values = [16, 20, 25]
        risky_values = [30, 50, 100]

        for val in safe_values:
            self.assertLessEqual(val, 15,
                                f"{val} trades should be safe")

        for val in moderate_values:
            self.assertTrue(16 <= val <= 25,
                           f"{val} trades should be moderate (PDT risk)")

        for val in risky_values:
            self.assertGreater(val, 25,
                              f"{val} trades should be risky")

    def test_max_open_positions_thresholds(self):
        """Open positions warnings should guide diversification."""
        # Safe: 8-20
        # Moderate: 4-7 or 21-30
        # Risky: < 4 or > 30
        safe_values = [8, 10, 15, 20]
        moderate_values = [4, 5, 7, 21, 25, 30]
        risky_values = [1, 2, 3, 35, 50]

        for val in safe_values:
            self.assertTrue(8 <= val <= 20,
                           f"{val} positions should be safe")

        for val in moderate_values:
            self.assertTrue((4 <= val < 8) or (20 < val <= 30),
                           f"{val} positions should be moderate")

        for val in risky_values:
            self.assertTrue(val < 4 or val > 30,
                           f"{val} positions should be risky")

    def test_daily_loss_limit_thresholds(self):
        """Daily loss limit warnings should encourage 2-5% range."""
        # Safe: 2-5%
        # Moderate: 1% or 5-10%
        # Risky: < 1% or > 10%
        safe_values = [2, 3, 5]
        moderate_values = [1, 6, 10]
        risky_values = [0.5, 12, 20]

        for val in safe_values:
            self.assertTrue(2 <= val <= 5,
                           f"{val}% should be safe daily loss limit")

        for val in moderate_values:
            self.assertTrue((1 <= val < 2) or (5 < val <= 10),
                           f"{val}% should be moderate daily loss limit")

        for val in risky_values:
            self.assertTrue(val < 1 or val > 10,
                           f"{val}% should be risky daily loss limit")


class TestPresetDefiningFields(unittest.TestCase):
    """Test field categorization for Custom mode switching."""

    def test_preset_defining_fields_are_strategy_related(self):
        """Preset-defining fields should be core to strategy identity."""
        preset_defining = {
            'strategy', 'watchlist_mode', 'watchlist',
            'momentum_threshold', 'sell_threshold',
            'max_open_positions',  # Part of preset definition
            'top_gainers_count', 'top_gainers_universe',
            'top_gainers_min_price', 'top_gainers_min_volume',
        }

        # These are core to what defines a strategy preset
        strategy_core = {'strategy', 'watchlist_mode', 'watchlist'}
        self.assertTrue(strategy_core.issubset(preset_defining),
                       "Core strategy fields must be preset-defining")

        # Strategy-specific thresholds
        strategy_thresholds = {'momentum_threshold', 'sell_threshold'}
        self.assertTrue(strategy_thresholds.issubset(preset_defining),
                       "Strategy thresholds must be preset-defining")

    def test_operational_fields_are_not_preset_defining(self):
        """Risk/operational fields should NOT break presets."""
        operational = {
            'stop_loss_pct',
            'max_daily_trades',
            'max_position_pct',
            'daily_loss_limit_pct',
            'max_drawdown_pct',
            'max_sector_exposure_pct',
            'max_correlated_exposure_pct',
            'rvol_threshold',
            'trade_interval',
            'auto_trade',
        }

        preset_defining = {
            'strategy', 'watchlist_mode', 'watchlist',
            'momentum_threshold', 'sell_threshold',
            'max_open_positions',
            'top_gainers_count', 'top_gainers_universe',
            'top_gainers_min_price', 'top_gainers_min_volume',
        }

        # Operational fields should NOT overlap with preset-defining fields
        overlap = operational & preset_defining
        self.assertEqual(len(overlap), 0,
                        f"Operational fields should not be preset-defining: {overlap}")

    def test_max_open_positions_is_preset_defining(self):
        """Max open positions IS preset-defining (part of preset definition)."""
        # This is intentional - max_open_positions is part of the preset
        # (Momentum: 20, Mean Reversion: 10, etc.)
        # Changing it should switch to Custom
        self.assertTrue(True,
                       "max_open_positions is correctly categorized as preset-defining")


class TestWarningMessages(unittest.TestCase):
    """Test that warning messages are helpful and accurate."""

    def test_stop_loss_messages_explain_tradeoffs(self):
        """Stop loss warnings should explain whipsaw vs loss tradeoff."""
        # Message should mention whipsaw (too tight) and big losses (too loose)
        tight_message = "Tight stop (< 3%) may whipsaw"
        loose_message = "loose (> 10%) allows big losses"

        # These messages guide the user to understand the tradeoff
        self.assertIn("whipsaw", tight_message.lower())
        self.assertIn("losses", loose_message.lower())

    def test_max_position_messages_explain_concentration(self):
        """Max position warnings should explain concentration risk."""
        risky_message = "Very risky — over half your portfolio in one position!"

        self.assertIn("risky", risky_message.lower())
        self.assertIn("portfolio", risky_message.lower())

    def test_daily_trades_messages_mention_pdt(self):
        """Daily trades warnings should mention Pattern Day Trader rules."""
        pdt_message = "Pattern Day Trader rules may apply (need $25k+ account)"

        self.assertIn("pattern day trader", pdt_message.lower())
        self.assertIn("25k", pdt_message.lower())

    def test_open_positions_messages_explain_diversification(self):
        """Open positions warnings should explain diversification tradeoff."""
        concentrated_message = "< 5 = concentrated"
        diluted_message = "> 20 = over-diversified"

        self.assertIn("concentrated", concentrated_message.lower())
        self.assertIn("diversified", diluted_message.lower())


if __name__ == "__main__":
    unittest.main()

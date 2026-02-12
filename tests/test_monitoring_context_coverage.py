import unittest

from monitoring.context import (
    _categorize_direction,
    _categorize_volatility,
    _summarize_bars,
)


class TestMarketContextHelpers(unittest.TestCase):
    def test_summarize_bars_skips_invalid_entries(self):
        bars = {
            "EMPTY": {},  # no close data
            "SHORT": {"close": {0: 100, 1: 101}},  # fewer than 3 closes
            "RETURNS": {"close": {0: 10, 1: 0, 2: 12}},  # only 1 valid return
        }

        avg_volatility, direction_bias = _summarize_bars(bars)

        self.assertIsNone(avg_volatility)
        self.assertEqual(direction_bias, "unknown")

    def test_categorize_volatility_high(self):
        self.assertEqual(_categorize_volatility(0.02), "high")

    def test_categorize_direction_bearish(self):
        directions = [-0.5, -0.1, -0.2, 0.05]
        self.assertEqual(_categorize_direction(directions), "bearish")

    def test_categorize_direction_mixed(self):
        directions = [-0.1, 0.05, -0.02, 0.03]
        self.assertEqual(_categorize_direction(directions), "mixed")

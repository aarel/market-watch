import unittest

from risk.position_sizer import PositionSizer


class TestPositionSizer(unittest.TestCase):
    def test_scales_by_strength(self):
        sizer = PositionSizer(scale_by_strength=True, min_strength=0.0, max_strength=1.0)
        trade_value = sizer.calculate_trade_value(
            signal_strength=0.5,
            account_value=100000,
            buying_power=100000,
            max_position_pct=0.2,
        )
        self.assertAlmostEqual(trade_value, 10000.0)

    def test_caps_by_buying_power(self):
        sizer = PositionSizer(scale_by_strength=True, min_strength=0.0, max_strength=1.0)
        trade_value = sizer.calculate_trade_value(
            signal_strength=1.0,
            account_value=100000,
            buying_power=5000,
            max_position_pct=0.2,
        )
        self.assertAlmostEqual(trade_value, 5000.0)

    def test_clamps_strength(self):
        sizer = PositionSizer(scale_by_strength=True, min_strength=0.1, max_strength=1.0)
        trade_value = sizer.calculate_trade_value(
            signal_strength=2.0,
            account_value=100000,
            buying_power=100000,
            max_position_pct=0.1,
        )
        self.assertAlmostEqual(trade_value, 10000.0)

        trade_value_low = sizer.calculate_trade_value(
            signal_strength=0.05,
            account_value=100000,
            buying_power=100000,
            max_position_pct=0.1,
        )
        self.assertAlmostEqual(trade_value_low, 1000.0)

    def test_no_strength_scaling(self):
        sizer = PositionSizer(scale_by_strength=False, min_strength=0.0, max_strength=1.0)
        trade_value = sizer.calculate_trade_value(
            signal_strength=0.2,
            account_value=100000,
            buying_power=100000,
            max_position_pct=0.1,
        )
        self.assertAlmostEqual(trade_value, 10000.0)

    def test_returns_zero_when_base_value_non_positive(self):
        sizer = PositionSizer(scale_by_strength=True, min_strength=0.0, max_strength=1.0)
        trade_value = sizer.calculate_trade_value(
            signal_strength=0.5,
            account_value=-1000,
            buying_power=5000,
            max_position_pct=0.1,
        )
        self.assertEqual(trade_value, 0.0)

    def test_none_signal_strength_clamps_to_zero(self):
        sizer = PositionSizer(scale_by_strength=True, min_strength=0.0, max_strength=1.0)
        trade_value = sizer.calculate_trade_value(
            signal_strength=None,
            account_value=100000,
            buying_power=100000,
            max_position_pct=0.1,
        )
        self.assertEqual(trade_value, 0.0)


if __name__ == "__main__":
    unittest.main()

import types
import unittest

from server.routers.analytics import _serialize_positions_for_concentration


class TestPositionSerialization(unittest.TestCase):
    def test_weights_and_unrealized(self):
        positions = [
            types.SimpleNamespace(
                symbol="AAPL",
                market_value=6000,
                qty=30,
                avg_entry_price=180,
                current_price=200,
                unrealized_pl=None,
            ),
            types.SimpleNamespace(
                symbol="MSFT",
                market_value=4000,
                qty=20,
                avg_entry_price=210,
                current_price=200,
                unrealized_pl=None,
            ),
        ]
        rows = _serialize_positions_for_concentration(positions, portfolio_value=10000)
        self.assertEqual(len(rows), 2)
        # weights
        self.assertAlmostEqual(rows[0]["weight_pct"], 60.0)
        self.assertAlmostEqual(rows[1]["weight_pct"], 40.0)
        # unrealized P/L (profit on AAPL, loss on MSFT)
        self.assertGreater(rows[0]["unrealized_pl"], 0)
        self.assertLess(rows[1]["unrealized_pl"], 0)

    def test_handles_zero_portfolio(self):
        positions = [
            types.SimpleNamespace(
                symbol="AAPL",
                market_value=0,
                qty=0,
                avg_entry_price=0,
                current_price=0,
            )
        ]
        rows = _serialize_positions_for_concentration(positions, portfolio_value=0)
        self.assertEqual(rows[0]["weight_pct"], 0)
        self.assertEqual(rows[0]["unrealized_pl"], 0)


if __name__ == "__main__":
    unittest.main()

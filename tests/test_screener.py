import unittest
from types import SimpleNamespace

from screener import (
    _snapshot_price,
    _snapshot_prev_close,
    _snapshot_volume,
    compute_top_gainers,
)


def _snapshot(price, prev_close, volume):
    return SimpleNamespace(
        latest_trade=SimpleNamespace(price=price),
        daily_bar=SimpleNamespace(c=price, v=volume),
        prev_daily_bar=SimpleNamespace(c=prev_close, v=volume),
        minute_bar=None,
    )


class TestSnapshotHelpers(unittest.TestCase):
    """Test helper functions for snapshot data extraction."""

    def test_snapshot_price_none_snapshot(self):
        """Test _snapshot_price returns None when snapshot is None."""
        result = _snapshot_price(None)
        self.assertIsNone(result)  # Line 7

    def test_snapshot_price_daily_bar_fallback(self):
        """Test _snapshot_price falls back to daily_bar."""
        snapshot = SimpleNamespace(
            latest_trade=None,
            daily_bar=SimpleNamespace(c=150.50),
        )
        result = _snapshot_price(snapshot)
        self.assertEqual(result, 150.50)  # Line 13

    def test_snapshot_price_minute_bar_fallback(self):
        """Test _snapshot_price falls back to minute_bar."""
        snapshot = SimpleNamespace(
            latest_trade=None,
            daily_bar=None,
            minute_bar=SimpleNamespace(c=149.75),
        )
        result = _snapshot_price(snapshot)
        self.assertEqual(result, 149.75)  # Line 16

    def test_snapshot_prev_close_none_snapshot(self):
        """Test _snapshot_prev_close returns None when snapshot is None."""
        result = _snapshot_prev_close(None)
        self.assertIsNone(result)  # Line 22

    def test_snapshot_prev_close_no_prev_bar(self):
        """Test _snapshot_prev_close returns None when no prev_daily_bar."""
        snapshot = SimpleNamespace(prev_daily_bar=None)
        result = _snapshot_prev_close(snapshot)
        self.assertIsNone(result)  # Line 26

    def test_snapshot_volume_none_snapshot(self):
        """Test _snapshot_volume returns 0 when snapshot is None."""
        result = _snapshot_volume(None)
        self.assertEqual(result, 0)  # Line 31

    def test_snapshot_volume_with_data(self):
        """Test _snapshot_volume extracts volume correctly."""
        snapshot = SimpleNamespace(
            daily_bar=SimpleNamespace(v=1000000),
            prev_daily_bar=SimpleNamespace(v=500000),
        )
        result = _snapshot_volume(snapshot)
        self.assertEqual(result, 1000000)  # Returns max volume

    def test_snapshot_price_no_data_available(self):
        """Test _snapshot_price returns None when no price data exists."""
        snapshot = SimpleNamespace(
            latest_trade=None,
            daily_bar=None,
            minute_bar=None,
        )
        result = _snapshot_price(snapshot)
        self.assertIsNone(result)  # Line 17


class TestScreener(unittest.TestCase):
    def test_compute_top_gainers_filters_and_sorts(self):
        snapshots = {
            "AAA": _snapshot(110, 100, 2_000_000),
            "BBB": _snapshot(105, 100, 500_000),  # low volume
            "CCC": _snapshot(102, 100, 2_000_000),
            "DDD": _snapshot(4, 4, 2_000_000),    # low price
        }

        result = compute_top_gainers(snapshots, min_price=5, min_volume=1_000_000, limit=2)
        self.assertEqual([item["symbol"] for item in result], ["AAA", "CCC"])
        self.assertGreater(result[0]["change_pct"], result[1]["change_pct"])

    def test_compute_top_gainers_skips_invalid_data(self):
        """Test that entries with None price or prev_close are skipped."""
        snapshots = {
            "VALID": _snapshot(110, 100, 2_000_000),
            "NO_PRICE": SimpleNamespace(
                latest_trade=None,
                daily_bar=None,
                minute_bar=None,
                prev_daily_bar=SimpleNamespace(c=100, v=1_000_000),
            ),
            "NO_PREV": SimpleNamespace(
                latest_trade=SimpleNamespace(price=110),
                daily_bar=SimpleNamespace(c=110, v=1_000_000),
                prev_daily_bar=None,
            ),
        }

        result = compute_top_gainers(snapshots, min_price=5, min_volume=1_000_000, limit=10)
        # Only VALID should be included (line 55 continue)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["symbol"], "VALID")

    def test_compute_top_gainers_low_volume_fallback(self):
        """Test that low volume entries are used when not enough high volume entries."""
        snapshots = {
            "HIGH_VOL": _snapshot(110, 100, 2_000_000),  # 10% gain, high volume
            "LOW_VOL_1": _snapshot(120, 100, 500_000),   # 20% gain, low volume
            "LOW_VOL_2": _snapshot(115, 100, 500_000),   # 15% gain, low volume
        }

        # Request 3 results but only 1 has high volume
        result = compute_top_gainers(snapshots, min_price=5, min_volume=1_000_000, limit=3)

        # Should get all 3, with low volume entries filling the gap (lines 76-78)
        self.assertEqual(len(result), 3)
        symbols = [item["symbol"] for item in result]
        self.assertIn("HIGH_VOL", symbols)
        self.assertIn("LOW_VOL_1", symbols)
        self.assertIn("LOW_VOL_2", symbols)
        # High volume entries come first, then low volume are appended
        self.assertEqual(result[0]["symbol"], "HIGH_VOL")   # High volume entry
        self.assertEqual(result[1]["symbol"], "LOW_VOL_1")  # 20% gain (top low vol)
        self.assertEqual(result[2]["symbol"], "LOW_VOL_2")  # 15% gain (2nd low vol)


if __name__ == "__main__":
    unittest.main()

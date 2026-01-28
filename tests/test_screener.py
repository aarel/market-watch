import unittest
from types import SimpleNamespace

from screener import compute_top_gainers


def _snapshot(price, prev_close, volume):
    return SimpleNamespace(
        latest_trade=SimpleNamespace(price=price),
        daily_bar=SimpleNamespace(c=price, v=volume),
        prev_daily_bar=SimpleNamespace(c=prev_close, v=volume),
        minute_bar=None,
    )


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


if __name__ == "__main__":
    unittest.main()

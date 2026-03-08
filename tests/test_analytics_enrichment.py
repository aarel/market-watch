"""Unit tests for analytics.enrichment — subsequent-performance enrichment."""
import unittest
from datetime import UTC, datetime, timedelta

from analytics.enrichment import enrich_with_subsequent_performance


def _ts(days_offset: float, base: datetime | None = None) -> str:
    """Return an ISO timestamp offset from base (default: 2026-01-01 UTC)."""
    if base is None:
        base = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    return (base + timedelta(days=days_offset)).isoformat()


def _snap(days_offset: float, equity: float, base: datetime | None = None) -> dict:
    return {"timestamp": _ts(days_offset, base), "equity": equity}


def _trade(days_offset: float, base: datetime | None = None, **kwargs) -> dict:
    t = {"timestamp": _ts(days_offset, base), "symbol": "AAPL", "side": "buy",
         "filled_avg_price": 100.0}
    t.update(kwargs)
    return t


class TestEnrichWithSubsequentPerformance(unittest.TestCase):

    def test_normal_enrichment_all_windows_available(self):
        """Perf fields are computed correctly when all future snapshots exist."""
        snaps = [
            _snap(0.0, equity=100_000),   # baseline (at trade time)
            _snap(1.1, equity=101_000),   # +1 day window
            _snap(5.1, equity=105_000),   # +5 day window
            _snap(10.1, equity=110_000),  # +10 day window
        ]
        trades = [_trade(0.0)]
        result = enrich_with_subsequent_performance(trades, snaps)

        self.assertEqual(len(result), 1)
        r = result[0]
        self.assertAlmostEqual(r["perf_1d"], 0.01)    # (101k-100k)/100k
        self.assertAlmostEqual(r["perf_5d"], 0.05)    # (105k-100k)/100k
        self.assertAlmostEqual(r["perf_10d"], 0.10)   # (110k-100k)/100k

    def test_missing_future_snapshot_returns_none(self):
        """perf_Nd is None when no equity snapshot exists for that window."""
        snaps = [
            _snap(0.0, equity=100_000),  # baseline only — no future data
        ]
        trades = [_trade(0.0)]
        result = enrich_with_subsequent_performance(trades, snaps)

        self.assertIsNone(result[0]["perf_1d"])
        self.assertIsNone(result[0]["perf_5d"])
        self.assertIsNone(result[0]["perf_10d"])

    def test_empty_trades_returns_empty(self):
        """Empty trade list returns empty list without error."""
        snaps = [_snap(0.0, equity=100_000)]
        result = enrich_with_subsequent_performance([], snaps)
        self.assertEqual(result, [])

    def test_empty_snapshots_all_none(self):
        """All perf fields are None when equity_snapshots is empty."""
        trades = [_trade(0.0)]
        result = enrich_with_subsequent_performance(trades, [])
        self.assertIsNone(result[0]["perf_1d"])
        self.assertIsNone(result[0]["perf_5d"])
        self.assertIsNone(result[0]["perf_10d"])

    def test_trade_with_no_timestamp_all_none(self):
        """Trade with missing timestamp gets None for all perf fields."""
        snaps = [_snap(0.0, equity=100_000), _snap(1.0, equity=101_000)]
        trades = [{"symbol": "AAPL", "side": "buy"}]  # no timestamp
        result = enrich_with_subsequent_performance(trades, snaps)
        self.assertIsNone(result[0]["perf_1d"])
        self.assertIsNone(result[0]["perf_10d"])

    def test_inputs_not_mutated(self):
        """Original trades and snapshots lists are not modified."""
        snaps = [_snap(0.0, equity=100_000), _snap(1.1, equity=102_000)]
        trades = [_trade(0.0)]
        original_trade_keys = set(trades[0].keys())
        enrich_with_subsequent_performance(trades, snaps)
        self.assertEqual(set(trades[0].keys()), original_trade_keys)

    def test_custom_days_parameter(self):
        """Custom days list produces only those perf fields."""
        snaps = [_snap(0.0, equity=100_000), _snap(3.1, equity=103_000)]
        trades = [_trade(0.0)]
        result = enrich_with_subsequent_performance(trades, snaps, days=[3])
        r = result[0]
        self.assertIn("perf_3d", r)
        self.assertAlmostEqual(r["perf_3d"], 0.03)
        self.assertNotIn("perf_1d", r)
        self.assertNotIn("perf_5d", r)

    def test_multiple_trades_enriched_independently(self):
        """Each trade uses its own baseline from the equity curve."""
        snaps = [
            _snap(0.0, equity=100_000),   # baseline for trade 1
            _snap(1.1, equity=101_000),   # +1d for trade 1
            _snap(5.0, equity=105_000),   # baseline for trade 2
            _snap(6.1, equity=106_000),   # +1d for trade 2
        ]
        trades = [_trade(0.0), _trade(5.0)]
        result = enrich_with_subsequent_performance(trades, snaps, days=[1])
        self.assertAlmostEqual(result[0]["perf_1d"], 0.01)   # (101k-100k)/100k
        self.assertAlmostEqual(result[1]["perf_1d"], 1/105)  # (106k-105k)/105k

    def test_negative_performance_computed_correctly(self):
        """Negative equity change produces negative perf value."""
        snaps = [
            _snap(0.0, equity=100_000),
            _snap(1.1, equity=95_000),
        ]
        trades = [_trade(0.0)]
        result = enrich_with_subsequent_performance(trades, snaps, days=[1])
        self.assertAlmostEqual(result[0]["perf_1d"], -0.05)


if __name__ == "__main__":
    unittest.main()

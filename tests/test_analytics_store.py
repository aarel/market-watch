"""
Comprehensive tests for analytics/store.py

Tests JSONL-based persistence for equity snapshots and trades.
"""
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Thread

from analytics.store import AnalyticsStore, _cutoff_from_period, _parse_ts
from universe import Universe


class TestAnalyticsStore(unittest.TestCase):
    """Test AnalyticsStore file-based persistence."""

    def setUp(self):
        """Create temporary directory for each test and use SIMULATION universe."""
        self.original_cwd = os.getcwd()
        self.temp_dir = tempfile.mkdtemp()
        os.chdir(self.temp_dir)

        # Create universe-scoped directory structure in temp dir
        logs_dir = Path(self.temp_dir) / "logs" / "simulation"
        logs_dir.mkdir(parents=True, exist_ok=True)

        self.store = AnalyticsStore(Universe.SIMULATION)
        self.test_session_id = "session_20260124_test001"

    def tearDown(self):
        """Clean up temporary files."""
        import shutil
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # ==================== WRITE OPERATIONS ====================

    def test_record_equity_basic(self):
        """Test recording a single equity snapshot."""
        snapshot = {"session_id": self.test_session_id, "timestamp": "2026-01-24T10:00:00", "equity": 100000}
        self.store.record_equity(snapshot)

        # Verify file was created
        self.assertTrue(self.store.equity_path.exists())

        # Verify content
        with open(self.store.equity_path) as f:
            line = f.readline()
            data = json.loads(line)
            self.assertEqual(data["equity"], 100000)
            self.assertIn("timestamp", data)

    def test_record_equity_multiple(self):
        """Test recording multiple equity snapshots."""
        snapshots = [
            {"session_id": self.test_session_id, "timestamp": "2026-01-24T10:00:00", "equity": 100000},
            {"session_id": self.test_session_id, "timestamp": "2026-01-24T11:00:00", "equity": 101000},
            {"session_id": self.test_session_id, "timestamp": "2026-01-24T12:00:00", "equity": 99500},
        ]
        for snap in snapshots:
            self.store.record_equity(snap)

        # Verify all written
        loaded = self.store.load_equity(period="all")
        self.assertEqual(len(loaded), 3)
        self.assertEqual(loaded[0]["equity"], 100000)
        self.assertEqual(loaded[2]["equity"], 99500)

    def test_record_equity_auto_timestamp(self):
        """Test automatic timestamp injection if missing."""
        snapshot = {"session_id": self.test_session_id, "equity": 105000}
        self.store.record_equity(snapshot)

        loaded = self.store.load_equity(period="all")
        self.assertEqual(len(loaded), 1)
        self.assertIn("timestamp", loaded[0])
        # Should be close to now
        ts = datetime.fromisoformat(loaded[0]["timestamp"])
        self.assertLess((datetime.now(timezone.utc) - ts).total_seconds(), 5)

    def test_record_equity_empty_dict(self):
        """Test that empty dict is ignored."""
        self.store.record_equity({"session_id": self.test_session_id, "universe": "simulation", "data_lineage_id": "lineage"})
        self.assertTrue(self.store.equity_path.exists())

    def test_record_equity_none(self):
        """Test that None is ignored."""
        self.store.record_equity(None)
        self.assertFalse(self.store.equity_path.exists())

    def test_record_trade_basic(self):
        """Test recording a single trade."""
        trade = {
            "session_id": self.test_session_id,
            "timestamp": "2026-01-24T10:30:00",
            "symbol": "AAPL",
            "side": "buy",
            "qty": 10,
            "filled_avg_price": 150.0,
        }
        self.store.record_trade(trade)

        # Verify file created
        self.assertTrue(self.store.trades_path.exists())

        # Verify content
        loaded = self.store.load_trades(period="all")
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0]["symbol"], "AAPL")
        self.assertEqual(loaded[0]["qty"], 10)

    def test_record_trade_multiple(self):
        """Test recording multiple trades."""
        trades = [
            {"session_id": self.test_session_id, "symbol": "AAPL", "side": "buy", "qty": 10, "filled_avg_price": 150.0},
            {"session_id": self.test_session_id, "symbol": "GOOGL", "side": "buy", "qty": 5, "filled_avg_price": 140.0},
            {"session_id": self.test_session_id, "symbol": "AAPL", "side": "sell", "qty": 5, "filled_avg_price": 155.0},
        ]
        for trade in trades:
            self.store.record_trade(trade)

        loaded = self.store.load_trades(period="all")
        self.assertEqual(len(loaded), 3)
        self.assertEqual(loaded[0]["symbol"], "AAPL")
        self.assertEqual(loaded[2]["symbol"], "AAPL")

    # ==================== READ OPERATIONS ====================

    def test_load_equity_all(self):
        """Test loading all equity snapshots."""
        for i in range(5):
            self.store.record_equity({"session_id": self.test_session_id, "equity": 100000 + i * 1000, "universe": "simulation", "data_lineage_id": "lineage"})

        loaded = self.store.load_equity(period="all")
        self.assertEqual(len(loaded), 5)

    def test_load_equity_empty(self):
        """Test loading from non-existent file."""
        loaded = self.store.load_equity(period="all")
        self.assertEqual(loaded, [])

    def test_load_equity_period_30d(self):
        """Test loading last 30 days of equity."""
        now = datetime.now(timezone.utc)
        snapshots = [
            {"session_id": self.test_session_id, "timestamp": (now - timedelta(days=45)).isoformat(), "equity": 100000},
            {"session_id": self.test_session_id, "timestamp": (now - timedelta(days=20)).isoformat(), "equity": 101000},
            {"session_id": self.test_session_id, "timestamp": (now - timedelta(days=10)).isoformat(), "equity": 102000},
            {"session_id": self.test_session_id, "timestamp": now.isoformat(), "equity": 103000},
        ]
        for snap in snapshots:
            self.store.record_equity(snap)

        loaded = self.store.load_equity(period="30d")
        # Should get last 3 (within 30 days)
        self.assertEqual(len(loaded), 3)
        self.assertEqual(loaded[0]["equity"], 101000)

    def test_load_equity_period_ytd(self):
        """Test loading YTD equity."""
        now = datetime.now(timezone.utc)
        year_start = datetime(now.year, 1, 1, tzinfo=timezone.utc)
        snapshots = [
            {"session_id": self.test_session_id, "timestamp": (year_start - timedelta(days=10)).isoformat(), "equity": 100000},
            {"session_id": self.test_session_id, "timestamp": year_start.isoformat(), "equity": 101000},
            {"session_id": self.test_session_id, "timestamp": now.isoformat(), "equity": 102000},
        ]
        for snap in snapshots:
            self.store.record_equity(snap)

        loaded = self.store.load_equity(period="ytd")
        # Should get from year start onward
        self.assertGreaterEqual(len(loaded), 2)

    def test_load_trades_with_limit(self):
        """Test loading trades with limit."""
        for i in range(20):
            self.store.record_trade({"session_id": self.test_session_id, "symbol": f"SYM{i}", "side": "buy", "qty": 10, "universe": "simulation", "data_lineage_id": "lineage"})

        loaded = self.store.load_trades(period="all", limit=10)
        # Should get last 10
        self.assertEqual(len(loaded), 10)

    def test_load_trades_period_filter(self):
        """Test trade period filtering."""
        now = datetime.now(timezone.utc)
        trades = [
            {"session_id": self.test_session_id, "timestamp": (now - timedelta(days=100)).isoformat(), "symbol": "OLD", "side": "buy"},
            {"session_id": self.test_session_id, "timestamp": (now - timedelta(days=50)).isoformat(), "symbol": "MID", "side": "buy"},
            {"session_id": self.test_session_id, "timestamp": now.isoformat(), "symbol": "NEW", "side": "buy"},
        ]
        for trade in trades:
            self.store.record_trade(trade)

        # Load last 90 days
        loaded = self.store.load_trades(period="90d")
        # Should exclude the 100-day-old trade
        symbols = [t["symbol"] for t in loaded]
        self.assertNotIn("OLD", symbols)
        self.assertIn("MID", symbols)
        self.assertIn("NEW", symbols)

    # ==================== EDGE CASES ====================

    def test_malformed_jsonl_ignored(self):
        """Test that malformed JSONL lines are skipped."""
        # Write valid entry
        self.store.record_equity({"session_id": self.test_session_id, "equity": 100000, "universe": "simulation", "data_lineage_id": "lineage"})

        # Manually append malformed line
        with open(self.store.equity_path, "a") as f:
            f.write("this is not json\n")
            f.write('{"equity": 101000}\n')

        # Should load only valid entries
        loaded = self.store.load_equity(period="all")
        self.assertEqual(len(loaded), 2)
        self.assertEqual(loaded[0]["equity"], 100000)
        self.assertEqual(loaded[1]["equity"], 101000)

    def test_empty_lines_ignored(self):
        """Test that empty lines are skipped."""
        self.store.record_equity({"session_id": self.test_session_id, "equity": 100000, "universe": "simulation", "data_lineage_id": "lineage"})

        # Add empty lines
        with open(self.store.equity_path, "a") as f:
            f.write("\n")
            f.write("   \n")

        self.store.record_equity({"session_id": self.test_session_id, "equity": 101000, "universe": "simulation", "data_lineage_id": "lineage"})

        loaded = self.store.load_equity(period="all")
        self.assertEqual(len(loaded), 2)

    def test_missing_timestamp_handled(self):
        """Test records without timestamp in filter."""
        # Write record with no timestamp
        with open(self.store.equity_path, "a") as f:
            f.write('{"equity": 100000}\n')

        # Should still load it
        loaded = self.store.load_equity(period="all")
        self.assertEqual(len(loaded), 1)

    def test_thread_safety_equity(self):
        """Test concurrent writes to equity file."""
        def write_equity(value):
            for i in range(10):
                    self.store.record_equity({"session_id": self.test_session_id, "equity": value + i, "universe": "simulation", "data_lineage_id": "lineage"})

        threads = [Thread(target=write_equity, args=(i * 1000,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should have 50 entries (5 threads * 10 writes each)
        loaded = self.store.load_equity(period="all")
        self.assertEqual(len(loaded), 50)

    def test_thread_safety_trades(self):
        """Test concurrent writes to trades file."""
        def write_trades(symbol):
            for i in range(10):
                    self.store.record_trade({"session_id": self.test_session_id, "symbol": symbol, "side": "buy", "qty": i, "universe": "simulation", "data_lineage_id": "lineage"})

        threads = [Thread(target=write_trades, args=(f"SYM{i}",)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        loaded = self.store.load_trades(period="all")
        self.assertEqual(len(loaded), 50)

    # ==================== DIRECTORY CREATION ====================

    def test_directory_creation(self):
        """Test that directories are created if they don't exist."""
        # Test with PAPER universe
        store = AnalyticsStore(Universe.PAPER)

        store.record_equity({"session_id": self.test_session_id, "equity": 100000, "universe": "paper", "data_lineage_id": "lineage"})

        # Directory should be created
        expected_dir = Path(self.temp_dir) / "logs" / "paper"
        self.assertTrue(expected_dir.exists())
        self.assertTrue(store.equity_path.exists())


class TestCutoffFromPeriod(unittest.TestCase):
    """Test period string parsing."""

    def test_period_all(self):
        """Test 'all' period returns None."""
        self.assertIsNone(_cutoff_from_period("all"))
        self.assertIsNone(_cutoff_from_period(""))
        self.assertIsNone(_cutoff_from_period(None))

    def test_period_days(self):
        """Test 'Nd' format."""
        cutoff = _cutoff_from_period("30d")
        self.assertIsNotNone(cutoff)
        delta = datetime.now(timezone.utc) - cutoff
        # Should be approximately 30 days
        self.assertGreater(delta.days, 29)
        self.assertLess(delta.days, 31)

    def test_period_weeks(self):
        """Test 'Nw' format."""
        cutoff = _cutoff_from_period("2w")
        delta = datetime.now(timezone.utc) - cutoff
        # Should be approximately 14 days
        self.assertGreater(delta.days, 13)
        self.assertLess(delta.days, 15)

    def test_period_months(self):
        """Test 'Nm' format."""
        cutoff = _cutoff_from_period("3m")
        delta = datetime.now(timezone.utc) - cutoff
        # Approximate: 3 months ≈ 90 days
        self.assertGreater(delta.days, 88)
        self.assertLess(delta.days, 92)

    def test_period_ytd(self):
        """Test YTD period."""
        cutoff = _cutoff_from_period("ytd")
        now = datetime.now(timezone.utc)
        expected = datetime(now.year, 1, 1, tzinfo=timezone.utc)
        self.assertEqual(cutoff.year, expected.year)
        self.assertEqual(cutoff.month, expected.month)
        self.assertEqual(cutoff.day, expected.day)

    def test_period_invalid(self):
        """Test invalid period returns None."""
        self.assertIsNone(_cutoff_from_period("invalid"))
        self.assertIsNone(_cutoff_from_period("xyz"))


class TestParseTimestamp(unittest.TestCase):
    """Test timestamp parsing helper."""

    def test_parse_iso_string(self):
        """Test parsing ISO format string."""
        ts = _parse_ts("2026-01-24T10:30:00")
        self.assertIsInstance(ts, datetime)
        self.assertEqual(ts.year, 2026)
        self.assertEqual(ts.month, 1)
        self.assertEqual(ts.day, 24)

    def test_parse_datetime_object(self):
        """Test passing datetime object."""
        now = datetime.now()
        ts = _parse_ts(now)
        self.assertEqual(ts, now)

    def test_parse_none(self):
        """Test None returns None."""
        self.assertIsNone(_parse_ts(None))

    def test_parse_invalid_string(self):
        """Test invalid string returns None."""
        self.assertIsNone(_parse_ts("not a date"))
        self.assertIsNone(_parse_ts("2026-99-99"))

    def test_parse_iso_with_timezone(self):
        """Test parsing ISO format with timezone."""
        ts = _parse_ts("2026-01-24T10:30:00Z")
        self.assertIsInstance(ts, datetime)


if __name__ == "__main__":
    unittest.main()

"""Tests for analytics store schema validation."""
import unittest
import tempfile
import os
from pathlib import Path

from analytics.store import AnalyticsStore, SchemaValidationError
from universe import Universe


class TestAnalyticsSchemaValidation(unittest.TestCase):
    """Test that AnalyticsStore enforces schema requirements."""

    def setUp(self):
        """Create temporary directory for each test."""
        self.original_cwd = os.getcwd()
        self.temp_dir = tempfile.mkdtemp()
        os.chdir(self.temp_dir)

        # Create universe-scoped directory structure
        logs_dir = Path(self.temp_dir) / "logs" / "simulation"
        logs_dir.mkdir(parents=True, exist_ok=True)

        self.store = AnalyticsStore(Universe.SIMULATION)
        self.test_session_id = "session_20260124_test001"

    def tearDown(self):
        """Clean up temporary files."""
        import shutil
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # ==================== EQUITY SCHEMA VALIDATION ====================

    def test_equity_requires_session_id(self):
        """Equity snapshot must have session_id."""
        snapshot = {"equity": 100000}

        with self.assertRaises(SchemaValidationError) as ctx:
            self.store.record_equity(snapshot)

        self.assertIn("session_id", str(ctx.exception).lower())

    def test_equity_rejects_empty_session_id(self):
        """Equity snapshot cannot have empty session_id."""
        snapshot = {"session_id": "", "equity": 100000}

        with self.assertRaises(SchemaValidationError) as ctx:
            self.store.record_equity(snapshot)

        self.assertIn("empty", str(ctx.exception).lower())
        self.assertIn("session_id", str(ctx.exception).lower())

    def test_equity_validates_universe_match(self):
        """Equity snapshot universe must match store universe."""
        # Store expects SIMULATION, snapshot has LIVE
        snapshot = {
            "session_id": self.test_session_id,
            "universe": "live",  # Wrong universe!
            "equity": 100000
        }

        with self.assertRaises(SchemaValidationError) as ctx:
            self.store.record_equity(snapshot)

        self.assertIn("mismatch", str(ctx.exception).lower())
        self.assertIn("live", str(ctx.exception))
        self.assertIn("simulation", str(ctx.exception))

    def test_equity_accepts_valid_snapshot(self):
        """Valid equity snapshot with all required fields should work."""
        snapshot = {
            "session_id": self.test_session_id,
            "equity": 100000,
            "portfolio_value": 100000,
            "cash": 50000
        }

        # Should not raise
        self.store.record_equity(snapshot)

        # Verify it was written
        loaded = self.store.load_equity(period="all")
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0]["session_id"], self.test_session_id)

    # ==================== TRADE SCHEMA VALIDATION ====================

    def test_trade_requires_session_id(self):
        """Trade record must have session_id."""
        trade = {"symbol": "AAPL", "side": "buy", "qty": 10}

        with self.assertRaises(SchemaValidationError) as ctx:
            self.store.record_trade(trade)

        self.assertIn("session_id", str(ctx.exception).lower())

    def test_trade_rejects_empty_session_id(self):
        """Trade record cannot have empty session_id."""
        trade = {"session_id": "", "symbol": "AAPL", "side": "buy", "qty": 10}

        with self.assertRaises(SchemaValidationError) as ctx:
            self.store.record_trade(trade)

        self.assertIn("empty", str(ctx.exception).lower())
        self.assertIn("session_id", str(ctx.exception).lower())

    def test_trade_requires_symbol(self):
        """Trade record must have symbol."""
        trade = {"session_id": self.test_session_id, "side": "buy", "qty": 10}

        with self.assertRaises(SchemaValidationError) as ctx:
            self.store.record_trade(trade)

        self.assertIn("symbol", str(ctx.exception).lower())

    def test_trade_requires_side(self):
        """Trade record must have side."""
        trade = {"session_id": self.test_session_id, "symbol": "AAPL", "qty": 10}

        with self.assertRaises(SchemaValidationError) as ctx:
            self.store.record_trade(trade)

        self.assertIn("side", str(ctx.exception).lower())

    def test_trade_validates_side_values(self):
        """Trade side must be 'buy' or 'sell'."""
        trade = {"session_id": self.test_session_id, "symbol": "AAPL", "side": "hold", "qty": 10}

        with self.assertRaises(SchemaValidationError) as ctx:
            self.store.record_trade(trade)

        self.assertIn("side", str(ctx.exception).lower())
        self.assertIn("hold", str(ctx.exception))
        self.assertIn("buy", str(ctx.exception))
        self.assertIn("sell", str(ctx.exception))

    def test_trade_validates_universe_match(self):
        """Trade universe must match store universe."""
        trade = {
            "session_id": self.test_session_id,
            "universe": "paper",  # Wrong universe!
            "symbol": "AAPL",
            "side": "buy",
            "qty": 10
        }

        with self.assertRaises(SchemaValidationError) as ctx:
            self.store.record_trade(trade)

        self.assertIn("mismatch", str(ctx.exception).lower())
        self.assertIn("paper", str(ctx.exception))
        self.assertIn("simulation", str(ctx.exception))

    def test_trade_accepts_valid_record(self):
        """Valid trade record with all required fields should work."""
        trade = {
            "session_id": self.test_session_id,
            "symbol": "AAPL",
            "side": "buy",
            "qty": 10,
            "filled_avg_price": 150.0,
            "notional": 1500.0
        }

        # Should not raise
        self.store.record_trade(trade)

        # Verify it was written
        loaded = self.store.load_trades(period="all")
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0]["session_id"], self.test_session_id)
        self.assertEqual(loaded[0]["symbol"], "AAPL")

    # ==================== UNIVERSE AUTO-TAGGING ====================

    def test_equity_auto_tagged_with_universe(self):
        """Store automatically tags equity with universe."""
        snapshot = {"session_id": self.test_session_id, "equity": 100000}
        self.store.record_equity(snapshot)

        loaded = self.store.load_equity(period="all")
        self.assertEqual(loaded[0]["universe"], "simulation")

    def test_trade_auto_tagged_with_universe(self):
        """Store automatically tags trade with universe."""
        trade = {"session_id": self.test_session_id, "symbol": "AAPL", "side": "buy"}
        self.store.record_trade(trade)

        loaded = self.store.load_trades(period="all")
        self.assertEqual(loaded[0]["universe"], "simulation")

    def test_trade_auto_tagged_with_validity_class(self):
        """Store automatically tags trade with validity_class."""
        trade = {"session_id": self.test_session_id, "symbol": "AAPL", "side": "buy"}
        self.store.record_trade(trade)

        loaded = self.store.load_trades(period="all")
        self.assertIn("validity_class", loaded[0])
        # SIMULATION should have validity_class = "not_real_money"
        self.assertEqual(loaded[0]["validity_class"], Universe.SIMULATION.default_validity_class)


if __name__ == "__main__":
    unittest.main()

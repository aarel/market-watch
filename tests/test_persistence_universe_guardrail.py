"""
Guardrail tests for universe-scoped persistence and logs.

Marked as expected failures until persistence helpers enforce universe
namespacing and reject cross-universe writes.
"""
import os
import tempfile
import unittest


class TestPersistenceUniverseGuardrail(unittest.TestCase):
    @unittest.expectedFailure
    def test_cross_universe_write_rejected(self):
        """
        Writing SIM data into a LIVE path (or vice versa) must raise to
        prevent mixed-universe persistence.
        """
        from analytics.store import AnalyticsStore

        with tempfile.TemporaryDirectory() as tmpdir:
            sim_path = os.path.join(tmpdir, "simulation", "trades.jsonl")
            live_path = os.path.join(tmpdir, "live", "trades.jsonl")

            sim_store = AnalyticsStore(sim_path)
            live_store = AnalyticsStore(live_path)

            # Seed a SIM trade
            sim_store.append_trade({"universe": "simulation", "session_id": "s1", "symbol": "AAPL", "price": 100})

            # Attempt to write a LIVE trade into the SIM store path should fail
            with self.assertRaises(Exception):
                sim_store.append_trade({"universe": "live", "session_id": "s2", "symbol": "AAPL", "price": 100})

            # Attempt to write SIM trade into LIVE store path should fail
            with self.assertRaises(Exception):
                live_store.append_trade({"universe": "simulation", "session_id": "s3", "symbol": "AAPL", "price": 100})


if __name__ == "__main__":
    unittest.main()

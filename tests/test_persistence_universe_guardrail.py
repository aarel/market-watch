"""
Guardrail tests for universe-scoped persistence and logs.

Marked as expected failures until persistence helpers enforce universe
namespacing and reject cross-universe writes.
"""
import unittest

from analytics.store import AnalyticsStore, SchemaValidationError
from universe import Universe


class TestPersistenceUniverseGuardrail(unittest.TestCase):
    def test_cross_universe_write_rejected(self):
        """
        Writing SIM data into a LIVE store (or vice versa) must raise to
        prevent mixed-universe persistence.
        """
        sim_store = AnalyticsStore(Universe.SIMULATION)
        live_store = AnalyticsStore(Universe.LIVE)

        # Seed a SIM trade
        sim_store.record_trade({"universe": "simulation", "session_id": "s1", "data_lineage_id": "d1", "symbol": "AAPL", "side": "buy"})

        # Attempt to write a LIVE trade into the SIM store should fail
        with self.assertRaises(SchemaValidationError):
            sim_store.record_trade({"universe": "live", "session_id": "s2", "data_lineage_id": "d2", "symbol": "AAPL", "side": "buy"})

        # Attempt to write SIM trade into LIVE store should fail
        with self.assertRaises(SchemaValidationError):
            live_store.record_trade({"universe": "simulation", "session_id": "s3", "data_lineage_id": "d3", "symbol": "AAPL", "side": "buy"})


if __name__ == "__main__":
    unittest.main()

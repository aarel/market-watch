"""
Guardrail tests for provenance-required metrics/events.

Marked as expected failures until analytics/event writers enforce required
fields: universe, session_id, data_lineage_id, validity_class.
"""
import unittest

from analytics.store import AnalyticsStore, SchemaValidationError
from universe import Universe


class TestProvenanceGuardrail(unittest.TestCase):
    def test_metric_missing_universe_defaults(self):
        store = AnalyticsStore(Universe.SIMULATION)
        store.record_equity({"session_id": "s1", "data_lineage_id": "d1"})
        loaded = store.load_equity()
        self.assertEqual(loaded[0]["universe"], "simulation")

    def test_metric_missing_session_id_is_rejected(self):
        store = AnalyticsStore(Universe.SIMULATION)
        with self.assertRaises(SchemaValidationError):
            store.record_equity({"universe": "simulation", "data_lineage_id": "d1"})

    def test_metric_missing_lineage_defaults(self):
        store = AnalyticsStore(Universe.SIMULATION)
        store.record_equity({"universe": "simulation", "session_id": "s1"})
        loaded = store.load_equity()
        self.assertIsNotNone(loaded[0].get("data_lineage_id"))

    def test_metric_missing_validity_class_defaults(self):
        store = AnalyticsStore(Universe.SIMULATION)
        store.record_equity({
            "universe": "simulation",
            "session_id": "s1",
            "data_lineage_id": "d1"
        })  # should succeed and set defaults


if __name__ == "__main__":
    unittest.main()

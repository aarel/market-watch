"""
Guardrail tests for provenance-required metrics/events.

Marked as expected failures until analytics/event writers enforce required
fields: universe, session_id, data_lineage_id, validity_class.
"""
import unittest


class TestProvenanceGuardrail(unittest.TestCase):
    @unittest.expectedFailure
    def test_metric_missing_universe_is_rejected(self):
        from analytics.store import AnalyticsStore

        store = AnalyticsStore(":memory:")  # assume in-memory allowed
        with self.assertRaises(Exception):
            store.append_metric({"session_id": "s1", "data_lineage_id": "d1", "validity_class": "SIM_VALID_FOR_TRAINING"})

    @unittest.expectedFailure
    def test_metric_missing_session_id_is_rejected(self):
        from analytics.store import AnalyticsStore

        store = AnalyticsStore(":memory:")
        with self.assertRaises(Exception):
            store.append_metric({"universe": "simulation", "data_lineage_id": "d1", "validity_class": "SIM_VALID_FOR_TRAINING"})

    @unittest.expectedFailure
    def test_metric_missing_lineage_is_rejected(self):
        from analytics.store import AnalyticsStore

        store = AnalyticsStore(":memory:")
        with self.assertRaises(Exception):
            store.append_metric({"universe": "simulation", "session_id": "s1", "validity_class": "SIM_VALID_FOR_TRAINING"})

    @unittest.expectedFailure
    def test_metric_missing_validity_class_is_rejected(self):
        from analytics.store import AnalyticsStore

        store = AnalyticsStore(":memory:")
        with self.assertRaises(Exception):
            store.append_metric({"universe": "simulation", "session_id": "s1", "data_lineage_id": "d1"})


if __name__ == "__main__":
    unittest.main()

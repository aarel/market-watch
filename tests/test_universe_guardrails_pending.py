"""
Pending guardrail tests for universe isolation.

These are deliberately skipped until the corresponding guardrail code is
implemented. They express the required invariants so future work can
unskip/implement rather than rediscover requirements.
"""
import unittest


@unittest.skip("Guardrail invariants not enforced yet")
class TestUniverseGuardrails(unittest.TestCase):
    def test_live_order_cannot_use_sim_or_paper_broker(self):
        """
        Invariant: A LIVE order must not be constructed/submitted through a
        SIMULATION or PAPER execution authority. Expect a hard failure at
        construction or submission time.
        """
        self.fail("Implement broker construction with explicit universe and assert mismatch raises")

    def test_persistence_scoped_by_universe(self):
        """
        Invariant: No persistence/log stream may mix universes. A write to a
        SIM path followed by a LIVE write to the same path must be rejected.
        """
        self.fail("Enforce universe-scoped roots for data/logs and assert cross-write raises")

    def test_provenance_fields_required_for_metrics_and_events(self):
        """
        Invariant: Every metric/trade/event must carry
        {universe, session_id, data_lineage_id, validity_class}; writes
        missing any required field must be rejected.
        """
        self.fail("Add schema validation to analytics/event writers and assert missing field raises")

    def test_universe_transition_is_destructive(self):
        """
        Invariant: Universe cannot change without a destructive transition
        (broker/event bus/agents/writers/caches rebuilt; new session_id).
        Attempting to hot-toggle must fail.
        """
        self.fail("Implement transition manager and assert hot toggle raises")


if __name__ == "__main__":
    unittest.main()

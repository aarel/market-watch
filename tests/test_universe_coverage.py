import unittest

from universe import (
    Universe,
    UniverseContext,
    get_data_path,
    get_log_path,
    get_shared_data_path,
    get_system_log_path,
    validate_universe_transition,
)


class TestUniverseCoverage(unittest.TestCase):
    def test_universe_properties(self):
        self.assertTrue(Universe.LIVE.is_real_capital)
        self.assertFalse(Universe.PAPER.is_real_capital)
        self.assertFalse(Universe.SIMULATION.is_real_capital)

        self.assertTrue(Universe.SIMULATION.allows_market_hours_override)
        self.assertFalse(Universe.LIVE.allows_market_hours_override)

        self.assertTrue(Universe.LIVE.requires_explicit_confirmation)
        self.assertFalse(Universe.PAPER.requires_explicit_confirmation)

    def test_default_validity_class(self):
        self.assertEqual(Universe.LIVE.default_validity_class, "LIVE_VERIFIED")
        self.assertEqual(Universe.PAPER.default_validity_class, "PAPER_ONLY")
        self.assertEqual(Universe.SIMULATION.default_validity_class, "SIM_VALID_FOR_TRAINING")

    def test_from_string_invalid_raises(self):
        with self.assertRaises(ValueError) as ctx:
            Universe.from_string("unknown")
        self.assertIn("Invalid universe", str(ctx.exception))

    def test_universe_context_to_dict(self):
        context = UniverseContext(Universe.SIMULATION, session_id="session_test", data_lineage_id="lineage")
        data = context.to_dict()

        self.assertEqual(data["universe"], "simulation")
        self.assertEqual(data["session_id"], "session_test")
        self.assertEqual(data["data_lineage_id"], "lineage")
        self.assertEqual(data["validity_class"], "SIM_VALID_FOR_TRAINING")
        self.assertIsNotNone(data["created_at"])
        self.assertIsNotNone(context.created_at)

    def test_path_helpers(self):
        self.assertEqual(get_data_path(Universe.SIMULATION, "config.json"), "data/simulation/config.json")
        self.assertEqual(get_log_path(Universe.LIVE, "trades.jsonl"), "logs/live/trades.jsonl")
        self.assertEqual(get_system_log_path(Universe.LIVE, "agent_events.jsonl"), "logs/live/system/agent_events.jsonl")
        self.assertEqual(get_shared_data_path("sector_map.json"), "data/shared/sector_map.json")

    def test_validate_universe_transition(self):
        metadata = validate_universe_transition(Universe.SIMULATION, Universe.PAPER, "test")
        self.assertEqual(metadata["from_universe"], "simulation")
        self.assertEqual(metadata["to_universe"], "paper")
        self.assertEqual(metadata["reason"], "test")
        self.assertIn("warning", metadata)

        with self.assertRaises(ValueError):
            validate_universe_transition(Universe.LIVE, Universe.LIVE, "no-op")


if __name__ == "__main__":
    unittest.main()

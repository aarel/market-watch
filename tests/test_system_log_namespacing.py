"""
Guardrail tests to ensure system/observability logs are universe-scoped.
"""
import os
import tempfile
import unittest
from pathlib import Path

from universe import Universe, get_system_log_path


class TestSystemLogNamespacing(unittest.TestCase):
    def test_system_log_path_is_universe_scoped(self):
        path_live = get_system_log_path(Universe.LIVE, "agent_events.jsonl")
        path_sim = get_system_log_path(Universe.SIMULATION, "agent_events.jsonl")
        self.assertTrue(path_live.startswith("logs/live/system/"))
        self.assertTrue(path_sim.startswith("logs/simulation/system/"))
        self.assertNotEqual(path_live, path_sim)

    def test_cross_universe_write_rejected(self):
        """
        Writing a SIM log entry into a LIVE system path must raise.
        """
        from monitoring.logger import SystemLogWriter
        with tempfile.TemporaryDirectory() as tmpdir:
            live_path = Path(tmpdir) / "logs" / "live" / "system" / "agent_events.jsonl"
            live_writer = SystemLogWriter(Universe.LIVE, base_dir=Path(tmpdir))
            live_writer.write({"universe": "live", "event": "ok"})

            sim_writer = SystemLogWriter(Universe.SIMULATION, base_dir=Path(tmpdir))
            with self.assertRaises(ValueError):
                sim_writer.write({"universe": "live", "event": "oops"})


if __name__ == "__main__":
    unittest.main()

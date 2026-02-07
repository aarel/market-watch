import os
import tempfile
import unittest
from pathlib import Path

from agents.dev.dra_audit_agent import DRAAuditAgent
from agents.event_bus import EventBus
from universe import Universe, UniverseContext


class TestDRAAuditAgent(unittest.TestCase):
    def test_draft_audit_tracks_changes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "development_docs" / "audits" / "_state").mkdir(parents=True, exist_ok=True)
            (root / "src").mkdir(parents=True, exist_ok=True)
            target = root / "src" / "alpha.py"
            target.write_text("print('one')", encoding="utf-8")

            context = UniverseContext(Universe.SIMULATION)
            bus = EventBus(context)
            agent = DRAAuditAgent(bus, repo_root=root)
            out_dir = root / "development_docs" / "audits"

            first = agent.draft_audit("Example", ["src"], out_dir)
            self.assertTrue(first.path.exists())

            target.write_text("print('two')", encoding="utf-8")
            stat = target.stat()
            os.utime(target, (stat.st_atime, stat.st_mtime + 5))

            second = agent.draft_audit("Example", ["src"], out_dir)
            self.assertIn("src/alpha.py", second.diff.modified)


if __name__ == "__main__":
    unittest.main()

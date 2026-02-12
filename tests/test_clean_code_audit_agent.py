import tempfile
import unittest
from pathlib import Path

from agents.dev.clean_code_audit_agent import CleanCodeAuditAgent, ProjectIndex
from agents.event_bus import EventBus
from universe import Universe, UniverseContext


class TestProjectIndex(unittest.TestCase):
    def test_diff_detects_add_remove_modify(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "a.txt").write_text("one", encoding="utf-8")
            (root / "b.txt").write_text("two", encoding="utf-8")

            indexer = ProjectIndex(root, exclude_dirs=set())
            before = indexer.scan()

            # modify a, remove b, add c
            (root / "a.txt").write_text("one+two", encoding="utf-8")
            (root / "b.txt").unlink()
            (root / "c.txt").write_text("three", encoding="utf-8")

            after = indexer.scan()
            diff = indexer.diff(before, after)

            self.assertIn("c.txt", diff.added)
            self.assertIn("b.txt", diff.removed)
            self.assertIn("a.txt", diff.modified)


class TestCleanCodeAuditAgent(unittest.TestCase):
    def test_draft_audit_writes_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "development_docs" / "clean_code_audits" / "_state").mkdir(parents=True, exist_ok=True)
            (root / "src").mkdir(parents=True, exist_ok=True)
            (root / "src" / "example.py").write_text("print('hi')", encoding="utf-8")

            context = UniverseContext(Universe.SIMULATION)
            bus = EventBus(context)
            agent = CleanCodeAuditAgent(bus, repo_root=root)
            out_dir = root / "development_docs" / "clean_code_audits"
            output = agent.draft_audit("Example", ["src"], out_dir, None)

            self.assertTrue(output.exists())


if __name__ == "__main__":
    unittest.main()

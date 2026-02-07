import os
import tempfile
import unittest
from pathlib import Path

from agents.dev.docs_scaffold_agent import DocScaffoldPlanner


class TestDocScaffoldPlanner(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.repo_root = Path(self.tmpdir.name)
        self.docs_root = self.repo_root / "development_docs"
        self.docs_root.mkdir(parents=True, exist_ok=True)

        # Seed sample files
        (self.docs_root / "ROADMAP.md").write_text("roadmap", encoding="utf-8")
        (self.docs_root / "DRA_review_feedback.md").write_text("audit", encoding="utf-8")
        (self.docs_root / "PHASE_1_COMPLETE.md").write_text("phase", encoding="utf-8")
        (self.docs_root / "TECHNICAL_REPORT.md").write_text("report", encoding="utf-8")
        (self.docs_root / "notes.txt").write_text("misc", encoding="utf-8")

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_build_and_apply_plan(self):
        planner = DocScaffoldPlanner(repo_root=self.repo_root)
        plans = planner.build_plan()
        by_name = {p.src.name: p.dest for p in plans}

        self.assertEqual(by_name["ROADMAP.md"], self.docs_root / "roadmap" / "ROADMAP.md")
        self.assertEqual(by_name["DRA_review_feedback.md"], self.docs_root / "audits" / "DRA_review_feedback.md")
        self.assertEqual(by_name["PHASE_1_COMPLETE.md"], self.docs_root / "phases" / "PHASE_1_COMPLETE.md")
        self.assertEqual(by_name["TECHNICAL_REPORT.md"], self.docs_root / "reports" / "TECHNICAL_REPORT.md")
        self.assertEqual(by_name["notes.txt"], self.docs_root / "misc" / "notes.txt")

        planner.apply_plan(plans)

        self.assertTrue((self.docs_root / "roadmap" / "ROADMAP.md").exists())
        self.assertTrue((self.docs_root / "audits" / "DRA_review_feedback.md").exists())
        self.assertTrue((self.docs_root / "phases" / "PHASE_1_COMPLETE.md").exists())
        self.assertTrue((self.docs_root / "reports" / "TECHNICAL_REPORT.md").exists())
        self.assertTrue((self.docs_root / "misc" / "notes.txt").exists())

    def test_write_index(self):
        planner = DocScaffoldPlanner(repo_root=self.repo_root)
        planner.apply_plan(planner.build_plan())
        index_path = planner.write_index()
        self.assertTrue(index_path.exists())
        content = index_path.read_text(encoding="utf-8")
        self.assertIn("development_docs Index", content)
        self.assertIn("roadmap/ROADMAP.md", content)


if __name__ == "__main__":
    unittest.main()

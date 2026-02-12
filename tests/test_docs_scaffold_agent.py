import os
import tempfile
import unittest
from datetime import UTC, datetime, timezone
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

    def test_date_bucket_plan(self):
        planner = DocScaffoldPlanner(repo_root=self.repo_root)
        audit_file = self.docs_root / "DRA_audit_note.md"
        audit_file.write_text("audit", encoding="utf-8")
        timestamp = datetime(2026, 2, 6, 12, 0, 0, tzinfo=UTC).timestamp()
        os.utime(audit_file, (timestamp, timestamp))

        plans = planner.build_plan(date_bucket_categories=["audits"])
        by_name = {p.src.name: p.dest for p in plans}
        self.assertEqual(
            by_name["DRA_audit_note.md"],
            self.docs_root / "audits" / "2026-02-06" / "DRA_audit_note.md",
        )

    def test_date_bucket_rebucket(self):
        planner = DocScaffoldPlanner(repo_root=self.repo_root)
        audit_dir = self.docs_root / "audits" / "2026-02-05"
        audit_dir.mkdir(parents=True, exist_ok=True)
        audit_file = audit_dir / "DRA_old.md"
        audit_file.write_text("audit", encoding="utf-8")
        timestamp = datetime(2026, 2, 6, 12, 0, 0, tzinfo=UTC).timestamp()
        os.utime(audit_file, (timestamp, timestamp))

        plans = planner.build_plan(date_bucket_categories=["audits"])
        by_name = {p.src.name: p.dest for p in plans}
        self.assertEqual(
            by_name["DRA_old.md"],
            self.docs_root / "audits" / "2026-02-06" / "DRA_old.md",
        )


if __name__ == "__main__":
    unittest.main()

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from commscribe.db.migrate_from_md import migrate
from commscribe.engine.communicate_db import CommunicateDB


class SQLiteEngineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db_path = self.root / "communicate.db"
        self.schema_path = Path("commscribe/db/schema.sql")
        self.db = CommunicateDB(self.db_path)
        self.db.init_schema(self.schema_path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_lifecycle_transitions(self):
        self.db.create_request("REQ-1", "Title 1", "Objective 1", status="INPUT_PAD")
        self.db.transition_status("REQ-1", "IN_PROGRESS")
        self.db.transition_status("REQ-1", "BLOCKED")
        self.db.transition_status("REQ-1", "IN_PROGRESS")
        self.db.upsert_verification_block("REQ-1", "obj", "qc", "risks", "ok")
        self.db.transition_status("REQ-1", "DONE")
        row = self.db.get_request("REQ-1")
        self.assertEqual(row["status"], "DONE")

        self.db.create_request("REQ-2", "Title 2", "Objective 2", status="INPUT_PAD")
        with self.assertRaises(ValueError):
            self.db.transition_status("REQ-2", "DONE")

    def test_verification_enforcement_for_done(self):
        self.db.create_request("REQ-3", "Title 3", "Objective 3", status="INPUT_PAD")
        self.db.transition_status("REQ-3", "IN_PROGRESS")
        with self.assertRaises(ValueError) as ctx:
            self.db.transition_status("REQ-3", "DONE")
        self.assertIn("verification_blocks", str(ctx.exception))

    def test_migration_integrity_preserves_req_ids(self):
        md = self.root / "communicate.md"
        js = self.root / "communicate.json"
        report = self.root / "report.md"
        md.write_text("# dummy\n", encoding="utf-8")
        payload = {
            "schema_version": 1,
            "canonical_store": "communicate.json",
            "requests": [
                {
                    "request_id": "REQ-A",
                    "status": "DONE",
                    "created_at": "2026-02-17T00:00:00+00:00",
                    "last_updated_at": "2026-02-17T01:00:00+00:00",
                    "request_text": "TITLE:\nA\nOBJECTIVE:\nObj A",
                    "objective": "Obj A",
                },
                {
                    "request_id": "REQ-B",
                    "status": "NEW",
                    "created_at": "2026-02-17T02:00:00+00:00",
                    "last_updated_at": "2026-02-17T03:00:00+00:00",
                    "request_text": "TITLE:\nB\nOBJECTIVE:\nObj B",
                    "objective": "Obj B",
                },
            ],
        }
        js.write_text(json.dumps(payload), encoding="utf-8")

        migrate(md, js, self.db_path, self.schema_path, report)

        with sqlite3.connect(self.db_path) as conn:
            ids = [r[0] for r in conn.execute("SELECT id FROM requests ORDER BY id").fetchall()]
        self.assertEqual(ids, ["REQ-A", "REQ-B"])
        self.assertTrue(report.exists())

    def test_export_markdown_equivalence(self):
        self.db.create_request("REQ-10", "First", "Obj 1", status="INPUT_PAD")
        self.db.create_request("REQ-11", "Second", "Obj 2", status="IN_PROGRESS")
        exported = self.db.export_markdown()
        self.assertIn("## REQUEST REQ-10", exported)
        self.assertIn("## REQUEST REQ-11", exported)
        self.assertIn("- TITLE: First", exported)
        self.assertIn("- OBJECTIVE: Obj 2", exported)


if __name__ == "__main__":
    unittest.main()

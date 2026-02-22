import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from commscribe.api.requests_api import RequestAPI


class UiDbIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db = self.root / "communicate.db"
        self.json_file = self.root / "communicate.json"
        self.schema = Path("commscribe/db/schema.sql")
        self.api = RequestAPI.from_env_or_args(
            json_file=self.json_file,
            db_path=self.db,
            schema_path=self.schema,
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_create_req_via_api_visible_in_ui_list(self):
        rid = self.api.create_request("TITLE:\nReq A\nOBJECTIVE:\nObj A")
        rows = self.api.get_all_requests()
        ids = [r["id"] for r in rows]
        self.assertIn(rid, ids)

    def test_update_req_reflects_in_list_and_detail(self):
        rid = self.api.create_request("TITLE:\nReq B\nOBJECTIVE:\nObj B")
        self.api.update_request(rid, status="BLOCKED", log_entry="blocked")
        detail = self.api.get_request(rid)
        self.assertIsNotNone(detail)
        self.assertEqual(detail["status"], "BLOCKED")
        self.assertEqual(detail["logs"][-1]["log_entry"], "blocked")

    def test_complete_with_verification_allowed(self):
        rid = self.api.create_request("TITLE:\nReq C\nOBJECTIVE:\nObj C")
        self.api.update_request(rid, status="IN_PROGRESS")
        self.api.complete_request(
            rid,
            verification={
                "objectives_addressed": "yes",
                "quality_checks": "ok",
                "risks": "low",
                "final_status": "pass",
            },
        )
        detail = self.api.get_request(rid)
        self.assertEqual(detail["status"], "DONE")
        self.assertIsNotNone(detail["verification"])

    def test_complete_without_verification_blocked(self):
        rid = self.api.create_request("TITLE:\nReq D\nOBJECTIVE:\nObj D")
        with self.assertRaises(ValueError):
            self.api.update_request(rid, status="DONE")

    def test_archived_hidden_by_default(self):
        rid = self.api.create_request("TITLE:\nReq E\nOBJECTIVE:\nObj E")
        # Access sqlite-specific helper for archive toggle.
        self.api.store.set_archived(rid, True)  # type: ignore[attr-defined]
        visible = self.api.get_all_requests(include_archived=False)
        self.assertNotIn(rid, [r["id"] for r in visible])
        all_rows = self.api.get_all_requests(include_archived=True)
        self.assertIn(rid, [r["id"] for r in all_rows])

    def test_export_markdown_matches_db_state(self):
        rid = self.api.create_request("TITLE:\nReq F\nOBJECTIVE:\nObj F")
        self.api.update_request(rid, log_entry="note")
        md = self.api.export_markdown()
        self.assertIn(f"## REQUEST {rid}", md)
        self.assertIn("- TITLE: Req F", md)
        self.assertIn("- OBJECTIVE: Obj F", md)

    def test_get_all_requests_supports_date_filter(self):
        rid = self.api.create_request("TITLE:\nReq G\nOBJECTIVE:\nObj G")
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).replace(microsecond=0).isoformat()
        with self.api.store.db._connect() as conn:  # noqa: SLF001
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                "UPDATE requests SET created_at = ?, updated_at = ? WHERE id = ?",
                (yesterday, yesterday, rid),
            )
            conn.commit()
        today = datetime.now(timezone.utc).date().isoformat()
        filtered = self.api.get_all_requests(created_date=today, source="communicate>")
        self.assertNotIn(rid, [r["id"] for r in filtered])


if __name__ == "__main__":
    unittest.main()

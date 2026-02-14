import json
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "commscribe" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from communicate_scan import QUEUE_END, QUEUE_START, _section, parse_blocks_from_markdown
from start_communicate_ui import load_requests_from_json, selected_req_from_url, write_input_pad_via_scan

SCAN_SCRIPT = ROOT / "commscribe" / "scripts" / "communicate_scan.py"
TEMPLATE = ROOT / "commscribe" / "communicate.md"
UI_FILE = ROOT / "commscribe" / "ui" / "index.html"
THEME_FILE = ROOT / "commscribe" / "ui" / "theme.css"
MW_THEME_FILE = ROOT / "commscribe" / "ui" / "market-watch-theme.css"


class CommunicateUiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.doc = Path(self.tmp.name) / "communicate.md"
        self.json_file = Path(self.tmp.name) / "communicate.json"
        self.failure_log = Path(self.tmp.name) / "failure_log.json"
        self.doc.write_text(TEMPLATE.read_text(encoding="utf-8"), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def run_scan(self, *args):
        return subprocess.run(
            [
                "python3",
                str(SCAN_SCRIPT),
                "--file",
                str(self.doc),
                "--json",
                str(self.json_file),
                "--failure-log",
                str(self.failure_log),
                *args,
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_ui_uses_scan_set_input_command_contract(self):
        write_input_pad_via_scan(
            scan_script=SCAN_SCRIPT,
            communicate_file=self.doc,
            json_file=self.json_file,
            failure_log_file=self.failure_log,
            text="UI writes through scan path",
            lock_timeout=5,
        )
        body = self.doc.read_text(encoding="utf-8")
        self.assertIn("UI writes through scan path", body)

    def test_set_input_lock_contention_fails_closed(self):
        lock_file = self.json_file.with_suffix(self.json_file.suffix + ".lock")
        lock_file.write_text("1234", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "Concurrent write detected"):
            write_input_pad_via_scan(
                scan_script=SCAN_SCRIPT,
                communicate_file=self.doc,
                json_file=self.json_file,
                failure_log_file=self.failure_log,
                text="blocked",
                lock_timeout=1,
            )

    def test_concurrent_set_input_and_consume_no_queue_clobber(self):
        body = self.doc.read_text(encoding="utf-8")
        body = body.replace(
            "Paste request text here. One request at a time. Include files/paths if relevant.",
            "Scanner request",
        )
        self.doc.write_text(body, encoding="utf-8")
        queue = _section(self.doc.read_text(encoding="utf-8"), QUEUE_START, QUEUE_END)
        baseline_count = len(parse_blocks_from_markdown(queue))

        ui_result = {}

        def ui_writer():
            try:
                write_input_pad_via_scan(
                    scan_script=SCAN_SCRIPT,
                    communicate_file=self.doc,
                    json_file=self.json_file,
                    failure_log_file=self.failure_log,
                    text="UI next request",
                    lock_timeout=5,
                )
                ui_result["ok"] = True
            except Exception as exc:  # pragma: no cover - defensive capture
                ui_result["error"] = str(exc)

        thread = threading.Thread(target=ui_writer)
        thread.start()
        consume = self.run_scan("consume")
        thread.join()

        self.assertEqual(consume.returncode, 0)
        self.assertTrue(ui_result.get("ok"), ui_result.get("error"))

        state = json.loads(self.json_file.read_text(encoding="utf-8"))
        self.assertEqual(len(state["requests"]), baseline_count + 1)
        self.assertIn("request_text", state["requests"][0])

        updated = self.doc.read_text(encoding="utf-8")
        self.assertIn("<!-- REQUEST_QUEUE_START -->", updated)
        self.assertIn("<!-- REQUEST_QUEUE_END -->", updated)
        self.assertIn("<!-- COMPLETION_INDEX_START -->", updated)
        self.assertIn("<!-- COMPLETION_INDEX_END -->", updated)

    def test_selected_req_from_url_parses_query_and_hash(self):
        self.assertEqual(selected_req_from_url("/communicate?req=REQ-20260212-111111"), "REQ-20260212-111111")
        self.assertEqual(selected_req_from_url("/#/REQ-20260212-222222"), "REQ-20260212-222222")
        self.assertEqual(selected_req_from_url("/?x=1#/REQ-20260212-333333"), "REQ-20260212-333333")
        self.assertEqual(selected_req_from_url("/"), "")

    def test_load_requests_from_json_returns_list(self):
        payload = {
            "schema_version": 1,
            "canonical_store": "communicate.json",
            "requests": [
                {"request_id": "REQ-1", "status": "DONE"},
                {"request_id": "REQ-2", "status": "NEW"},
            ],
        }
        self.json_file.write_text(json.dumps(payload), encoding="utf-8")
        requests = load_requests_from_json(self.json_file)
        self.assertEqual(len(requests), 2)
        self.assertEqual(requests[0]["request_id"], "REQ-1")

    def test_ui_contains_req_link_and_route_logic(self):
        html = UI_FILE.read_text(encoding="utf-8")
        self.assertIn("`?req=${encodeURIComponent", html)
        self.assertIn("parseSelectedReqFromLocation", html)
        self.assertIn("/api/request/", html)
        self.assertIn("history.pushState", html)

    def test_ui_uses_runtime_local_theme_files(self):
        html = UI_FILE.read_text(encoding="utf-8")
        self.assertIn('href="theme.css"', html)
        self.assertIn('href="market-watch-theme.css"', html)
        self.assertNotIn("cdn", html.lower())
        self.assertTrue(THEME_FILE.exists())
        self.assertTrue(MW_THEME_FILE.exists())

    def test_ui_status_chip_and_theme_toggle_present(self):
        html = UI_FILE.read_text(encoding="utf-8")
        self.assertIn("status-chip", html)
        self.assertIn("toggle-theme", html)
        self.assertIn("market-theme", html)
        self.assertIn("toggle-sort", html)
        self.assertIn("sortRequestList", html)
        self.assertIn("Sort: Newest", html)


if __name__ == "__main__":
    unittest.main()

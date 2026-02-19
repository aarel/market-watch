import json
import hashlib
import subprocess
import tempfile
import unittest
import datetime as dt
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "commscribe" / "scripts" / "communicate_scan.py"
TEMPLATE = ROOT / "commscribe" / "communicate.md"


class CommunicateScanTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.doc = Path(self.tmp.name) / "communicate.md"
        self.json_file = Path(self.tmp.name) / "communicate.json"
        self.failure_log = Path(self.tmp.name) / "failure_log.json"
        self.doc.write_text(TEMPLATE.read_text(encoding="utf-8"), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def run_cmd(self, *args):
        return subprocess.run(
            [
                "python3",
                str(SCRIPT),
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

    def _put_input(self, text):
        body = self.doc.read_text(encoding="utf-8")
        start = "<!-- INPUT_PAD_START -->"
        end = "<!-- INPUT_PAD_END -->"
        pattern = re.compile(re.escape(start) + r"\n?(.*?)\n?" + re.escape(end), re.DOTALL)
        body, count = pattern.subn(f"{start}\n{text}\n{end}", body, count=1)
        self.assertEqual(count, 1, "INPUT PAD markers missing in template")
        self.doc.write_text(body, encoding="utf-8")

    def _break_queue_end_marker(self):
        body = self.doc.read_text(encoding="utf-8")
        body = body.replace("<!-- REQUEST_QUEUE_END -->", "<!-- REQUEST_QUEUE_END_BROKEN -->")
        self.doc.write_text(body, encoding="utf-8")

    def _repair_queue_end_marker(self):
        body = self.doc.read_text(encoding="utf-8")
        body = body.replace("<!-- REQUEST_QUEUE_END_BROKEN -->", "<!-- REQUEST_QUEUE_END -->")
        self.doc.write_text(body, encoding="utf-8")

    def _request_index_section(self):
        body = self.doc.read_text(encoding="utf-8")
        start = "<!-- REQUEST_INDEX_START -->"
        end = "<!-- REQUEST_INDEX_END -->"
        return body.split(start, 1)[1].split(end, 1)[0]

    def _queue_request_ids(self):
        body = self.doc.read_text(encoding="utf-8")
        queue = body.split("<!-- REQUEST_QUEUE_START -->", 1)[1].split("<!-- REQUEST_QUEUE_END -->", 1)[0]
        return re.findall(r"## REQUEST (REQ-[0-9]{8}-[0-9]{6}(?:-[0-9]+)?)", queue)

    def _index_request_ids(self):
        section = self._request_index_section()
        return re.findall(r"\[([^\]]+)\]\(#", section)

    def test_consume_creates_request_and_json_authority(self):
        self._put_input("Implement feature X")
        result = self.run_cmd("consume")
        self.assertEqual(result.returncode, 0)
        req_id = result.stdout.strip()

        updated = self.doc.read_text(encoding="utf-8")
        self.assertIn("### status\nNEW", updated)
        self.assertIn("### request_text\nImplement feature X", updated)

        state = json.loads(self.json_file.read_text(encoding="utf-8"))
        created = [r for r in state["requests"] if r["request_id"] == req_id]
        self.assertEqual(len(created), 1)
        self.assertEqual(created[0]["status"], "NEW")

    def test_transition_validation_rejects_new_to_done(self):
        self._put_input("Do a task")
        rid = self.run_cmd("consume").stdout.strip()
        out = self.run_cmd("complete", "--id", rid, "--result", "ok", "--evidence", "cmd")
        self.assertNotEqual(out.returncode, 0)
        self.assertIn("Cannot complete while status is NEW", out.stderr)

    def test_terminal_state_immutability(self):
        self._put_input("Ship docs")
        rid = self.run_cmd("consume").stdout.strip()
        self.assertEqual(self.run_cmd("ack", "--id", rid, "--plan", "1) Write docs").returncode, 0)
        self.assertEqual(self.run_cmd("complete", "--id", rid, "--result", "Done", "--evidence", "git diff").returncode, 0)

        out = self.run_cmd("ack", "--id", rid, "--plan", "2) Try mutate DONE")
        self.assertNotEqual(out.returncode, 0)
        self.assertIn("Terminal state is immutable", out.stderr)

    def test_concurrency_lock_contention(self):
        self._put_input("Task under lock")
        lock_file = self.json_file.with_suffix(self.json_file.suffix + ".lock")
        lock_file.write_text("1234", encoding="utf-8")

        out = self.run_cmd("--lock-timeout", "1", "consume")
        self.assertNotEqual(out.returncode, 0)
        self.assertIn("Concurrent write detected", out.stderr)

    def test_ack_log_complete_updates_completion_index(self):
        self._put_input("Ship docs")
        rid = self.run_cmd("consume").stdout.strip()
        self.assertEqual(self.run_cmd("ack", "--id", rid, "--plan", "1) Write docs").returncode, 0)
        self.assertEqual(self.run_cmd("log", "--id", rid, "--message", "Updated README").returncode, 0)
        self.assertEqual(self.run_cmd("complete", "--id", rid, "--result", "Done", "--evidence", "git diff").returncode, 0)

        updated = self.doc.read_text(encoding="utf-8")
        self.assertIn(f"- {rid}: DONE", updated)
        self.assertIn("### status\nDONE", updated)

    def test_corrupted_json_creates_failure_artifact(self):
        self._put_input("Will parse fail")
        self.json_file.write_text("{bad json", encoding="utf-8")
        out = self.run_cmd("consume")
        self.assertNotEqual(out.returncode, 0)
        self.assertIn("SYSTEM_BLOCKED persisted", out.stderr)
        self.assertTrue(self.failure_log.exists())
        payload = json.loads(self.failure_log.read_text(encoding="utf-8"))
        self.assertEqual(len(payload["events"]), 1)
        event = payload["events"][0]
        self.assertEqual(event["event_type"], "SYSTEM_BLOCKED")
        self.assertEqual(event["error_type"], "ValueError")
        self.assertEqual(
            event["file_hash"],
            hashlib.sha256(self.json_file.read_bytes()).hexdigest(),
        )

    def test_corrupted_json_remains_unchanged_and_no_duplicate_artifacts(self):
        self._put_input("Will parse fail")
        self.json_file.write_text("{bad json", encoding="utf-8")
        before = self.json_file.read_text(encoding="utf-8")
        first = self.run_cmd("consume")
        second = self.run_cmd("consume")
        after = self.json_file.read_text(encoding="utf-8")

        self.assertNotEqual(first.returncode, 0)
        self.assertNotEqual(second.returncode, 0)
        self.assertEqual(before, after)

        payload = json.loads(self.failure_log.read_text(encoding="utf-8"))
        blocked_events = [e for e in payload["events"] if e["event_type"] == "SYSTEM_BLOCKED"]
        self.assertEqual(len(blocked_events), 1)

    def test_recovery_after_repair_clears_system_blocked(self):
        self._put_input("Will parse fail")
        self.json_file.write_text("{bad json", encoding="utf-8")
        self.assertNotEqual(self.run_cmd("consume").returncode, 0)

        repaired = {"schema_version": 1, "canonical_store": "communicate.json", "requests": []}
        self.json_file.write_text(json.dumps(repaired), encoding="utf-8")

        status = self.run_cmd("system-status")
        self.assertEqual(status.returncode, 0)
        self.assertIn("SYSTEM_OK", status.stdout)

        payload = json.loads(self.failure_log.read_text(encoding="utf-8"))
        event_types = [e["event_type"] for e in payload["events"]]
        self.assertIn("SYSTEM_BLOCKED", event_types)
        self.assertIn("SYSTEM_RECOVERED", event_types)

    def test_system_blocked_surfaces_on_empty_input_consume(self):
        self.json_file.write_text("{bad json", encoding="utf-8")
        before = self.json_file.read_text(encoding="utf-8")
        out = self.run_cmd("consume")
        after = self.json_file.read_text(encoding="utf-8")

        self.assertNotEqual(out.returncode, 0)
        self.assertIn("SYSTEM_BLOCKED", out.stderr)
        self.assertEqual(before, after)

        payload = json.loads(self.failure_log.read_text(encoding="utf-8"))
        blocked_events = [e for e in payload["events"] if e["event_type"] == "SYSTEM_BLOCKED"]
        self.assertEqual(len(blocked_events), 1)

    def test_empty_input_not_blocked_is_deterministic_noop(self):
        self._put_input("Paste request text here. One request at a time. Include files/paths if relevant.")
        result = self.run_cmd("consume")
        self.assertEqual(result.returncode, 0)
        self.assertIn("No new INPUT PAD content. Nothing to do.", result.stdout)
        state = json.loads(self.json_file.read_text(encoding="utf-8"))
        self.assertIsInstance(state.get("requests"), list)

    def test_markdown_structural_failure_records_markdown_source(self):
        self._put_input("Trigger markdown marker failure")
        self._break_queue_end_marker()
        md_hash = hashlib.sha256(self.doc.read_bytes()).hexdigest()
        out = self.run_cmd("consume")

        self.assertNotEqual(out.returncode, 0)
        self.assertIn("SYSTEM_BLOCKED persisted", out.stderr)
        payload = json.loads(self.failure_log.read_text(encoding="utf-8"))
        event = payload["events"][0]
        self.assertEqual(event["event_type"], "SYSTEM_BLOCKED")
        self.assertEqual(event["failure_scope"], "STRUCTURAL_MARKDOWN_FAILURE")
        self.assertEqual(event["source_file"], str(self.doc))
        self.assertEqual(event["source_hash"], md_hash)

    def test_markdown_only_repair_clears_system_blocked_without_json_mutation(self):
        repaired = {"schema_version": 1, "canonical_store": "communicate.json", "requests": []}
        self.json_file.write_text(json.dumps(repaired), encoding="utf-8")
        self._put_input("Trigger markdown marker failure")
        self._break_queue_end_marker()
        self.assertNotEqual(self.run_cmd("consume").returncode, 0)
        before_json_hash = hashlib.sha256(self.json_file.read_bytes()).hexdigest()
        self._repair_queue_end_marker()

        status = self.run_cmd("system-status")
        after_json_hash = hashlib.sha256(self.json_file.read_bytes()).hexdigest()

        self.assertEqual(status.returncode, 0)
        self.assertIn("SYSTEM_OK", status.stdout)
        self.assertEqual(before_json_hash, after_json_hash)

        payload = json.loads(self.failure_log.read_text(encoding="utf-8"))
        event_types = [e["event_type"] for e in payload["events"]]
        self.assertIn("SYSTEM_BLOCKED", event_types)
        self.assertIn("SYSTEM_RECOVERED", event_types)

    def test_request_index_updates_with_request_status_and_anchor(self):
        self._put_input("Objective line\nMore detail")
        rid = self.run_cmd("consume").stdout.strip()
        self.assertEqual(self.run_cmd("ack", "--id", rid, "--plan", "Plan").returncode, 0)
        self.assertEqual(self.run_cmd("complete", "--id", rid, "--result", "Done", "--evidence", "Evidence").returncode, 0)

        body = self.doc.read_text(encoding="utf-8")
        self.assertIn(f'<a id="{rid}"></a>', body)

        index = self._request_index_section()
        self.assertIn(f"- [{rid}](#{rid}) — DONE — Objective line", index)

    def test_request_index_no_duplicates_on_noop_rerun(self):
        self._put_input("One line summary")
        rid = self.run_cmd("consume").stdout.strip()
        before = self._request_index_section()
        noop = self.run_cmd("consume")
        after = self._request_index_section()

        self.assertEqual(noop.returncode, 0)
        self.assertIn("No new INPUT PAD content. Nothing to do.", noop.stdout)
        self.assertEqual(before, after)
        self.assertEqual(after.count(f"[{rid}](#{rid})"), 1)

    def test_consume_accepts_multi_requirement_objective_block(self):
        self._put_input(
            "REQ ENTRY\n"
            "TITLE: Objective list acceptance\n"
            "OBJECTIVE:\n"
            "1) Validate multi-item objective parsing.\n"
            "2) Preserve intent for all required checks.\n"
            "3) Prevent false invalid-objective failures.\n"
            "4) Keep consume lifecycle deterministic.\n"
            "5) Record objective text in canonical state.\n"
            "STATUS: IN_PROGRESS"
        )
        result = self.run_cmd("consume")
        self.assertEqual(result.returncode, 0, result.stderr)
        rid = result.stdout.strip()
        state = json.loads(self.json_file.read_text(encoding="utf-8"))
        req = [r for r in state["requests"] if r["request_id"] == rid][0]
        self.assertIn("Validate multi-item objective parsing.", req["objective"])
        self.assertIn("Record objective text in canonical state.", req["objective"])

    def test_markdown_queue_and_index_render_newest_first_without_mutating_json_order(self):
        self._put_input("Req one")
        rid1 = self.run_cmd("consume").stdout.strip()
        self._put_input("Req two")
        rid2 = self.run_cmd("consume").stdout.strip()
        self._put_input("Req three")
        rid3 = self.run_cmd("consume").stdout.strip()
        self.assertTrue(rid1 and rid2 and rid3)

        state = json.loads(self.json_file.read_text(encoding="utf-8"))
        json_order = [r["request_id"] for r in state["requests"]]
        self.assertEqual(json_order[-3:], [rid1, rid2, rid3])

        def sort_key(req):
            return (dt.datetime.fromisoformat(req["created_at"]), req["request_id"])

        expected_desc = [r["request_id"] for r in sorted(state["requests"], key=sort_key, reverse=True)]
        queue_ids = self._queue_request_ids()
        index_ids = self._index_request_ids()
        self.assertEqual(queue_ids[:3], expected_desc[:3])
        self.assertEqual(index_ids[:3], expected_desc[:3])


if __name__ == "__main__":
    unittest.main()

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "commscribe" / "scripts" / "communicate_scan.py"
TEMPLATE = ROOT / "commscribe" / "communicate.md"
SCRIPT_DIR = ROOT / "commscribe" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import communicate_scan as scan  # noqa: E402


class ReqLogNormalizationTests(unittest.TestCase):
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

    def _put_input(self, text: str):
        body = self.doc.read_text(encoding="utf-8")
        body = body.replace(
            "Paste request text here. One request at a time. Include files/paths if relevant.",
            text,
        )
        self.doc.write_text(body, encoding="utf-8")

    def test_proper_extraction_only_objective_sentence(self):
        request = """TITLE
X
OBJECTIVE
Persist objective field only.
REQUIRED ACTIONS
1. Do work
"""
        extracted = scan.extract_objective(request)
        self.assertEqual(extracted, "Persist objective field only.")

    def test_reject_full_body_capture_stops_before_required_actions(self):
        request = """OBJECTIVE
Capture this objective sentence only.
REQUIRED ACTIONS
1. This must not be captured.
"""
        extracted = scan.extract_objective(request)
        self.assertEqual(extracted, "Capture this objective sentence only.")
        self.assertNotIn("REQUIRED ACTIONS", extracted)

    def test_reject_missing_objective(self):
        self._put_input("TITLE\nNo objective token present.\n")
        out = self.run_scan("consume")
        self.assertNotEqual(out.returncode, 0)
        self.assertIn("OBJECTIVE section missing — REQ entry not recorded.", out.stderr)

    def test_reject_overlength_objective(self):
        long_objective = "A" * 501
        self.assertFalse(scan.validate_objective(long_objective))
        self._put_input(f"TITLE\nX\nOBJECTIVE\n{long_objective}\n")
        out = self.run_scan("consume")
        self.assertNotEqual(out.returncode, 0)
        self.assertIn("OBJECTIVE field invalid — contains non-objective content.", out.stderr)

    def test_reject_bullet_section_contamination(self):
        request = """OBJECTIVE
Keep this clean.
- Bullet should invalidate objective.
"""
        with self.assertRaises(ValueError) as ctx:
            scan.extract_objective(request)
        self.assertIn("OBJECTIVE field invalid — contains non-objective content.", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()

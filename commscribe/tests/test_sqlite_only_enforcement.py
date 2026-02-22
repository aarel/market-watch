from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from commscribe.api.requests_api import RequestAPI

ROOT = Path(__file__).resolve().parents[2]
COMMSCRIBE_ROOT = ROOT / "commscribe"


class SQLiteOnlyEnforcementTests(unittest.TestCase):
    def test_request_api_backend_is_fixed_to_sqlite(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            api = RequestAPI.from_env_or_args(
                json_file=root / "communicate.json",
                db_path=root / "communicate.db",
                schema_path=ROOT / "commscribe/db/schema.sql",
            )
            self.assertEqual(api.backend, "sqlite")

    def test_mysql_backend_selection_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            with self.assertRaisesRegex(ValueError, "Only sqlite backend is supported"):
                RequestAPI.from_env_or_args(
                    json_file=root / "communicate.json",
                    db_path=root / "communicate.db",
                    schema_path=ROOT / "commscribe/db/schema.sql",
                    backend="mysql",
                )

    def test_no_mysql_references_outside_allowed_history_docs(self):
        allowed = {
            Path("commscribe/communicate.md"),
            Path("commscribe/communicate.json"),
            Path("commscribe/tests/test_sqlite_only_enforcement.py"),
        }
        violations: list[str] = []
        for path in COMMSCRIBE_ROOT.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(ROOT)
            if rel in allowed:
                continue
            if ".git" in rel.parts or ".venv" in rel.parts or "__pycache__" in rel.parts or "archive" in rel.parts:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            if "mysql" in text.lower():
                violations.append(str(rel))
        self.assertEqual(violations, [], f"Unexpected mysql references: {violations}")


if __name__ == "__main__":
    unittest.main()

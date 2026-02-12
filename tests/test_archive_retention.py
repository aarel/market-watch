from __future__ import annotations

import tempfile
import unittest
import zipfile
from datetime import date
from pathlib import Path

from scripts.archive_retention import ArchiveTarget, enforce_retention


class TestArchiveRetention(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_zips_old_date_bucket_and_keeps_recent_day(self) -> None:
        archive_root = self.root / "test_results" / "archive"
        zip_root = self.root / "test_results" / "archive_zips"

        old_file = archive_root / "2025-12-15" / "test_run_20251215_010101.log"
        recent_file = archive_root / "2026-02-01" / "test_run_20260201_010101.log"
        old_file.parent.mkdir(parents=True, exist_ok=True)
        recent_file.parent.mkdir(parents=True, exist_ok=True)
        old_file.write_text("old\n", encoding="utf-8")
        recent_file.write_text("recent\n", encoding="utf-8")

        target = ArchiveTarget("test-results", archive_root, zip_root)
        stats = enforce_retention(
            target,
            today=date(2026, 2, 11),
            retention_days=30,
            apply=True,
        )

        zip_path = zip_root / "12_15_2025.zip"
        self.assertTrue(zip_path.exists())
        self.assertFalse(old_file.exists())
        self.assertTrue(recent_file.exists())
        self.assertEqual(stats.days_zipped, 1)
        self.assertEqual(stats.files_zipped, 1)

        with zipfile.ZipFile(zip_path) as bundle:
            self.assertIn(
                "2025-12-15/test_run_20251215_010101.log",
                bundle.namelist(),
            )

    def test_parses_date_from_filename_when_no_date_bucket_dir(self) -> None:
        archive_root = self.root / "logs" / "archive"
        zip_root = self.root / "logs" / "archive_zips"

        old_file = (
            archive_root
            / "2026-01"
            / "observability"
            / "agent_events.jsonl.20251210_010101"
        )
        old_file.parent.mkdir(parents=True, exist_ok=True)
        old_file.write_text("event\n", encoding="utf-8")

        target = ArchiveTarget("logs", archive_root, zip_root)
        stats = enforce_retention(
            target,
            today=date(2026, 2, 11),
            retention_days=30,
            apply=True,
        )

        zip_path = zip_root / "12_10_2025.zip"
        self.assertTrue(zip_path.exists())
        self.assertEqual(stats.days_zipped, 1)
        self.assertFalse(old_file.exists())

        with zipfile.ZipFile(zip_path) as bundle:
            self.assertIn(
                "2026-01/observability/agent_events.jsonl.20251210_010101",
                bundle.namelist(),
            )

    def test_skips_existing_zip_without_deleting_source(self) -> None:
        archive_root = self.root / "logs" / "archive"
        zip_root = self.root / "logs" / "archive_zips"

        old_file = archive_root / "2025-12-01" / "post_market_20251201_010101.log"
        old_file.parent.mkdir(parents=True, exist_ok=True)
        old_file.write_text("old\n", encoding="utf-8")

        zip_root.mkdir(parents=True, exist_ok=True)
        existing_zip = zip_root / "12_01_2025.zip"
        with zipfile.ZipFile(existing_zip, mode="w") as bundle:
            bundle.writestr("existing.txt", "already there")

        target = ArchiveTarget("logs", archive_root, zip_root)
        stats = enforce_retention(
            target,
            today=date(2026, 2, 11),
            retention_days=30,
            apply=True,
        )

        self.assertTrue(existing_zip.exists())
        self.assertTrue(old_file.exists())
        self.assertEqual(stats.days_skipped_existing_zip, 1)
        self.assertEqual(stats.days_zipped, 0)


if __name__ == "__main__":
    unittest.main()

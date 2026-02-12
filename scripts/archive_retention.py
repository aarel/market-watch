"""Retention and zip archival for logs and test results.

Default behavior is dry-run. Use --apply to write zip files and remove source
files after successful compression.
"""
from __future__ import annotations

import argparse
import re
import zipfile
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DATE_DIR_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
DATE_TOKEN_RE = re.compile(r"(?<!\d)(\d{8})(?!\d)")


@dataclass(frozen=True)
class ArchiveTarget:
    name: str
    archive_root: Path
    zip_root: Path


@dataclass
class RetentionStats:
    target_name: str
    days_considered: int = 0
    days_zipped: int = 0
    days_skipped_existing_zip: int = 0
    files_zipped: int = 0


def _parse_cli_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def _parse_yyyymmdd(value: str) -> date | None:
    try:
        return datetime.strptime(value, "%Y%m%d").date()
    except ValueError:
        return None


def _infer_file_date(file_path: Path, archive_root: Path) -> date:
    rel = file_path.relative_to(archive_root)

    for part in reversed(rel.parts):
        if DATE_DIR_RE.match(part):
            return datetime.strptime(part, "%Y-%m-%d").date()

    for token in DATE_TOKEN_RE.findall(file_path.name):
        parsed = _parse_yyyymmdd(token)
        if parsed is not None:
            return parsed

    return datetime.fromtimestamp(file_path.stat().st_mtime).date()


def _zip_name(day: date) -> str:
    return day.strftime("%m_%d_%Y.zip")


def _is_older_than_retention(day: date, today: date, retention_days: int) -> bool:
    keep_from = today - timedelta(days=retention_days - 1)
    return day < keep_from


def _group_files_by_day(archive_root: Path) -> dict[date, list[Path]]:
    grouped: dict[date, list[Path]] = defaultdict(list)
    if not archive_root.is_dir():
        return grouped

    for item in archive_root.rglob("*"):
        if not item.is_file():
            continue
        if item.suffix.lower() == ".zip":
            continue
        day = _infer_file_date(item, archive_root)
        grouped[day].append(item)
    return grouped


def _write_zip(
    archive_root: Path,
    files: list[Path],
    zip_path: Path,
) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = zip_path.with_suffix(".zip.tmp")
    if tmp_path.exists():
        tmp_path.unlink()

    with zipfile.ZipFile(tmp_path, mode="w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for file_path in sorted(files):
            arcname = file_path.relative_to(archive_root).as_posix()
            bundle.write(file_path, arcname=arcname)

    tmp_path.replace(zip_path)


def _delete_files(files: list[Path]) -> None:
    for file_path in files:
        if file_path.exists():
            file_path.unlink()


def _cleanup_empty_dirs(root: Path) -> None:
    if not root.exists():
        return
    for directory in sorted(root.rglob("*"), reverse=True):
        if directory.is_dir() and not any(directory.iterdir()):
            directory.rmdir()


def enforce_retention(
    target: ArchiveTarget,
    *,
    today: date,
    retention_days: int,
    apply: bool,
) -> RetentionStats:
    stats = RetentionStats(target_name=target.name)
    grouped = _group_files_by_day(target.archive_root)

    for day in sorted(grouped):
        if not _is_older_than_retention(day, today, retention_days):
            continue

        files = grouped[day]
        zip_path = target.zip_root / _zip_name(day)
        stats.days_considered += 1

        if zip_path.exists():
            print(f"{target.name}: skip {zip_path.name} (already exists)")
            stats.days_skipped_existing_zip += 1
            continue

        if apply:
            _write_zip(target.archive_root, files, zip_path)
            _delete_files(files)
            _cleanup_empty_dirs(target.archive_root)
            print(f"{target.name}: zipped {zip_path.name} ({len(files)} file(s))")
        else:
            print(
                f"{target.name}: dry-run would zip {zip_path.name} "
                f"({len(files)} file(s))"
            )

        stats.days_zipped += 1
        stats.files_zipped += len(files)

    return stats


def _resolve_targets(args: argparse.Namespace) -> list[ArchiveTarget]:
    logs_target = ArchiveTarget(
        name="logs",
        archive_root=args.logs_archive_root.resolve(),
        zip_root=args.logs_zip_root.resolve(),
    )
    test_results_target = ArchiveTarget(
        name="test-results",
        archive_root=args.test_results_archive_root.resolve(),
        zip_root=args.test_results_zip_root.resolve(),
    )
    if args.target == "logs":
        return [logs_target]
    if args.target == "test-results":
        return [test_results_target]
    return [logs_target, test_results_target]


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Zip archive content older than retention window into MM_DD_YYYY.zip "
            "files under archive_zips roots."
        )
    )
    parser.add_argument(
        "--target",
        choices=("all", "logs", "test-results"),
        default="all",
        help="Which archive set to process",
    )
    parser.add_argument(
        "--retention-days",
        type=int,
        default=30,
        help="Keep this many recent days uncompressed (default: 30)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write zip files and delete source files after compression",
    )
    parser.add_argument(
        "--today",
        type=_parse_cli_date,
        default=None,
        help="Override today's date (YYYY-MM-DD) for deterministic runs",
    )
    parser.add_argument(
        "--logs-archive-root",
        type=Path,
        default=REPO_ROOT / "logs" / "archive",
        help="Path to logs archive root",
    )
    parser.add_argument(
        "--logs-zip-root",
        type=Path,
        default=REPO_ROOT / "logs" / "archive_zips",
        help="Path to logs zip archive output",
    )
    parser.add_argument(
        "--test-results-archive-root",
        type=Path,
        default=REPO_ROOT / "test_results" / "archive",
        help="Path to test_results archive root",
    )
    parser.add_argument(
        "--test-results-zip-root",
        type=Path,
        default=REPO_ROOT / "test_results" / "archive_zips",
        help="Path to test_results zip archive output",
    )
    args = parser.parse_args()

    if args.retention_days < 1:
        print("ERROR: --retention-days must be >= 1")
        return 2

    today = args.today or date.today()
    print(f"Mode: {'apply' if args.apply else 'dry-run'}")
    print(f"Today: {today}")
    print(f"Retention window: keep last {args.retention_days} day(s) uncompressed")

    totals = RetentionStats(target_name="total")
    for target in _resolve_targets(args):
        print(f"\nTarget: {target.name}")
        print(f"  archive root: {target.archive_root}")
        print(f"  zip output:   {target.zip_root}")

        if not target.archive_root.exists():
            print("  skip: archive root does not exist")
            continue

        stats = enforce_retention(
            target,
            today=today,
            retention_days=args.retention_days,
            apply=args.apply,
        )
        totals.days_considered += stats.days_considered
        totals.days_zipped += stats.days_zipped
        totals.days_skipped_existing_zip += stats.days_skipped_existing_zip
        totals.files_zipped += stats.files_zipped

    print("\nSummary:")
    print(f"  days considered: {totals.days_considered}")
    print(f"  days zipped: {totals.days_zipped}")
    print(f"  days skipped (existing zip): {totals.days_skipped_existing_zip}")
    print(f"  files zipped: {totals.files_zipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

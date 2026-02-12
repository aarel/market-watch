"""Inventory runtime config keys across the repo and write a report."""
from __future__ import annotations

import argparse
import os
import re
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from server.config_manager import RuntimeConfig

DEFAULT_EXCLUDE_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    "test_results",
    "logs",
}

DEFAULT_EXCLUDE_EXTS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".ico",
    ".pdf",
    ".zip",
    ".gz",
    ".tar",
    ".tgz",
    ".bz2",
    ".7z",
    ".sqlite",
    ".db",
    ".pyc",
}

MAX_FILE_BYTES = 2_000_000


@dataclass
class InventoryStats:
    scanned_files: int
    skipped_files: int
    key_counts: dict[str, int]
    key_files: dict[str, dict[Path, int]]


def get_runtime_config_keys() -> list[str]:
    return sorted(RuntimeConfig.model_fields.keys())


def _should_skip_file(path: Path, exclude_dirs: Iterable[str]) -> bool:
    if path.suffix.lower() in DEFAULT_EXCLUDE_EXTS:
        return True
    if path.name.startswith(".") and path.suffix == "":
        return True
    try:
        if path.stat().st_size > MAX_FILE_BYTES:
            return True
    except OSError:
        return True
    for part in path.parts:
        if part in exclude_dirs:
            return True
    return False


def _iter_candidate_files(repo_root: Path, exclude_dirs: Iterable[str]) -> Iterable[Path]:
    exclude_dirs = set(exclude_dirs)
    for root, dirs, files in os.walk(repo_root):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for filename in files:
            path = Path(root) / filename
            if _should_skip_file(path, exclude_dirs):
                continue
            yield path


def _read_text(path: Path) -> str | None:
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if b"\x00" in data:
        return None
    try:
        return data.decode("utf-8", errors="ignore")
    except Exception:
        return None


def _compile_key_patterns(keys: Iterable[str]) -> dict[str, re.Pattern[str]]:
    patterns: dict[str, re.Pattern[str]] = {}
    for key in keys:
        pattern = re.compile(rf"(?<![A-Za-z0-9_]){re.escape(key)}(?![A-Za-z0-9_])")
        patterns[key] = pattern
    return patterns


def _scan_repo(repo_root: Path, keys: list[str], exclude_dirs: Iterable[str]) -> InventoryStats:
    key_counts: dict[str, int] = dict.fromkeys(keys, 0)
    key_files: dict[str, dict[Path, int]] = {key: {} for key in keys}
    patterns = _compile_key_patterns(keys)
    scanned = 0
    skipped = 0

    for path in _iter_candidate_files(repo_root, exclude_dirs):
        content = _read_text(path)
        if content is None:
            skipped += 1
            continue
        scanned += 1
        for key, pattern in patterns.items():
            matches = pattern.findall(content)
            if not matches:
                continue
            count = len(matches)
            key_counts[key] += count
            key_files[key][path] = key_files[key].get(path, 0) + count

    return InventoryStats(
        scanned_files=scanned,
        skipped_files=skipped,
        key_counts=key_counts,
        key_files=key_files,
    )


def _next_available_path(base: Path) -> Path:
    if not base.exists():
        return base
    stem = base.stem
    suffix = base.suffix
    counter = 2
    while True:
        candidate = base.with_name(f"{stem}_{counter}{suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def _render_report(
    stats: InventoryStats,
    repo_root: Path,
    exclude_dirs: Iterable[str],
    generated_at: datetime,
    keys: list[str],
) -> str:
    total_mentions = sum(stats.key_counts.values())
    lines: list[str] = []
    lines.append("# Config Inventory Report")
    lines.append("")
    lines.append(f"Generated (UTC): {generated_at.isoformat()}")
    lines.append(f"Repo root: `{repo_root}`")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- Keys scanned: {len(keys)}")
    lines.append(f"- Files scanned: {stats.scanned_files}")
    lines.append(f"- Files skipped: {stats.skipped_files}")
    lines.append(f"- Total mentions: {total_mentions}")
    lines.append(f"- Excluded dirs: {', '.join(sorted(exclude_dirs))}")
    lines.append("")
    lines.append("## Key Totals")
    lines.append("")
    lines.append("| Key | Total Mentions | Files |")
    lines.append("| --- | ---: | ---: |")
    for key in keys:
        lines.append(
            f"| `{key}` | {stats.key_counts.get(key, 0)} | {len(stats.key_files.get(key, {}))} |"
        )
    lines.append("")
    lines.append("## Key Details")
    lines.append("")
    for key in keys:
        lines.append(f"### `{key}`")
        lines.append(f"- Total mentions: {stats.key_counts.get(key, 0)}")
        files = stats.key_files.get(key, {})
        if not files:
            lines.append("- Files: none")
            lines.append("")
            continue
        lines.append("- Files:")
        for path, count in sorted(files.items(), key=lambda item: (-item[1], str(item[0]))):
            rel_path = path.relative_to(repo_root)
            lines.append(f"  - `{rel_path}` ({count})")
        lines.append("")
    return "\n".join(lines)


def generate_config_inventory(
    repo_root: Path | None = None,
    output_dir: Path | None = None,
    exclude_dirs: Iterable[str] | None = None,
) -> tuple[Path, InventoryStats]:
    repo_root = repo_root or REPO_ROOT
    exclude_dirs = set(exclude_dirs or DEFAULT_EXCLUDE_DIRS)
    keys = get_runtime_config_keys()
    stats = _scan_repo(repo_root, keys, exclude_dirs)

    generated_at = datetime.now(UTC)
    date_label = generated_at.date().isoformat()
    output_dir = output_dir or (repo_root / "development_docs" / "audits" / date_label)
    output_dir.mkdir(parents=True, exist_ok=True)
    base_path = output_dir / f"Config_Inventory_{date_label}.md"
    output_path = _next_available_path(base_path)
    report = _render_report(stats, repo_root, exclude_dirs, generated_at, keys)
    output_path.write_text(report, encoding="utf-8")
    return output_path, stats


def main() -> int:
    parser = argparse.ArgumentParser(description="Inventory runtime config keys across the repo.")
    parser.add_argument("--repo", default=str(REPO_ROOT), help="Repo root path")
    parser.add_argument(
        "--output-dir",
        default="",
        help="Output directory (defaults to development_docs/audits/<date>)",
    )
    parser.add_argument(
        "--exclude-dirs",
        default="",
        help="Comma-separated dir names to exclude (adds to defaults)",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo).resolve()
    exclude_dirs = set(DEFAULT_EXCLUDE_DIRS)
    if args.exclude_dirs:
        exclude_dirs.update({part.strip() for part in args.exclude_dirs.split(",") if part.strip()})

    output_dir = Path(args.output_dir).resolve() if args.output_dir else None
    output_path, stats = generate_config_inventory(
        repo_root=repo_root,
        output_dir=output_dir,
        exclude_dirs=exclude_dirs,
    )
    print(f"Config inventory written: {output_path}")
    print(f"Keys scanned: {len(stats.key_counts)}")
    print(f"Files scanned: {stats.scanned_files}")
    print(f"Files skipped: {stats.skipped_files}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

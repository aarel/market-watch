"""Clean Code Audit Agent - drafts clean-code DRA audits and tracks project changes."""
from __future__ import annotations

import json
import os
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from agents.base import BaseAgent

DEFAULT_EXCLUDE_DIRS = {
    ".git",
    ".venv",
    ".venv-wsl",
    "venv",
    "__pycache__",
    "logs",
    "test_results",
    "data",
    "img",
    "market-watch-data.zip",
}
DEFAULT_EXCLUDE_FILES: set[str] = set()
DEFAULT_EXCLUDE_SUFFIXES = {".pyc"}


@dataclass
class FileRecord:
    path: str
    size: int
    mtime: float
    ctime: float | None
    birthtime: float | None


@dataclass
class IndexDiff:
    added: list[str]
    removed: list[str]
    modified: list[str]


class ProjectIndex:
    """Tracks project structure and changes over time."""

    def __init__(
        self,
        repo_root: Path,
        exclude_dirs: Iterable[str] | None = None,
        exclude_files: Iterable[str] | None = None,
    ):
        self.repo_root = repo_root
        self.exclude_dirs = set(DEFAULT_EXCLUDE_DIRS if exclude_dirs is None else exclude_dirs)
        self.exclude_files = set(DEFAULT_EXCLUDE_FILES if exclude_files is None else exclude_files)

    def scan(self, include_dev_docs: bool = False) -> dict[str, FileRecord]:
        records: dict[str, FileRecord] = {}
        for path in self.repo_root.rglob("*"):
            if path.is_dir():
                if self._is_excluded_dir(path, include_dev_docs):
                    continue
                continue
            if self._is_excluded_file(path, include_dev_docs):
                continue
            rel = path.relative_to(self.repo_root).as_posix()
            stat = path.stat()
            record = FileRecord(
                path=rel,
                size=stat.st_size,
                mtime=stat.st_mtime,
                ctime=stat.st_ctime if os.name == "nt" else None,
                birthtime=getattr(stat, "st_birthtime", None),
            )
            records[rel] = record
        return records

    def diff(self, previous: dict[str, FileRecord], current: dict[str, FileRecord]) -> IndexDiff:
        prev_keys = set(previous.keys())
        curr_keys = set(current.keys())
        added = sorted(curr_keys - prev_keys)
        removed = sorted(prev_keys - curr_keys)
        modified: list[str] = []
        for key in sorted(prev_keys & curr_keys):
            prev = previous[key]
            curr = current[key]
            if prev.mtime != curr.mtime or prev.size != curr.size:
                modified.append(key)
        return IndexDiff(added=added, removed=removed, modified=modified)

    def _is_excluded_dir(self, path: Path, include_dev_docs: bool) -> bool:
        for part in path.parts:
            if part in self.exclude_dirs:
                return True
            if not include_dev_docs and part == "development_docs":
                return True
        return False

    def _is_excluded_file(self, path: Path, include_dev_docs: bool) -> bool:
        if path.name in self.exclude_files:
            return True
        if not include_dev_docs and "development_docs" in path.parts:
            return True
        if path.suffix in DEFAULT_EXCLUDE_SUFFIXES:
            return True
        for part in path.parts:
            if part in self.exclude_dirs:
                return True
        return False


class CleanCodeAuditAgent(BaseAgent):
    """Dev-only agent that drafts clean-code DRA audits and tracks repo changes."""

    def __init__(
        self,
        event_bus,
        repo_root: str | Path | None = None,
        state_dir: str | Path | None = None,
        include_dev_docs: bool = False,
    ):
        super().__init__("CleanCodeAuditAgent", event_bus)
        self.repo_root = Path(repo_root) if repo_root else Path(__file__).resolve().parents[2]
        self.include_dev_docs = include_dev_docs
        self.state_dir = Path(state_dir) if state_dir else (
            self.repo_root / "development_docs" / "clean_code_audits" / "_state"
        )
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.state_dir / "project_index.json"
        self.indexer = ProjectIndex(self.repo_root)

    async def start(self):
        await super().start()

    async def stop(self):
        await super().stop()

    def update_index(self) -> IndexDiff:
        previous = self._load_index()
        current = self.indexer.scan(include_dev_docs=self.include_dev_docs)
        diff = self.indexer.diff(previous, current)
        self._save_index(current)
        self._write_structure_report(current, diff)
        self._write_change_log(diff)
        return diff

    def draft_audit(
        self,
        target: str,
        scope: Iterable[str],
        output_dir: Path,
        template_path: Path | None = None,
        verbose: bool = False,
    ) -> Path:
        def emit(message: str) -> None:
            if verbose:
                print(message, flush=True)

        emit("Starting clean-code audit draft...")
        output_dir.mkdir(parents=True, exist_ok=True)
        template = self._load_template(template_path)
        emit(f"Template: {'custom' if template_path else 'auto'}")
        now = datetime.now(UTC)
        stamp = now.strftime("%Y-%m-%d")
        safe_target = _sanitize_target(target)
        out_path = output_dir / f"DRA_CleanCode_{safe_target}_Draft_{stamp}.md"

        emit("Updating project index...")
        diff = self.update_index()
        emit(f"Index updated. Added={len(diff.added)} Removed={len(diff.removed)} Modified={len(diff.modified)}")
        emit("Resolving scope files...")
        scope_files = _resolve_scope_files(
            self.repo_root,
            scope,
            include_dev_docs=self.include_dev_docs,
            exclude_dirs=self.indexer.exclude_dirs,
            exclude_files=self.indexer.exclude_files,
        )
        emit(f"Scope files resolved: {len(scope_files)}")

        evidence = _format_evidence(
            target=target,
            scope=scope,
            scope_files=scope_files,
            diff=diff,
        )

        content = template.rstrip() + "\n\n---\n\n" + evidence
        out_path.write_text(content, encoding="utf-8")
        emit(f"Audit draft created: {out_path}")
        return out_path

    def _load_index(self) -> dict[str, FileRecord]:
        if not self.index_path.exists():
            return {}
        data = json.loads(self.index_path.read_text(encoding="utf-8"))
        records: dict[str, FileRecord] = {}
        for item in data.get("files", []):
            records[item["path"]] = FileRecord(
                path=item["path"],
                size=item["size"],
                mtime=item["mtime"],
                ctime=item.get("ctime"),
                birthtime=item.get("birthtime"),
            )
        return records

    def _save_index(self, records: dict[str, FileRecord]) -> None:
        payload = {
            "generated_at": datetime.now(UTC).isoformat(),
            "files": [
                {
                    "path": rec.path,
                    "size": rec.size,
                    "mtime": rec.mtime,
                    "ctime": rec.ctime,
                    "birthtime": rec.birthtime,
                }
                for rec in records.values()
            ],
        }
        self.index_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _write_structure_report(self, records: dict[str, FileRecord], diff: IndexDiff) -> None:
        summary = _structure_summary(records)
        lines = [
            "# Project Structure Snapshot",
            "",
            f"Generated: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}",
            "",
            f"Total files: {summary['total_files']}",
            f"Total size (bytes): {summary['total_size']}",
            "",
            "## Top-Level Buckets",
        ]
        for bucket, count in summary["top_level_counts"].items():
            lines.append(f"- {bucket}: {count}")
        lines.append("")
        lines.append("## Recent Changes")
        lines.append(f"- Added: {len(diff.added)}")
        lines.append(f"- Removed: {len(diff.removed)}")
        lines.append(f"- Modified: {len(diff.modified)}")
        self.state_dir.joinpath("project_structure.md").write_text("\n".join(lines), encoding="utf-8")

    def _write_change_log(self, diff: IndexDiff) -> None:
        stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        payload = {
            "generated_at": datetime.now(UTC).isoformat(),
            "added": diff.added,
            "removed": diff.removed,
            "modified": diff.modified,
        }
        self.state_dir.joinpath(f"changes_{stamp}.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _load_template(self, template_path: Path | None) -> str:
        if template_path and template_path.exists():
            return template_path.read_text(encoding="utf-8")

        candidates = list(self.repo_root.glob("development_docs/clean_code_audits/**/DRA_CleanCode_Template.md"))
        if candidates:
            latest = max(candidates, key=lambda p: p.stat().st_mtime)
            return latest.read_text(encoding="utf-8")

        return _fallback_template()


def _fallback_template() -> str:
    return (
        "# DRA Clean Code Audit (Draft)\n\n"
        "**Status:** Draft (needs review)\n\n"
        "## Gate Summary\n\n"
        "| Gate | Status | Notes |\n| --- | --- | --- |\n"
        "| Problem Framing | Pending |  |\n"
        "| Objective & Metric | Pending |  |\n"
        "| Assumptions | Pending |  |\n"
        "| Constraints | Pending |  |\n"
        "| Model Frame | Pending |  |\n"
        "| Comparative Reasoning | Pending |  |\n"
        "| Error & Uncertainty | Pending |  |\n"
        "| Coherence | Pending |  |\n"
    )


def _format_evidence(target: str, scope: Iterable[str], scope_files: list[str], diff: IndexDiff) -> str:
    def _join(items: list[str]) -> str:
        if not items:
            return "-"
        return ", ".join(items[:50]) + (" ..." if len(items) > 50 else "")

    lines = [
        "## Evidence Pack",
        "",
        f"Target: {target}",
        f"Scope patterns: {', '.join(scope) if scope else 'n/a'}",
        f"Scope file count: {len(scope_files)}",
        "",
        "Recent changes since last index:",
        f"Added: {_join(diff.added)}",
        f"Removed: {_join(diff.removed)}",
        f"Modified: {_join(diff.modified)}",
        "",
        "Scope file list:",
    ]
    if scope_files:
        lines.extend([f"- {path}" for path in scope_files])
    else:
        lines.append("- (no files matched)")
    return "\n".join(lines)


def _resolve_scope_files(
    repo_root: Path,
    scope: Iterable[str],
    include_dev_docs: bool = False,
    exclude_dirs: Iterable[str] | None = None,
    exclude_files: Iterable[str] | None = None,
) -> list[str]:
    files: set[str] = set()
    exclude_dir_set = set(DEFAULT_EXCLUDE_DIRS if exclude_dirs is None else exclude_dirs)
    exclude_file_set = set(DEFAULT_EXCLUDE_FILES if exclude_files is None else exclude_files)

    def _should_include(path: Path) -> bool:
        if path.suffix in DEFAULT_EXCLUDE_SUFFIXES:
            return False
        if path.name in exclude_file_set:
            return False
        rel = path.relative_to(repo_root)
        parts = rel.parts
        if not include_dev_docs and "development_docs" in parts:
            return False
        for part in parts:
            if part in exclude_dir_set:
                return False
        return True

    for entry in scope:
        if not entry:
            continue
        candidate = repo_root / entry
        if candidate.exists():
            if candidate.is_file():
                if _should_include(candidate):
                    files.add(candidate.relative_to(repo_root).as_posix())
            else:
                for path in candidate.rglob("*"):
                    if path.is_file():
                        if _should_include(path):
                            files.add(path.relative_to(repo_root).as_posix())
            continue
        for path in repo_root.glob(entry):
            if path.is_file():
                if _should_include(path):
                    files.add(path.relative_to(repo_root).as_posix())
            elif path.is_dir():
                for sub in path.rglob("*"):
                    if sub.is_file():
                        if _should_include(sub):
                            files.add(sub.relative_to(repo_root).as_posix())
    return sorted(files)


def _sanitize_target(target: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in ("_", "-") else "_" for ch in target.strip())
    return cleaned.strip("_") or "Unknown"


def _structure_summary(records: dict[str, FileRecord]) -> dict[str, object]:
    total_files = len(records)
    total_size = sum(rec.size for rec in records.values())
    top_level: dict[str, int] = {}
    for rec in records.values():
        first = rec.path.split("/", 1)[0]
        top_level[first] = top_level.get(first, 0) + 1
    return {
        "total_files": total_files,
        "total_size": total_size,
        "top_level_counts": dict(sorted(top_level.items())),
    }

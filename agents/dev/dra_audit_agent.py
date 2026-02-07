"""DRA Audit Agent - drafts DRA audits with evidence packs (dev-only)."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

from agents.base import BaseAgent
from agents.events import LogEvent
from agents.dev.clean_code_audit_agent import (
    ProjectIndex,
    IndexDiff,
    _resolve_scope_files,
    _sanitize_target,
    _structure_summary,
    FileRecord,
)


@dataclass
class DraftAudit:
    path: Path
    diff: IndexDiff


class DRAAuditAgent(BaseAgent):
    """Dev-only agent that drafts DRA audits with explicit evidence packs."""

    def __init__(
        self,
        event_bus,
        repo_root: str | Path | None = None,
        include_dev_docs: bool = False,
        state_dir: str | Path | None = None,
    ):
        super().__init__("DRAAuditAgent", event_bus)
        self.repo_root = Path(repo_root) if repo_root else Path(__file__).resolve().parents[2]
        self.indexer = ProjectIndex(self.repo_root)
        self.include_dev_docs = include_dev_docs
        self.state_dir = Path(state_dir) if state_dir else (
            self.repo_root / "development_docs" / "audits" / "_state"
        )
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.state_dir / "project_index.json"

    async def start(self):
        await super().start()

    async def stop(self):
        await super().stop()

    def draft_audit(
        self,
        target: str,
        scope: Iterable[str],
        output_dir: Path,
        verbose: bool = False,
    ) -> DraftAudit:
        def emit(message: str) -> None:
            if verbose:
                print(message, flush=True)

        emit("Starting DRA audit draft...")
        output_dir.mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc)
        stamp = now.strftime("%Y-%m-%d")
        safe_target = _sanitize_target(target)
        out_path = output_dir / f"DRA_Audit_{safe_target}_Draft_{stamp}.md"

        emit("Updating project index...")
        diff = self.update_index()
        emit(f"Index updated. Added={len(diff.added)} Removed={len(diff.removed)} Modified={len(diff.modified)}")
        emit("Resolving scope files...")
        scope_files = _resolve_scope_files(self.repo_root, scope)
        emit(f"Scope files resolved: {len(scope_files)}")

        content = _dra_template(
            target=target,
            scope=scope,
            scope_files=scope_files,
            diff=diff,
        )
        out_path.write_text(content, encoding="utf-8")
        emit(f"Audit draft created: {out_path}")
        return DraftAudit(path=out_path, diff=diff)

    def update_index(self) -> IndexDiff:
        previous = self._load_index()
        current = self.indexer.scan(include_dev_docs=self.include_dev_docs)
        diff = self.indexer.diff(previous, current)
        self._save_index(current)
        self._write_structure_report(current, diff)
        self._write_change_log(diff)
        return diff

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
            "generated_at": datetime.now(timezone.utc).isoformat(),
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
            f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
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
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "added": diff.added,
            "removed": diff.removed,
            "modified": diff.modified,
        }
        self.state_dir.joinpath(f"changes_{stamp}.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _dra_template(
    target: str,
    scope: Iterable[str],
    scope_files: list[str],
    diff: IndexDiff,
) -> str:
    def _join(items: list[str]) -> str:
        if not items:
            return "-"
        return ", ".join(items[:50]) + (" ..." if len(items) > 50 else "")

    lines = [
        "# DRA Audit (Draft)",
        "",
        "**Status:** Draft (needs review)",
        "",
        "## Header",
        f"- Audit Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
        f"- Target: {target}",
        f"- Scope: {', '.join(scope) if scope else 'n/a'}",
        "",
        "## Gate Summary (Draft)",
        "| Gate | Status | Notes |",
        "| --- | --- | --- |",
        "| Problem Framing | Pending |  |",
        "| Objective & Metric | Pending |  |",
        "| Assumptions | Pending |  |",
        "| Constraints | Pending |  |",
        "| Model Frame | Pending |  |",
        "| Comparative Reasoning | Pending |  |",
        "| Error & Uncertainty | Pending |  |",
        "| Coherence | Pending |  |",
        "",
        "## Evidence Pack",
        f"Scope file count: {len(scope_files)}",
        "Recent changes (no baseline loaded):",
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

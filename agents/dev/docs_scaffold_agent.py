"""DocScaffoldAgent - organizes development_docs without deleting content."""
from __future__ import annotations

import json
import re
import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

from agents.base import BaseAgent
from agents.events import LogEvent


@dataclass
class MovePlan:
    src: Path
    dest: Path
    reason: str


class DocScaffoldPlanner:
    """Plans and applies a safe reorganization of development_docs."""

    def __init__(self, repo_root: str | Path | None = None):
        self.repo_root = Path(repo_root) if repo_root else Path(__file__).resolve().parents[1]
        self.docs_root = self.repo_root / "development_docs"
        self.output_dir = self.docs_root / "_scaffold_runs"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.category_rules: list[tuple[str, list[re.Pattern[str]]]] = [
            ("audits", [
                re.compile(r"^DRA_.*"),
                re.compile(r".*_DRA_.*"),
                re.compile(r"^FUNCTION_DRA_.*"),
            ]),
            ("roadmap", [
                re.compile(r"^ROADMAP.*"),
                re.compile(r"^roadmap-.*"),
            ]),
            ("phases", [
                re.compile(r"^PHASE_.*"),
                re.compile(r"^P0_.*"),
                re.compile(r"^POST_PHASE.*"),
                re.compile(r"^WEEK.*"),
                re.compile(r"^TIMEZONE_FIX_.*"),
                re.compile(r"^INTEGRATION_TEST_.*"),
                re.compile(r"^UI_P0_.*"),
            ]),
            ("reports", [
                re.compile(r"^TECHNICAL_REPORT.*"),
                re.compile(r"^PROJECT_STATUS_.*"),
                re.compile(r"^MIGRATION_ASSESSMENT.*"),
                re.compile(r"^TESTS_Q_AND_A.*"),
            ]),
            ("reviews", [
                re.compile(r"^codex-.*"),
                re.compile(r"^gemini-.*"),
                re.compile(r"^merged_review.*"),
                re.compile(r"^diff_.*"),
                re.compile(r"^other_llm.*"),
                re.compile(r"^latest_auditor_.*"),
                re.compile(r"^auditor_.*"),
                re.compile(r"^gemini_chat.*"),
                re.compile(r"^gemini_eval.*"),
            ]),
            ("decisions", [
                re.compile(r"^UNIVERSE_.*"),
                re.compile(r"^position_sizing_spec.*"),
                re.compile(r"^stakeholder_value_assessment.*"),
                re.compile(r"^design_modularization_plan.*"),
                re.compile(r"^plan_before_live_trade.*"),
            ]),
            ("logs", [
                re.compile(r"^localhost-.*\\.log"),
            ]),
            ("misc", [
                re.compile(r".*"),
            ]),
        ]

    def build_plan(self, include_directories: bool = False) -> list[MovePlan]:
        if not self.docs_root.exists():
            return []
        plans: list[MovePlan] = []
        for path in sorted(self.docs_root.iterdir()):
            if path.name.startswith("_"):
                continue
            if path.is_dir():
                if include_directories:
                    target = self._categorize(path.name)
                    if target and not self._already_in_category(path, target):
                        plans.append(MovePlan(path, self.docs_root / target / path.name, f"category:{target}"))
                continue
            target = self._categorize(path.name)
            if not target:
                continue
            if self._already_in_category(path, target):
                continue
            plans.append(MovePlan(path, self.docs_root / target / path.name, f"category:{target}"))
        return plans

    def apply_plan(self, plans: Iterable[MovePlan]) -> list[MovePlan]:
        applied: list[MovePlan] = []
        for plan in plans:
            plan.dest.parent.mkdir(parents=True, exist_ok=True)
            plan.src.rename(plan.dest)
            applied.append(plan)
        return applied

    def write_index(self) -> Path:
        index_path = self.docs_root / "README.md"
        lines = [
            "# development_docs Index",
            "",
            f"Updated: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
            "",
        ]
        categories = sorted({p.name for p in self.docs_root.iterdir() if p.is_dir() and not p.name.startswith("_")})
        for category in categories:
            lines.append(f"## {category}")
            lines.append("")
            for file in sorted((self.docs_root / category).rglob("*")):
                if file.is_dir():
                    continue
                rel = file.relative_to(self.docs_root)
                lines.append(f"- `{rel}`")
            lines.append("")
        index_path.write_text("\n".join(lines), encoding="utf-8")
        return index_path

    def write_plan(self, plans: Iterable[MovePlan]) -> Path:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        path = self.output_dir / f"plan_{stamp}.json"
        payload = [
            {"src": str(p.src), "dest": str(p.dest), "reason": p.reason}
            for p in plans
        ]
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path

    def _categorize(self, name: str) -> str | None:
        for category, patterns in self.category_rules:
            if any(p.match(name) for p in patterns):
                return category
        return None

    def _already_in_category(self, path: Path, category: str) -> bool:
        return path.parent == (self.docs_root / category)


class DocScaffoldAgent(BaseAgent):
    """Development-only agent that periodically scaffolds development_docs."""

    def __init__(
        self,
        event_bus,
        repo_root: str | Path | None = None,
        interval_minutes: int = 60,
        apply: bool = False,
        include_directories: bool = False,
        write_index: bool = False,
    ):
        super().__init__("DocScaffoldAgent", event_bus)
        self.interval_minutes = max(5, interval_minutes)
        self.apply = apply
        self.include_directories = include_directories
        self.write_index_flag = write_index
        self.planner = DocScaffoldPlanner(repo_root=repo_root)
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        await super().start()
        self._task = asyncio.create_task(self._loop())

    async def stop(self):
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        await super().stop()

    async def _loop(self):
        while self.running:
            try:
                await self.run_once()
            except Exception as exc:
                await self.event_bus.publish(LogEvent(
                    universe=self.universe,
                    session_id=self.session_id,
                    source=self.name,
                    level="warning",
                    message=f"Doc scaffolding error: {exc}",
                ))
            await asyncio.sleep(self.interval_minutes * 60)

    async def run_once(self):
        plans = self.planner.build_plan(include_directories=self.include_directories)
        plan_path = self.planner.write_plan(plans)
        if self.apply and plans:
            self.planner.apply_plan(plans)
        if self.write_index_flag:
            self.planner.write_index()
        await self.event_bus.publish(LogEvent(
            universe=self.universe,
            session_id=self.session_id,
            source=self.name,
            level="info",
            message=f"Doc scaffolding planned {len(plans)} moves (plan: {plan_path.name})",
        ))

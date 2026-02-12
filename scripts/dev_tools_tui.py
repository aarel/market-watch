"""Dev tools TUI wrapper for maintenance agents and audits."""
from __future__ import annotations

import argparse
import curses
import json
import os
import re
import selectors
import shlex
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON_BIN = sys.executable
PRESET_FILE = REPO_ROOT / "audit_presets.json"

MENU_ACTIONS: list[tuple[str, Callable[[curses._CursesWindow], None]]] = []
VERBOSE = True
ACTION_HELP: dict[str, list[str]] = {
    "Run Clean Code Audit (draft)": [
        "Drafts a clean-code DRA audit with an evidence pack.",
        "Use when you want structure/quality issues surfaced quickly.",
        "Scope supports comma-separated paths or globs.",
    ],
    "Update Clean Code Index (no draft)": [
        "Updates project index + change log only (no audit file).",
        "Use for daily tracking or before/after large changes.",
    ],
    "Run DRA Audit (draft)": [
        "Drafts a DRA audit with evidence pack for the target scope.",
        "Use for phase verification or implementation completeness checks.",
        "Choose a preset (Agents, Project, Logs, Tests, etc.) or Custom.",
    ],
    "Run Test Audit": [
        "Runs pytest with optional coverage, writes report to test_results.",
        "Use to validate test quality and coverage gaps.",
    ],
    "Run Test Suite (logged)": [
        "Runs the full test suite with logging via ./run_tests.",
        "Creates test_results/test_run_* and latest_summary.txt.",
    ],
    "Project Scaffold (repo hygiene)": [
        "Moves stale files into date buckets (docs archive, tests cleanup, test_results).",
        "Optionally runs development_docs organizer.",
        "Non-destructive: moves only; no deletions.",
    ],
    "Organize development_docs": [
        "Moves docs into categorized/date buckets and updates README index.",
        "Use after adding or reviewing docs. Apply moves to update files.",
    ],
    "View Latest Coverage Report": [
        "Shows the latest test audit summary plus coverage report tail.",
        "Useful after running Test Audit or Run Test Suite.",
    ],
    "Rotate Logs": [
        "Runs log rotation (daily or weekly) via scripts/rotate_logs.py.",
        "Use to keep logs tidy outside of cron.",
    ],
    "Dev Server Control": [
        "Start/stop/status for the dev server (background).",
        "Uses scripts/serve.py with the safety keyword.",
    ],
}

DEFAULT_DRA_PRESETS: dict[str, dict[str, object]] = {
    "Agents": {"target": "Agents", "scope": "agents", "include_dev_docs": False},
    "ProjectWide": {
        "target": "ProjectWide",
        "scope": (
            "agents,alerts,analytics,backtest,monitoring,risk,server,strategies,static,"
            "tests,docs,scripts,config.py,broker.py,server.py,start_app.sh,universe.py,screener.py"
        ),
        "include_dev_docs": False,
    },
}

DEFAULT_CLEAN_CODE_PRESETS: dict[str, dict[str, object]] = {
    "Architecture": {
        "target": "Architecture",
        "scope": "agents,alerts,analytics,monitoring,risk,server,strategies",
        "include_dev_docs": False,
    },
    "TestDesign": {
        "target": "TestDesign",
        "scope": "tests,tests/README.md",
        "include_dev_docs": False,
    },
}


def load_audit_presets(path: Path = PRESET_FILE) -> dict[str, dict[str, dict[str, object]]]:
    if not path.exists():
        return {"dra": DEFAULT_DRA_PRESETS, "clean_code": DEFAULT_CLEAN_CODE_PRESETS}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"dra": DEFAULT_DRA_PRESETS, "clean_code": DEFAULT_CLEAN_CODE_PRESETS}

    dra = raw.get("dra") if isinstance(raw, dict) else None
    clean = raw.get("clean_code") if isinstance(raw, dict) else None
    tests = raw.get("tests") if isinstance(raw, dict) else None
    if not isinstance(dra, dict) or not isinstance(clean, dict) or not isinstance(tests, dict):
        return {"dra": DEFAULT_DRA_PRESETS, "clean_code": DEFAULT_CLEAN_CODE_PRESETS, "tests": {}}
    return {"dra": dra, "clean_code": clean, "tests": tests}


def _select_preset(
    presets: dict[str, dict[str, object]],
    selection: str,
) -> tuple[str | None, dict[str, object] | None]:
    if not selection:
        return None, None
    if selection.strip().lower() == "custom":
        return None, None
    mapping = {key.lower(): key for key in presets}
    key = mapping.get(selection.strip().lower())
    if not key:
        return None, None
    return key, presets[key]

@dataclass
class MenuItem:
    label: str
    handler: Callable[[curses._CursesWindow], None]


class TUI:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.menu_items: list[MenuItem] = []
        self.selected = 0

    def add_item(self, label: str, handler: Callable[[curses._CursesWindow], None]) -> None:
        self.menu_items.append(MenuItem(label, handler))

    def run(self) -> None:
        curses.curs_set(0)
        self.stdscr.nodelay(False)
        self.stdscr.keypad(True)
        while True:
            self._render_menu()
            key = self.stdscr.getch()
            if key in (curses.KEY_UP, ord("k")):
                self.selected = (self.selected - 1) % len(self.menu_items)
            elif key in (curses.KEY_DOWN, ord("j")):
                self.selected = (self.selected + 1) % len(self.menu_items)
            elif key in (ord("?"), ord("h"), ord("H")):
                label = self.menu_items[self.selected].label
                lines = ACTION_HELP.get(label, ["No help available."])
                popup_message(self.stdscr, f"Help: {label}", lines)
            elif key == 5:  # Ctrl+E
                global VERBOSE
                VERBOSE = not VERBOSE
            elif key in (curses.KEY_ENTER, 10, 13):
                self.menu_items[self.selected].handler(self.stdscr)
            elif key in (ord("q"), 27):
                break

    def _render_menu(self) -> None:
        self.stdscr.clear()
        height, width = self.stdscr.getmaxyx()
        title = "Dev Tools"
        verbose_state = "ON" if VERBOSE else "OFF"
        subtitle = f"Arrows: navigate  Enter: select  ?: help  Ctrl+E: verbose {verbose_state}  q: quit"
        self._center_text(1, title, curses.A_BOLD)
        self._center_text(2, subtitle, curses.A_DIM)

        start_y = 4
        for idx, item in enumerate(self.menu_items):
            prefix = "> " if idx == self.selected else "  "
            line = f"{prefix}{item.label}"
            attr = curses.A_REVERSE if idx == self.selected else curses.A_NORMAL
            self.stdscr.addnstr(start_y + idx, 2, line, width - 4, attr)

        self.stdscr.refresh()

    def _center_text(self, y: int, text: str, attr: int) -> None:
        height, width = self.stdscr.getmaxyx()
        x = max(0, (width - len(text)) // 2)
        self.stdscr.addnstr(y, x, text, width - x, attr)


def popup_message(stdscr, title: str, lines: list[str]) -> None:
    h, w = stdscr.getmaxyx()
    win_h = min(12, max(6, len(lines) + 4))
    win_w = min(90, max(40, max(len(title), *(len(line) for line in lines)) + 4))
    if h < 6 or w < 30:
        stdscr.clear()
        stdscr.addnstr(0, 0, f"{title}", max(0, w - 1), curses.A_BOLD)
        for idx, line in enumerate(lines[: max(0, h - 3)]):
            stdscr.addnstr(1 + idx, 0, line, max(0, w - 1))
        stdscr.addnstr(max(0, h - 1), 0, "Press any key to continue", max(0, w - 1), curses.A_DIM)
        stdscr.refresh()
        stdscr.getch()
        return

    win_h = min(win_h, h - 2)
    win_w = min(win_w, w - 2)
    win = curses.newwin(win_h, win_w, max(0, (h - win_h) // 2), max(0, (w - win_w) // 2))
    win.keypad(True)
    win.box()
    try:
        win.addnstr(0, 2, f" {title} ", win_w - 4, curses.A_BOLD)
        for i, line in enumerate(lines[: win_h - 4]):
            win.addnstr(2 + i, 2, line, win_w - 4)
        win.addnstr(win_h - 2, 2, "Press any key to continue", win_w - 4, curses.A_DIM)
    except curses.error:
        pass
    win.refresh()
    win.getch()


def popup_confirm(stdscr, title: str, question: str) -> bool:
    h, w = stdscr.getmaxyx()
    win_h, win_w = 7, min(80, max(40, len(question) + 6))
    if h < 6 or w < 30:
        stdscr.clear()
        stdscr.addnstr(0, 0, f"{title}", max(0, w - 1), curses.A_BOLD)
        stdscr.addnstr(2, 0, question, max(0, w - 1))
        stdscr.addnstr(4, 0, "Confirm? (y/n, Enter=Yes)", max(0, w - 1), curses.A_DIM)
        stdscr.refresh()
        curses.flushinp()
        while True:
            key = stdscr.getch()
            if key in (ord("y"), ord("Y"), curses.KEY_ENTER, 10, 13):
                return True
            if key in (ord("n"), ord("N"), 27):
                return False
    win_h = min(win_h, h - 2)
    win_w = min(win_w, w - 2)
    win = curses.newwin(win_h, win_w, max(0, (h - win_h) // 2), max(0, (w - win_w) // 2))
    win.keypad(True)
    win.nodelay(False)
    win.box()
    try:
        win.addnstr(0, 2, f" {title} ", win_w - 4, curses.A_BOLD)
        win.addnstr(2, 2, question, win_w - 4)
        win.addnstr(4, 2, "Confirm? (y/n, Enter=Yes)", win_w - 4, curses.A_DIM)
    except curses.error:
        pass
    win.refresh()
    curses.flushinp()
    while True:
        key = win.getch()
        if key in (ord("y"), ord("Y"), curses.KEY_ENTER, 10, 13):
            return True
        if key in (ord("n"), ord("N"), 27):
            return False


def popup_inputs(stdscr, title: str, fields: list[tuple[str, str]]) -> list[str]:
    curses.echo()
    h, w = stdscr.getmaxyx()
    win_h = min(4 + len(fields) * 2, h - 2)
    win_w = min(96, max(50, max(len(label) + len(default) + 6 for label, default in fields)))
    if h < 6 or w < 40:
        stdscr.clear()
        stdscr.addnstr(0, 0, f"{title}", max(0, w - 1), curses.A_BOLD)
        results = []
        for idx, (label, default) in enumerate(fields):
            y = 2 + idx * 2
            prompt = f"{label} [{default}]: " if default else f"{label}: "
            stdscr.addnstr(y, 0, prompt, max(0, w - 1))
            stdscr.refresh()
            input_bytes = stdscr.getstr(y, min(len(prompt), max(0, w - 1)))
            value = input_bytes.decode("utf-8") if input_bytes else ""
            results.append(value if value else default)
        curses.noecho()
        return results

    win_h = min(win_h, h - 2)
    win_w = min(win_w, w - 2)
    win = curses.newwin(win_h, win_w, max(0, (h - win_h) // 2), max(0, (w - win_w) // 2))
    win.keypad(True)
    win.box()
    try:
        win.addnstr(0, 2, f" {title} ", win_w - 4, curses.A_BOLD)
    except curses.error:
        pass
    results: list[str] = []
    for idx, (label, default) in enumerate(fields):
        y = 2 + idx * 2
        prompt = f"{label} [{default}]: " if default else f"{label}: "
        try:
            win.addnstr(y, 2, prompt, win_w - 4)
        except curses.error:
            pass
        win.refresh()
        input_bytes = win.getstr(y, 2 + len(prompt), max(1, win_w - len(prompt) - 4))
        value = input_bytes.decode("utf-8") if input_bytes else ""
        results.append(value if value else default)
    curses.noecho()
    return results


def _render_stream_window(stdscr, title: str, lines: list[str], status_line: str | None = None) -> None:
    try:
        stdscr.clear()
        height, width = stdscr.getmaxyx()
        stdscr.addnstr(0, 0, title, width - 1, curses.A_BOLD)
        help_line = "Press Ctrl+E in menu to toggle verbose output."
        if status_line:
            help_line = f"{help_line} | {status_line}"
        stdscr.addnstr(1, 0, help_line, width - 1, curses.A_DIM)
        output_top = 3
        output_bottom = height - 1 if status_line else height
        available = max(0, output_bottom - output_top)
        start_line = max(0, len(lines) - available)
        view = lines[start_line:start_line + available]
        for idx, line in enumerate(view):
            stdscr.addnstr(output_top + idx, 0, line, max(0, width - 1))
        if status_line:
            stdscr.addnstr(height - 1, 0, status_line, width - 1, curses.A_DIM)
        stdscr.refresh()
    except curses.error:
        pass


_PYTEST_STATUS_RE = re.compile(
    r"^(?P<nodeid>\S+::\S+.*?)\s+(?P<status>PASSED|FAILED|SKIPPED|XFAIL|XPASS|ERROR)"
)


def _parse_pytest_status_line(line: str) -> str | None:
    match = _PYTEST_STATUS_RE.match(line.strip())
    if not match:
        return None
    return match.group("nodeid")


def _collect_test_count(marker_expr: str) -> int:
    cmd = [PYTHON_BIN, "-m", "pytest", "tests", "--collect-only", "-q"]
    if marker_expr:
        cmd.extend(["-m", marker_expr])
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    try:
        proc = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True, env=env)
    except Exception:
        return 0
    if proc.returncode != 0:
        return 0
    lines = [line for line in proc.stdout.splitlines() if "::" in line]
    return len(lines)


def run_command(stdscr, cmd: list[str], details: list[str] | None = None) -> None:
    preview = " ".join(shlex.quote(part) for part in cmd)
    if not popup_confirm(stdscr, "Run Command", f"Run: {preview}"):
        return
    try:
        stdscr.clear()
        stdscr.addnstr(0, 0, "Running command...", curses.A_BOLD)
        stdscr.addnstr(1, 0, "Press Ctrl+E to toggle verbose in menu.", curses.A_DIM)
        if VERBOSE and details:
            for idx, line in enumerate(details[:6]):
                stdscr.addnstr(3 + idx, 0, line, curses.A_NORMAL)
            stdscr.addnstr(10, 0, preview, curses.A_DIM)
        else:
            stdscr.addnstr(3, 0, preview, curses.A_DIM)
        stdscr.refresh()
    except curses.error:
        pass
    try:
        proc = subprocess.run(
            cmd,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        output = []
        if proc.stdout:
            output.extend(proc.stdout.strip().splitlines()[-6:])
        if proc.stderr:
            output.append("[stderr]")
            output.extend(proc.stderr.strip().splitlines()[-6:])
        status_line = f"Exit code: {proc.returncode}"
        popup_message(stdscr, "Command Complete", [status_line] + output if output else [status_line])
    except Exception as exc:
        popup_message(stdscr, "Command Failed", [str(exc)])


def run_command_streaming(
    stdscr,
    cmd: list[str],
    details: list[str] | None = None,
    progress_total: int = 0,
) -> None:
    preview = " ".join(shlex.quote(part) for part in cmd)
    if not popup_confirm(stdscr, "Run Command", f"Run: {preview}"):
        return
    output_lines: list[str] = []
    title = "Running command (streaming output)..."
    status_line = "Working"
    if details and VERBOSE:
        output_lines.extend(details)
        output_lines.append("")
    _render_stream_window(stdscr, title, output_lines, status_line)
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=REPO_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
    except Exception as exc:
        popup_message(stdscr, "Command Failed", [str(exc)])
        return
    dot_count = 0
    last_tick = time.time()
    selector = selectors.DefaultSelector()
    if proc.stdout:
        selector.register(proc.stdout, selectors.EVENT_READ)

    completed = 0
    current_test = ""
    try:
        stream_open = True
        while True:
            events = selector.select(timeout=0.2)
            for key, _mask in events:
                line = key.fileobj.readline()
                if line:
                    output_lines.append(line.rstrip())
                    if progress_total:
                        parsed = _parse_pytest_status_line(line)
                        if parsed:
                            completed += 1
                            current_test = parsed
                    _render_stream_window(stdscr, title, output_lines, status_line)
                else:
                    try:
                        selector.unregister(key.fileobj)
                    except Exception:
                        pass
                    stream_open = False
            now = time.time()
            if now - last_tick >= 1.0:
                if progress_total:
                    percent = int((completed / progress_total) * 100) if progress_total else 0
                    status_line = f"{current_test or 'Running tests'} ... {percent}% ({completed}/{progress_total})"
                else:
                    dot_count = (dot_count + 1) % 4
                    status_line = "Working" + ("." * dot_count)
                _render_stream_window(stdscr, title, output_lines, status_line)
                last_tick = now
            if proc.poll() is not None and (not events or not stream_open):
                break
    except KeyboardInterrupt:
        try:
            proc.terminate()
        except Exception:
            pass
        try:
            proc.wait(timeout=2)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
        popup_message(stdscr, "Command Cancelled", ["Interrupted by user."])
        return

    if proc.stdout:
        for line in proc.stdout:
            output_lines.append(line.rstrip())
    rc = proc.wait()
    tail = output_lines[-8:] if output_lines else []
    log_line = _extract_prefix_line(output_lines, "Log file:")
    summary_line = _extract_prefix_line(output_lines, "Summary file:")
    audit_line = _extract_prefix_line(output_lines, "Draft audit written:")
    completion = [f"Exit code: {rc}"]
    if log_line:
        completion.append(log_line)
    if summary_line:
        completion.append(summary_line)
    if audit_line:
        completion.append(audit_line)
    if tail:
        completion.append("")
        completion.append("Last output:")
        completion.extend(tail)
    popup_message(stdscr, "Command Complete", completion)


def _extract_prefix_line(lines: list[str], prefix: str) -> str | None:
    for line in lines:
        if line.strip().startswith(prefix):
            return line.strip()
    return None


def handle_clean_code_audit(stdscr) -> None:
    presets = load_audit_presets().get("clean_code", {})
    preset_names = "/".join(list(presets.keys()) + ["Custom"]) if presets else "Custom"
    preset, = popup_inputs(
        stdscr,
        "Clean Code Preset",
        [
            (f"Preset ({preset_names})", "Architecture" if presets else "Custom"),
        ],
    )
    preset_key, config = _select_preset(presets, preset)
    if config:
        target = str(config.get("target", "Architecture"))
        scope = str(config.get("scope", "agents,analytics,server,static"))
        output_dir = "development_docs/clean_code_audits"
        include_docs = "y" if config.get("include_dev_docs") else "n"
        template_path = ""
    else:
        target, scope, output_dir, template_path, include_docs = popup_inputs(
            stdscr,
            "Clean Code Audit (Custom)",
            [
                ("Target", "ProjectStructure"),
                ("Scope (comma paths/globs)", "agents,analytics,server,static"),
                ("Output dir", "development_docs/clean_code_audits"),
                ("Template path", ""),
                ("Include development_docs? (y/n)", "n"),
            ],
        )
    cmd = [
        PYTHON_BIN,
        "scripts/run_clean_code_audit.py",
        "--target",
        target,
        "--scope",
        scope,
        "--output-dir",
        output_dir,
    ]
    if template_path:
        cmd.extend(["--template", template_path])
    if include_docs.lower().startswith("y"):
        cmd.append("--include-dev-docs")
    if VERBOSE:
        cmd.append("--verbose")
    details = [
        "Draft clean-code audit with evidence pack.",
        f"Preset: {preset_key if config else 'Custom'}",
        f"Target: {target}",
        f"Scope: {scope or 'n/a'}",
        f"Output: {output_dir}",
        f"Template: {template_path or 'auto'}",
        f"Include development_docs: {'yes' if include_docs.lower().startswith('y') else 'no'}",
    ]
    run_command_streaming(stdscr, cmd, details)


def handle_clean_code_index(stdscr) -> None:
    include_docs, = popup_inputs(
        stdscr,
        "Clean Code Index",
        [
            ("Include development_docs? (y/n)", "n"),
        ],
    )
    cmd = [PYTHON_BIN, "scripts/run_clean_code_audit.py", "--index-only"]
    if include_docs.lower().startswith("y"):
        cmd.append("--include-dev-docs")
    if VERBOSE:
        cmd.append("--verbose")
    details = [
        "Update clean-code index and change log (no draft).",
        f"Include development_docs: {'yes' if include_docs.lower().startswith('y') else 'no'}",
    ]
    run_command(stdscr, cmd, details)


def handle_dra_audit(stdscr) -> None:
    presets = load_audit_presets().get("dra", {})
    preset_names = "/".join(list(presets.keys()) + ["Custom"]) if presets else "Custom"
    preset, = popup_inputs(
        stdscr,
        "DRA Audit Preset",
        [
            (f"Preset ({preset_names})", "Agents" if presets else "Custom"),
        ],
    )
    preset_key, config = _select_preset(presets, preset)
    if config:
        target = str(config.get("target", "Agents"))
        scope = str(config.get("scope", "agents"))
        output_dir = "development_docs/audits"
        include_docs = "y" if config.get("include_dev_docs") else "n"
    else:
        target, scope, output_dir, include_docs = popup_inputs(
            stdscr,
            "DRA Audit (Custom)",
            [
                ("Target label (free text)", "PhaseD_Analytics"),
                ("Scope (comma paths/globs)", "analytics,server,static"),
                ("Output dir", "development_docs/audits"),
                ("Include development_docs? (y/n)", "n"),
            ],
        )
    cmd = [
        PYTHON_BIN,
        "scripts/run_dra_audit.py",
        "--target",
        target,
        "--scope",
        scope,
        "--output-dir",
        output_dir,
    ]
    if include_docs.lower().startswith("y"):
        cmd.append("--include-dev-docs")
    if VERBOSE:
        cmd.append("--verbose")
    details = [
        "Draft DRA audit with evidence pack.",
        f"Preset: {preset_key if config else 'Custom'}",
        f"Target: {target}",
        f"Scope: {scope or 'n/a'}",
        f"Output: {output_dir}",
        f"Include development_docs: {'yes' if include_docs.lower().startswith('y') else 'no'}",
    ]
    run_command_streaming(stdscr, cmd, details)


def handle_test_audit(stdscr) -> None:
    run_tests, run_coverage, repo_root = popup_inputs(
        stdscr,
        "Test Audit",
        [
            ("Run tests? (y/n)", "y"),
            ("Run coverage? (y/n)", "y"),
            ("Repo root (blank for current)", ""),
        ],
    )
    cmd = [PYTHON_BIN, "scripts/run_test_audit.py"]
    if run_tests.lower().startswith("n"):
        cmd.append("--no-tests")
    if run_coverage.lower().startswith("n"):
        cmd.append("--no-coverage")
    if repo_root:
        cmd.extend(["--repo", repo_root])
    if VERBOSE:
        cmd.append("--verbose")
    details = [
        "Run pytest with optional coverage.",
        f"Run tests: {'yes' if not run_tests.lower().startswith('n') else 'no'}",
        f"Run coverage: {'yes' if not run_coverage.lower().startswith('n') else 'no'}",
        f"Repo root: {repo_root or str(REPO_ROOT)}",
        "Outputs: test_results/test_audit_*",
    ]
    run_command_streaming(stdscr, cmd, details)


def handle_run_tests(stdscr) -> None:
    presets = load_audit_presets().get("tests", {})
    preset_names = "/".join(list(presets.keys()) + ["Custom"]) if presets else "Custom"
    preset, = popup_inputs(
        stdscr,
        "Test Suite Preset",
        [
            (f"Preset ({preset_names})", "All" if presets else "Custom"),
        ],
    )
    marker_expr = ""
    preset_key = None
    if preset.strip().lower() != "custom" and presets:
        mapping = {key.lower(): key for key in presets.keys()}
        preset_key = mapping.get(preset.strip().lower())
        if preset_key:
            marker_expr = str(presets[preset_key].get("marker", "")).strip()
    if preset_key is None:
        marker_expr, = popup_inputs(
            stdscr,
            "Custom Test Marker",
            [
                ("Marker expression (blank = all)", ""),
            ],
        )
        marker_expr = (marker_expr or "").strip()

    total = _collect_test_count(marker_expr)
    cmd = ["./run_tests"]
    if marker_expr:
        cmd.extend(["-m", marker_expr])
    if VERBOSE:
        cmd.append("--verbose")
    details = [
        "Run test suite with logging.",
        f"Preset: {preset_key or 'Custom'}",
        f"Marker: {marker_expr or 'all'}",
        "Uses scripts/run_tests.sh if available.",
        "Outputs: test_results/test_run_* and latest_summary.txt",
        "Verbose mode shows per-test progress in the log.",
    ]
    run_command_streaming(stdscr, cmd, details, progress_total=total)


def handle_docs_scaffold(stdscr) -> None:
    apply_flag, include_dirs, write_index, date_buckets = popup_inputs(
        stdscr,
        "Docs Scaffold",
        [
            ("Apply moves? (y/n)", "n"),
            ("Include directories? (y/n)", "n"),
            ("Write README index? (y/n)", "y"),
            ("Date buckets (comma or 'all')", "all"),
        ],
    )
    cmd = [PYTHON_BIN, "scripts/organize_development_docs.py"]
    if apply_flag.lower().startswith("y"):
        cmd.append("--apply")
    if include_dirs.lower().startswith("y"):
        cmd.append("--include-directories")
    if write_index.lower().startswith("y"):
        cmd.append("--write-index")
    if date_buckets:
        cmd.extend(["--date-buckets", date_buckets])
    details = [
        "Organize development_docs into categories/date buckets.",
        f"Apply moves: {'yes' if apply_flag.lower().startswith('y') else 'no'}",
        f"Include directories: {'yes' if include_dirs.lower().startswith('y') else 'no'}",
        f"Write README index: {'yes' if write_index.lower().startswith('y') else 'no'}",
        f"Date buckets: {date_buckets or 'none'}",
    ]
    run_command(stdscr, cmd, details)


def handle_project_scaffold(stdscr) -> None:
    apply_flag, docs_archive, tests_cleanup, test_results, dev_docs = popup_inputs(
        stdscr,
        "Project Scaffold",
        [
            ("Apply moves? (y/n)", "n"),
            ("Move docs/archive? (y/n)", "y"),
            ("Cleanup tests/ non-tests? (y/n)", "y"),
            ("Archive test_results logs? (y/n)", "y"),
            ("Run development_docs organizer? (y/n)", "n"),
        ],
    )
    cmd = [PYTHON_BIN, "scripts/organize_project_files.py"]
    if apply_flag.lower().startswith("y"):
        cmd.append("--apply")
    if docs_archive.lower().startswith("y"):
        cmd.append("--docs-archive")
    if tests_cleanup.lower().startswith("y"):
        cmd.append("--tests-cleanup")
    if test_results.lower().startswith("y"):
        cmd.append("--test-results")
    if dev_docs.lower().startswith("y"):
        cmd.append("--dev-docs")
    details = [
        "Repo hygiene scaffolder.",
        f"Apply: {'yes' if apply_flag.lower().startswith('y') else 'no'}",
        f"Docs archive: {'yes' if docs_archive.lower().startswith('y') else 'no'}",
        f"Tests cleanup: {'yes' if tests_cleanup.lower().startswith('y') else 'no'}",
        f"Test results: {'yes' if test_results.lower().startswith('y') else 'no'}",
        f"Dev docs: {'yes' if dev_docs.lower().startswith('y') else 'no'}",
    ]
    run_command_streaming(stdscr, cmd, details)


def handle_view_coverage(stdscr) -> None:
    tail_lines, list_files, limit = popup_inputs(
        stdscr,
        "Coverage Report",
        [
            ("Tail lines (0 = none)", "80"),
            ("List files (missing/zero/low)? (y/n)", "n"),
            ("List limit", "20"),
        ],
    )
    cmd = [
        PYTHON_BIN,
        "scripts/show_test_audit_summary.py",
        "--tail",
        tail_lines,
        "--limit",
        limit,
    ]
    if list_files.lower().startswith("y"):
        cmd.append("--list-files")
    details = [
        "Show latest test audit summary + coverage tail.",
        f"Tail lines: {tail_lines}",
        f"List files: {'yes' if list_files.lower().startswith('y') else 'no'}",
        f"List limit: {limit}",
    ]
    run_command_streaming(stdscr, cmd, details)


def handle_rotate_logs(stdscr) -> None:
    mode, logs_root = popup_inputs(
        stdscr,
        "Rotate Logs",
        [
            ("Mode (daily/weekly)", "daily"),
            ("Logs root (blank = default)", ""),
        ],
    )
    cmd = [PYTHON_BIN, "scripts/rotate_logs.py"]
    if mode.strip().lower().startswith("w"):
        cmd.append("--weekly")
    else:
        cmd.append("--daily")
    if logs_root:
        cmd.extend(["--logs-root", logs_root])
    details = [
        "Rotate log files.",
        f"Mode: {'weekly' if mode.strip().lower().startswith('w') else 'daily'}",
        f"Logs root: {logs_root or 'default'}",
    ]
    run_command_streaming(stdscr, cmd, details)


def handle_dev_server_control(stdscr) -> None:
    action, reload_flag, no_lifespan, log_level, workers = popup_inputs(
        stdscr,
        "Dev Server Control",
        [
            ("Action (start/stop/status)", "status"),
            ("Reload? (y/n)", "n"),
            ("No lifespan? (y/n)", "n"),
            ("Log level", "info"),
            ("Workers (blank = default)", ""),
        ],
    )
    cmd = [
        PYTHON_BIN,
        "scripts/dev_server_control.py",
        action.strip().lower() or "status",
    ]
    if reload_flag.lower().startswith("y"):
        cmd.append("--reload")
    if no_lifespan.lower().startswith("y"):
        cmd.append("--no-lifespan")
    if log_level:
        cmd.extend(["--log-level", log_level])
    if workers:
        cmd.extend(["--workers", workers])
    details = [
        "Dev server control (background).",
        f"Action: {action}",
        f"Reload: {'yes' if reload_flag.lower().startswith('y') else 'no'}",
        f"No lifespan: {'yes' if no_lifespan.lower().startswith('y') else 'no'}",
        f"Log level: {log_level or 'default'}",
        f"Workers: {workers or 'default'}",
    ]
    run_command_streaming(stdscr, cmd, details)


def get_menu_actions() -> list[tuple[str, Callable[[curses._CursesWindow], None]]]:
    return [
        ("Run Clean Code Audit (draft)", handle_clean_code_audit),
        ("Update Clean Code Index (no draft)", handle_clean_code_index),
        ("Run DRA Audit (draft)", handle_dra_audit),
        ("Run Test Audit", handle_test_audit),
        ("Run Test Suite (logged)", handle_run_tests),
        ("View Latest Coverage Report", handle_view_coverage),
        ("Rotate Logs", handle_rotate_logs),
        ("Dev Server Control", handle_dev_server_control),
        ("Project Scaffold (repo hygiene)", handle_project_scaffold),
        ("Organize development_docs", handle_docs_scaffold),
    ]


def run_command_headless(cmd: list[str]) -> int:
    preview = " ".join(shlex.quote(part) for part in cmd)
    print(f"Running: {preview}")
    proc = subprocess.run(cmd, cwd=REPO_ROOT)
    return proc.returncode


def validate_menu() -> list[str]:
    errors: list[str] = []
    labels: list[str] = []
    handlers: list[Callable | None] = []
    for label, handler in MENU_ACTIONS:
        labels.append(label)
        handlers.append(handler)

    if len(labels) != len(set(labels)):
        errors.append("Duplicate menu labels detected.")
    for idx, handler in enumerate(handlers):
        if handler is None:
            errors.append(f"Menu item '{labels[idx]}' has no handler.")
    if not labels:
        errors.append("No menu items registered.")
    return errors


def _resolve_action(action: str) -> Callable[[object | None], None] | None:
    action = (action or "").strip().lower()
    mapping = {label.lower(): handler for label, handler in MENU_ACTIONS}
    return mapping.get(action)


def handle_clean_code_audit_headless(args: argparse.Namespace) -> int:
    cmd = [
        PYTHON_BIN,
        "scripts/run_clean_code_audit.py",
        "--target",
        args.target or "ProjectStructure",
        "--scope",
        args.scope or "agents,analytics,server,static",
        "--output-dir",
        args.output_dir or "development_docs/clean_code_audits",
    ]
    if args.template:
        cmd.extend(["--template", args.template])
    if args.include_dev_docs:
        cmd.append("--include-dev-docs")
    if args.verbose:
        cmd.append("--verbose")
    return run_command_headless(cmd)


def handle_clean_code_index_headless(args: argparse.Namespace) -> int:
    cmd = [PYTHON_BIN, "scripts/run_clean_code_audit.py", "--index-only"]
    if args.include_dev_docs:
        cmd.append("--include-dev-docs")
    if args.verbose:
        cmd.append("--verbose")
    return run_command_headless(cmd)


def handle_dra_audit_headless(args: argparse.Namespace) -> int:
    cmd = [
        PYTHON_BIN,
        "scripts/run_dra_audit.py",
        "--target",
        args.target or "PhaseD_Analytics",
        "--scope",
        args.scope or "analytics,server,static",
        "--output-dir",
        args.output_dir or "development_docs/audits",
    ]
    if args.include_dev_docs:
        cmd.append("--include-dev-docs")
    if args.verbose:
        cmd.append("--verbose")
    return run_command_headless(cmd)


def handle_test_audit_headless(args: argparse.Namespace) -> int:
    cmd = [PYTHON_BIN, "scripts/run_test_audit.py"]
    if args.no_tests:
        cmd.append("--no-tests")
    if args.no_coverage:
        cmd.append("--no-coverage")
    if args.repo:
        cmd.extend(["--repo", args.repo])
    return run_command_headless(cmd)


def handle_run_tests_headless(_args: argparse.Namespace) -> int:
    cmd = ["./run_tests"]
    marker_expr = ""
    if getattr(_args, "test_preset", ""):
        presets = load_audit_presets().get("tests", {})
        mapping = {key.lower(): key for key in presets.keys()}
        preset_key = mapping.get(str(_args.test_preset).strip().lower())
        if preset_key:
            marker_expr = str(presets[preset_key].get("marker", "")).strip()
    if getattr(_args, "marker", ""):
        marker_expr = str(_args.marker).strip()
    if marker_expr:
        cmd.extend(["-m", marker_expr])
    if getattr(_args, "verbose", False):
        cmd.append("--verbose")
    if getattr(_args, "quiet", False):
        cmd.append("--quiet")
    return run_command_headless(cmd)


def handle_docs_scaffold_headless(args: argparse.Namespace) -> int:
    cmd = [PYTHON_BIN, "scripts/organize_development_docs.py"]
    if args.apply:
        cmd.append("--apply")
    if args.include_directories:
        cmd.append("--include-directories")
    if args.write_index:
        cmd.append("--write-index")
    if args.date_buckets:
        cmd.extend(["--date-buckets", args.date_buckets])
    return run_command_headless(cmd)


def handle_project_scaffold_headless(args: argparse.Namespace) -> int:
    cmd = [PYTHON_BIN, "scripts/organize_project_files.py"]
    if args.apply:
        cmd.append("--apply")
    if args.docs_archive:
        cmd.append("--docs-archive")
    if args.tests_cleanup:
        cmd.append("--tests-cleanup")
    if args.test_results:
        cmd.append("--test-results")
    if args.dev_docs:
        cmd.append("--dev-docs")
    return run_command_headless(cmd)


def handle_view_coverage_headless(args: argparse.Namespace) -> int:
    cmd = [PYTHON_BIN, "scripts/show_test_audit_summary.py"]
    tail = args.tail or (120 if args.verbose else 80)
    if tail:
        cmd.extend(["--tail", str(tail)])
    if args.list_files:
        cmd.append("--list-files")
    if args.limit:
        cmd.extend(["--limit", str(args.limit)])
    return run_command_headless(cmd)


def handle_rotate_logs_headless(args: argparse.Namespace) -> int:
    cmd = [PYTHON_BIN, "scripts/rotate_logs.py"]
    mode = (args.log_mode or "daily").strip().lower()
    if mode.startswith("w"):
        cmd.append("--weekly")
    else:
        cmd.append("--daily")
    if args.logs_root:
        cmd.extend(["--logs-root", args.logs_root])
    return run_command_headless(cmd)


def handle_dev_server_headless(args: argparse.Namespace) -> int:
    cmd = [
        PYTHON_BIN,
        "scripts/dev_server_control.py",
        (args.server_action or "status").strip().lower(),
    ]
    if args.host:
        cmd.extend(["--host", args.host])
    if args.port:
        cmd.extend(["--port", str(args.port)])
    if args.reload:
        cmd.append("--reload")
    if args.no_lifespan:
        cmd.append("--no-lifespan")
    if args.log_level:
        cmd.extend(["--log-level", args.log_level])
    if args.workers:
        cmd.extend(["--workers", str(args.workers)])
    if args.keyword:
        cmd.extend(["--keyword", args.keyword])
    if args.pid_file:
        cmd.extend(["--pid-file", args.pid_file])
    if args.log_file:
        cmd.extend(["--log-file", args.log_file])
    return run_command_headless(cmd)


def main(stdscr) -> None:
    tui = TUI(stdscr)
    for label, handler in MENU_ACTIONS:
        tui.add_item(label, handler)
    tui.add_item("Exit", lambda s: None)

    def _exit_if_selected(_stdscr):
        raise SystemExit(0)

    tui.menu_items[-1] = MenuItem("Exit", _exit_if_selected)

    try:
        tui.run()
    except SystemExit:
        pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dev tools TUI")
    parser.add_argument("--check", action="store_true", help="Validate menu registry and exit")
    parser.add_argument("--run", default="", help="Run a menu action headlessly by label")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output for headless run")
    parser.add_argument("--quiet", action="store_true", help="Enable quiet output for headless run")
    parser.add_argument("--target", default="")
    parser.add_argument("--scope", default="")
    parser.add_argument("--output-dir", dest="output_dir", default="")
    parser.add_argument("--template", default="")
    parser.add_argument("--include-dev-docs", action="store_true")
    parser.add_argument("--no-tests", action="store_true")
    parser.add_argument("--no-coverage", action="store_true")
    parser.add_argument("--repo", default="")
    parser.add_argument("--marker", default="")
    parser.add_argument("--test-preset", default="")
    parser.add_argument("--tail", type=int, default=0)
    parser.add_argument("--list-files", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--log-mode", default="")
    parser.add_argument("--logs-root", default="")
    parser.add_argument("--server-action", default="")
    parser.add_argument("--host", default="")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--reload", action="store_true")
    parser.add_argument("--no-lifespan", action="store_true")
    parser.add_argument("--log-level", default="")
    parser.add_argument("--workers", type=int, default=0)
    parser.add_argument("--keyword", default="")
    parser.add_argument("--pid-file", default="")
    parser.add_argument("--log-file", default="")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--include-directories", action="store_true")
    parser.add_argument("--write-index", action="store_true")
    parser.add_argument("--date-buckets", default="")
    parser.add_argument("--docs-archive", action="store_true")
    parser.add_argument("--tests-cleanup", action="store_true")
    parser.add_argument("--test-results", action="store_true")
    parser.add_argument("--dev-docs", action="store_true")
    args = parser.parse_args()

    MENU_ACTIONS = get_menu_actions()

    if args.check:
        problems = validate_menu()
        if problems:
            print("Menu validation failed:")
            for problem in problems:
                print(f"- {problem}")
            raise SystemExit(1)
        print("Menu validation OK.")
        raise SystemExit(0)

    if args.run:
        action = _resolve_action(args.run)
        if not action:
            print(f"Unknown action: {args.run}")
            print("Available actions:")
            for label, _handler in MENU_ACTIONS:
                print(f"- {label}")
            raise SystemExit(2)
        headless_map = {
            handle_clean_code_audit: handle_clean_code_audit_headless,
            handle_clean_code_index: handle_clean_code_index_headless,
            handle_dra_audit: handle_dra_audit_headless,
            handle_test_audit: handle_test_audit_headless,
            handle_run_tests: handle_run_tests_headless,
            handle_view_coverage: handle_view_coverage_headless,
            handle_rotate_logs: handle_rotate_logs_headless,
            handle_dev_server_control: handle_dev_server_headless,
            handle_project_scaffold: handle_project_scaffold_headless,
            handle_docs_scaffold: handle_docs_scaffold_headless,
        }
        handler = headless_map.get(action)
        if not handler:
            print("Selected action is not runnable headlessly.")
            raise SystemExit(3)
        raise SystemExit(handler(args))

    curses.wrapper(main)

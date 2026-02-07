"""TestAuditAgent - local test and coverage audit without API dependencies."""
from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class CoverageSummary:
    covered_percent: float
    total_statements: int
    covered_statements: int
    missing_files: list[str]
    zero_coverage_files: list[str]
    low_coverage_files: list[str]


@dataclass
class TestValiditySummary:
    total_tests: int
    tests_without_asserts: list[str]
    skipped_tests: list[str]
    xfailed_tests: list[str]
    empty_tests: list[str]
    nonstandard_test_files: list[str]


class TestAuditAgent:
    """Runs pytest with coverage and audits test validity heuristically."""

    def __init__(self, repo_root: str | Path | None = None):
        self.repo_root = Path(repo_root) if repo_root else Path(__file__).resolve().parents[2]
        self.tests_dir = self.repo_root / "tests"
        self.output_root = self.repo_root / "test_results" / "test_audit"
        self.include_dirs = {
            "agents",
            "alerts",
            "analytics",
            "monitoring",
            "risk",
            "server",
            "strategies",
            "backtest",
            "data",
        }
        self.exclude_dirs = {
            "tests",
            "venv",
            "__pycache__",
            "static",
            "img",
            "logs",
            "test_results",
            "development_docs",
            "docs",
            "scripts",
            "agent-trainer",
        }
        self.exclude_files = {
            "server.py",
            "start_app.sh",
        }

    def run_audit(self, run_tests: bool = True, run_coverage: bool = True) -> dict:
        run_dir = self._create_run_dir()
        summary: dict[str, object] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "run_dir": str(run_dir),
            "pytest": None,
            "coverage": None,
            "test_validity": None,
        }

        if run_tests:
            pytest_result = self._run_pytest_with_coverage(run_dir, run_coverage)
            summary["pytest"] = pytest_result
            if pytest_result.get("coverage_json"):
                summary["coverage"] = self._analyze_coverage(pytest_result["coverage_json"])
        if summary["coverage"] is None:
            summary["coverage"] = self._analyze_coverage(None)

        summary["test_validity"] = self._analyze_tests()

        self._write_summary(run_dir, summary)
        return summary

    def _create_run_dir(self) -> Path:
        stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        run_dir = self.output_root / f"test_audit_{stamp}"
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir

    def _coverage_available(self) -> bool:
        try:
            import coverage  # noqa: F401
        except Exception:
            return False
        return True

    def _run_pytest_with_coverage(self, run_dir: Path, run_coverage: bool) -> dict:
        result: dict[str, object] = {
            "exit_code": None,
            "stdout": None,
            "stderr": None,
            "coverage_json": None,
            "coverage_report": None,
            "coverage_enabled": False,
            "coverage_error": None,
        }
        stdout_path = run_dir / "pytest_stdout.txt"
        stderr_path = run_dir / "pytest_stderr.txt"

        env = os.environ.copy()
        env["PYTHONPATH"] = str(self.repo_root)

        if run_coverage and self._coverage_available():
            result["coverage_enabled"] = True
            cov_file = run_dir / ".coverage"
            env["COVERAGE_FILE"] = str(cov_file)
            cmd = [sys.executable, "-m", "coverage", "run", "-m", "pytest", "tests", "-q"]
        else:
            if run_coverage:
                result["coverage_error"] = "coverage not installed"
            cmd = [sys.executable, "-m", "pytest", "tests", "-q"]

        proc = subprocess.run(
            cmd,
            cwd=self.repo_root,
            env=env,
            capture_output=True,
            text=True,
        )
        stdout_path.write_text(proc.stdout, encoding="utf-8")
        stderr_path.write_text(proc.stderr, encoding="utf-8")
        result["exit_code"] = proc.returncode
        result["stdout"] = str(stdout_path)
        result["stderr"] = str(stderr_path)

        if result["coverage_enabled"]:
            coverage_json = run_dir / "coverage.json"
            coverage_report = run_dir / "coverage_report.txt"
            json_proc = subprocess.run(
                [sys.executable, "-m", "coverage", "json", "-o", str(coverage_json)],
                cwd=self.repo_root,
                env=env,
                capture_output=True,
                text=True,
            )
            report_proc = subprocess.run(
                [sys.executable, "-m", "coverage", "report", "-m"],
                cwd=self.repo_root,
                env=env,
                capture_output=True,
                text=True,
            )
            coverage_report.write_text(report_proc.stdout, encoding="utf-8")
            if json_proc.returncode == 0 and coverage_json.exists():
                result["coverage_json"] = str(coverage_json)
            else:
                result["coverage_error"] = json_proc.stderr.strip() or "coverage json failed"
            result["coverage_report"] = str(coverage_report)

        return result

    def _analyze_coverage(self, coverage_json_path: str | None) -> CoverageSummary:
        if not coverage_json_path or not os.path.exists(coverage_json_path):
            return CoverageSummary(
                covered_percent=0.0,
                total_statements=0,
                covered_statements=0,
                missing_files=[],
                zero_coverage_files=[],
                low_coverage_files=[],
            )

        python_files = self._collect_python_files()
        coverage_files: set[Path] = set()
        covered_percent = 0.0
        total_statements = 0
        covered_statements = 0
        zero_coverage: list[str] = []
        low_coverage: list[str] = []

        data = json.loads(Path(coverage_json_path).read_text(encoding="utf-8"))
        files = data.get("files", {})
        for filename, payload in files.items():
            path = Path(filename).resolve()
            coverage_files.add(path)
            summary = payload.get("summary", {})
            percent = float(summary.get("percent_covered", 0.0))
            if percent == 0.0:
                zero_coverage.append(str(path))
            elif percent < 50.0:
                low_coverage.append(str(path))
            total_statements += int(summary.get("num_statements", 0))
            covered_statements += int(summary.get("covered_lines", 0))
        if total_statements:
            covered_percent = round((covered_statements / total_statements) * 100, 2)

        missing_files = [str(p) for p in sorted(python_files) if p not in coverage_files]

        return CoverageSummary(
            covered_percent=covered_percent,
            total_statements=total_statements,
            covered_statements=covered_statements,
            missing_files=missing_files,
            zero_coverage_files=sorted(zero_coverage),
            low_coverage_files=sorted(low_coverage),
        )

    def _collect_python_files(self) -> set[Path]:
        files: set[Path] = set()
        for path in self.repo_root.rglob("*.py"):
            rel = path.relative_to(self.repo_root)
            if any(part in self.exclude_dirs for part in rel.parts):
                continue
            if rel.name in self.exclude_files:
                continue
            if rel.parts[0] in self.include_dirs or len(rel.parts) == 1:
                files.add(path.resolve())
        return files

    def _analyze_tests(self) -> TestValiditySummary:
        tests_without_asserts: list[str] = []
        skipped_tests: list[str] = []
        xfailed_tests: list[str] = []
        empty_tests: list[str] = []
        nonstandard_test_files: list[str] = []
        total_tests = 0

        if not self.tests_dir.exists():
            return TestValiditySummary(0, [], [], [], [], [])

        for path in sorted(self.tests_dir.rglob("*.py")):
            if path.name.startswith("test_") is False:
                nonstandard_test_files.append(str(path))
            source = path.read_text(encoding="utf-8")
            try:
                tree = ast.parse(source)
            except SyntaxError:
                continue
            collector = _TestCollector(path)
            collector.visit(tree)
            total_tests += len(collector.tests)
            tests_without_asserts.extend(collector.tests_without_asserts)
            skipped_tests.extend(collector.skipped_tests)
            xfailed_tests.extend(collector.xfailed_tests)
            empty_tests.extend(collector.empty_tests)

        return TestValiditySummary(
            total_tests=total_tests,
            tests_without_asserts=tests_without_asserts,
            skipped_tests=skipped_tests,
            xfailed_tests=xfailed_tests,
            empty_tests=empty_tests,
            nonstandard_test_files=nonstandard_test_files,
        )

    def _write_summary(self, run_dir: Path, summary: dict) -> None:
        json_path = run_dir / "summary.json"
        json_path.write_text(json.dumps(summary, indent=2, default=_json_default), encoding="utf-8")
        markdown_path = run_dir / "summary.md"
        markdown_path.write_text(_summary_markdown(summary), encoding="utf-8")


class _TestCollector(ast.NodeVisitor):
    def __init__(self, path: Path):
        self.path = path
        self.tests: list[str] = []
        self.tests_without_asserts: list[str] = []
        self.skipped_tests: list[str] = []
        self.xfailed_tests: list[str] = []
        self.empty_tests: list[str] = []
        self._class_stack: list[str] = []

    def visit_ClassDef(self, node: ast.ClassDef):
        self._class_stack.append(node.name)
        self.generic_visit(node)
        self._class_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._handle_test(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._handle_test(node)
        self.generic_visit(node)

    def _handle_test(self, node: ast.AST) -> None:
        name = getattr(node, "name", "")
        if not name.startswith("test"):
            return
        qualified = self._qualify(name)
        self.tests.append(qualified)
        if _is_decorated_skip(node):
            self.skipped_tests.append(qualified)
        if _is_decorated_xfail(node):
            self.xfailed_tests.append(qualified)
        visitor = _AssertVisitor()
        visitor.visit(node)
        if visitor.is_empty:
            self.empty_tests.append(qualified)
        if not visitor.has_assert and not visitor.has_assert_like:
            self.tests_without_asserts.append(qualified)

    def _qualify(self, name: str) -> str:
        prefix = "::".join(self._class_stack)
        if prefix:
            return f"{self.path}::{prefix}::{name}"
        return f"{self.path}::{name}"


class _AssertVisitor(ast.NodeVisitor):
    def __init__(self):
        self.has_assert = False
        self.has_assert_like = False
        self.is_empty = True

    def visit_Assert(self, node: ast.Assert):
        self.has_assert = True
        self.is_empty = False

    def visit_Call(self, node: ast.Call):
        self.is_empty = False
        if _is_assert_like_call(node):
            self.has_assert_like = True
        self.generic_visit(node)

    def visit_Raise(self, node: ast.Raise):
        self.is_empty = False

    def visit_Pass(self, node: ast.Pass):
        pass


def _is_assert_like_call(node: ast.Call) -> bool:
    func = node.func
    if isinstance(func, ast.Attribute):
        if func.attr.startswith("assert"):
            return True
        if func.attr in {"raises", "fail", "skip", "xfail"}:
            return True
        if isinstance(func.value, ast.Name) and func.value.id in {"pytest", "unittest"}:
            return True
    if isinstance(func, ast.Name) and func.id in {"assert", "raises", "fail"}:
        return True
    return False


def _is_decorated_skip(node: ast.AST) -> bool:
    decorators = getattr(node, "decorator_list", [])
    return any(_decorator_matches(dec, {"skip", "skipif"}) for dec in decorators)


def _is_decorated_xfail(node: ast.AST) -> bool:
    decorators = getattr(node, "decorator_list", [])
    return any(_decorator_matches(dec, {"xfail"}) for dec in decorators)


def _decorator_matches(dec: ast.AST, names: set[str]) -> bool:
    if isinstance(dec, ast.Attribute):
        return dec.attr in names
    if isinstance(dec, ast.Call):
        if isinstance(dec.func, ast.Attribute):
            return dec.func.attr in names
    return False


def _json_default(value):
    if isinstance(value, (CoverageSummary, TestValiditySummary)):
        return value.__dict__
    return str(value)


def _summary_markdown(summary: dict) -> str:
    cov = _as_dict(summary.get("coverage"))
    test = _as_dict(summary.get("test_validity"))
    lines = [
        "# Test Audit Summary",
        "",
        f"Timestamp: {summary.get('timestamp')}",
        "",
    ]
    if cov:
        lines.extend([
            "## Coverage",
            f"Total statements: {cov.get('total_statements')}",
            f"Covered statements: {cov.get('covered_statements')}",
            f"Coverage percent: {cov.get('covered_percent')}%",
            "",
            f"Missing files (not executed): {len(cov.get('missing_files', []))}",
            f"Zero coverage files: {len(cov.get('zero_coverage_files', []))}",
            f"Low coverage files (<50%): {len(cov.get('low_coverage_files', []))}",
            "",
        ])
    if test:
        lines.extend([
            "## Test Validity",
            f"Total tests discovered: {test.get('total_tests')}",
            f"Tests without asserts: {len(test.get('tests_without_asserts', []))}",
            f"Skipped tests: {len(test.get('skipped_tests', []))}",
            f"Xfailed tests: {len(test.get('xfailed_tests', []))}",
            f"Empty tests: {len(test.get('empty_tests', []))}",
            f"Nonstandard test files: {len(test.get('nonstandard_test_files', []))}",
        ])
    lines.append("")
    return "\n".join(lines)


def _as_dict(obj):
    if obj is None:
        return None
    if hasattr(obj, "__dict__"):
        return obj.__dict__
    return obj

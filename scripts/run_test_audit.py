"""Run local test and coverage audit (no API dependency)."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agents.dev.test_audit_agent import TestAuditAgent


def _as_dict(obj):
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "__dict__"):
        return obj.__dict__
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Run test audit with optional coverage.")
    parser.add_argument("--no-tests", action="store_true", help="Skip running pytest")
    parser.add_argument("--no-coverage", action="store_true", help="Skip coverage instrumentation")
    parser.add_argument("--repo", default=None, help="Repo root (defaults to current repo)")
    parser.add_argument("--verbose", action="store_true", help="Verbose progress output")
    args = parser.parse_args()

    if args.verbose:
        print("Starting test audit...", flush=True)
        print(f"Run tests: {'yes' if not args.no_tests else 'no'}", flush=True)
        print(f"Run coverage: {'yes' if not args.no_coverage else 'no'}", flush=True)

    agent = TestAuditAgent(repo_root=Path(args.repo) if args.repo else None)
    if args.verbose:
        print("Running audit phases (pytest, coverage, validity)...", flush=True)
    summary = agent.run_audit(
        run_tests=not args.no_tests,
        run_coverage=not args.no_coverage,
        verbose=args.verbose,
    )
    if args.verbose:
        print("Phase 2/3: Coverage analysis...", flush=True)
        print("Phase 3/3: Test validity analysis...", flush=True)
    print("Test audit complete:")
    print(f"  Run dir: {summary.get('run_dir')}")
    cov = _as_dict(summary.get("coverage"))
    if cov:
        print(f"  Coverage: {cov.get('covered_percent')}%")
        print(f"  Missing files: {len(cov.get('missing_files', []))}")
    test = _as_dict(summary.get("test_validity"))
    if test:
        print(f"  Tests without asserts: {len(test.get('tests_without_asserts', []))}")
        print(f"  Skipped tests: {len(test.get('skipped_tests', []))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

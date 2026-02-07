"""Run local test and coverage audit (no API dependency)."""
from __future__ import annotations

import argparse
from pathlib import Path

from agents.dev.test_audit_agent import TestAuditAgent


def main() -> int:
    parser = argparse.ArgumentParser(description="Run test audit with optional coverage.")
    parser.add_argument("--no-tests", action="store_true", help="Skip running pytest")
    parser.add_argument("--no-coverage", action="store_true", help="Skip coverage instrumentation")
    parser.add_argument("--repo", default=None, help="Repo root (defaults to current repo)")
    args = parser.parse_args()

    agent = TestAuditAgent(repo_root=Path(args.repo) if args.repo else None)
    summary = agent.run_audit(run_tests=not args.no_tests, run_coverage=not args.no_coverage)
    print("Test audit complete:")
    print(f"  Run dir: {summary.get('run_dir')}")
    cov = summary.get("coverage")
    if cov:
        print(f"  Coverage: {cov.get('covered_percent')}%")
        print(f"  Missing files: {len(cov.get('missing_files', []))}")
    test = summary.get("test_validity")
    if test:
        print(f"  Tests without asserts: {len(test.get('tests_without_asserts', []))}")
        print(f"  Skipped tests: {len(test.get('skipped_tests', []))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

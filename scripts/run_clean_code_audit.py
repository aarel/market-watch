"""Run clean code audit drafting with project change tracking (dev-only)."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agents.dev.clean_code_audit_agent import CleanCodeAuditAgent


class _NullBus:
    """Minimal stand-in for BaseAgent (no event bus usage in CLI mode)."""
    def __init__(self):
        self._context = type("ctx", (), {"universe": None, "session_id": "dev-cli"})


def main() -> int:
    parser = argparse.ArgumentParser(description="Draft clean-code DRA audits.")
    parser.add_argument("--target", default="", help="Audit target label")
    parser.add_argument("--scope", default="", help="Comma-separated paths/globs for evidence")
    parser.add_argument("--output-dir", default="development_docs/clean_code_audits", help="Output directory")
    parser.add_argument("--template", default="", help="Path to clean code audit template")
    parser.add_argument("--include-dev-docs", action="store_true", help="Include development_docs in indexing")
    parser.add_argument("--index-only", action="store_true", help="Only update project index + change log")
    args = parser.parse_args()

    agent = CleanCodeAuditAgent(_NullBus(), include_dev_docs=args.include_dev_docs)
    if args.index_only:
        diff = agent.update_index()
        print(f"Index updated. Added={len(diff.added)} Removed={len(diff.removed)} Modified={len(diff.modified)}")
        return 0
    if not args.target:
        raise SystemExit("error: --target is required unless --index-only is set")
    scope = [s.strip() for s in args.scope.split(",") if s.strip()]
    template_path = Path(args.template) if args.template else None
    output_dir = Path(args.output_dir)
    output_path = agent.draft_audit(args.target, scope, output_dir, template_path)
    print(f"Draft audit written: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

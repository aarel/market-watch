"""Run DRA audit drafting with evidence packs (dev-only)."""
from __future__ import annotations

import argparse
import sys
import threading
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agents.dev.dra_audit_agent import DRAAuditAgent


class _NullBus:
    """Minimal stand-in for BaseAgent (no event bus usage in CLI mode)."""
    def __init__(self):
        self._context = type("ctx", (), {"universe": None, "session_id": "dev-cli"})


def main() -> int:
    parser = argparse.ArgumentParser(description="Draft DRA audits (implementation/phase).")
    parser.add_argument("--target", required=True, help="Audit target label")
    parser.add_argument("--scope", default="", help="Comma-separated paths/globs for evidence")
    parser.add_argument("--output-dir", default="development_docs/audits", help="Output directory")
    parser.add_argument("--include-dev-docs", action="store_true", help="Include development_docs in indexing")
    parser.add_argument("--verbose", action="store_true", help="Verbose progress output")
    args = parser.parse_args()

    agent = DRAAuditAgent(_NullBus(), include_dev_docs=args.include_dev_docs)
    scope = [s.strip() for s in args.scope.split(",") if s.strip()]
    output_dir = Path(args.output_dir)
    stop_event: threading.Event | None = None
    dotter: threading.Thread | None = None

    if args.verbose and sys.stdout.isatty():
        stop_event = threading.Event()

        def _dotter():
            while not stop_event.wait(1.0):
                print(".", flush=True)

        dotter = threading.Thread(target=_dotter, daemon=True)
        dotter.start()

    try:
        output = agent.draft_audit(args.target, scope, output_dir, verbose=args.verbose)
        print(f"Draft audit written: {output.path}")
    finally:
        if stop_event:
            stop_event.set()
        if dotter:
            dotter.join(timeout=1.0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""
Convenient launcher for the Market-Watch FastAPI server.

Usage:
  python scripts/serve.py --keyword "activate market-watch" [--reload] [--host 0.0.0.0] [--port 8000]

The safety keyword helps avoid accidentally starting live trading. Set
`--keyword "activate market-watch"` to proceed.
"""

import argparse
import os
import sys
from pathlib import Path

# Add project root to sys.path so uvicorn can import server module
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import uvicorn


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Start the Market-Watch API service.")
    parser.add_argument(
        "--keyword",
        default="",
        help='Safety phrase; must be exactly "activate market-watch" to start.',
    )
    parser.add_argument(
        "--host",
        default=os.getenv("API_HOST", "127.0.0.1"),
        help="Bind host (default from API_HOST env or 127.0.0.1).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("API_PORT", "8000")),
        help="Bind port (default from API_PORT env or 8000).",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload (development only).",
    )
    parser.add_argument(
        "--no-lifespan",
        action="store_true",
        help="Skip heavy startup (broker/agents) by setting FASTAPI_DISABLE_LIFESPAN=1.",
    )
    parser.add_argument(
        "--log-level",
        default=os.getenv("UVICORN_LOG_LEVEL", "info"),
        help="Uvicorn log level (info, debug, warning...).",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Number of worker processes (requires reload=False).",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if args.keyword.strip().lower() != "activate market-watch":
        print('Refusing to start: pass --keyword "activate market-watch" to confirm.', file=sys.stderr)
        sys.exit(1)

    if args.no_lifespan:
        os.environ["FASTAPI_DISABLE_LIFESPAN"] = "1"

    uvicorn.run(
        "server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=args.log_level,
        workers=args.workers,
    )


if __name__ == "__main__":
    main()

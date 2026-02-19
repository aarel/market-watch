#!/usr/bin/env python3
"""CLI for SQLite-backed communicate engine."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from commscribe.engine.communicate_db import CommunicateDB


def parse_artifact(value: str) -> tuple[str, str]:
    if ":" not in value:
        raise argparse.ArgumentTypeError("artifact must be file_path:change_type")
    p, t = value.split(":", 1)
    return p.strip(), t.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="commscribe/db/communicate.db")
    parser.add_argument("--schema", default="commscribe/db/schema.sql")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_create = sub.add_parser("create")
    p_create.add_argument("--id", required=True)
    p_create.add_argument("--title", required=True)
    p_create.add_argument("--objective", required=True)
    p_create.add_argument("--status", default="INPUT_PAD")
    p_create.add_argument("--artifact", action="append", type=parse_artifact)

    p_update = sub.add_parser("update")
    p_update.add_argument("--id", required=True)
    p_update.add_argument("--status")
    p_update.add_argument("--log")
    p_update.add_argument("--artifact", action="append", type=parse_artifact)

    p_complete = sub.add_parser("complete")
    p_complete.add_argument("--id", required=True)
    p_complete.add_argument("--objectives-addressed", required=True)
    p_complete.add_argument("--quality-checks", required=True)
    p_complete.add_argument("--risks", required=True)
    p_complete.add_argument("--final-status", required=True)

    p_status = sub.add_parser("status")
    p_status.add_argument("--id")

    p_export = sub.add_parser("export-md")
    p_export.add_argument("--output", required=True)

    args = parser.parse_args()
    db = CommunicateDB(args.db)
    db.init_schema(args.schema)

    if args.cmd == "create":
        db.create_request(args.id, args.title, args.objective, status=args.status, artifacts=args.artifact)
        print(args.id)
        return 0

    if args.cmd == "update":
        if args.status:
            db.transition_status(args.id, args.status)
        if args.log:
            db.add_log(args.id, args.log)
        if args.artifact:
            for fp, ct in args.artifact:
                db.add_artifact(args.id, fp, ct)
        print(args.id)
        return 0

    if args.cmd == "complete":
        db.complete_with_verification(
            args.id,
            objectives_addressed=args.objectives_addressed,
            quality_checks=args.quality_checks,
            risks=args.risks,
            final_status=args.final_status,
        )
        print(args.id)
        return 0

    if args.cmd == "status":
        if args.id:
            row = db.get_request(args.id)
            print(f"{row['id']} {row['status']} {row['updated_at']}")
        else:
            for row in db.list_requests():
                print(f"{row['id']} {row['status']} {row['updated_at']}")
        return 0

    if args.cmd == "export-md":
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(db.export_markdown(), encoding="utf-8")
        print(str(out))
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())

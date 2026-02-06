"""Log rotation for market-watch.

Two modes, both intended to be called from cron:

    --daily   Move yesterday's completed logs from logs/ into logs/weekly/,
              preserving the subdirectory structure.  Runs every morning
              (e.g. 5 AM ET) so nothing is moved while files are still live.

    --weekly  Move everything in logs/weekly/ into logs/archive/YYYY-MM/
              keyed on each file's modification date.  Runs Sunday 11:59 PM ET.

What is rotated (date-stamped, completed files only):
    logs/post_market_YYYYMMDD_HHMMSS.log
    logs/<subdir>/agent_events.jsonl.YYYYMMDD_HHMMSS

What is NOT touched:
    Active .jsonl files (trades, equity, sessions, un-suffixed agent_events)
    README files, err.txt, latest_*.* state files
"""

import argparse
import re
import shutil
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

# ── timezone helper (ET without pytz) ────────────────────────────────────────
# US/Eastern offset: EST = -5, EDT = -4.  We only need it to compute "today in ET".

def _is_edt(dt: datetime) -> bool:
    """Approximate US EDT rule: second Sunday of March through first Sunday of Nov."""
    year = dt.year
    # Second Sunday of March
    mar1 = datetime(year, 3, 1)
    edt_start = mar1 + timedelta(days=(6 - mar1.weekday() + 7) % 7 + 7)
    # First Sunday of November
    nov1 = datetime(year, 11, 1)
    est_start = nov1 + timedelta(days=(6 - nov1.weekday()) % 7)
    return edt_start <= dt.replace(tzinfo=None) < est_start


def _today_et() -> date:
    utc_now = datetime.now(timezone.utc)
    offset = timedelta(hours=-4) if _is_edt(utc_now) else timedelta(hours=-5)
    return (utc_now + offset).date()


# ── file-pattern matchers ────────────────────────────────────────────────────
_POST_MARKET_RE = re.compile(r"^post_market_(\d{8})_\d{6}\.log$")
_AGENT_EVENTS_ROTATED_RE = re.compile(r"^agent_events\.jsonl\.(\d{8})_\d{6}$")


def _extract_date(filename: str) -> date | None:
    """Pull the YYYYMMDD date out of a rotatable filename, or None."""
    for pattern in (_POST_MARKET_RE, _AGENT_EVENTS_ROTATED_RE):
        m = pattern.match(filename)
        if m:
            return datetime.strptime(m.group(1), "%Y%m%d").date()
    return None


# ── daily rotation ───────────────────────────────────────────────────────────

def rotate_daily(logs_root: Path):
    """Move completed (older-than-today) date-stamped logs into logs/weekly/."""
    today = _today_et()
    weekly_dir = logs_root / "weekly"
    moved = 0

    for f in logs_root.rglob("*"):
        if not f.is_file():
            continue
        # Skip anything already inside weekly/ or archive/
        try:
            f.relative_to(weekly_dir)
            continue
        except ValueError:
            pass
        try:
            f.relative_to(logs_root / "archive")
            continue
        except ValueError:
            pass

        file_date = _extract_date(f.name)
        if file_date is None or file_date >= today:
            continue  # not a rotatable file, or still today's log

        # Mirror the subdirectory structure under weekly/
        rel = f.relative_to(logs_root)
        dest = weekly_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)

        if dest.exists():
            print(f"  skip (already exists): {rel}")
            continue

        shutil.move(str(f), str(dest))
        print(f"  daily -> weekly: {rel}")
        moved += 1

    print(f"Daily rotation complete: {moved} file(s) moved to weekly/")


# ── weekly archive ───────────────────────────────────────────────────────────

def rotate_weekly(logs_root: Path):
    """Move everything in logs/weekly/ into logs/archive/YYYY-MM/ by mtime."""
    weekly_dir = logs_root / "weekly"
    if not weekly_dir.is_dir():
        print("Nothing in weekly/ — no archive needed.")
        return

    archive_root = logs_root / "archive"
    moved = 0

    for f in weekly_dir.rglob("*"):
        if not f.is_file():
            continue

        # Determine month from the filename date if extractable, else fall back to mtime
        file_date = _extract_date(f.name)
        if file_date is None:
            file_date = datetime.fromtimestamp(f.stat().st_mtime).date()

        month_dir = archive_root / f"{file_date.year}-{file_date.month:02d}"

        # Preserve relative path under weekly/ inside the month bucket
        rel = f.relative_to(weekly_dir)
        dest = month_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)

        if dest.exists():
            print(f"  skip (already exists): {month_dir.name}/{rel}")
            continue

        shutil.move(str(f), str(dest))
        print(f"  weekly -> archive/{month_dir.name}: {rel}")
        moved += 1

    # Clean up empty dirs left behind in weekly/
    for d in sorted(weekly_dir.rglob("*"), reverse=True):
        if d.is_dir() and not any(d.iterdir()):
            d.rmdir()
    if weekly_dir.is_dir() and not any(weekly_dir.iterdir()):
        weekly_dir.rmdir()

    print(f"Weekly archive complete: {moved} file(s) moved to archive/")


# ── entry point ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Rotate market-watch logs")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--daily", action="store_true", help="Move yesterday's logs to weekly/")
    group.add_argument("--weekly", action="store_true", help="Archive weekly/ into archive/YYYY-MM/")
    parser.add_argument("--logs-root", type=Path, default=None,
                        help="Path to logs/ directory (default: auto-detect from script location)")
    args = parser.parse_args()

    if args.logs_root:
        logs_root = args.logs_root.resolve()
    else:
        # Script lives at project/scripts/rotate_logs.py → project/logs/
        logs_root = (Path(__file__).resolve().parent.parent / "logs")

    if not logs_root.is_dir():
        print(f"ERROR: logs directory not found at {logs_root}")
        return

    print(f"Logs root: {logs_root}")
    print(f"Today (ET): {_today_et()}")

    if args.daily:
        rotate_daily(logs_root)
    else:
        rotate_weekly(logs_root)


if __name__ == "__main__":
    main()

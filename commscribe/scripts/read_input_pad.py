#!/usr/bin/env python3
"""Read communicate.md INPUT PAD with retry polling to avoid transient false-empty reads."""

from __future__ import annotations

import argparse
import time
from pathlib import Path

INPUT_START = "<!-- INPUT_PAD_START -->"
INPUT_END = "<!-- INPUT_PAD_END -->"
PLACEHOLDER = "Paste request text here. One request at a time. Include files/paths if relevant."


def parse_input_pad(text: str) -> str:
    a = text.find(INPUT_START)
    b = text.find(INPUT_END)
    if a == -1 or b == -1 or b < a:
        raise ValueError("MISSING_MARKERS")
    return text[a + len(INPUT_START) : b].strip()


def read_with_retries(path: Path, retries: int, delay: float) -> str:
    last = ""
    for i in range(retries + 1):
        content = path.read_text(encoding="utf-8")
        value = parse_input_pad(content)
        last = value
        # Treat anything non-empty and non-placeholder as real input.
        if value and value != PLACEHOLDER:
            return value
        if i < retries:
            time.sleep(delay)
    return last


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", default="commscribe/communicate.md")
    parser.add_argument("--retries", type=int, default=2, help="Additional reads before reporting empty.")
    parser.add_argument("--delay", type=float, default=0.4, help="Delay between retries in seconds.")
    args = parser.parse_args()

    path = Path(args.file)
    try:
        value = read_with_retries(path, retries=max(args.retries, 0), delay=max(args.delay, 0.0))
    except FileNotFoundError:
        print("ERROR: FILE_NOT_FOUND")
        return 1
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 1

    if not value or value == PLACEHOLDER:
        print("EMPTY")
        return 0

    print(value)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

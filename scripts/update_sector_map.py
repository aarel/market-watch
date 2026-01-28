#!/usr/bin/env python3
"""Update the sector map from a market data provider."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import requests

import config
import screener_universe as universe


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Update sector map from a data provider")
    parser.add_argument(
        "--provider",
        default="fmp",
        choices=["fmp"],
        help="Data provider to use (default: fmp)",
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("FMP_API_KEY", ""),
        help="API key for provider (default: FMP_API_KEY env var)",
    )
    parser.add_argument(
        "--fmp-base-url",
        default=os.getenv("FMP_BASE_URL", "https://financialmodelingprep.com/stable"),
        help="FMP base URL (default: https://financialmodelingprep.com/stable)",
    )
    parser.add_argument(
        "--output",
        default=config.SECTOR_MAP_PATH or "data/sector_map.json",
        help="Output JSON path",
    )
    parser.add_argument(
        "--universe",
        default=config.TOP_GAINERS_UNIVERSE,
        help="Universe name (default: TOP_GAINERS_UNIVERSE)",
    )
    parser.add_argument(
        "--symbols",
        default="",
        help="Comma-separated symbols to include",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Re-fetch sectors even if already mapped",
    )
    parser.add_argument(
        "--fill-missing",
        action="store_true",
        help="Fill missing symbols with 'Unknown' when provider has no data",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.2,
        help="Seconds to sleep between requests (default: 0.2)",
    )
    return parser.parse_args()


def fetch_sector_fmp(symbol: str, api_key: str, session: requests.Session, base_url: str) -> str:
    """
    Fetch sector using the latest FMP stable endpoint.

    FMP moved free-tier endpoints from /api/v3 to /stable. The stable profile
    endpoint takes ?symbol=SYMBOL rather than embedding the symbol in the path.
    """
    base = base_url.rstrip("/")
    url = f"{base}/profile?symbol={symbol}&apikey={api_key}"
    response = session.get(url, timeout=10)
    response.raise_for_status()
    data = response.json()
    if isinstance(data, list) and data:
        sector = (data[0].get("sector") or "").strip()
        return sector
    return ""


def load_existing(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception:
        return {}
    if isinstance(data, dict):
        return data
    return {}


def collect_symbols(universe_name: str, extra_symbols: str) -> list[str]:
    symbols = set(s.upper() for s in config.WATCHLIST)
    symbols.update(s.upper() for s in config.MARKET_INDEX_SYMBOLS)
    symbols.update(s.upper() for s in universe.get_universe(universe_name))

    if extra_symbols:
        for raw in extra_symbols.split(","):
            raw = raw.strip()
            if raw:
                symbols.add(raw.upper())

    return sorted(symbols)


def main() -> int:
    args = parse_args()

    if args.provider == "fmp" and not args.api_key:
        print("Missing API key. Set FMP_API_KEY or pass --api-key.")
        return 1

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    current = load_existing(output_path)
    symbols = collect_symbols(args.universe, args.symbols)

    session = requests.Session()
    updated = 0
    skipped = 0

    for symbol in symbols:
        if not args.refresh and symbol in current and current[symbol]:
            skipped += 1
            continue

        try:
            if args.provider == "fmp":
                sector = fetch_sector_fmp(symbol, args.api_key, session, args.fmp_base_url)
            else:
                sector = ""
        except Exception as exc:
            print(f"{symbol}: error fetching sector ({exc})")
            sector = ""

        if sector:
            current[symbol] = sector
            updated += 1
        elif args.fill_missing:
            current[symbol] = current.get(symbol) or "Unknown"
            updated += 1
        else:
            print(f"{symbol}: no sector data")

        if args.sleep:
            time.sleep(args.sleep)

    sorted_data = dict(sorted(current.items(), key=lambda item: item[0]))
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(sorted_data, handle, indent=2)
        handle.write("\n")

    print(f"Updated {output_path} ({updated} updated, {skipped} skipped)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

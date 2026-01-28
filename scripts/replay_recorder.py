"""
Replay Recorder: fetches intraday bars from Alpaca and stores them for SIM replay.

Usage:
    python scripts/replay_recorder.py --symbols AAPL,MSFT,SPY --date 2026-01-25 --timeframe 1Min

Defaults:
    date: today (UTC)
    timeframe: 1Min
    limit: 390 (approx full trading day)
Output:
    data/replay/<symbol>-<YYYYMMDD>.csv
"""
import argparse
import os
from datetime import datetime, timedelta, date

import pandas as pd
import alpaca_trade_api as tradeapi

import config


def fetch_and_save(symbol: str, target_date: date, timeframe: str, limit: int):
    api = tradeapi.REST(
        config.ALPACA_API_KEY,
        config.ALPACA_SECRET_KEY,
        config.get_alpaca_url(),
        api_version="v2",
    )

    # Alpaca wants ISO start/end; fetch that day with a buffer
    start = datetime.combine(target_date, datetime.min.time()) + timedelta(hours=9)
    end = start + timedelta(hours=24)

    bars = api.get_bars(
        symbol,
        timeframe=timeframe,
        start=start.isoformat(),
        end=end.isoformat(),
        limit=limit,
        feed=config.DATA_FEED,
    ).df

    if bars.empty:
        print(f"[warn] No bars for {symbol} on {target_date}")
        return

    bars = bars.reset_index()
    bars = bars.rename(columns={"timestamp": "timestamp"})
    out_dir = "data/replay"
    os.makedirs(out_dir, exist_ok=True)
    fname = os.path.join(out_dir, f"{symbol}-{target_date.strftime('%Y%m%d')}.csv")
    bars[["timestamp", "open", "high", "low", "close", "volume"]].to_csv(fname, index=False)
    print(f"[ok] Saved {symbol} -> {fname} ({len(bars)} rows)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", required=True, help="Comma-separated symbols")
    parser.add_argument("--date", help="YYYY-MM-DD (default: today UTC)")
    parser.add_argument("--timeframe", default="1Min", help="Alpaca timeframe (e.g., 1Min)")
    parser.add_argument("--limit", type=int, default=390, help="Max bars to fetch")
    args = parser.parse_args()

    tgt_date = datetime.strptime(args.date, "%Y-%m-%d").date() if args.date else datetime.utcnow().date()
    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]

    for sym in symbols:
        fetch_and_save(sym, tgt_date, args.timeframe, args.limit)


if __name__ == "__main__":
    main()

# Risk Controls

This document describes how Market-Watch enforces risk constraints and how to configure them.

## Overview

Risk checks run inside the `RiskAgent` before any order is submitted. A signal is allowed only if all checks pass.

High-level flow:

1. Daily trade limit check
2. Circuit breaker check (daily loss + max drawdown)
3. Max open positions
4. Sector exposure
5. Correlation exposure
6. Position sizing + minimum trade value

If any check fails, the trade is rejected with a reason.

## Position Sizing

The position sizer converts signal strength into a trade value, bounded by:

- `MAX_POSITION_PCT` (percent of portfolio)
- `buying_power`
- `POSITION_SIZER_MIN_STRENGTH` / `POSITION_SIZER_MAX_STRENGTH`

Defaults are conservative. Increase `MAX_POSITION_PCT` only after validating strategy risk.

## Circuit Breaker

The circuit breaker halts new buys when:

- **Daily loss limit** (`DAILY_LOSS_LIMIT_PCT`) is breached
- **Max drawdown** (`MAX_DRAWDOWN_PCT`) is exceeded

This protection is portfolio-wide and resets at the next market day.

## Sector Exposure

Sector exposure prevents concentration in a single sector.

Configuration:

- `MAX_SECTOR_EXPOSURE_PCT` (fraction of portfolio)
- `SECTOR_MAP_PATH` or `SECTOR_MAP_JSON`

The default sector map lives in `data/sector_map.json`. It is a starter list that covers common large-cap symbols and ETFs. Extend it to cover your watchlist. You can also provide the map directly as a JSON string via the `SECTOR_MAP_JSON` environment variable, which takes precedence over the file path.

To refresh sectors automatically, use:

```bash
FMP_API_KEY=your_key_here venv/bin/python scripts/update_sector_map.py
```

This pulls sectors from Financial Modeling Prep. Use `--refresh` to re-fetch all entries and `--fill-missing` to set `Unknown` when the provider has no data.

Example:

```json
{
  "AAPL": "Technology",
  "MSFT": "Technology",
  "JPM": "Financials"
}
```

If a symbol is missing from the map, the sector check is skipped for that symbol.

## Correlation Exposure

Correlation exposure prevents stacking highly correlated positions.

Configuration:

- `CORRELATION_THRESHOLD` (default 0.8)
- `CORRELATION_LOOKBACK_DAYS` (default 30)
- `MAX_CORRELATED_EXPOSURE_PCT` (default 0.40)

The system computes daily returns for the candidate symbol and compares them to existing positions. If correlation >= threshold, that position counts toward the correlated exposure cap.

If insufficient price history is available, the correlation check is skipped.

## Configuration & Persistence

- **Initial Defaults**: On first run, all risk parameters are loaded from your `.env` file (via `config.py`).
- **Live Updates**: You can adjust all risk knobs live in the web UI's "Configuration" card. Changes are applied immediately to the running bot.
- **Persistence**: These runtime changes are automatically saved to `data/config_state.json` (this path can be overridden with the `CONFIG_STATE_PATH` env var). On subsequent startups, the bot will load this file, overriding any values in your `.env` file.
- **Reverting to Defaults**: To revert all settings back to their original `.env` values, you must delete the `data/config_state.json` file and restart the bot. The recommended way to do this is via the `POST /api/config/reset` endpoint, which can be triggered from the UI.

## Recommended Defaults

Conservative starting points:

- `MAX_POSITION_PCT`: 0.10 to 0.25
- `MAX_SECTOR_EXPOSURE_PCT`: 0.30
- `MAX_CORRELATED_EXPOSURE_PCT`: 0.40
- `DAILY_LOSS_LIMIT_PCT`: 0.03
- `MAX_DRAWDOWN_PCT`: 0.10 to 0.20

Adjust only after backtesting and paper trading.

## Operational Notes

- **Sector map coverage matters**: if you trade a broader universe, expand `data/sector_map.json`.
- **Correlation uses daily bars**: ensure the broker can return enough history for your symbols.
- **Skipped checks**: if data is missing, sector/correlation checks do not block trades. For stricter behavior, ensure complete maps and data coverage.

## Quick Setup Checklist

1. Set `SECTOR_MAP_PATH=data/sector_map.json`
2. Add your core watchlist symbols to the map
3. Keep defaults while validating strategy performance
4. Tighten limits only after confirming stable returns

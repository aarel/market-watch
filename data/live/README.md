# Live Universe Data

This directory contains data for the LIVE universe (real capital trading).

**CRITICAL:** This universe involves real money and irreversible transactions.

## Files

- `config.json` - Live-only runtime configuration
- `positions.json` - Current live positions
- `equity.jsonl` - Live equity curve (time series)

## Safety

- Never manually edit files in this directory
- All writes are audited with session_id and timestamps
- Backups recommended before live trading

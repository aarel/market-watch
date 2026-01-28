# Shared Data (Universe-Agnostic)

This directory contains data that is truly universe-agnostic.

## Files

- `historical/` - Cached historical market data (OHLCV bars)
- `sector_map.json` - Sector classifications for symbols
- `replay/` - Recorded market data for simulation replay

## Warning

Only add data here if it's explicitly safe to share across universes.
Most data should be universe-scoped.

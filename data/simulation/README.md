# Simulation Universe Data

This directory contains data for the SIMULATION universe (synthetic environment).

Uses FakeBroker with replayed or generated data, can run 24/7.

## Files

- `config.json` - Simulation-only runtime configuration
- `positions.json` - Current simulation positions
- `equity.jsonl` - Simulation equity curve (time series)

## Notes

- Results marked as SIM_VALID_FOR_TRAINING or SIM_INVALID_FOR_TRAINING
- Can override market hours
- Safe for experimentation

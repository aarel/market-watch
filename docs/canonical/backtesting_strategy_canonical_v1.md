# Backtesting Strategy Canonical v1

## Scope
Defines strategy behavior and backtesting workflow authority for simulation analysis.

## Invariants
- Strategy semantics and backtest procedure must reference the same assumptions.
- Automation scripts must not redefine strategy/backtest core semantics.

## Implementation Linkage
- `backtest/*` modules
- strategy modules referenced in docs
- `scripts/post_market_backtest.py`

## Test Linkage
- UNKNOWN

## Source Lineage
- Primary: `docs/BACKTEST.md`
- Supporting: `docs/STRATEGIES.md`, `scripts/README.md`

## Conflict Notes
- Strategy and backtest docs split behavior authority; this file establishes precedence on workflow/assumption authority.

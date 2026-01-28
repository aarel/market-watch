# Configuration Alignment - January 25, 2026

## Summary of Changes

This document tracks the configuration alignment work completed to fix SIMULATION_MODE and resolve config mismatches between `.env`, `config_state.json`, and `config.py`.

---

## Problem Statement

1. **SIMULATION_MODE was not working as expected**
   - User believed it would auto-enable after market hours for training
   - Actually: Manual on/off switch only, no scheduling
   - Missing from runtime config persistence (not in config_state.json)

2. **Massive config value mismatches**
   - `.env` had "HIGH RISK" settings (100% position sizes, 20 trades/day)
   - `config_state.json` had conservative settings (0.15% positions, 5 trades/day)
   - Runtime was using config_state.json, making .env comments misleading

3. **Analytics not displaying**
   - Market closed (weekend), SIMULATION_MODE=false
   - No data flowing, can't test analytics UI
   - Need SIM mode to generate test data

---

## Changes Made

### 1. Enabled SIMULATION_MODE

**File: `.env`**
```diff
- SIMULATION_MODE=false
+ SIMULATION_MODE=true
```

**File: `data/config_state.json`**
```diff
  "auto_trade": true,
+ "simulation_mode": true,
  "top_gainers_count": 20,
```

### 2. Added SIMULATION_MODE to Runtime Config Persistence

**File: `server.py`**

Added `"simulation_mode"` to:
- `PERSISTED_CONFIG_KEYS` set (line ~291)
- `_config_snapshot()` function (line ~314)
- `load_config_state()` handler (line ~370)

**Result:** SIMULATION_MODE now persists across restarts and can be toggled via UI config API.

### 3. Aligned Configuration Values

**File: `.env`** - Updated to match actual running values:
```diff
- MAX_POSITION_PCT=1.0  # HIGH RISK: 100% of portfolio in single position
+ MAX_POSITION_PCT=0.0015  # 0.15% of portfolio per position

- MAX_DAILY_TRADES=20   # HIGH RISK: Many trades per day
+ MAX_DAILY_TRADES=5       # Maximum 5 trades per day

+ MAX_OPEN_POSITIONS=50    # Maximum concurrent positions (was missing)

- STOP_LOSS_PCT=0.10    # HIGH RISK: 10% stop loss (bigger swings)
+ STOP_LOSS_PCT=0.0005     # 0.05% stop loss

- MOMENTUM_THRESHOLD=0.01  # HIGH RISK: 1% threshold (more trades)
+ MOMENTUM_THRESHOLD=0.0003  # 0.03% momentum threshold

- SELL_THRESHOLD=-0.02  # HIGH RISK: Hold through -2% dips
+ SELL_THRESHOLD=-0.00015    # -0.015% sell threshold
```

**Removed misleading "HIGH RISK" comments** - these values weren't actually active.

### 4. Improved Documentation

**File: `.env.example`**

Enhanced SIMULATION_MODE documentation:
```env
# Simulation mode: "true" or "false"
# When true: Uses FakeBroker with synthetic market data. Market is always "open".
#   - Useful for testing strategies after market hours or on weekends
#   - Generates realistic price movements for training/development
#   - No real API calls to Alpaca for market data
# When false: Uses real Alpaca API for market data (respects market hours)
SIMULATION_MODE=false
```

Added note about runtime config:
```env
# NOTE: Runtime config in data/config_state.json will override these .env defaults
# after the first run. Changes via UI are persisted to config_state.json.
```

---

## What SIMULATION_MODE Actually Does

### When SIMULATION_MODE=true:
- ✅ Uses `FakeBroker` instead of `AlpacaBroker`
- ✅ Generates synthetic market data with realistic price movements
- ✅ Market is **always open** (no market hours restrictions)
- ✅ No API calls to Alpaca for market data
- ✅ Perfect for testing/training after hours or weekends
- ✅ Can test analytics, strategies, risk controls without burning API quota

### When SIMULATION_MODE=false:
- ✅ Uses real Alpaca API
- ✅ Respects actual market hours
- ✅ Real market data (subject to market open/close)
- ✅ Uses paper trading or live trading based on TRADING_MODE

---

## Configuration Priority

**Load order:**
1. `.env` file is read on startup (via `load_dotenv()`)
2. `config.py` reads from environment variables
3. `load_config_state()` reads `data/config_state.json` and **overrides** config.py values
4. UI changes update config.py in-memory
5. `/api/config` POST saves to `config_state.json` via `save_config_state()`

**Result:** `config_state.json` is the "source of truth" after first run.

---

## Next Steps

### Immediate (Completed)
- [x] Enable SIMULATION_MODE in .env
- [x] Add simulation_mode to runtime config persistence
- [x] Align .env and config_state.json values
- [x] Document SIMULATION_MODE behavior

### Testing (Next)
- [ ] Restart server with SIMULATION_MODE=true
- [ ] Verify FakeBroker generates data
- [ ] Check if analytics metrics populate
- [ ] Confirm position concentration chart renders

### Future Enhancements
- [ ] Add auto-scheduling for SIMULATION_MODE
  - Example: `SIM_MODE_AUTO_ENABLE_AFTER_CLOSE_MINUTES=30`
  - Automatically switch to SIM mode 30 min after market close
  - Switch back to real mode when market opens
- [ ] Add UI toggle for SIMULATION_MODE in config panel
- [ ] Add visual indicator in UI when in SIM mode

---

## Files Modified

1. `.env` - Enabled SIM mode, aligned values, added MAX_OPEN_POSITIONS
2. `.env.example` - Improved SIMULATION_MODE docs, added runtime config note
3. `server.py` - Added simulation_mode to persistence (3 locations)
4. `data/config_state.json` - Added simulation_mode: true
5. `CONFIG_ALIGNMENT_NOTES.md` - This document

---

## Testing Checklist

After server restart with these changes:

- [ ] Server starts without errors
- [ ] `config.SIMULATION_MODE` is `True`
- [ ] FakeBroker is active (check logs for "Simulated" messages)
- [ ] Market shows as "open" even on weekends
- [ ] Analytics equity snapshots are recorded
- [ ] Analytics metrics display in UI (return, drawdown, Sharpe)
- [ ] Position concentration chart renders
- [ ] Config changes via UI persist to config_state.json
- [ ] simulation_mode persists after restart

---

*Generated: 2026-01-25*

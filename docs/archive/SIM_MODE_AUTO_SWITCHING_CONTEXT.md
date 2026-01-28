# SIM Mode Auto-Switching Feature - Context Document

**Date:** 2026-01-25
**Session:** Configuration alignment and SIM mode investigation
**Status:** Feature gap identified - auto-switching NOT implemented

---

## CRITICAL UNDERSTANDING

### The Original Vision (What User Expected)

**SIM MODE should automatically switch based on real market hours:**

1. **During Market Hours (9:30am - 4:30pm ET, Mon-Fri):**
   - ✅ Use real Alpaca API (SIMULATION_MODE=false)
   - 🟢 MARKET OPEN badge (green)
   - 🔴 SIM OFF badge (red)
   - Get real market data for live/paper trading

2. **After Market Close (after 4:30pm ET or weekends):**
   - Wait 30 minutes for market to "cool down"
   - ✅ **Automatically enable SIM MODE** (SIMULATION_MODE=true)
   - 🔴 MARKET CLOSED badge (red)
   - 🟢 SIM ON badge (green)
   - FakeBroker generates synthetic data → analytics continue working

3. **Purpose:**
   - Train the bot 24/7 even when market is closed
   - Generate analytics data during off-hours
   - Test strategies on weekends
   - Seamless transition between real and simulated trading

### What Was Actually Built (Current State)

**SIM MODE is a MANUAL toggle only:**

- ❌ No automatic switching based on time
- ❌ No market hours detection
- ❌ No scheduled transition logic
- ✅ Can manually set SIMULATION_MODE=true/false in .env
- ✅ Persists to config_state.json
- ✅ FakeBroker works when enabled
- ✅ Badge displays work (after cache refresh)

**Current behavior on Sunday 10am:**
- Market is closed
- SIM mode is manually ON (because we set it in .env)
- Should generate data, but auto-switching doesn't exist

---

## Technical Requirements for Auto-Switching

### 1. Market Hours Detection

```python
import pytz
from datetime import datetime, time

def is_market_open_now() -> bool:
    """
    Check if US stock market is currently open.

    Market hours: 9:30am - 4:30pm ET, Monday-Friday
    Excludes market holidays (NYSE calendar)
    """
    et_tz = pytz.timezone('America/New_York')
    now_et = datetime.now(et_tz)

    # Check if weekend
    if now_et.weekday() >= 5:  # 5=Saturday, 6=Sunday
        return False

    # Check if within trading hours
    market_open = time(9, 30)
    market_close = time(16, 30)
    current_time = now_et.time()

    if current_time < market_open or current_time >= market_close:
        return False

    # TODO: Check market holidays (NYSE calendar)
    return True
```

### 2. Auto-Switch Background Task

```python
import asyncio

class MarketHoursMonitor:
    """Background task to auto-switch SIM mode based on market hours."""

    def __init__(self, cooldown_minutes=30):
        self.cooldown_minutes = cooldown_minutes
        self.market_close_time = None
        self.sim_mode_active = False

    async def monitor_loop(self):
        """Run every minute to check market status."""
        while True:
            await asyncio.sleep(60)  # Check every minute

            market_open = is_market_open_now()

            if not market_open:
                # Market is closed
                if self.market_close_time is None:
                    self.market_close_time = datetime.now()

                # Check if cooldown period has passed
                minutes_since_close = (datetime.now() - self.market_close_time).total_minutes()

                if minutes_since_close >= self.cooldown_minutes and not self.sim_mode_active:
                    # Enable SIM mode
                    await self.enable_sim_mode()
                    self.sim_mode_active = True
                    print(f"[AUTO-SWITCH] SIM mode enabled (market closed {minutes_since_close:.0f} min ago)")

            else:
                # Market is open
                self.market_close_time = None

                if self.sim_mode_active:
                    # Disable SIM mode
                    await self.disable_sim_mode()
                    self.sim_mode_active = False
                    print("[AUTO-SWITCH] SIM mode disabled (market opened)")

    async def enable_sim_mode(self):
        """Switch to simulation mode."""
        # Problem: Broker is instantiated at startup
        # Can't easily swap AlpacaBroker <-> FakeBroker at runtime
        # Options:
        #   1. Restart server (not ideal)
        #   2. Make broker switchable (requires refactor)
        #   3. Always use FakeBroker for data when market closed
        pass

    async def disable_sim_mode(self):
        """Switch to real broker mode."""
        pass
```

### 3. Major Challenge: Runtime Broker Switching

**Current architecture:**
```python
# server.py line 30
if config.SIMULATION_MODE:
    Broker = FakeBroker
else:
    Broker = AlpacaBroker

# line 421
state.broker = Broker()  # Instantiated ONCE at startup
```

**Problem:** Broker is chosen at startup and can't be swapped without restart.

**Solution options:**

**Option A: Restart Server (hacky)**
- Detect market hours change
- Update config.SIMULATION_MODE
- Restart the server process
- ❌ Disrupts running agents, loses in-memory state

**Option B: Broker Wrapper (better)**
```python
class AutoSwitchingBroker:
    """Wrapper that delegates to real or fake broker based on market hours."""

    def __init__(self):
        self.real_broker = AlpacaBroker()
        self.fake_broker = FakeBroker()
        self.use_simulation = False

    def get_current_broker(self):
        market_open = is_market_open_now()

        if not market_open:
            # Market closed, use simulation after cooldown
            if self._cooldown_passed():
                self.use_simulation = True
        else:
            # Market open, use real broker
            self.use_simulation = False

        return self.fake_broker if self.use_simulation else self.real_broker

    def get_account(self):
        return self.get_current_broker().get_account()

    def get_positions(self):
        return self.get_current_broker().get_positions()

    # ... delegate all methods
```

**Option C: Always-On Hybrid (simplest for now)**
```python
# Use real broker for trading during market hours
# But FakeBroker can ALWAYS run in background generating data
# Analytics pulls from whichever is active
```

---

## What Was Done This Session

### Files Modified

1. **`.env`**
   - Set `SIMULATION_MODE=true` (manual toggle)
   - Aligned config values with config_state.json

2. **`server.py`**
   - Added `simulation_mode` to PERSISTED_CONFIG_KEYS
   - Added to `_config_snapshot()` function
   - Added to `load_config_state()` handler

3. **`data/config_state.json`**
   - Added `"simulation_mode": true`

4. **`static/index.html`**
   - Updated badge logic: ON=GREEN, OFF=RED, PAPER=YELLOW
   - Fixed position concentration chart (white text)
   - Market/SIM/Auto-trade badges now color-coded correctly

5. **`.env.example`**
   - Documented SIMULATION_MODE behavior
   - Added note about runtime config override

6. **`CONFIG_ALIGNMENT_NOTES.md`** (created)
   - Full documentation of config changes

7. **`test_analytics_api.py`** (created)
   - Diagnostic script to test analytics endpoints

### Issues Identified

1. ❌ **Auto-switching NOT implemented** - this is the main gap
2. ❌ **Analytics metrics showing "--"** - may be data format or calculation issue
3. ❌ **Position concentration chart blank** - may be Chart.js rendering issue
4. ⚠️ **Browser cache** - UI changes require hard refresh (Ctrl+Shift+R)

---

## Next Steps

### Immediate (Manual Workaround)

For now, SIM mode works as a manual toggle:

1. **When market is closed (nights/weekends):**
   ```bash
   # In .env
   SIMULATION_MODE=true

   # Restart server
   python server.py
   ```

2. **When market opens (9:30am ET Mon-Fri):**
   ```bash
   # In .env
   SIMULATION_MODE=false

   # Restart server
   python server.py
   ```

### Phase 11+ Feature: Auto-Switching SIM Mode

**Add to ROADMAP.md under "Phase 11: Testing & Reliability" or create new phase:**

#### Requirements

1. **Market Hours Detection**
   - Implement `is_market_open_now()` function
   - Use pytz for ET timezone handling
   - Integrate NYSE holiday calendar (pandas_market_calendars)
   - Handle early closes (e.g., day after Thanksgiving)

2. **Background Monitor Task**
   - Run every 1-5 minutes
   - Track market state transitions
   - Implement 30-minute cooldown after close
   - Log state changes

3. **Runtime Broker Switching**
   - **Option A:** Restart server on transition (simple but disruptive)
   - **Option B:** Broker wrapper pattern (clean but requires refactor)
   - **Option C:** Hybrid mode (both brokers run, switch data source)

4. **UI Indicators**
   - Show countdown to SIM mode activation after close
   - Display next market open/close time
   - Auto-update badges without page refresh

5. **Configuration**
   ```env
   # New .env variables needed
   SIM_AUTO_SWITCH_ENABLED=true
   SIM_COOLDOWN_MINUTES=30
   SIM_FORCE_MODE=false  # Override auto-switching
   ```

6. **Testing**
   - Unit tests for market hours detection
   - Integration tests for broker switching
   - Manual testing during market transitions

#### Dependencies

```txt
pytz>=2023.3
pandas-market-calendars>=4.3.0  # For NYSE holiday calendar
```

#### Estimated Complexity

- **Small:** Market hours detection (2-3 hours)
- **Medium:** Background monitor task (4-6 hours)
- **Large:** Runtime broker switching (8-12 hours with testing)
- **Total:** 2-3 days of development

---

## Analytics Issues (Separate from SIM Switching)

**Problem:** Analytics metric cards show "--" even with data in equity.jsonl

**To debug:**
```bash
# Start server
python server.py

# In another terminal
python test_analytics_api.py
```

**Check:**
1. Is `/api/analytics/summary` returning data?
2. Is `compute_equity_metrics()` calculating correctly?
3. Is UI JavaScript parsing the response?
4. Are there enough data points (need 2+ for metrics)?

**Related files:**
- `analytics/metrics.py` - Calculation logic
- `analytics/store.py` - Data loading
- `server.py` - API endpoints (lines 806-910)
- `static/index.html` - UI rendering (lines 2440-2475)

---

## Color Coding Reference (Current Implementation)

| Badge | ON State | OFF State | Special |
|-------|----------|-----------|---------|
| **MARKET** | 🟢 MARKET OPEN | 🔴 MARKET CLOSED | Based on real time |
| **SIM** | 🟢 SIM ON | 🔴 SIM OFF | Manual toggle |
| **PAPER** | 🟡 PAPER | 🟡 LIVE | Trading mode |
| **AUTO-TRADE** | 🟢 AUTO-TRADE ON | 🔴 AUTO-TRADE OFF | Bot state |

**Rule:** ON = GREEN, OFF = RED, PAPER = YELLOW

---

## Key Takeaways

1. **SIM mode works** - just not automatically
2. **Auto-switching is a new feature** - not in current codebase
3. **Requires architectural changes** - broker selection at runtime
4. **Not trivial** - 2-3 days of dev work
5. **Valuable feature** - enables 24/7 bot training and analytics

---

## Questions for Next Session

1. **Priority:** Should auto-switching be Phase 11 or later?
2. **Approach:** Which broker switching option (A/B/C)?
3. **Analytics:** Fix metrics display first or build auto-switching?
4. **Testing:** Integration tests before or after auto-switching?
5. **Scope:** Full auto-switching or just manual SIM mode for now?

---

*Generated: 2026-01-25 by Claude Code*
*Review ROADMAP.md for project status and phase definitions*

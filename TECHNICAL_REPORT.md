# Market-Watch Trading Bot - Comprehensive Technical Report

**Report Date:** January 25, 2026
**Report Type:** Complete Codebase Analysis & Technical Review
**Audience:** Developers, Engineers, Technical Decision Makers
**Status:** Living Document

---

## Executive Summary

Market-Watch is an autonomous trading bot implementing agent-based architecture for algorithmic trading via Alpaca brokerage. The system supports paper and live trading with four built-in strategies, comprehensive backtesting, risk management, and analytics.

**Current State:**
- **Lines of Code:** ~8,500 (excluding tests and docs)
- **Test Coverage:** 174 unit tests, 100% pass rate
- **Architecture Maturity:** Phase 11 (Testing & CI/CD) - Production-ready core, feature gaps in analytics UI
- **Code Quality:** Good foundations, some technical debt, well-tested

**Key Strengths:**
- Clean agent-based architecture with event bus
- Comprehensive test suite
- Pluggable strategy framework
- Professional risk management
- Strong backtesting capabilities

**Critical Issues:**
- Analytics UI broken (metrics show "--", charts not rendering)
- Configuration split between .env and config_state.json (confusing)
- No auto-switching SIM mode (manual only)
- Broker instantiated at startup (can't swap at runtime)
- Documentation scattered across multiple locations

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [File Organization Analysis](#2-file-organization-analysis)
3. [Code Review by Module](#3-code-review-by-module)
4. [Configuration Management](#4-configuration-management)
5. [Testing Infrastructure](#5-testing-infrastructure)
6. [Dependencies](#6-dependencies)
7. [Technical Debt](#7-technical-debt)
8. [Security Considerations](#8-security-considerations)
9. [Performance Analysis](#9-performance-analysis)
10. [Documentation Review](#10-documentation-review)
11. [Deployment & Operations](#11-deployment--operations)
12. [Recommendations](#12-recommendations)

---

## 1. Architecture Overview

### 1.1 System Architecture

**Pattern:** Event-Driven Agent-Based System

```
┌─────────────────────────────────────────────────────────────┐
│                         server.py                            │
│                    (FastAPI Application)                      │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                    Coordinator                          │ │
│  │  ┌──────────────────────────────────────────────────┐  │ │
│  │  │              Event Bus                            │  │ │
│  │  │  (Pub/Sub Communication Channel)                  │  │ │
│  │  └──────────────────────────────────────────────────┘  │ │
│  │                                                          │ │
│  │  ┌─────────┐  ┌──────────┐  ┌─────────┐  ┌──────────┐ │ │
│  │  │  Data   │  │  Signal  │  │  Risk   │  │Execution │ │ │
│  │  │  Agent  │  │  Agent   │  │  Agent  │  │  Agent   │ │ │
│  │  └─────────┘  └──────────┘  └─────────┘  └──────────┘ │ │
│  │  ┌─────────┐  ┌──────────┐  ┌─────────┐  ┌──────────┐ │ │
│  │  │Monitor  │  │  Alert   │  │Analytics│  │Observ-   │ │ │
│  │  │ Agent   │  │  Agent   │  │  Agent  │  │ ability  │ │ │
│  │  └─────────┘  └──────────┘  └─────────┘  └──────────┘ │ │
│  └──────────────────────────────────────────────────────────┘│
│                                                               │
│  ┌──────────────────┐         ┌──────────────────┐          │
│  │  Broker Layer    │         │  Strategy Layer  │          │
│  │  ┌────────────┐  │         │  ┌────────────┐  │          │
│  │  │ AlpacaBroker│ │         │  │ Momentum   │  │          │
│  │  │ FakeBroker │  │         │  │ Mean Rev   │  │          │
│  │  └────────────┘  │         │  │ Breakout   │  │          │
│  └──────────────────┘         │  │ RSI        │  │          │
│                                │  └────────────┘  │          │
│                                └──────────────────┘          │
└───────────────────────────────────────────────────────────────┘
         │                                        │
         ▼                                        ▼
   Alpaca API                                WebSocket
  (Market Data                              (Browser UI)
   + Trading)
```

### 1.2 Core Components

#### 1.2.1 Entry Point: `server.py`

**Purpose:** FastAPI application, main entry point, WebSocket server

**Key Responsibilities:**
- Application lifecycle management (lifespan context manager)
- REST API endpoints (status, config, analytics, health)
- WebSocket broadcast to UI
- Agent coordinator initialization
- Configuration persistence

**Critical Code Flow:**
```python
# Startup sequence (line 416-458)
1. load_config_state() - Load runtime config from JSON
2. state.broker = Broker() - Instantiate broker (Alpaca or Fake based on SIMULATION_MODE)
3. state.analytics_store = AnalyticsStore() - Initialize analytics persistence
4. state.coordinator = Coordinator() - Create agent coordinator
5. coordinator.set_broadcast_callback(broadcast) - Wire WebSocket
6. Event subscriptions for MarketDataReady and SignalsUpdated
7. await coordinator.start() - Start all agents
8. Optional: observability evaluation loop
```

**Architecture Decision:** Broker choice happens at startup (lines 30-33):
```python
if config.SIMULATION_MODE:
    Broker = FakeBroker
else:
    Broker = AlpacaBroker
```
**⚠️ Limitation:** Cannot switch brokers without restarting server.

#### 1.2.2 Agent Coordinator: `agents/coordinator.py`

**Purpose:** Orchestrate all agents, manage event bus

**Agents Managed:**
1. **DataAgent** - Fetches market data every N minutes
2. **SignalAgent** - Generates buy/sell signals using strategy
3. **RiskAgent** - Validates signals against risk limits
4. **ExecutionAgent** - Places orders via broker
5. **MonitorAgent** - Tracks positions, triggers stop-loss
6. **AlertAgent** - Broadcasts events to UI
7. **ObservabilityAgent** - Logs events to JSONL (optional)
8. **AnalyticsAgent** - Records equity snapshots + trades (optional)

**Communication Pattern:**
```python
# Example event flow for a trade
DataAgent → MarketDataReady event
  ↓
SignalAgent → SignalGenerated event
  ↓
RiskAgent → RiskCheckPassed / RiskCheckFailed event
  ↓
ExecutionAgent → OrderExecuted / OrderFailed event
  ↓
MonitorAgent → (monitors position)
AnalyticsAgent → (records trade)
AlertAgent → (broadcasts to UI)
```

**Event Bus Pattern:** Pub/Sub (observers subscribe to specific event types)

**Location:** `agents/event_bus.py`
```python
class EventBus:
    def subscribe(self, event_type: Type[Event], callback: Callable):
        """Register callback for event type"""

    async def publish(self, event: Event):
        """Call all subscribers for this event type"""
```

---

## 2. File Organization Analysis

### 2.1 Current Structure

```
market-watch/
├── Root Level (48 files) ⚠️ TOO CLUTTERED
│   ├── server.py                    # Main entry point ✅
│   ├── broker.py                    # Alpaca integration ✅
│   ├── fake_broker.py               # Simulation broker ✅
│   ├── config.py                    # Configuration ✅
│   ├── screener.py                  # Top gainers logic ✅
│   ├── universe.py                  # Stock lists ✅
│   ├── test_analytics_api.py        # Diagnostic tool ⚠️ Should be in scripts/
│   ├── .env                         # Secrets ✅
│   ├── .env.example                 # Template ✅
│   ├── requirements.txt             # Dependencies ✅
│   ├── README.md                    # User docs ✅
│   ├── ROADMAP.md                   # Development plan ✅
│   ├── CONFIG_ALIGNMENT_NOTES.md    # Session notes ⚠️ Should be in docs/
│   ├── SIM_MODE_AUTO_SWITCHING_CONTEXT.md ⚠️ Should be in docs/
│   ├── DOCUMENTATION_UPDATE_SUMMARY.md ⚠️ Should be in docs/
│   ├── codex-project_review-1.md    ❌ REMOVE (old AI review)
│   ├── codex-project_review-2.md    ❌ REMOVE (old AI review)
│   ├── gemini-project_review-1.md   ❌ REMOVE (old AI review)
│   ├── gemini-project_review-2.md   ❌ REMOVE (old AI review)
│   ├── merged_review.md             ❌ REMOVE (old AI review)
│   ├── err.txt                      ❌ REMOVE (test output)
│   └── test_err.txt                 ❌ REMOVE (test output)
│
├── agents/                          # Agent system ✅ WELL ORGANIZED
│   ├── __init__.py
│   ├── base.py                      # BaseAgent class
│   ├── coordinator.py               # Orchestrator
│   ├── event_bus.py                 # Pub/sub system
│   ├── events.py                    # Event classes
│   ├── data_agent.py
│   ├── signal_agent.py
│   ├── risk_agent.py
│   ├── execution_agent.py
│   ├── monitor_agent.py
│   ├── alert_agent.py
│   ├── observability_agent.py
│   └── analytics_agent.py
│
├── strategies/                      # Trading strategies ✅ WELL ORGANIZED
│   ├── __init__.py
│   ├── base.py                      # Strategy ABC
│   ├── momentum.py
│   ├── mean_reversion.py
│   ├── breakout.py
│   └── rsi.py
│
├── backtest/                        # Backtesting engine ✅ WELL ORGANIZED
│   ├── __init__.py
│   ├── __main__.py                  # CLI entry point
│   ├── cli.py                       # Command parsing
│   ├── data.py                      # Historical data
│   ├── engine.py                    # Simulation
│   ├── metrics.py                   # Performance calc
│   └── results.py                   # Results export
│
├── analytics/                       # Analytics system ✅ CLEAN
│   ├── metrics.py                   # Calculations
│   └── store.py                     # JSONL persistence
│
├── risk/                            # Risk management ✅ CLEAN
│   ├── __init__.py
│   ├── circuit_breaker.py
│   └── position_sizer.py
│
├── monitoring/                      # Observability ✅ WELL ORGANIZED
│   ├── __init__.py
│   ├── __main__.py                  # CLI entry point
│   ├── evaluator.py                 # Log analyzer
│   ├── expectations.py              # Validation rules
│   ├── logger.py
│   ├── models.py
│   ├── reason_codes.py
│   ├── report.py
│   └── context.py
│
├── scripts/                         # Utility scripts ✅ APPROPRIATE
│   ├── fix_tests.py
│   ├── post_market_backtest.py
│   └── update_sector_map.py
│
├── tests/                           # Unit tests ✅ COMPREHENSIVE
│   ├── test_analytics_metrics.py
│   ├── test_analytics_store.py
│   ├── test_backtest_*.py (4 files)
│   ├── test_circuit_breaker.py
│   ├── test_config_persistence.py
│   ├── test_data_agent_indices.py
│   ├── test_health_endpoint.py
│   ├── test_observability_endpoints.py
│   ├── test_position_sizer.py
│   ├── test_risk_agent_*.py (3 files)
│   ├── test_risk_breaker_endpoint.py
│   ├── test_screener.py
│   ├── test_security.py
│   ├── test_signals_updated.py
│   ├── test_strategy_*.py (4 files)
│   └── test_trade_interval.py
│
├── data/                            # Runtime data ✅ CORRECT
│   ├── analytics/                   # Equity + trade logs (JSONL)
│   ├── historical/                  # Backtest data (CSV)
│   ├── config_state.json            # Runtime config
│   └── sector_map.json              # Sector classifications
│
├── logs/                            # Application logs ✅ CORRECT
│   └── observability/
│       ├── agent_events.jsonl
│       ├── latest_eval.json
│       └── latest_report.txt
│
├── static/                          # Web UI ✅ SIMPLE
│   └── index.html                   # Single-file dashboard (160KB!)
│
├── docs/                            # Documentation ⚠️ INCOMPLETE
│   ├── ARCHITECTURE.md              # ✅ Exists
│   ├── RISK.md                      # ✅ Exists
│   ├── STRATEGIES.md                # ✅ Exists
│   ├── TESTS_FIXED_SUMMARY.md       # ✅ Exists
│   └── archive/
│       └── CLAUDE.md                # Old AI instructions
│
├── test_results/                    # Test outputs ✅ AUTO-GENERATED
│   └── test_run_*.log
│
├── img/                             # Screenshots ⚠️ MIXED PURPOSE
│   ├── analy_rep_pos_conc.png
│   └── header_SIM_mark_status_analy_cards_pos_conc_data.png
│
└── .claude/                         # Claude Code metadata ✅ IGNORE
```

### 2.2 File Organization Issues

#### Critical Problems

**1. Root Directory Clutter (13 unnecessary files)**

Files to **REMOVE** (old/obsolete):
- `codex-project_review-1.md` - Old Codex AI review
- `codex-project_review-2.md` - Old Codex AI review
- `gemini-project_review-1.md` - Old Gemini AI review
- `gemini-project_review-2.md` - Old Gemini AI review
- `merged_review.md` - Merged AI reviews
- `err.txt` - Test error output
- `test_err.txt` - Test error output

Files to **MOVE to docs/**:
- `CONFIG_ALIGNMENT_NOTES.md` → `docs/CONFIG_ALIGNMENT_NOTES.md`
- `SIM_MODE_AUTO_SWITCHING_CONTEXT.md` → `docs/SIM_MODE_AUTO_SWITCHING.md`
- `DOCUMENTATION_UPDATE_SUMMARY.md` → `docs/DOCUMENTATION_UPDATE_SUMMARY.md`

Files to **MOVE to scripts/**:
- `test_analytics_api.py` → `scripts/test_analytics_api.py`

**After cleanup, root should contain ONLY:**
- `server.py`, `broker.py`, `fake_broker.py`, `config.py`
- `screener.py`, `universe.py`
- `.env`, `.env.example`, `.gitignore`
- `requirements.txt`
- `README.md`, `ROADMAP.md`
- Module directories (agents/, strategies/, backtest/, etc.)

**2. Documentation Scattered**

Current locations:
- Root: `README.md`, `ROADMAP.md`
- `docs/`: Architecture, risk, strategies docs
- `docs/archive/`: Old docs
- Root: Session notes (should be in docs/)

**Proposed structure:**
```
docs/
├── user-guide/
│   ├── README.md (link to root)
│   ├── getting-started.md
│   ├── configuration.md
│   ├── strategies.md (current STRATEGIES.md)
│   └── analytics.md
├── developer/
│   ├── architecture.md (current ARCHITECTURE.md)
│   ├── contributing.md
│   ├── testing.md
│   └── api-reference.md
├── operations/
│   ├── deployment.md
│   ├── monitoring.md
│   └── troubleshooting.md
├── decisions/
│   ├── CONFIG_ALIGNMENT_NOTES.md
│   ├── SIM_MODE_AUTO_SWITCHING.md
│   └── DOCUMENTATION_UPDATE_SUMMARY.md
└── archive/
    └── (old docs)
```

**3. Static UI in Single 160KB File**

`static/index.html` is monolithic:
- HTML structure
- CSS styles (inline)
- JavaScript (3000+ lines inline)

**Impact:**
- Hard to maintain
- Browser caching issues
- No build process
- Chart.js inline mixing with business logic

**Recommendation:** Keep as-is for now (Phase 5+)
- Works well enough
- Refactor when adding features
- Consider: HTML + separate CSS/JS files with cache-busting

---

## 3. Code Review by Module

### 3.1 Server Layer (`server.py`)

**File:** `server.py` (968 lines)

**Quality:** ⭐⭐⭐⭐ (4/5) - Good structure, some complexity

**Strengths:**
- Clean FastAPI patterns
- Proper async/await usage
- Health check endpoint
- CORS middleware configured
- Lifespan management for agents

**Issues:**

**3.1.1 Broker Instantiation Pattern** (Lines 30-33, 421)
```python
# Global decision at startup
if config.SIMULATION_MODE:
    Broker = FakeBroker
else:
    Broker = AlpacaBroker

# Later in lifespan
state.broker = Broker()
```

**Problem:** Cannot switch brokers without restart
**Impact:** Blocks SIM mode auto-switching feature
**Fix:** Implement broker wrapper or hot-reload mechanism

**3.1.2 Configuration Persistence** (Lines 275-390)
```python
PERSISTED_CONFIG_KEYS = {
    "strategy", "watchlist", "watchlist_mode",
    "momentum_threshold", "sell_threshold",
    # ... 16 total fields
}

def load_config_state():
    # Reads JSON, overwrites config.py module globals
    for key, value in data.items():
        if key == "strategy":
            config.STRATEGY = str(value).lower()
        elif key == "watchlist":
            config.WATCHLIST = value
        # ... 16 elif branches
```

**Problems:**
1. **Long if/elif chain** - Hard to maintain
2. **Module global mutation** - Not thread-safe
3. **Implicit overrides** - .env values silently replaced
4. **No validation** - Invalid JSON crashes silently

**Fix:** Use dataclass or Pydantic model:
```python
from dataclasses import dataclass, asdict
from typing import List

@dataclass
class RuntimeConfig:
    strategy: str = "momentum"
    watchlist: List[str] = field(default_factory=list)
    # ... all fields with types

    @classmethod
    def from_file(cls, path: str) -> "RuntimeConfig":
        with open(path) as f:
            data = json.load(f)
        return cls(**data)  # Auto-validates fields

    def save(self, path: str):
        with open(path, 'w') as f:
            json.dump(asdict(self), f, indent=2)
```

**3.1.3 Analytics Endpoints** (Lines 806-935)

```python
@app.get("/api/analytics/summary")
async def get_equity_summary(period: str = "30d"):
    store = _get_analytics_store()
    equity = store.load_equity(period=period)
    metrics = compute_equity_metrics(equity)
    return {"period": period, "metrics": asdict(metrics), "points": len(equity)}
```

**Quality:** ✅ Clean, well-structured
**Testing:** ✅ Covered by `test_health_endpoint.py`
**Issue:** UI not displaying data (JavaScript problem, not backend)

**3.1.4 WebSocket Broadcasting** (Lines 402-412)

```python
async def broadcast(message: dict):
    """Send message to all connected WebSocket clients."""
    dead = []
    for ws in state.websockets:
        try:
            await ws.send_json(message)
        except:
            dead.append(ws)
    for ws in dead:
        state.websockets.discard(ws)
```

**Problem:** Bare `except:` swallows all exceptions
**Fix:**
```python
except (ConnectionClosedError, WebSocketDisconnect) as e:
    logger.debug(f"WebSocket connection closed: {e}")
    dead.append(ws)
except Exception as e:
    logger.error(f"Unexpected WebSocket error: {e}")
    dead.append(ws)
```

### 3.2 Agent System (`agents/`)

**Quality:** ⭐⭐⭐⭐⭐ (5/5) - Excellent architecture

**Files:**
- `base.py` (47 lines) - Abstract base class
- `coordinator.py` (179 lines) - Orchestrator
- `event_bus.py` (28 lines) - Pub/sub
- `events.py` (98 lines) - Event classes
- 8 agent implementations (60-180 lines each)

**Architecture Pattern:** Observer + Template Method

```python
# base.py
class BaseAgent(ABC):
    def __init__(self, name: str, event_bus: "EventBus"):
        self.name = name
        self.event_bus = event_bus
        self._running = False

    @abstractmethod
    async def start(self):
        """Start agent operations"""

    def status(self) -> dict:
        """Return agent status"""
```

**Strengths:**
1. Clean separation of concerns
2. Minimal coupling (agents don't know about each other)
3. Easy to add new agents
4. Testable in isolation
5. Async-native design

**Event Flow Example:**
```python
# data_agent.py
async def fetch_data(self):
    # ... fetch from broker
    await self.event_bus.publish(MarketDataReady(
        symbols=symbols,
        bars=bars,
        market_open=market_open
    ))

# signal_agent.py (subscriber)
async def _handle_market_data(self, event: MarketDataReady):
    signals = self.strategy.analyze(...)
    await self.event_bus.publish(SignalsUpdated(signals=signals))
```

**Code Quality Issues:**

**3.2.1 AnalyticsAgent - Missing Fill Prices** (`agents/analytics_agent.py` lines 48-67)

```python
async def _handle_order_executed(self, event: OrderExecuted):
    trade = {
        "timestamp": datetime.now().isoformat(),
        "order_id": event.order_id,
        "symbol": event.symbol,
        "side": event.side,
        "qty": event.qty,
        "filled_avg_price": None,  # ⚠️ ALWAYS NULL
        "notional": event.notional,
        # ...
    }
    self.store.record_trade(trade)
```

**Problem:** `filled_avg_price` is always `None`
**Impact:** Trade analytics can't calculate P&L, win rate broken
**Root Cause:** `OrderExecuted` event doesn't include price
**Fix:** Extract price from broker order response:

```python
# In execution_agent.py after order fills
order = await broker.submit_order(...)
await self.event_bus.publish(OrderExecuted(
    order_id=order.id,
    symbol=order.symbol,
    side=order.side,
    qty=order.qty,
    filled_avg_price=float(order.filled_avg_price),  # Add this
    notional=order.notional
))
```

**3.2.2 Observability Agent** (`agents/observability_agent.py`)

**Quality:** ⭐⭐⭐⭐⭐ (5/5) - Professional structured logging

```python
async def _handle_event(self, event: Event):
    """Log all events to JSONL"""
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "event_type": event.__class__.__name__,
        "data": event.__dict__,
    }
    self.logger.log(log_entry)
```

**Integration:** Works with `monitoring/evaluator.py` for analysis
**Output:** `logs/observability/agent_events.jsonl`
**Feature:** Scheduled evaluation reports

**No issues found.** ✅

### 3.3 Strategy System (`strategies/`)

**Quality:** ⭐⭐⭐⭐ (4/5) - Clean design, good separation

**Base Class:** `strategies/base.py`

```python
class Strategy(ABC):
    name: str = "Base Strategy"
    description: str = ""

    @abstractmethod
    def analyze(
        self,
        symbol: str,
        bars: List[dict],
        position: Optional[dict]
    ) -> Signal:
        """Return buy/sell/hold signal with strength"""
```

**Signal Structure:**
```python
@dataclass
class Signal:
    signal_type: SignalType  # BUY, SELL, HOLD
    strength: float  # 0.0 to 1.0
    reason: str
    metadata: dict
```

**Implemented Strategies:**

1. **Momentum** (`momentum.py` - 125 lines)
   - Calculates price momentum over lookback period
   - Buy when momentum > threshold
   - Sell when momentum < sell_threshold
   - **Test Coverage:** 11 tests ✅

2. **Mean Reversion** (`mean_reversion.py` - 120 lines)
   - Detects oversold/overbought vs moving average
   - Buy when price significantly below MA
   - Sell when price returns to/above MA
   - **Test Coverage:** 9 tests ✅

3. **Breakout** (`breakout.py` - 155 lines)
   - Identifies consolidation ranges
   - Buy on breakout above high
   - Sell on breakdown below low
   - **Test Coverage:** 13 tests ✅

4. **RSI** (`rsi.py` - 104 lines)
   - Relative Strength Index indicator
   - Buy when oversold (< 30)
   - Sell when overbought (> 70)
   - **Test Coverage:** 9 tests ✅

**Code Quality:**

✅ **Strengths:**
- Consistent structure across all strategies
- Pure functions (no side effects)
- Well-documented parameters
- Comprehensive tests
- Signal metadata for debugging

⚠️ **Issues:**

**3.3.1 Hardcoded Magic Numbers**

Example from `rsi.py`:
```python
class RSIStrategy(Strategy):
    def __init__(
        self,
        period: int = 14,        # Magic number
        oversold: float = 30.0,  # Magic number
        overbought: float = 70.0 # Magic number
    ):
```

**Issue:** RSI thresholds (30/70) are industry standard but not configurable via .env
**Impact:** Low - these are reasonable defaults
**Fix (optional):** Add to config:
```python
RSI_OVERSOLD_THRESHOLD = float(os.getenv("RSI_OVERSOLD", "30"))
RSI_OVERBOUGHT_THRESHOLD = float(os.getenv("RSI_OVERBOUGHT", "70"))
```

**3.3.2 No Multi-Timeframe Support**

All strategies analyze single timeframe (daily bars by default)
**Missing:** Ability to check multiple timeframes (e.g., daily + hourly)
**Impact:** Limits strategy sophistication
**Future Enhancement:** Phase 2+ feature

**3.3.3 Stop-Loss Coupled to Strategy**

Each strategy implements stop-loss check:
```python
# In every strategy
if position:
    unrealized_plpc = position.get("unrealized_plpc", 0)
    if unrealized_plpc <= -config.STOP_LOSS_PCT:
        return Signal(SignalType.SELL, 1.0, "Stop-loss triggered")
```

**Issue:** Stop-loss logic duplicated 4 times
**Better:** MonitorAgent handles stop-loss centrally (already exists!)
**Fix:** Remove stop-loss from strategies, rely on MonitorAgent

**Actually:** MonitorAgent DOES handle stop-loss (`agents/monitor_agent.py` lines 51-64), but strategies also check. This is **redundant but safe** (defense in depth).

### 3.4 Risk Management (`risk/`)

**Quality:** ⭐⭐⭐⭐⭐ (5/5) - Professional implementation

**Files:**
- `circuit_breaker.py` (122 lines) - Daily loss + drawdown limits
- `position_sizer.py` (85 lines) - Position sizing by signal strength

**3.4.1 Circuit Breaker** (`circuit_breaker.py`)

```python
class CircuitBreaker:
    def __init__(
        self,
        daily_loss_limit_pct: float = 0.03,  # 3%
        max_drawdown_pct: float = 0.15        # 15%
    ):
        self.peak_equity = 0.0
        self.start_of_day_equity = 0.0
        self.tripped = False
        self.reason = ""
```

**Features:**
- Daily loss limit (resets at midnight ET)
- Max drawdown from peak
- Manual reset endpoint
- Persistent reason tracking

**Test Coverage:** 3 tests ✅
**Issues:** None found ✅

**3.4.2 Position Sizer** (`position_sizer.py`)

```python
def calculate_position_size(
    portfolio_value: float,
    buying_power: float,
    max_position_pct: float,
    signal_strength: float = 1.0,
    scale_by_strength: bool = True
) -> float:
    """
    Calculate position size with signal strength scaling.

    Returns: Maximum notional value for this position
    """
    base_size = portfolio_value * max_position_pct

    if scale_by_strength:
        # Weak signals get smaller positions
        scaled_size = base_size * signal_strength
    else:
        scaled_size = base_size

    # Cap by buying power
    return min(scaled_size, buying_power)
```

**Strengths:**
- Signal strength scaling (optional)
- Buying power protection
- Well-tested (4 tests)

**Issues:** None found ✅

**3.4.3 Risk Agent** (`agents/risk_agent.py`)

**Lines:** 218 lines
**Responsibilities:**
- Position size calculation
- Circuit breaker checks
- Max open positions limit
- Sector exposure limits
- Correlation exposure limits

**Key Logic:**
```python
async def _validate_signal(self, event: SignalGenerated):
    # 1. Circuit breaker check
    if self.circuit_breaker.is_tripped():
        return  # Block all buys

    # 2. Max positions check
    if len(positions) >= max_positions:
        return

    # 3. Sector exposure check
    sector_exposure = self._calculate_sector_exposure(...)
    if sector_exposure > MAX_SECTOR_EXPOSURE_PCT:
        return

    # 4. Correlation exposure check
    correlated_exposure = self._calculate_correlated_exposure(...)
    if correlated_exposure > MAX_CORRELATED_EXPOSURE_PCT:
        return

    # 5. Position sizing
    position_size = calculate_position_size(...)
    if position_size < MIN_TRADE_VALUE:
        return

    # All checks passed
    await self.event_bus.publish(RiskCheckPassed(...))
```

**Test Coverage:** 6 tests across 3 test files ✅
**Code Quality:** Excellent ✅

**Minor Issue:** Sector correlation calculation reads price data from broker
**Impact:** Extra API calls, could be cached
**Priority:** Low

---

## 4. Configuration Management

### 4.1 Configuration Architecture

**Two-Tier System:**

1. **`.env` file** - Initial defaults, loaded at startup
2. **`config_state.json`** - Runtime overrides, persists UI changes

**Priority:** `config_state.json` > `.env`

**Flow:**
```
Startup:
1. load_dotenv() reads .env → config.py module globals
2. load_config_state() reads JSON → overwrites config.py globals
3. Agents use config.py values

Runtime:
1. User changes setting in UI
2. POST /api/config updates config.py globals
3. save_config_state() writes to JSON
4. Next restart: JSON values take precedence
```

**Files:**
- `config.py` - Module with all settings as globals
- `.env` - Secret keys + default values
- `.env.example` - Template
- `data/config_state.json` - Runtime overrides

### 4.2 Configuration Issues

**4.2.1 Confusing Priority System**

**Problem:** Users expect .env changes to apply, but JSON overrides them
**Example:**
```bash
# User edits .env
MAX_POSITION_PCT=0.10

# Restarts server
# But config_state.json has:
{"max_position_pct": 0.0015}

# Result: 0.0015 is used (JSON wins)
```

**Current Mitigation:** Documented in README.md and .env.example (as of today)
**Better Fix:** Show warning on startup if JSON overrides exist

**4.2.2 No Schema Validation**

`config_state.json` can contain invalid data:
```json
{
  "max_position_pct": "not a number",  // Should be float
  "strategy": 123,                      // Should be string
  "watchlist": "AAPL"                   // Should be list
}
```

**Current Behavior:** Silent failure or runtime errors
**Fix:** Add Pydantic validation:

```python
from pydantic import BaseModel, validator

class ConfigState(BaseModel):
    strategy: str
    watchlist: List[str]
    max_position_pct: float

    @validator('max_position_pct')
    def validate_position_pct(cls, v):
        if not 0 <= v <= 1:
            raise ValueError('Must be between 0 and 1')
        return v
```

**4.2.3 Incomplete Persistence**

Some config values don't persist:
- `SIMULATION_MODE` - ✅ Added today (now persists)
- `TRADING_MODE` (paper/live) - ❌ Not persisted
- `AUTO_TRADE` - ✅ Persists
- `API_TOKEN` - ❌ Not persisted (correct - security)

**Inconsistency:** Some UI-changeable values persist, others don't

### 4.3 Environment Variables

**File:** `.env` (46 lines)

**Categories:**
1. **Secrets** (required):
   - `ALPACA_API_KEY`
   - `ALPACA_SECRET_KEY`
   - `FMP_API_KEY` (optional)

2. **Trading Mode**:
   - `TRADING_MODE` (paper/live)
   - `SIMULATION_MODE` (true/false)
   - `DATA_FEED` (iex/sip)

3. **Trading Behavior**:
   - `AUTO_TRADE`
   - `TRADE_INTERVAL_MINUTES`
   - `STRATEGY`
   - `WATCHLIST_MODE`

4. **Risk Parameters** (13 settings):
   - Position sizing
   - Stop loss
   - Circuit breakers
   - Exposure limits

5. **System**:
   - `API_PORT`
   - `API_TOKEN` (optional)
   - `WEBHOOK_URL` (optional)

**Current State:** ✅ Well-documented, aligned with config_state.json as of today

**Missing:**
- `MAX_OPEN_POSITIONS` - Exists in config_state.json, not in .env.example
- `RSI_OVERSOLD`, `RSI_OVERBOUGHT` - Strategy params not exposed
- `SIM_AUTO_SWITCH_ENABLED` - Future feature not yet added

---

## 5. Testing Infrastructure

### 5.1 Test Suite Overview

**Location:** `tests/` directory (23 test files)
**Total Tests:** 174 tests
**Pass Rate:** 100% ✅
**Execution Time:** ~0.3 seconds
**Framework:** Python `unittest` (not pytest)

**Coverage by Module:**

| Module | Test Files | Test Count | Status |
|--------|-----------|------------|--------|
| Analytics | 2 | 51 | ✅ 100% |
| Backtesting | 4 | 33 | ✅ 100% |
| Strategies | 4 | 45 | ✅ 100% |
| Risk Management | 4 | 13 | ✅ 100% |
| API Endpoints | 3 | 19 | ✅ 100% |
| Agents | 2 | 2 | ✅ 100% |
| Security | 1 | 5 | ✅ 100% |
| Configuration | 1 | 3 | ✅ 100% |
| Utilities | 2 | 3 | ✅ 100% |

### 5.2 Test Organization

**Pattern:** One test file per module

```
tests/
├── test_analytics_metrics.py      # 21 tests - equity & trade metrics
├── test_analytics_store.py        # 30 tests - JSONL persistence
├── test_backtest_data.py          # 7 tests - historical data
├── test_backtest_engine.py        # 6 tests - simulation
├── test_backtest_metrics.py       # 11 tests - performance calc
├── test_backtest_results.py       # 9 tests - results export
├── test_circuit_breaker.py        # 3 tests - risk limits
├── test_config_persistence.py     # 3 tests - JSON config
├── test_data_agent_indices.py     # 1 test - market indices
├── test_health_endpoint.py        # 16 tests - health checks
├── test_observability_endpoints.py # 4 tests - observability API
├── test_position_sizer.py         # 4 tests - position sizing
├── test_risk_agent_exposure.py    # 3 tests - sector/correlation
├── test_risk_agent_limits.py      # 1 test - max positions
├── test_risk_agent_sizer.py       # 2 tests - risk+sizing integration
├── test_risk_breaker_endpoint.py  # 2 tests - reset API
├── test_screener.py               # 1 test - top gainers
├── test_security.py               # 5 tests - API auth/CORS
├── test_signals_updated.py        # 1 test - event emission
├── test_strategy_breakout.py      # 13 tests - breakout strategy
├── test_strategy_mean_reversion.py # 9 tests - mean reversion
├── test_strategy_momentum.py      # 11 tests - momentum strategy
├── test_strategy_rsi.py           # 9 tests - RSI strategy
└── test_trade_interval.py         # 2 tests - config validation
```

### 5.3 Test Quality

**Strengths:**
1. **Comprehensive Coverage** - All critical paths tested
2. **Fast Execution** - 0.3 seconds for 174 tests
3. **Isolated Tests** - No dependencies between tests
4. **Clear Names** - `test_buy_signal_strong_momentum`
5. **Good Documentation** - Docstrings explain what's tested

**Example of High-Quality Test:**
```python
# test_strategy_momentum.py
def test_buy_signal_strong_momentum(self):
    """Test buy signal when momentum exceeds threshold."""
    strategy = MomentumStrategy(
        lookback_days=5,
        momentum_threshold=0.02
    )

    # Create price data with 5% momentum
    bars = [
        {"timestamp": "2023-01-01", "close": 100},
        {"timestamp": "2023-01-02", "close": 102},
        {"timestamp": "2023-01-03", "close": 103},
        {"timestamp": "2023-01-04", "close": 104},
        {"timestamp": "2023-01-05", "close": 105},  # +5% from start
    ]

    signal = strategy.analyze("AAPL", bars, position=None)

    self.assertEqual(signal.signal_type, SignalType.BUY)
    self.assertGreater(signal.strength, 0.5)
    self.assertIn("momentum", signal.reason.lower())
```

**Issues:**

**5.3.1 Missing Integration Tests**

Current tests are all **unit tests** (test single function/class in isolation)
**Missing:** Integration tests for full trading flow

**Example needed:**
```python
class TestEndToEndTrade(unittest.TestCase):
    """Test complete trade lifecycle from signal to execution."""

    async def test_full_buy_flow(self):
        # 1. DataAgent fetches data
        # 2. SignalAgent generates BUY signal
        # 3. RiskAgent validates
        # 4. ExecutionAgent places order
        # 5. MonitorAgent tracks position
        # 6. AnalyticsAgent logs trade
        # Verify: trade appears in analytics, position exists
```

**Priority:** High (documented in ROADMAP as Phase 11 deliverable)

**5.3.2 No Performance/Load Tests**

Tests don't verify:
- Memory usage during multi-day backtest
- WebSocket broadcast performance with 100 connections
- Analytics query performance with 10,000 trades

**Priority:** Medium (Phase 11+)

**5.3.3 Missing Dependency:** `httpx`

**Issue Found:** `test_health_endpoint.py` requires `httpx` for `TestClient`
**Status:** ✅ FIXED TODAY - Added `httpx>=0.24.0` to requirements.txt

**Evidence:**
```python
# test_health_endpoint.py line 11
from fastapi.testclient import TestClient  # Requires httpx
```

### 5.4 Test Execution

**Methods:**

1. **Unit tests (recommended):**
```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

2. **Via test script** (doesn't exist in current directory):
```bash
./run_tests.sh  # Missing - should create
```

**Test Results Location:**
- Logs: `test_results/test_run_<timestamp>.log` (auto-generated)

**Missing:**
- No coverage report (% of code covered)
- No test runner script in repo root
- No CI/CD integration (Phase 11 deliverable)

---

## 6. Dependencies

### 6.1 External Dependencies

**File:** `requirements.txt` (10 packages)

```txt
alpaca-trade-api>=3.0.0      # Broker API client
pandas>=2.0.0                # Data manipulation
numpy>=1.24.0                # Numerical computing
python-dotenv>=1.0.0         # Environment variables
requests>=2.31.0             # HTTP client
schedule>=1.2.0              # Task scheduling (unused?)
fastapi>=0.109.0             # Web framework
uvicorn[standard]>=0.27.0    # ASGI server
psutil>=5.9.0                # System monitoring
httpx>=0.24.0                # HTTP client for tests (added today)
```

**Analysis:**

✅ **Essential:**
- `alpaca-trade-api` - Core functionality
- `fastapi` + `uvicorn` - Web server
- `pandas` + `numpy` - Data processing
- `python-dotenv` - Config management
- `psutil` - Health checks

⚠️ **Unused:**
- `schedule` - Not found in any .py file
  ```bash
  $ grep -r "import schedule" .
  # No results
  ```
  **Recommendation:** Remove from requirements.txt

❓ **Questionable:**
- `requests` - Only used in `screener.py` for top gainers API
  - Could use `httpx` instead (already a dep)
  - Low priority optimization

**Missing:**
- `pytz` - Needed for market hours detection (future SIM auto-switch feature)
- `pandas-market-calendars` - NYSE holiday calendar (future feature)

### 6.2 Internal Dependencies

**Module Import Graph:**

```
server.py
├── config.py
├── broker.py (→ alpaca-trade-api)
├── fake_broker.py
├── screener.py (→ requests, config)
├── agents.coordinator (→ event_bus, all agents)
│   ├── agents.data_agent (→ broker, screener)
│   ├── agents.signal_agent (→ strategies)
│   ├── agents.risk_agent (→ risk.circuit_breaker, risk.position_sizer)
│   ├── agents.execution_agent (→ broker)
│   ├── agents.monitor_agent (→ broker)
│   ├── agents.analytics_agent (→ analytics.store)
│   └── agents.observability_agent (→ monitoring.logger)
├── analytics.store
├── analytics.metrics
└── monitoring.evaluator
```

**Circular Dependencies:** None found ✅

**Coupling Analysis:**

**Tight Coupling (expected):**
- `server.py` ↔ `agents.coordinator` - Orchestrator pattern
- `agents` ↔ `event_bus` - Pub/sub pattern
- `signal_agent` ↔ `strategies` - Strategy pattern

**Good Abstractions:**
- Broker interface (`broker.py` + `fake_broker.py`)
- Strategy base class (`strategies/base.py`)
- Agent base class (`agents/base.py`)

**No problematic coupling found** ✅

---

## 7. Technical Debt

### 7.1 Code-Level Debt

**7.1.1 Hardcoded Values**

**Location:** `server.py` line 275-294
```python
PERSISTED_CONFIG_KEYS = {
    "strategy", "watchlist", "watchlist_mode",
    "momentum_threshold", "sell_threshold",
    # ... 20 keys hardcoded as strings
}
```

**Issue:** Adding new persisted config requires touching 3 places:
1. Add to `PERSISTED_CONFIG_KEYS` set
2. Add to `_config_snapshot()` dict
3. Add if/elif branch in `load_config_state()`

**Impact:** Medium - error-prone, hard to maintain
**Fix:** Reflection-based approach or dataclass

**7.1.2 Magic Numbers**

**Examples:**
```python
# server.py line 429
await asyncio.sleep(max(config.OBSERVABILITY_EVAL_INTERVAL_MINUTES, 1) * 60)
# Why 1? Why 60? Should be named constants

# fake_broker.py line 79
jiggle = random.uniform(-jiggle_factor, jiggle_factor)
# Formula not documented

# screener.py line 43
min_price = max(min_price, 1.0)
# Why 1.0? Should be MIN_ACCEPTABLE_PRICE
```

**Impact:** Low - code works, but readability suffers
**Priority:** Low

**7.1.3 Bare Except Clauses**

**Found in 3 locations:**

1. `server.py` line 408
```python
except:  # Too broad
    dead.append(ws)
```

2. `analytics/store.py` multiple locations
```python
try:
    data = json.loads(line)
except:  # Swallows all errors
    continue
```

**Issue:** Masks unexpected errors, hard to debug
**Fix:** Catch specific exceptions

**7.1.4 No Type Hints in Older Code**

**Newer code has type hints:**
```python
# agents/base.py (good)
def status(self) -> dict:
    """Return agent status"""
```

**Older code lacks them:**
```python
# server.py (mixed)
def _get_analytics_store():  # No return type
    return state.analytics_store
```

**Impact:** Low - Python is dynamically typed
**Priority:** Medium (improves IDE support, catches bugs)

### 7.2 Architectural Debt

**7.2.1 Broker Instantiation at Startup**

**Problem:** Cannot switch between AlpacaBroker and FakeBroker without restart
**Impact:** Blocks SIM mode auto-switching feature
**Documented:** Yes (in SIM_MODE_AUTO_SWITCHING_CONTEXT.md)
**Priority:** High (required for Phase 11 feature)

**Proposed Fix:** Broker wrapper pattern
```python
class AutoSwitchingBroker:
    def __init__(self):
        self.alpaca = AlpacaBroker()
        self.fake = FakeBroker()

    def _active_broker(self):
        if should_use_simulation():
            return self.fake
        return self.alpaca

    def get_account(self):
        return self._active_broker().get_account()

    # Delegate all methods...
```

**7.2.2 Monolithic UI File**

**File:** `static/index.html` (3,600 lines)
**Contains:**
- HTML structure
- CSS (inline <style>)
- JavaScript (3,000+ lines)
- Chart.js initialization
- WebSocket handling
- API calls
- UI state management

**Problems:**
1. Hard to maintain
2. No build process
3. Browser caching issues
4. No code organization (everything in global scope)

**Impact:** Medium - works, but hard to modify
**Priority:** Low (Phase 5+ - Enhanced Paper Trading)

**Future:** Extract into separate files:
```
static/
├── index.html
├── css/
│   └── app.css
└── js/
    ├── app.js
    ├── charts.js
    ├── api.js
    └── websocket.js
```

**7.2.3 Analytics UI Not Displaying Data**

**Problem:** Backend API works, UI shows "--"
**Root Causes Identified:**
1. Browser caching (old JavaScript)
2. Chart.js rendering issue (white text fix attempted)
3. Insufficient data points for metrics calculation
4. Trades missing `filled_avg_price` (prevents P&L calc)

**Status:** Partially diagnosed, not fixed
**Priority:** High (Phase 4 should be 100%)
**Next Steps:**
1. Debug with `python test_analytics_api.py`
2. Check browser console for errors
3. Fix AnalyticsAgent to capture fill prices
4. Add cache-busting to index.html

### 7.3 Testing Debt

**7.3.1 No Integration Tests**

**Current:** 174 unit tests (single function/class)
**Missing:** End-to-end flow tests

**Gap:** Cannot verify:
- Full trade lifecycle (data → signal → risk → execution → analytics)
- Multi-agent coordination
- Error recovery scenarios
- WebSocket message flow

**Priority:** High (Phase 11 deliverable)

**7.3.2 No CI/CD Pipeline**

**Current:** Tests run manually
**Missing:**
- GitHub Actions workflow
- Automated testing on push
- Test coverage reports
- Linting/formatting checks

**Priority:** High (Phase 11 deliverable)

### 7.4 Documentation Debt

**7.4.1 Scattered Documentation**

**Locations:**
- Root: README.md, ROADMAP.md
- docs/: Architecture, risk, strategies
- Root: Session notes (3 files added today)
- Root: Old AI reviews (5 files to delete)

**Issue:** No clear documentation hierarchy
**Priority:** Medium

**7.4.2 Incomplete API Documentation**

**Missing:**
- API endpoint reference
- WebSocket message format
- Configuration schema
- Error codes

**Priority:** Medium (Phase 10 - Documentation)

**7.4.3 No Developer Onboarding Guide**

**Missing:**
- How to add a new strategy
- How to add a new agent
- How to add a new risk check
- Development workflow

**Priority:** Medium (Phase 10)

---

## 8. Security Considerations

### 8.1 Authentication & Authorization

**Current Implementation:** `server.py` lines 62-82

```python
def require_api_access(
    request: Request,
    api_token: Optional[str] = Header(None, alias="Authorization")
):
    """Verify API access via token or localhost."""

    # Allow localhost without token
    if _is_loopback_host(request.client.host):
        return

    # Require token for non-localhost
    if not config.API_TOKEN:
        raise HTTPException(403, "API_TOKEN not configured")

    if not api_token or api_token != f"Bearer {config.API_TOKEN}":
        raise HTTPException(401, "Invalid API token")
```

**Security Model:**
- ✅ Localhost always allowed (for development)
- ✅ Remote access requires Bearer token
- ✅ Health endpoint exempt (no auth required)
- ✅ CORS configured with allowed origins

**Test Coverage:** 5 tests in `test_security.py` ✅

**Issues:**

**8.1.1 No Rate Limiting**

**Risk:** API abuse (DoS via excessive requests)
**Impact:** Medium
**Mitigation:** Add rate limiting middleware

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.get("/api/status")
@limiter.limit("10/minute")  # 10 requests per minute
async def get_status():
    ...
```

**8.1.2 Token in Environment Variable**

**Current:** `API_TOKEN=secret_value_here` in .env
**Risk:** Low - .env is in .gitignore
**Better:** Use secrets management (AWS Secrets Manager, HashiCorp Vault)
**Priority:** Low (acceptable for self-hosted)

**8.1.3 No HTTPS Enforcement**

**Current:** HTTP only (localhost:8000)
**Risk:** Token sent in plaintext over network
**Impact:** High if accessed remotely
**Mitigation:** Deploy behind nginx/traefik with TLS
**Priority:** Critical for production deployment

### 8.2 Secret Management

**Secrets in .env:**
- `ALPACA_API_KEY` - Broker credentials
- `ALPACA_SECRET_KEY` - Broker credentials
- `API_TOKEN` - API authentication
- `FMP_API_KEY` - Market data API (optional)

**Current State:**
✅ `.gitignore` excludes `.env`
✅ `.env.example` doesn't contain real secrets
✅ README warns to never commit .env

**Issues:**

**8.2.1 Secrets in Logs**

**Checked:** No evidence of secrets in logs ✅
**Good:** Broker credentials not logged
**Good:** API tokens not in error messages

**8.2.2 Secrets in Error Responses**

**Checked:** HTTP errors don't leak config ✅
**Example:**
```python
# If API_TOKEN not set
raise HTTPException(403, "API_TOKEN not configured")
# ✅ Good - doesn't reveal if token exists
```

### 8.3 Input Validation

**API Endpoints:**

**Good Examples:**
```python
# server.py line 682
@app.post("/api/config")
async def update_config(updates: dict):
    for key in updates:
        if key not in PERSISTED_CONFIG_KEYS:
            continue  # ✅ Ignore unknown keys

    # Validate specific fields
    if "max_position_pct" in updates:
        value = float(updates["max_position_pct"])
        if not 0 <= value <= 1:
            raise HTTPException(400, "Invalid range")
```

**Issues:**

**8.3.1 No Schema Validation**

**Risk:** Malformed JSON crashes server
**Example:**
```json
POST /api/config
{"max_position_pct": "not a number"}
# Result: ValueError in server
```

**Fix:** Use Pydantic models:
```python
from pydantic import BaseModel

class ConfigUpdate(BaseModel):
    max_position_pct: Optional[float] = None

    @validator('max_position_pct')
    def validate_range(cls, v):
        if v and not 0 <= v <= 1:
            raise ValueError('Must be 0-1')
        return v

@app.post("/api/config")
async def update_config(updates: ConfigUpdate):
    # Auto-validated by Pydantic
```

**8.3.2 Path Traversal in Analytics Export**

**Checked:** No user-controlled file paths in API ✅
**Good:** Export endpoints use fixed filenames

### 8.4 Dependency Vulnerabilities

**Check:** `requirements.txt` for known CVEs

**Recommendation:** Run security audit:
```bash
pip install safety
safety check -r requirements.txt
```

**Priority:** High (should be in CI/CD)

---

## 9. Performance Analysis

### 9.1 Known Performance Characteristics

**Test Suite:** 174 tests in 0.3 seconds ✅ Excellent

**Backtesting:** From test logs:
```
Running backtest: 2023-01-01 to 2023-02-15
Symbols: TEST
Initial capital: $10,000.00
Trading days: 46
# Completes in < 1 second
```
✅ Good performance for single-symbol backtest

**Web Server:** FastAPI + async/await
✅ Appropriate for I/O-bound workload

### 9.2 Potential Bottlenecks

**9.2.1 Analytics JSONL File Growth**

**Current:**
```bash
$ ls -lh data/analytics/
324K equity.jsonl
191K trades.jsonl
```

**Growth Rate:**
- Equity: 1 snapshot per minute when bot running
- Trades: Variable (depends on strategy)

**Projection:**
- 1 year of 24/7 operation: ~170MB equity.jsonl
- With 10,000 trades: ~10MB trades.jsonl

**Issue:** Loading entire file into memory
```python
# analytics/store.py
def load_equity(self, period: str = "all"):
    with open(self.equity_file) as f:
        for line in f:
            records.append(json.loads(line))  # All in memory
    return records
```

**Impact:** Low (files stay small for typical usage)
**Fix (if needed):** Stream processing or SQLite

**9.2.2 No Database**

**Current:** Flat files only
- Config: JSON
- Analytics: JSONL
- Backtests: CSV

**Limitations:**
- No complex queries
- No indexing
- No transactions
- No concurrent writes (lock-based)

**When database needed:**
- Multi-user support
- Query optimization
- Reporting dashboards
- Historical analysis

**Priority:** Low (Phase 8 - Configuration Management mentions DB)

**9.2.3 WebSocket Broadcasting**

**Current:** Loop through all connections
```python
for ws in state.websockets:
    await ws.send_json(message)
```

**Scalability:** Limited to ~100 concurrent connections
**Impact:** Low (single-user deployment)
**Fix (if needed):** Redis pub/sub or message queue

### 9.3 Optimization Opportunities

**9.3.1 Top Gainers API Calls**

**Current:** `screener.py` makes HTTP request every fetch
**Frequency:** Every `TRADE_INTERVAL_MINUTES` (1-5 minutes)
**Caching:** None

**Optimization:** Cache for 5-10 minutes
```python
from functools import lru_cache
from datetime import datetime, timedelta

_cache = {"data": None, "expires": None}

def get_top_gainers():
    now = datetime.now()
    if _cache["expires"] and now < _cache["expires"]:
        return _cache["data"]  # Return cached

    data = _fetch_from_api()  # Expensive call
    _cache["data"] = data
    _cache["expires"] = now + timedelta(minutes=5)
    return data
```

**Impact:** Reduce API calls by 80%
**Priority:** Low

**9.3.2 Sector Exposure Calculation**

**Current:** Fetches price data for correlation calc every signal
**Impact:** Extra broker API calls
**Optimization:** Cache recent price bars
**Priority:** Low

---

## 10. Documentation Review

### 10.1 User-Facing Documentation

**README.md** (164 lines)
- ✅ Quick start guide
- ✅ Feature overview
- ✅ Architecture diagram (text)
- ✅ Configuration table (comprehensive)
- ✅ Command examples
- ⚠️ No screenshots/videos
- ⚠️ No troubleshooting section

**Quality:** ⭐⭐⭐⭐ (4/5) - Good technical reference

**ROADMAP.md** (1,290 lines)
- ✅ Vision and goals
- ✅ Target audiences
- ✅ Phase-by-phase plan
- ✅ Technical debt tracking
- ✅ Changelog
- ✅ Updated today with latest status
- ⚠️ Very long (hard to navigate)

**Quality:** ⭐⭐⭐⭐⭐ (5/5) - Excellent strategic document

### 10.2 Developer Documentation

**docs/ARCHITECTURE.md**
- Content unknown (not reviewed in this session)
- Referenced in README

**docs/RISK.md**
- Content unknown
- Referenced in README

**docs/STRATEGIES.md**
- Content unknown
- Referenced in README

**docs/TESTS_FIXED_SUMMARY.md**
- Test improvement history
- Useful for understanding test evolution

**Session Notes (Added Today):**
- `CONFIG_ALIGNMENT_NOTES.md` - Config system explanation
- `SIM_MODE_AUTO_SWITCHING_CONTEXT.md` - Feature spec
- `DOCUMENTATION_UPDATE_SUMMARY.md` - Meta-doc

**Quality:** ⚠️ Incomplete, scattered
**Priority:** Medium (Phase 10 deliverable)

### 10.3 Code Documentation

**Docstrings:**

**Good Examples:**
```python
# backtest/engine.py
def run(self, symbols: List[str], start: str, end: str) -> BacktestResults:
    """
    Run backtest simulation.

    Args:
        symbols: List of stock tickers to trade
        start: Start date (YYYY-MM-DD)
        end: End date (YYYY-MM-DD)

    Returns:
        BacktestResults with equity curve, trades, metrics
    """
```

**Missing Docstrings:**
- Most functions in `server.py` (75% missing)
- Utility functions in `screener.py`
- Helper functions throughout

**Impact:** Medium - harder for new devs
**Priority:** Low (code is relatively self-explanatory)

### 10.4 API Documentation

**Missing:**
- OpenAPI/Swagger spec (FastAPI can auto-generate)
- Endpoint descriptions
- Request/response schemas
- Error codes

**How to Generate:**
```python
# Add to server.py
app = FastAPI(
    title="Market-Watch Trading Bot",
    description="Algorithmic trading API",
    version="1.0.0",
    docs_url="/docs",  # Swagger UI
    redoc_url="/redoc"  # ReDoc
)
```

**Priority:** Low (auto-generated docs exist at /docs endpoint)

---

## 11. Deployment & Operations

### 11.1 Deployment Readiness

**Current State:** Development-oriented

**Production Checklist:**

❌ **Not Production-Ready:**
- No HTTPS/TLS
- No systemd service file
- No health check monitoring
- No log rotation
- No backup strategy
- No disaster recovery plan
- No deployment automation
- No environment promotion (dev → staging → prod)

✅ **Has:**
- Health check endpoint
- Structured logging (observability)
- Configuration management
- Error handling (mostly)

**Missing for Production:**

1. **Process Management**
   ```ini
   # /etc/systemd/system/market-watch.service
   [Unit]
   Description=Market-Watch Trading Bot
   After=network.target

   [Service]
   Type=simple
   User=trader
   WorkingDirectory=/opt/market-watch
   ExecStart=/opt/market-watch/.venv/bin/python server.py
   Restart=always
   RestartSec=10

   [Install]
   WantedBy=multi-user.target
   ```

2. **Reverse Proxy**
   ```nginx
   # /etc/nginx/sites-available/market-watch
   server {
       listen 443 ssl;
       server_name trading.example.com;

       ssl_certificate /etc/letsencrypt/live/trading.example.com/fullchain.pem;
       ssl_certificate_key /etc/letsencrypt/live/trading.example.com/privkey.pem;

       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection "upgrade";
       }
   }
   ```

3. **Monitoring**
   - Uptime monitoring (UptimeRobot, Pingdom)
   - Error alerting (Sentry, Rollbar)
   - Performance monitoring (New Relic, DataDog)

4. **Backups**
   ```bash
   # Daily backup script
   #!/bin/bash
   tar -czf /backups/market-watch-$(date +%Y%m%d).tar.gz \
       /opt/market-watch/data \
       /opt/market-watch/.env \
       /opt/market-watch/logs

   # Retain 30 days
   find /backups -name "market-watch-*.tar.gz" -mtime +30 -delete
   ```

**Priority:** Critical before live trading

### 11.2 Operational Procedures

**Missing:**

1. **Runbooks**
   - How to restart after crash
   - How to reset circuit breaker
   - How to change strategies mid-day
   - How to recover from bad trades

2. **Monitoring Dashboards**
   - Equity curve in real-time
   - Error rate tracking
   - API latency
   - Trade execution time

3. **Incident Response**
   - Who to call
   - Escalation procedures
   - Rollback procedures

**Priority:** High (before live trading)

---

## 12. Recommendations

### 12.1 Immediate Actions (This Week)

**Priority: CRITICAL**

1. **Clean Up Root Directory**
   ```bash
   # Remove old AI reviews
   rm codex-project_review-*.md gemini-project_review-*.md merged_review.md
   rm err.txt test_err.txt

   # Move to docs/
   mv CONFIG_ALIGNMENT_NOTES.md docs/decisions/
   mv SIM_MODE_AUTO_SWITCHING_CONTEXT.md docs/decisions/
   mv DOCUMENTATION_UPDATE_SUMMARY.md docs/decisions/

   # Move to scripts/
   mv test_analytics_api.py scripts/
   ```
   **Impact:** Cleaner project, easier navigation
   **Effort:** 10 minutes

2. **Fix Analytics UI Issues**
   - Debug with `python scripts/test_analytics_api.py`
   - Check browser console for errors
   - Fix AnalyticsAgent to capture `filled_avg_price`
   - Add cache-busting to index.html (`<script src="app.js?v=1.0.0">`)

   **Impact:** Phase 4 becomes 100% complete
   **Effort:** 2-4 hours

3. **Create Test Runner Script**
   ```bash
   # run_tests.sh
   #!/bin/bash
   echo "Running Market-Watch Test Suite..."
   source .venv/bin/activate
   python -m unittest discover -s tests -p "test_*.py" -v
   ```
   **Impact:** Easier for new developers
   **Effort:** 15 minutes

### 12.2 Short-Term Improvements (This Month)

**Priority: HIGH**

4. **Add Pydantic Validation to Config**
   - Replace manual if/elif chains
   - Add type checking
   - Prevent invalid config values

   **Impact:** Fewer runtime errors, better UX
   **Effort:** 4-6 hours

5. **Fix AnalyticsAgent Fill Prices**
   - Modify `OrderExecuted` event to include price
   - Update AnalyticsAgent to record it
   - Update tests

   **Impact:** Trade analytics work correctly
   **Effort:** 2-3 hours

6. **Add Integration Tests**
   - Test full trade flow (5-10 tests)
   - Test error recovery scenarios
   - Test multi-agent coordination

   **Impact:** Catch bugs earlier, confidence in changes
   **Effort:** 8-12 hours

7. **Set Up CI/CD Pipeline**
   ```yaml
   # .github/workflows/test.yml
   name: Tests
   on: [push, pull_request]
   jobs:
     test:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v2
         - uses: actions/setup-python@v2
           with:
             python-version: 3.12
         - run: pip install -r requirements.txt
         - run: python -m unittest discover -s tests
   ```
   **Impact:** Automated testing, prevent regressions
   **Effort:** 2-3 hours

### 12.3 Medium-Term Features (Next Quarter)

**Priority: MEDIUM**

8. **Implement SIM Mode Auto-Switching**
   - Market hours detection (pytz)
   - Background monitor task
   - Broker wrapper for runtime switching
   - UI countdown display

   **Impact:** 24/7 bot training
   **Effort:** 2-3 days (documented in SIM_MODE_AUTO_SWITCHING_CONTEXT.md)

9. **Refactor UI into Separate Files**
   - Extract CSS to `static/css/app.css`
   - Extract JS to `static/js/app.js`
   - Add build step with cache-busting

   **Impact:** Easier maintenance, better caching
   **Effort:** 1-2 days

10. **Add Database Layer**
    - SQLite for local deployments
    - Schema for config, trades, equity
    - Migration scripts

    **Impact:** Better querying, scalability
    **Effort:** 3-4 days

### 12.4 Long-Term Enhancements (Next Year)

**Priority: LOW**

11. **Production Deployment Guide**
    - Systemd service file
    - Nginx config
    - TLS setup
    - Monitoring integration

    **Impact:** Safe live trading
    **Effort:** 1 week

12. **Complete Documentation Overhaul**
    - Reorganize docs/ structure
    - Write missing guides
    - Add screenshots/videos
    - API reference

    **Impact:** Easier onboarding
    **Effort:** 2-3 weeks

13. **Performance Optimization**
    - Add caching layers
    - Optimize SQL queries (if DB added)
    - Profile and optimize hot paths

    **Impact:** Handle larger scale
    **Effort:** 1-2 weeks

### 12.5 Code Quality Improvements

**Ongoing:**

14. **Add Type Hints**
    - Target: 80% of functions
    - Use mypy for validation

    **Impact:** Better IDE support, catch bugs
    **Effort:** 1-2 hours per module

15. **Improve Error Handling**
    - Replace bare `except:` clauses
    - Add specific exception types
    - Better error messages

    **Impact:** Easier debugging
    **Effort:** 2-3 hours

16. **Extract Magic Numbers**
    - Named constants for all numbers
    - Configuration for tunable values

    **Impact:** Better readability
    **Effort:** 1-2 hours

---

## Appendix A: File Inventory

### A.1 Source Files (66 files)

**Python Files:**
- Main: `server.py` (968 lines)
- Brokers: `broker.py`, `fake_broker.py`
- Config: `config.py`, `universe.py`, `screener.py`
- Agents: 13 files in `agents/`
- Strategies: 5 files in `strategies/`
- Backtest: 7 files in `backtest/`
- Analytics: 2 files in `analytics/`
- Risk: 3 files in `risk/`
- Monitoring: 8 files in `monitoring/`
- Scripts: 3 files in `scripts/`
- Tests: 23 files in `tests/`

**Configuration:**
- `.env` (secrets + config)
- `.env.example` (template)
- `.gitignore`
- `requirements.txt`

**Documentation:**
- `README.md`
- `ROADMAP.md`
- `docs/ARCHITECTURE.md`
- `docs/RISK.md`
- `docs/STRATEGIES.md`
- `docs/TESTS_FIXED_SUMMARY.md`
- 3 session notes (to be moved to docs/)

**Web UI:**
- `static/index.html` (3,600 lines)

**Data Files:**
- `data/config_state.json`
- `data/sector_map.json`
- `data/analytics/*.jsonl` (runtime)
- `data/historical/*.csv` (backtest cache)

**Logs:**
- `logs/observability/*.jsonl` (runtime)

### A.2 Lines of Code Summary

| Module | Files | Lines | Comments |
|--------|-------|-------|----------|
| `server.py` | 1 | 968 | Main API |
| `agents/` | 13 | ~1,500 | Agent system |
| `strategies/` | 5 | ~600 | Trading strategies |
| `backtest/` | 7 | ~1,200 | Backtest engine |
| `analytics/` | 2 | ~400 | Analytics system |
| `risk/` | 3 | ~250 | Risk management |
| `monitoring/` | 8 | ~800 | Observability |
| `tests/` | 23 | ~5,000 | Test suite |
| `static/index.html` | 1 | 3,600 | Web UI |
| Other | 8 | ~500 | Utilities, config |
| **Total** | **71** | **~14,800** | Incl. tests + UI |

**Production Code Only:** ~9,200 lines (excluding tests and UI)

---

## Appendix B: Test Coverage Map

| Module | Test File | Tests | Coverage |
|--------|-----------|-------|----------|
| **Analytics** | | | |
| `analytics/metrics.py` | `test_analytics_metrics.py` | 21 | Equity + trade metrics ✅ |
| `analytics/store.py` | `test_analytics_store.py` | 30 | JSONL persistence ✅ |
| **Backtesting** | | | |
| `backtest/data.py` | `test_backtest_data.py` | 7 | Historical data ✅ |
| `backtest/engine.py` | `test_backtest_engine.py` | 6 | Simulation ✅ |
| `backtest/metrics.py` | `test_backtest_metrics.py` | 11 | Performance calc ✅ |
| `backtest/results.py` | `test_backtest_results.py` | 9 | Export ✅ |
| **Strategies** | | | |
| `strategies/momentum.py` | `test_strategy_momentum.py` | 11 | Momentum ✅ |
| `strategies/mean_reversion.py` | `test_strategy_mean_reversion.py` | 9 | Mean reversion ✅ |
| `strategies/breakout.py` | `test_strategy_breakout.py` | 13 | Breakout ✅ |
| `strategies/rsi.py` | `test_strategy_rsi.py` | 9 | RSI ✅ |
| **Risk** | | | |
| `risk/circuit_breaker.py` | `test_circuit_breaker.py` | 3 | Circuit breaker ✅ |
| `risk/position_sizer.py` | `test_position_sizer.py` | 4 | Position sizing ✅ |
| `agents/risk_agent.py` | `test_risk_agent_*.py` | 6 | Risk checks ✅ |
| **API** | | | |
| `server.py` (health) | `test_health_endpoint.py` | 16 | Health checks ✅ |
| `server.py` (observability) | `test_observability_endpoints.py` | 4 | Observability API ✅ |
| `server.py` (security) | `test_security.py` | 5 | Auth/CORS ✅ |
| `server.py` (risk reset) | `test_risk_breaker_endpoint.py` | 2 | Reset API ✅ |
| **Other** | | | |
| `config.py` | `test_config_persistence.py` | 3 | Config save/load ✅ |
| `screener.py` | `test_screener.py` | 1 | Top gainers ✅ |
| `agents/signal_agent.py` | `test_signals_updated.py` | 1 | Event emission ✅ |
| `agents/data_agent.py` | `test_data_agent_indices.py` | 1 | Market indices ✅ |
| `server.py` (trade interval) | `test_trade_interval.py` | 2 | Config validation ✅ |

**Total:** 174 tests, 100% pass rate

---

## Appendix C: Configuration Reference

### C.1 Environment Variables

See `.env.example` for complete list (54 variables)

**Categories:**
1. Credentials (4 required)
2. Trading mode (3 settings)
3. Strategy (10+ parameters)
4. Risk management (13 settings)
5. System (7 settings)
6. Observability (7 settings)

### C.2 Runtime Config (JSON)

**File:** `data/config_state.json`

**Persisted Fields (20):**
- `strategy`, `watchlist`, `watchlist_mode`
- `momentum_threshold`, `sell_threshold`
- `stop_loss_pct`, `max_position_pct`
- `max_daily_trades`, `max_open_positions`
- `daily_loss_limit_pct`, `max_drawdown_pct`
- `max_sector_exposure_pct`, `max_correlated_exposure_pct`
- `trade_interval`, `auto_trade`, `simulation_mode`
- `top_gainers_count`, `top_gainers_universe`
- `top_gainers_min_price`, `top_gainers_min_volume`

**Priority:** JSON > .env (runtime overrides)

---

## Appendix D: Agent Responsibility Matrix

| Agent | Responsibilities | Events Published | Events Subscribed |
|-------|-----------------|------------------|-------------------|
| **DataAgent** | Fetch market data | MarketDataReady | - |
| **SignalAgent** | Generate signals | SignalGenerated, SignalsUpdated | MarketDataReady |
| **RiskAgent** | Validate signals | RiskCheckPassed, RiskCheckFailed | SignalGenerated |
| **ExecutionAgent** | Place orders | OrderExecuted, OrderFailed | RiskCheckPassed |
| **MonitorAgent** | Track positions | StopLossTriggered | MarketDataReady |
| **AlertAgent** | Broadcast to UI | - | All events |
| **AnalyticsAgent** | Record history | - | MarketDataReady, OrderExecuted |
| **ObservabilityAgent** | Log events | - | All events |

---

## Appendix E: Known Issues Log

| ID | Severity | Component | Description | Status |
|----|----------|-----------|-------------|--------|
| 1 | High | Analytics UI | Metrics show "--" instead of calculated values | Open |
| 2 | High | Analytics UI | Position concentration chart not rendering | Open |
| 3 | High | AnalyticsAgent | Trades recorded without filled_avg_price | Open |
| 4 | Medium | UI | Browser caching prevents UI updates | Workaround |
| 5 | Medium | Broker | Cannot switch at runtime (blocks SIM auto-switch) | Documented |
| 6 | Medium | Config | No schema validation for config_state.json | Open |
| 7 | Medium | Server | Bare except clauses swallow errors | Open |
| 8 | Low | Dependencies | `schedule` package unused | Open |
| 9 | Low | Docs | Scattered across multiple locations | Open |
| 10 | Low | Root | 7 unnecessary files cluttering directory | Open |

---

## Appendix F: Glossary

**Agent:** Autonomous component with specific responsibility
**Broker:** Interface to trading platform (Alpaca)
**Circuit Breaker:** Risk control that pauses trading after losses
**Event Bus:** Pub/sub communication channel between agents
**FakeBroker:** Simulated broker for testing
**Signal:** Buy/sell/hold recommendation from strategy
**SIM Mode:** Simulation mode using FakeBroker
**Strategy:** Algorithm for generating trading signals

---

## Document Metadata

**Version:** 1.0.0
**Created:** 2026-01-25
**Author:** Claude Code (Anthropic)
**Review Status:** Initial Draft
**Next Review:** TBD

**Related Documents:**
- [ROADMAP.md](ROADMAP.md) - Development plan
- [README.md](README.md) - User guide
- [SIM_MODE_AUTO_SWITCHING_CONTEXT.md](SIM_MODE_AUTO_SWITCHING_CONTEXT.md) - Feature spec
- [CONFIG_ALIGNMENT_NOTES.md](CONFIG_ALIGNMENT_NOTES.md) - Config system notes

**Changelog:**
- 2026-01-25: Initial comprehensive technical report

---

*End of Report*

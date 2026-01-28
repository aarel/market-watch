# Architecture Overview

> Technical architecture of the Market-Watch trading system

## Table of Contents

1. [High-Level Architecture](#high-level-architecture)
2. [Agent-Based System](#agent-based-system)
3. [Component Breakdown](#component-breakdown)
4. [Data Flow](#data-flow)
5. [Event Bus Pattern](#event-bus-pattern)
6. [Strategy Framework](#strategy-framework)
7. [Broker Abstraction](#broker-abstraction)
8. [Backtesting Engine](#backtesting-engine)
9. [Design Decisions](#design-decisions)
10. [Performance Considerations](#performance-considerations)

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Web UI                               │
│                    (static/index.html)                       │
└─────────────────────┬───────────────────────────────────────┘
                      │ REST API / WebSocket
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                      server.py                               │
│                  FastAPI + WebSocket                         │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                    Coordinator                               │
│            (agents/coordinator.py)                           │
└──┬──────────┬──────────┬────────────┬────────────┬─────────┘
   │          │          │            │            │
   │          │          │            │            │
┌──▼───┐  ┌──▼───┐  ┌──▼───┐    ┌──▼───┐    ┌──▼───┐
│ Data │  │Signal│  │ Risk │    │Exec  │    │Monitor│
│Agent │  │Agent │  │Agent │    │Agent │    │Agent  │
└──┬───┘  └──┬───┘  └──┬───┘    └──┬───┘    └──┬───┘
   │         │         │            │            │
   └─────────┴─────────┴────────────┴────────────┘
                      │
                Event Bus
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                  Broker Layer                                │
│         (broker.py / fake_broker.py)                         │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                 Alpaca API                                   │
│           (or simulated broker)                              │
└──────────────────────────────────────────────────────────────┘
```

---

## Agent-Based System

Market-Watch uses an **agent-based architecture** where specialized agents handle specific concerns and communicate via an event bus.

### Why Agent-Based?

**Benefits:**
- **Separation of Concerns:** Each agent has a single, well-defined responsibility
- **Scalability:** Easy to add new agents without modifying existing ones
- **Testability:** Agents can be tested in isolation
- **Flexibility:** Agents can be enabled/disabled independently
- **Loose Coupling:** Agents communicate via events, not direct calls

**Trade-offs:**
- More complex than monolithic design
- Requires understanding of event flow
- Async/await adds cognitive overhead

---

## Component Breakdown

### 1. Coordinator

**File:** `agents/coordinator.py`

**Role:** Orchestrates all agents, manages their lifecycle

**Responsibilities:**
- Initialize all agents with appropriate dependencies
- Start/stop agents in correct order
- Wire up event handlers
- Provide unified interface for server.py
- Handle configuration updates

**Key Methods:**
```python
async def start()  # Start all agents
async def stop()   # Stop all agents gracefully
def set_broadcast_callback()  # Set WebSocket broadcaster
async def manual_trade()  # Execute manual trades
async def refresh_data()  # Trigger data refresh
```

---

### 2. Data Agent

**File:** `agents/data_agent.py`

**Role:** Fetch market data periodically

**Responsibilities:**
- Fetch current prices via Alpaca snapshots
- Fetch historical bars for momentum calculation
- Get account and position data
- Refresh top gainers list (if configured)
- Publish `MarketDataReady` event

**Configuration:**
- `interval_minutes`: How often to fetch data (default: 5)
- `watchlist_mode`: "static" or "top_gainers"

**Event Emissions:**
- `MarketDataReady`: When data is fetched

---

### 3. Signal Agent

**File:** `agents/signal_agent.py`

**Role:** Generate trading signals using a strategy

**Responsibilities:**
- Listen for `MarketDataReady` events
- Convert market data to strategy-friendly format
- Call strategy.analyze() for each symbol
- Publish `SignalGenerated` events for actionable signals
- Publish `SignalsUpdated` event with all signals

**Key Features:**
- **Pluggable Strategies:** Uses Strategy interface
- **Position-Aware:** Passes current position info to strategy
- **Error Handling:** Gracefully handles strategy failures

**Event Subscriptions:**
- `MarketDataReady`

**Event Emissions:**
- `SignalGenerated`: For buy/sell signals
- `SignalsUpdated`: Summary of all signals

---

### 4. Risk Agent

**File:** `agents/risk_agent.py`

**Role:** Validate trades against risk rules

**Responsibilities:**
- Listen for `SignalGenerated` events
- Check if trade violates risk limits
- Publish `RiskCheckPassed` or `RiskCheckFailed`

**Risk Checks:**
- Position size limits (max % of portfolio)
- Daily trade limits
- Sufficient buying power
- Market open check
- Auto-trade enabled check

**Event Subscriptions:**
- `SignalGenerated`

**Event Emissions:**
- `RiskCheckPassed`: Trade approved
- `RiskCheckFailed`: Trade rejected

---

### 5. Execution Agent

**File:** `agents/execution_agent.py`

**Role:** Execute approved trades

**Responsibilities:**
- Listen for `RiskCheckPassed` events
- Calculate position sizes
- Submit orders to broker
- Publish success/failure events

**Position Sizing:**
- Fractional shares supported
- Based on `max_position_pct` config
- Respects available buying power

**Event Subscriptions:**
- `RiskCheckPassed`

**Event Emissions:**
- `OrderExecuted`: Order succeeded
- `OrderFailed`: Order failed

---

### 6. Monitor Agent

**File:** `agents/monitor_agent.py`

**Role:** Monitor positions for stop-loss triggers

**Responsibilities:**
- Periodically check all positions
- Calculate unrealized P&L
- Trigger stop-loss sells when thresholds exceeded
- Publish `StopLossTriggered` events

**Configuration:**
- `check_interval_seconds`: How often to check (default: 120)
- `stop_loss_pct`: Stop loss threshold (from config)

**Event Emissions:**
- `StopLossTriggered`: Position hit stop loss

---

### 7. Alert Agent

**File:** `agents/alert_agent.py`

**Role:** Log events and broadcast to WebSocket clients

**Responsibilities:**
- Subscribe to all events
- Maintain in-memory log
- Broadcast events to WebSocket clients
- Format events for UI consumption

**Event Subscriptions:**
- All events (via wildcard subscription)

---

## Data Flow

### Typical Trading Cycle

```
1. DataAgent.fetch_data()
   └─> Fetches prices, bars, account, positions
   └─> Publishes: MarketDataReady

2. SignalAgent._handle_market_data()
   └─> For each symbol:
       └─> strategy.analyze(symbol, bars, price, position)
       └─> Publishes: SignalGenerated (if buy/sell)
   └─> Publishes: SignalsUpdated (all signals)

3. RiskAgent._handle_signal()
   └─> Validates against risk rules
   └─> Publishes: RiskCheckPassed OR RiskCheckFailed

4. ExecutionAgent._handle_risk_check()
   └─> Calculates position size
   └─> broker.submit_order()
   └─> Publishes: OrderExecuted OR OrderFailed

5. MonitorAgent._check_positions() (periodic)
   └─> Checks P&L on all positions
   └─> If stop-loss triggered:
       └─> Publishes: StopLossTriggered
       └─> Converted to RiskCheckPassed for sell
       └─> Goes to ExecutionAgent

6. AlertAgent (subscribes to all)
   └─> Logs events
   └─> Broadcasts to WebSocket clients
```

---

## Event Bus Pattern

### Event Bus

**File:** `agents/event_bus.py`

**Pattern:** Pub/Sub (Publisher-Subscriber)

**How it Works:**
```python
# Subscription
event_bus.subscribe(MarketDataReady, my_handler)

# Publishing
await event_bus.publish(MarketDataReady(...))

# Unsubscription
event_bus.unsubscribe(MarketDataReady, my_handler)
```

**Benefits:**
- Decouples producers from consumers
- Multiple subscribers per event
- Easy to add new event types
- Async-friendly

**Event Types:**

| Event | Trigger | Subscribers |
|-------|---------|-------------|
| `MarketDataReady` | Data fetched | SignalAgent |
| `SignalGenerated` | Signal created | RiskAgent, AlertAgent |
| `SignalsUpdated` | All signals refreshed | AlertAgent |
| `RiskCheckPassed` | Trade approved | ExecutionAgent |
| `RiskCheckFailed` | Trade rejected | AlertAgent |
| `OrderExecuted` | Trade succeeded | MonitorAgent, AlertAgent |
| `OrderFailed` | Trade failed | AlertAgent |
| `StopLossTriggered` | Stop loss hit | Coordinator (converts to sell) |

---

## Strategy Framework

### Architecture

```
Strategy (ABC)
  ├─ MomentumStrategy
  ├─ MeanReversionStrategy
  ├─ BreakoutStrategy
  └─ RSIStrategy

SignalAgent uses Strategy via composition:
  signal_agent.strategy.analyze(...)
```

### Strategy Interface

**File:** `strategies/base.py`

```python
class Strategy(ABC):
    @property
    @abstractmethod
    def name(self) -> str: pass

    @property
    @abstractmethod
    def required_history(self) -> int: pass

    @abstractmethod
    def analyze(...) -> TradingSignal: pass
```

**Key Design Points:**
- **Stateless:** Strategies don't maintain state
- **Deterministic:** Same inputs → same outputs
- **Position-Aware:** Strategies know if we hold a position
- **Self-Documenting:** name and description properties

### Strategy Selection

1. **Environment Variable:** `STRATEGY=momentum` in .env
2. **Coordinator loads strategy:**
   ```python
   strategy = get_strategy(config.STRATEGY)
   ```
3. **Passes to SignalAgent:**
   ```python
   signal_agent = SignalAgent(event_bus, broker, strategy)
   ```
4. **SignalAgent delegates:**
   ```python
   signal = self.strategy.analyze(...)
   ```

See [STRATEGIES.md](STRATEGIES.md) for strategy documentation.

---

## Broker Abstraction

### Interface

**Files:** `broker.py`, `fake_broker.py`

**Purpose:** Abstract away broker-specific implementation

```
AlpacaBroker (production)
  └─ Uses Alpaca API
  └─ Real market data
  └─ Real order execution

FakeBroker (testing/simulation)
  └─ Simulated prices (random walk)
  └─ In-memory positions
  └─ No API calls
```

### Key Methods

```python
def get_account() -> Account
def get_positions() -> List[Position]
def get_position(symbol) -> Position
def get_bars(symbol, days) -> DataFrame
def get_current_price(symbol) -> float
def submit_order(symbol, qty, side) -> Order
def is_market_open() -> bool
```

### Selection

```python
# config.py
SIMULATION_MODE = os.getenv("SIMULATION_MODE", "false").lower() == "true"

# server.py
if config.SIMULATION_MODE:
    Broker = FakeBroker
else:
    Broker = AlpacaBroker

broker = Broker()
```

---

## Backtesting Engine

### Architecture

```
BacktestEngine
  ├─ HistoricalData (data management)
  ├─ BacktestBroker (simulated broker)
  ├─ Strategy (same as live)
  └─ PerformanceMetrics (results)
```

**Key Insight:** Backtesting uses the **same Strategy classes** as live trading.

### Data Flow

```
1. HistoricalData.download()
   └─> Fetches/caches data from Alpaca

2. BacktestEngine.run()
   └─> For each date:
       ├─> Get bars up to date (no lookahead)
       ├─> strategy.analyze(...)
       ├─> Simulate order execution
       ├─> Track positions and equity
       └─> Record trade

3. BacktestResults
   └─> Calculate metrics
   └─> Generate reports
   └─> Export to CSV/JSON
```

### Preventing Lookahead Bias

```python
# Only returns data available at that date
bars = data.get_bars_up_to(symbol, current_date, lookback_days)

# Order execution simulated at next bar's open
execution_price = next_day_open * (1 + slippage)
```

See [BACKTEST.md](BACKTEST.md) for usage documentation.

---

## Design Decisions

### 1. Agent-Based vs Monolithic

**Decision:** Agent-based

**Rationale:**
- Better separation of concerns
- Easier to extend (add new agents)
- Testable in isolation
- More professional/scalable

**Trade-off:** More complex, harder to understand initially

---

### 2. Event Bus vs Direct Calls

**Decision:** Event bus

**Rationale:**
- Loose coupling
- Easy to add new subscribers
- Events provide natural audit trail
- Aligns with async architecture

**Trade-off:** Harder to trace execution flow

---

### 3. Pluggable Strategies vs Hardcoded

**Decision:** Pluggable via Strategy interface

**Rationale:**
- Users can add custom strategies
- Easy to test strategies independently
- Backtest engine reuses same strategies
- Clean abstraction

**Trade-off:** More files, slightly more complex

---

### 4. In-Memory Config vs Database

**Decision:** In-memory with environment variable defaults

**Rationale:**
- Simpler for single-user deployment
- Fast reads (no DB queries)
- Config as code via .env

**Trade-off:** Changes lost on restart, no multi-user support

**Future:** Add database option (Phase 8)

---

### 5. FastAPI vs Flask

**Decision:** FastAPI

**Rationale:**
- Native async support (aligns with agent system)
- Built-in WebSocket support
- Automatic API documentation (Swagger)
- Type hints and validation
- Better performance

---

### 6. Pandas vs NumPy for Historical Data

**Decision:** Pandas

**Rationale:**
- Strategy interface uses DataFrames
- Easier time series operations
- Built-in resampling, rolling windows
- Better for financial data

**Trade-off:** Higher memory usage than pure NumPy

---

## Performance Considerations

### Memory Usage

**Current:**
- Historical data cached in DataFrames
- In-memory logs (limited to 1000 entries)
- No database (all state in RAM)

**Typical:** ~100MB for 5 symbols with 20-day history

**Scaling:**
- For 100+ symbols: Consider database for historical data
- For high-frequency: Use streaming instead of batch fetching

---

### Latency

**Trade Execution Path:**

| Step | Latency |
|------|---------|
| Market data fetch | 200-500ms (Alpaca API) |
| Signal generation | <10ms |
| Risk validation | <1ms |
| Order submission | 100-300ms (Alpaca API) |
| **Total** | **~300-800ms** |

**Bottlenecks:**
- Alpaca API calls (network bound)
- Not CPU or memory bound

---

### Concurrency

**Current Model:** Single-threaded async/await

**Why:**
- Python GIL makes threading inefficient for this workload
- Async/await perfect for I/O-bound operations (API calls)
- Simpler reasoning about state

**Future:** Could parallelize signal generation across symbols with ProcessPoolExecutor

---

### Caching

**What's Cached:**
- Historical data (in `data/historical/`)
- Asset names (in-memory)
- Top gainers list (refreshed on data fetch)

**What's Not Cached:**
- Current prices (always fresh)
- Account data (always fresh)
- Signals (regenerated each cycle)

---

## Technology Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| Web Framework | FastAPI | Async, WebSocket, auto-docs |
| Broker API | alpaca-trade-api | Official Alpaca client |
| Data Analysis | pandas, numpy | Standard for financial data |
| Async Runtime | asyncio | Built into Python |
| WebSocket | FastAPI WebSocket | Built-in support |
| HTTP Client | requests | For API calls in sync contexts |
| Configuration | python-dotenv | .env file support |

---

## File Structure

```
market-watch/
├── server.py              # Main entry point
├── config.py              # Configuration
├── broker.py              # Alpaca broker
├── fake_broker.py         # Simulated broker
├── screener.py            # Top gainers logic
├── universe.py            # Stock universe definitions
├── agents/
│   ├── __init__.py
│   ├── base.py            # BaseAgent
│   ├── coordinator.py     # Coordinator
│   ├── event_bus.py       # Event bus
│   ├── events.py          # Event definitions
│   ├── data_agent.py
│   ├── signal_agent.py
│   ├── risk_agent.py
│   ├── execution_agent.py
│   ├── monitor_agent.py
│   └── alert_agent.py
├── strategies/
│   ├── __init__.py
│   ├── base.py            # Strategy interface
│   ├── momentum.py
│   ├── mean_reversion.py
│   ├── breakout.py
│   └── rsi.py
├── backtest/
│   ├── __init__.py
│   ├── data.py            # Historical data
│   ├── engine.py          # Backtest engine
│   ├── metrics.py         # Performance metrics
│   ├── results.py         # Results formatting
│   └── cli.py             # CLI interface
├── static/
│   └── index.html         # Web UI
└── data/
    └── historical/        # Cached data
```

---

## Extension Points

Want to extend Market-Watch? These are the clean extension points:

### Add a New Strategy
1. Create `strategies/my_strategy.py`
2. Inherit from `Strategy`
3. Implement required methods
4. Register in `strategies/__init__.py`

### Add a New Agent
1. Create `agents/my_agent.py`
2. Inherit from `BaseAgent`
3. Subscribe to relevant events
4. Add to `Coordinator.__init__()`

### Add a New Event Type
1. Define in `agents/events.py`
2. Publish from appropriate agent
3. Subscribe in consuming agents

### Add a New Broker
1. Create `my_broker.py`
2. Implement same interface as `AlpacaBroker`
3. Update broker selection in `server.py`

### Add a New Risk Check
1. Modify `RiskAgent._validate_trade()`
2. Add new validation logic
3. Update rejection reasons

---

## Testing Strategy

### Unit Tests
- Test strategies with known price data
- Test metric calculations
- Test event bus subscriptions

### Integration Tests
- Test agent communication via events
- Test full trade cycle in simulation mode
- Test backtest accuracy

### System Tests
- Run with FakeBroker for hours
- Verify no memory leaks
- Check error handling

See [CONTRIBUTING.md](CONTRIBUTING.md) for testing guidelines.

---

## Security Considerations

### API Keys
- Never commit `.env` to git
- Use paper trading by default
- Require explicit `TRADING_MODE=live`

### WebSocket
- Consider authentication for production
- Rate limit messages
- Validate all incoming data

### Risk Controls
- Hard-coded max position size
- Daily trade limits
- Stop-loss enforcement
- Market hours check

---

## Future Architecture Improvements

From [ROADMAP.md](../ROADMAP.md):

1. **Database Layer** (Phase 8)
   - Persist configuration
   - Store trade history
   - Track performance over time

2. **Multi-Broker Support** (Phase 6)
   - Abstract broker interface
   - Support IB, TD Ameritrade
   - Broker comparison

3. **Enhanced Risk Management** (Phase 3 – completed)
   - Portfolio-level limits (max position, sector, correlated exposure)
   - Circuit breakers (daily loss, drawdown)
   - Implemented in `risk/` and enforced by `RiskAgent`

4. **Strategy Ensemble** (Future)
   - Run multiple strategies
   - Weighted signal combination
   - Strategy selection via ML

---

*Last updated: 2026-01-22*

# Market-Watch Evolution Roadmap

> A living document outlining the transformation of Market-Watch from a functional trading bot into a professional-grade algorithmic trading platform.

**Document Status:** Active Development
**Last Updated:** 2026-01-26
**Current Phase:** Phase 11 - Testing & CI/CD (In Progress)

**Related Documents:**
- **[TECHNICAL_REPORT.md](TECHNICAL_REPORT.md)** - Comprehensive technical analysis (architecture, code review, testing, security, performance)
- **[README.md](README.md)** - User guide and quick start
- **[SIM_MODE_AUTO_SWITCHING_CONTEXT.md](SIM_MODE_AUTO_SWITCHING_CONTEXT.md)** - Feature specification for auto-switching SIM mode
- **[CONFIG_ALIGNMENT_NOTES.md](CONFIG_ALIGNMENT_NOTES.md)** - Configuration system changes and notes

---

## Table of Contents

1. [Vision & Goals](#vision--goals)
2. [Target Audiences](#target-audiences)
3. [Current State Assessment](#current-state-assessment)
4. [Phase 1: Backtesting Engine](#phase-1-backtesting-engine) ✅ **COMPLETE**
5. [Phase 2: Strategy Framework](#phase-2-strategy-framework) ✅ **COMPLETE**
6. [Phase 3: Risk Management](#phase-3-risk-management)
7. [Phase 4: Analytics & Reporting](#phase-4-analytics--reporting)
8. [Phase 5: Enhanced Paper Trading](#phase-5-enhanced-paper-trading)
9. [Phase 6: Multi-Broker Support](#phase-6-multi-broker-support)
10. [Phase 7: Alerts & Notifications](#phase-7-alerts--notifications)
11. [Phase 8: Configuration Management](#phase-8-configuration-management)
12. [Phase 9: Market Awareness](#phase-9-market-awareness)
13. [Phase 10: Documentation & Onboarding](#phase-10-documentation--onboarding)
14. [Phase 11: Testing & Reliability](#phase-11-testing--reliability)
15. [Phase 12: Track Record Verification](#phase-12-track-record-verification)
16. [Technical Debt & Maintenance](#technical-debt--maintenance)
17. [Success Metrics](#success-metrics)

---

## Vision & Goals

### The Problem

Most retail algorithmic trading tools fall into two categories:

1. **Expensive platforms** ($100+/month) with steep learning curves
2. **Toy projects** that look good in demos but lack the rigor for real money

Market-Watch aims to occupy the middle ground: **a serious tool that's accessible to individuals**.

### The Vision

Transform Market-Watch into a platform where:

- **Strategies can be validated** before risking capital
- **Risk is managed systematically**, not through hope
- **Performance is measurable** and comparable to benchmarks
- **The learning curve is gentle** but the ceiling is high
- **Trust is verifiable**, not claimed

### Core Principles

1. **Prove before you trade** - No strategy goes live without backtested evidence
2. **Transparency over mystery** - Every decision the bot makes should be explainable
3. **Safety by default** - Conservative defaults, require explicit opt-in for aggressive settings
4. **Data ownership** - Users own their data, can export everything, no lock-in
5. **Honest metrics** - Report realistic performance, including costs and slippage

---

## Target Audiences

### Investors

**Who they are:** Individuals or funds evaluating algorithmic strategies for capital allocation.

**What they need:**
- Verifiable track records with auditable trade history
- Professional risk metrics (Sharpe, Sortino, max drawdown, VaR)
- Clear documentation of strategy logic and edge
- Stress test results across market regimes
- Regulatory compliance considerations

**What convinces them:**
- Multi-year backtest with out-of-sample validation
- Live track record matching backtest expectations
- Transparent fee and cost accounting
- Professional presentation and reporting

### Active Traders

**Who they are:** Individuals who trade their own capital and want automation.

**What they need:**
- Reliable execution without babysitting
- Customizable strategies matching their trading style
- Real-time monitoring and alerts
- Detailed trade analytics for improvement
- Multiple broker support for best execution

**What convinces them:**
- Stability and uptime track record
- Flexibility to implement their ideas
- Clear performance attribution
- Active development and support

### Hobbyists & Learners

**Who they are:** People interested in algorithmic trading as a skill or interest.

**What they need:**
- Low barrier to entry (easy setup, free tier)
- Educational content explaining concepts
- Safe environment to experiment (paper trading)
- Visible feedback on what's happening and why
- Community and documentation

**What convinces them:**
- "It just works" first experience
- Learning something new within the first hour
- Fun factor - seeing strategies compete
- Clear path from beginner to advanced

---

## Current State Assessment

### What Works Well

| Component | Status | Notes |
|-----------|--------|-------|
| Alpaca Integration | ✅ Solid | Orders, positions, market data all functional |
| Paper Trading | ✅ Functional | Uses real market data with simulated execution |
| Live Trading | ✅ Functional | Requires explicit opt-in, safety measures in place |
| Web UI | ✅ Basic | Real-time updates, manual trading, config changes |
| Strategy Framework | ✅ Working | 4 pluggable strategies (momentum, mean reversion, breakout, RSI) |
| Risk Controls | ✅ Complete | Position sizing, circuit breakers, sector/correlation exposure |
| Backtesting | ✅ Working | Engine, historical data, metrics, CLI exports |
| Testing Suite | ✅ Unit tests | Unit tests complete (backtest, strategies, metrics, API); integration pending |
| Observability | ✅ Basic | Structured logs, scheduled evaluations, UI summary |
| Simulation Mode | ✅ Limited | FakeBroker for testing without API credentials |
| Config Persistence | ✅ Basic | Runtime changes persisted to JSON file on save. |

### What's Missing

| Capability | Impact | Priority |
|------------|--------|----------|
| Advanced Analytics | High - Deeper P&L, attribution, and position analysis needed | Phase 4 |
| Integration/System Testing & CI | High - Essential for production reliability | Phase 11 |
| Advanced Configuration | Medium - No profiles, versioning, or advanced UI | Phase 8 |
| Alerts & Notifications | Medium - No external notifications (email, SMS, etc.) | Phase 7 |
| Multi-Broker | Medium - Alpaca lock-in | Phase 6 |
| Documentation & Onboarding Polish| Medium - Core docs updated, but needs user guides/tutorials | Phase 10 |

### Technical Debt

> **Detailed Analysis:** See [TECHNICAL_REPORT.md Section 7](TECHNICAL_REPORT.md#7-technical-debt) for comprehensive code-level debt analysis.

**Quick Summary:**
- ✅ Configuration split documented and aligned (`.env` and `config_state.json`)
- ⚠️ Root directory cluttered with 7+ obsolete files (cleanup plan in TECHNICAL_REPORT)
- ⚠️ No schema validation for config JSON (can crash silently)
- ⚠️ Broker cannot switch at runtime (blocks SIM auto-switching)
- ⚠️ Monolithic UI file (3,600 lines in single HTML file)
- ⚠️ Bare except clauses in 3 locations (swallow errors)
- ⚠️ Analytics UI broken (metrics show "--", charts don't render)
- ⚠️ No integration tests (182 unit tests, 0 end-to-end tests)
- ✅ Logging mostly standardized (event-driven model)
- ⚠️ Type hinting partial (newer code has, older code lacks)

**30+ specific issues tracked** with severity levels, line numbers, and fixes in TECHNICAL_REPORT.md Section 7 and Appendix E.

---

## Phase 1: Backtesting Engine

> **Status:** ✅ COMPLETE
> **Priority:** Critical
> **Completed:** 2025-01-19

### Why This First

Backtesting is foundational. Without it:
- Cannot validate strategy changes before deployment
- Cannot compare parameter configurations objectively
- Cannot provide investors with historical performance data
- Cannot stress-test against historical market conditions
- Users are essentially gambling, not trading systematically

### Requirements

#### Functional Requirements

1. **Historical Data Management**
   - Download historical OHLCV data from Alpaca API
   - Cache data locally to avoid repeated API calls
   - Support date range selection (start date, end date)
   - Handle data gaps, splits, and adjustments
   - Support multiple symbols simultaneously
   - Data format: Daily bars minimum, intraday optional

2. **Backtest Engine**
   - Event-driven simulation iterating through historical bars
   - Simulate order execution with configurable fill assumptions
   - Track positions, cash, and portfolio value over time
   - Support the existing MomentumStrategy (and future strategies)
   - Generate trade log with entry/exit prices, P&L per trade
   - Calculate equity curve (portfolio value at each time step)

3. **Performance Metrics**
   - Total return (absolute and percentage)
   - Annualized return
   - Sharpe ratio (risk-adjusted return)
   - Sortino ratio (downside risk-adjusted)
   - Maximum drawdown (peak-to-trough decline)
   - Maximum drawdown duration
   - Win rate (percentage of profitable trades)
   - Profit factor (gross profit / gross loss)
   - Average win vs average loss
   - Number of trades
   - Exposure time (percentage of time in market)

4. **Benchmark Comparison**
   - Compare strategy performance against buy-and-hold
   - Compare against SPY or user-specified benchmark
   - Calculate alpha and beta
   - Information ratio

5. **Results Output**
   - Summary statistics printout
   - Trade-by-trade log (CSV export)
   - Equity curve data (CSV export)
   - JSON format for programmatic access

#### Non-Functional Requirements

1. **Performance**
   - Backtest 5 years of daily data for 10 symbols in under 30 seconds
   - Memory efficient - don't load entire history into RAM if avoidable

2. **Accuracy**
   - Use close prices for signal calculation (matching live behavior)
   - Use next-day open for execution simulation (realistic fill)
   - Account for the fact that you can't trade on today's close after seeing it

3. **Usability**
   - Command-line interface for running backtests
   - Clear progress indication for long backtests
   - Helpful error messages for common issues (missing data, invalid dates)

### Architecture

```
backtest/
├── __init__.py
├── data.py           # Historical data fetching and caching
├── engine.py         # Core backtest simulation engine
├── metrics.py        # Performance metric calculations
├── results.py        # Results formatting and export
└── cli.py            # Command-line interface

# Data flow:
1. User specifies: strategy, symbols, date range, initial capital
2. data.py fetches/loads historical OHLCV data
3. engine.py iterates through each bar chronologically
4. Strategy generates signals based on available data (no lookahead)
5. engine.py simulates order execution
6. metrics.py calculates performance statistics
7. results.py formats and exports results
```

### Data Storage

```
data/
└── historical/
    ├── AAPL_daily.csv
    ├── GOOGL_daily.csv
    ├── SPY_daily.csv
    └── ...

# CSV Format:
timestamp,open,high,low,close,volume
2023-01-03,125.07,130.90,124.17,130.15,112117500
2023-01-04,126.89,128.66,125.08,126.36,89113600
...
```

### API Design

```python
# Running a backtest programmatically
from backtest import BacktestEngine, HistoricalData

# Load data
data = HistoricalData()
data.load(
    symbols=['AAPL', 'GOOGL', 'MSFT'],
    start='2021-01-01',
    end='2023-12-31'
)

# Run backtest (momentum strategy is built-in)
engine = BacktestEngine(
    data=data,
    initial_capital=100000,
    commission=0.00,  # Alpaca is commission-free
    slippage=0.001    # 0.1% slippage assumption
)

# Configure strategy parameters
engine.set_strategy_params(
    lookback_days=20,
    momentum_threshold=0.02,
    sell_threshold=-0.01
)

results = engine.run()

# Access results
print(results.summary())
print(f"Total Return: {results.total_return:.2%}")
print(f"Sharpe Ratio: {results.sharpe_ratio:.2f}")
print(f"Max Drawdown: {results.max_drawdown:.2%}")

# Export
results.to_csv('backtest_results.csv')
results.trades_to_csv('trade_log.csv')
```

### Command-Line Interface

```bash
# Basic backtest
python -m backtest --symbols AAPL,GOOGL,MSFT --start 2021-01-01 --end 2023-12-31

# With custom parameters
python -m backtest \
  --symbols AAPL,GOOGL,MSFT,NVDA,TSLA \
  --start 2020-01-01 \
  --end 2023-12-31 \
  --capital 100000 \
  --momentum-threshold 0.03 \
  --lookback 15 \
  --output results/my_backtest.json

# Download/update historical data
python -m backtest --download --symbols AAPL,GOOGL,MSFT --start 2020-01-01

# Compare against benchmark
python -m backtest --symbols AAPL,GOOGL --benchmark SPY --start 2021-01-01
```

### Metrics Calculations

```python
# Sharpe Ratio
# (Average Return - Risk Free Rate) / Standard Deviation of Returns
sharpe = (avg_daily_return - risk_free_rate) / std_daily_return * sqrt(252)

# Sortino Ratio
# Like Sharpe but only penalizes downside volatility
sortino = (avg_daily_return - risk_free_rate) / downside_deviation * sqrt(252)

# Maximum Drawdown
# Largest peak-to-trough decline in portfolio value
max_drawdown = max((peak - trough) / peak for peak, trough in drawdown_periods)

# Profit Factor
# Gross profits divided by gross losses
profit_factor = sum(winning_trades) / abs(sum(losing_trades))

# Win Rate
win_rate = num_profitable_trades / total_trades
```

### Edge Cases to Handle

1. **Insufficient data** - Strategy needs N days of history; first N days can't generate signals
2. **Missing bars** - Market holidays, halted stocks; forward-fill or skip
3. **Position sizing** - Can't buy fractional shares in backtest if not supported
4. **Cash management** - Handle case where signal fires but insufficient cash
5. **Same-day trades** - If multiple signals on same day, process in deterministic order
6. **Dividends/splits** - Use adjusted close prices or handle explicitly

### Testing the Backtest Engine

1. **Known outcome test** - Create synthetic data with predictable pattern, verify backtest produces expected result
2. **Boundary tests** - Single day, single symbol, no trades generated
3. **Benchmark test** - Buy-and-hold backtest should match actual historical return
4. **Reproducibility** - Same inputs always produce same outputs

### Deliverables

- [x] `backtest/data.py` - Historical data management
- [x] `backtest/engine.py` - Core simulation engine
- [x] `backtest/metrics.py` - Performance calculations
- [x] `backtest/results.py` - Results formatting and export
- [x] `backtest/cli.py` - Command-line interface
- [x] `backtest/__init__.py` - Package exports
- [x] `backtest/__main__.py` - Module entry point
- [x] `data/historical/` directory structure for cached data
- [x] Unit tests for metric calculations (completed in Phase 11)
- [ ] Integration test with real historical data (deferred to Phase 11)
- [x] Documentation - See [docs/BACKTEST.md](docs/BACKTEST.md)

### Phase 1 Documentation ✅

Documentation created at `docs/BACKTEST.md` covering:
- Purpose and capabilities
- Architecture and design decisions
- API reference (HistoricalData, BacktestEngine, BacktestResults)
- CLI usage guide with examples
- Example workflows
- Interpretation of all metrics
- Limitations and assumptions
- Troubleshooting guide

---

## Phase 2: Strategy Framework

> **Status:** ✅ COMPLETE
> **Priority:** High
> **Completed:** 2025-01-19

### Goals

- Abstract strategy interface allowing pluggable strategies
- Ship 2-3 built-in strategies beyond momentum
- Enable users to create custom strategies easily
- Support strategy parameter configuration

### Proposed Strategy Interface

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional
from enum import Enum

class Signal(Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"

@dataclass
class TradeSignal:
    symbol: str
    signal: Signal
    strength: float  # 0.0 to 1.0, for position sizing
    reason: str      # Human-readable explanation

class Strategy(ABC):
    """Base class for all trading strategies."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Strategy name for display and logging."""
        pass

    @property
    @abstractmethod
    def required_history(self) -> int:
        """Number of historical bars needed to generate signals."""
        pass

    @abstractmethod
    def analyze(self, symbol: str, bars: pd.DataFrame) -> TradeSignal:
        """
        Analyze a symbol and return a trading signal.

        Args:
            symbol: The ticker symbol
            bars: DataFrame with OHLCV data, most recent bar last

        Returns:
            TradeSignal with recommendation
        """
        pass

    def configure(self, **params):
        """Update strategy parameters."""
        for key, value in params.items():
            if hasattr(self, key):
                setattr(self, key, value)
```

### Built-in Strategies to Implement

1. **MomentumStrategy** (extract from SignalAgent into new interface)
   - Buy when price momentum exceeds threshold
   - Sell when momentum reverses
   - Currently implemented in `agents/signal_agent.py`

2. **MeanReversionStrategy**
   - Buy when price deviates below moving average
   - Sell when price returns to or exceeds average
   - Parameters: MA period, deviation threshold

3. **BreakoutStrategy**
   - Buy when price breaks above N-day high
   - Sell when price breaks below N-day low
   - Parameters: lookback period, confirmation bars

4. **RSIStrategy**
   - Buy when RSI crosses above oversold threshold
   - Sell when RSI crosses below overbought threshold
   - Parameters: RSI period, oversold level, overbought level

### Custom Strategy Loading

```python
# User creates strategies/my_strategy.py
class MyCustomStrategy(Strategy):
    name = "My Custom Strategy"
    required_history = 30

    def analyze(self, symbol, bars):
        # Custom logic here
        pass

# System auto-discovers strategies in strategies/ directory
```

### Deliverables

- [x] Abstract `Strategy` base class - `strategies/base.py`
- [x] Extract momentum logic from `SignalAgent` into `MomentumStrategy` class
- [x] Implement `MeanReversionStrategy` - MA-based mean reversion
- [x] Implement `BreakoutStrategy` - Channel breakout system
- [x] Implement `RSIStrategy` - RSI overbought/oversold signals
- [x] Strategy registry in `strategies/__init__.py` with `get_strategy()` function
- [x] Strategy selection via `STRATEGY` environment variable
- [x] SignalAgent refactored to use pluggable strategies
- [x] Coordinator updated to load strategy from config
- [x] Documentation - See [docs/STRATEGIES.md](docs/STRATEGIES.md)

### What Was Built

**Strategy Framework:**
- 4 complete trading strategies (Momentum, Mean Reversion, Breakout, RSI)
- Clean abstraction with `Strategy` base class
- Registry system for easy strategy instantiation
- Full integration with SignalAgent and server.py

**Configuration:**
- `STRATEGY` environment variable for strategy selection
- Backward compatible with existing config parameters
- Fallback to momentum strategy if invalid strategy specified

**Documentation:**
- Comprehensive strategy guide with examples
- Custom strategy creation tutorial
- Strategy selection guidelines
- Performance comparison table

---

## Phase 3: Risk Management

> **Status:** ✅ Complete
> **Priority:** High
> **Dependencies:** Phase 2 (risk rules need to interact with strategies)

### Goals

- Systematic position sizing based on risk, not arbitrary amounts
- Portfolio-level risk limits
- Automatic risk controls that can pause trading
- Configurable risk parameters

### Risk Components

#### Position Sizing

```python
class PositionSizer:
    """Calculate position sizes based on risk parameters."""

    def calculate_size(
        self,
        symbol: str,
        signal_strength: float,
        current_price: float,
        account_value: float,
        current_positions: dict
    ) -> int:
        """
        Returns number of shares to buy.

        Considers:
        - Maximum position size (% of portfolio)
        - Available cash
        - Signal strength (scale position by confidence)
        - Volatility adjustment (smaller positions in volatile stocks)
        - Existing exposure to correlated assets
        """
        pass
```

#### Risk Limits

| Limit | Description | Default |
|-------|-------------|---------|
| Max Position Size | Maximum % of portfolio in single position | 10% |
| Max Sector Exposure | Maximum % of portfolio in single sector | 30% |
| Max Correlated Exposure | Maximum % in highly correlated assets | 40% |
| Daily Loss Limit | Stop trading if daily loss exceeds | 3% |
| Max Drawdown Limit | Pause trading if drawdown exceeds | 15% |
| Max Open Positions | Maximum number of concurrent positions | 10 |

#### Circuit Breakers

```python
class CircuitBreaker:
    """Automatic trading halts based on risk conditions."""

    def check(self, portfolio_state: PortfolioState) -> Tuple[bool, str]:
        """
        Returns (should_halt, reason) tuple.

        Triggers:
        - Daily loss limit hit
        - Max drawdown exceeded
        - Unusual market volatility (VIX spike)
        - Technical issues (API errors, data gaps)
        """
        pass
```

### Deliverables

- [x] `PositionSizer` class with configurable rules
- [x] Risk limit enforcement in order execution (max open positions)
- [x] Sector exposure checks (configurable map + limit)
- [x] Correlation exposure checks (threshold + lookback)
- [x] `CircuitBreaker` class with configurable triggers
- [x] Risk controls surfaced & editable in UI (open positions, drawdown, daily loss)
- [x] Runtime config persistence (reload on restart)
- [x] Risk metrics in backtest results
- [x] Documentation refresh for current parameters

---

## Phase 4: Analytics & Reporting

> **Status:** 75% Complete (equity curve works, metrics display broken, charts need fixes)
> **Priority:** High
> **Dependencies:** Phase 1 (uses same metrics calculations)
> **Last Updated:** 2026-01-25
> **Known Issues:** See [TECHNICAL_REPORT.md Section 7.2](TECHNICAL_REPORT.md#72-analytics-issues) for detailed analysis of UI bugs and data issues

### Goals

- Comprehensive performance dashboard
- Trade-by-trade analysis
- Benchmark comparisons
- Exportable reports for external analysis

### Dashboard Components

#### Equity Curve Chart
- Portfolio value over time
- Benchmark overlay
- Drawdown visualization
- Markers for significant events (trades, circuit breaker triggers)

#### Performance Summary
- Period returns (daily, weekly, monthly, yearly, all-time)
- Risk metrics (Sharpe, Sortino, max drawdown)
- Win/loss statistics
- Comparison vs benchmarks

#### Trade Analysis
- Recent trades table with P&L
- Best and worst trades
- Trade duration analysis
- Entry/exit timing analysis

#### Position Analysis
- Current positions with unrealized P&L
- Position concentration chart
- Sector/correlation exposure

### Report Generation

```bash
# Generate PDF report
python -m reports generate --period 2023-Q4 --format pdf

# Generate investor-ready report
python -m reports investor --period 2023 --format pdf --include-methodology
```

### Deliverables

- [x] Equity curve visualization (with benchmark overlay) ✅
- [x] API endpoints for analytics data ✅
- [x] Data export (CSV, JSON; equity/trades) ✅
- [x] AnalyticsAgent recording equity snapshots and trades ✅
- [x] Analytics store (JSONL persistence) ✅
- [x] Performance summary metrics display (cards now parse summary + trades) ✅
- [x] Trade analysis views (table & P&L now populated by AnalyticsAgent) ✅
- [x] Position concentration chart (data serialization + chart update) ✅
- [ ] Report generation (PDF, HTML) - Deferred (pending automation)

### Known Issues (2026-01-25)

1. **Reporting output still pending**
   - HTML/PDF exports exist as lightweight template but need formatting + scheduling
   - **Action:** Build report generation workflow (PDF snapshot, HTML templated output)

---

## Phase 5: Enhanced Paper Trading

> **Status:** Planned
> **Priority:** Medium
> **Dependencies:** Phase 4 (uses analytics components)

### Goals

- Transform paper trading from "testing" to "learning"
- Annotated trade decisions
- What-if analysis
- Multi-configuration comparison

### Features

#### Annotated Trade Log

Every trade includes:
- Signal that triggered it
- Strategy reasoning ("Momentum crossed 2.3%, above 2.0% threshold")
- Market context at time of trade
- Subsequent performance

#### What-If Analysis

After paper trading period:
- "If you'd held 2 more days, you'd have made $X more/less"
- "If stop loss was 3% instead of 5%, you'd have..."
- Parameter sensitivity analysis

#### A/B Testing

Run multiple configurations simultaneously:
- Same strategy, different parameters
- Different strategies, same symbols
- Compare performance side-by-side

### Deliverables

- [ ] Enhanced trade logging with context
- [ ] What-if analysis engine
- [ ] A/B testing framework
- [ ] Comparison dashboard
- [ ] Paper trading insights report

---

## Phase 6: Multi-Broker Support

> **Status:** Planned
> **Priority:** Medium
> **Dependencies:** Phase 2 (broker abstraction needs strategy interface)

### Goals

- Abstract broker interface
- Support multiple brokers
- Enable broker comparison

### Broker Interface

```python
class Broker(ABC):
    """Abstract broker interface."""

    @abstractmethod
    def get_account(self) -> Account:
        """Get account information."""
        pass

    @abstractmethod
    def get_positions(self) -> List[Position]:
        """Get current positions."""
        pass

    @abstractmethod
    def get_bars(self, symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
        """Get historical price bars."""
        pass

    @abstractmethod
    def get_current_price(self, symbol: str) -> float:
        """Get current price."""
        pass

    @abstractmethod
    def submit_order(self, order: Order) -> OrderResult:
        """Submit an order."""
        pass

    @abstractmethod
    def is_market_open(self) -> bool:
        """Check if market is open."""
        pass
```

### Brokers to Support

1. **Alpaca** (existing) - Commission-free, good API
2. **Interactive Brokers** - Professional-grade, global markets
3. **TD Ameritrade** - Popular retail broker
4. **Coinbase/Binance** - Cryptocurrency support

### Deliverables

- [ ] Abstract `Broker` interface
- [ ] Refactor `AlpacaBroker` to interface
- [ ] Interactive Brokers implementation
- [ ] Broker selection in configuration
- [ ] Broker capability comparison documentation

---

## Phase 7: Alerts & Notifications

> **Status:** Planned
> **Priority:** Medium
> **Dependencies:** Phase 3 (risk alerts need risk management)

### Goals

- Timely notifications for important events
- Multiple delivery channels
- Configurable alert rules

### Alert Types

| Alert | Trigger | Default |
|-------|---------|---------|
| Trade Executed | Order filled | On |
| Signal Generated | Strategy produces buy/sell signal | Off |
| Risk Warning | Approaching risk limits | On |
| Circuit Breaker | Trading halted | On |
| Daily Summary | End of trading day | On |
| Error | System error or API issue | On |
| Performance Milestone | New high or significant drawdown | On |

### Delivery Channels

1. **Email** - Daily summaries, important alerts
2. **SMS** - Critical alerts only
3. **Telegram** - Real-time updates
4. **Discord** - Webhook integration
5. **Web Push** - Browser notifications

### Deliverables

- [ ] Alert definition framework
- [ ] Email integration
- [ ] Telegram bot integration
- [ ] Discord webhook integration
- [ ] Alert configuration UI
- [ ] Alert history log

---

## Phase 8: Configuration Management

> **Status:** Planned
> **Priority:** Medium
> **Dependencies:** None
> **Current System:** See [TECHNICAL_REPORT.md Section 4](TECHNICAL_REPORT.md#4-configuration-management) for analysis of existing .env + config_state.json system

### Goals

- Persistent configuration storage
- Named configuration profiles
- Version history
- Import/export

### Features

#### Persistent Storage

Move from in-memory to database:
- SQLite for single-user deployments
- PostgreSQL option for multi-user

#### Configuration Profiles

```bash
# Save current config as profile
python bot.py --save-profile aggressive

# Load a profile
python bot.py --profile conservative

# List profiles
python bot.py --list-profiles
```

#### Version History

- Track configuration changes over time
- Revert to previous configurations
- Annotate why changes were made

### Deliverables

- [ ] Database schema for configuration
- [ ] Profile management (create, load, delete)
- [ ] Version history with rollback
- [ ] Import/export (JSON, YAML)
- [ ] Configuration UI improvements

---

## Phase 9: Market Awareness

> **Status:** Planned
> **Priority:** Medium
> **Dependencies:** Phase 7 (uses notification system)

### Goals

- Understand market rhythms and events
- Avoid trading during dangerous periods
- Integrate economic calendar

### Features

#### Trading Windows

- Configurable trading hours (avoid open/close volatility)
- Respect market holidays
- Handle early closes

#### Economic Calendar

- Integrate economic event calendar
- Pause trading around FOMC announcements
- Alert before major events

#### Earnings Awareness

- Track earnings dates for watchlist
- Option to avoid trading around earnings
- Post-earnings volatility detection

### Deliverables

- [ ] Trading window configuration
- [ ] Market holiday calendar
- [ ] Economic calendar integration
- [ ] Earnings calendar integration
- [ ] Pre-event alerts
- [ ] Documentation of market awareness features

---

## Phase 10: Documentation & Onboarding

> **Status:** Planned
> **Priority:** Medium
> **Dependencies:** All features should be documented as built
> **Detailed Analysis:** See [TECHNICAL_REPORT.md Section 10](TECHNICAL_REPORT.md#10-documentation-review) for current documentation state and gaps

### Goals

- New user can go from zero to paper trading in 10 minutes
- All features documented with examples
- Architecture explained for contributors

### Documentation Structure

```
docs/
├── getting-started/
│   ├── installation.md
│   ├── quick-start.md
│   ├── first-backtest.md
│   └── first-paper-trade.md
├── user-guide/
│   ├── strategies.md
│   ├── backtesting.md
│   ├── paper-trading.md
│   ├── live-trading.md
│   ├── risk-management.md
│   └── analytics.md
├── reference/
│   ├── configuration.md
│   ├── api.md
│   ├── cli.md
│   └── metrics.md
├── development/
│   ├── architecture.md
│   ├── contributing.md
│   └── creating-strategies.md
└── concepts/
    ├── momentum-trading.md
    ├── risk-metrics.md
    └── backtesting-pitfalls.md
```

### Deliverables

- [ ] Quick start guide
- [ ] User guide for each feature
- [ ] API reference
- [ ] CLI reference
- [ ] Strategy development guide
- [ ] Architecture documentation
- [ ] Video walkthrough (optional)

---

## Phase 11: Testing & Reliability

> **Status:** ✅ In Progress (Unit Test Suite Complete)
> **Priority:** High
> **Dependencies:** Should be ongoing throughout development
> **Detailed Analysis:** See [TECHNICAL_REPORT.md Section 5](TECHNICAL_REPORT.md#5-testing-infrastructure) for complete test analysis

### Goals

- ✅ Comprehensive test coverage (unit tests)
- [ ] Integration test coverage (end-to-end flows)
- [ ] Automated CI/CD pipeline
- [x] System monitoring and health checks (health endpoint + observability)
- ✅ Graceful error handling (mostly)

### Testing Strategy

#### Unit Tests ✅ COMPLETE

**Current State:** 182 tests, 100% pass rate, ~0.3s execution time

**Coverage by Module:** (See TECHNICAL_REPORT.md Appendix B for complete map)
- Analytics: 51 tests (equity metrics, trade outcomes, JSONL persistence)
- Backtesting: 33 tests (data, engine, metrics, results export)
- Strategies: 45 tests (momentum, mean reversion, breakout, RSI)
- Risk Management: 13 tests (circuit breaker, position sizing, exposure limits)
- API Endpoints: 19 tests (health, observability, security, config)
- Other: 13 tests (agents, screener, config persistence)

**Strengths:**
- Fast execution (0.3 seconds total)
- Isolated tests (no dependencies)
- Clear naming conventions
- Good documentation

**Test Quality:** See TECHNICAL_REPORT.md Section 5.3 for detailed quality analysis

#### Integration Tests ❌ MISSING

**Gap Analysis:**
- Cannot verify full trade flow (data → signal → risk → execution → analytics)
- Cannot test multi-agent coordination
- Cannot test error recovery scenarios
- Cannot test WebSocket message flow

**Required Tests:**
- End-to-end trade lifecycle (buy signal to analytics log)
- Circuit breaker triggers stopping trades
- Stop-loss execution flow
- Configuration changes affecting agent behavior
- WebSocket broadcast to multiple clients

**Priority:** High (Phase 11 critical deliverable)
**Example:** TECHNICAL_REPORT.md Section 5.3.1

#### System Tests ❌ MISSING

**Missing Coverage:**
- Multi-day paper trading simulation (memory leaks, stability)
- Broker API failure handling and recovery
- Data feed interruption recovery
- WebSocket scalability (100+ connections)
- Analytics query performance (10,000+ trades)

**Priority:** Medium (Phase 11+)

### Monitoring

**Current:**
- ✅ Health check endpoint (`/api/health`)
- ✅ Observability logging (JSONL event stream)
- ✅ Scheduled evaluation reports
- ✅ Agent status tracking
- ✅ Automated TestAgent (scheduled `scripts/run_tests.sh` runs + log file) [logs/tests.jsonl]
- ✅ UI smoke-check agent (fetches dashboard, ensures selectors) [logs/ui_checks.jsonl]
- ✅ SessionLogger agent logs SIM account/position snapshots [logs/sessions.jsonl]
- ✅ ReplayRecorder agent captures intraday bars for offline SIM [data/replay/*.csv]

**Missing:**
- [ ] Performance metrics (API latency, error rates)
- [ ] Uptime monitoring integration
- [ ] Alert on anomalies
- [ ] Dashboard for operational metrics

**Security Analysis:** TECHNICAL_REPORT.md Section 8
**Performance Analysis:** TECHNICAL_REPORT.md Section 9

### Deliverables

- [x] Unit test suite (unittest) - **213 tests, 100% pass rate** ✅
- [x] Test coverage for all strategies (Momentum, Mean Reversion, Breakout, RSI) ✅
- [x] Test coverage for backtesting engine ✅
- [x] Test coverage for performance metrics ✅
- [x] Test coverage for analytics module (store + metrics) ✅
- [x] Universe isolation enforcement tests (10 tests validating EventBus, event routing, cross-contamination prevention) ✅
- [x] Broker universe constraint tests (8 tests validating FakeBroker=SIMULATION, AlpacaBroker=LIVE/PAPER) ✅
- [x] Analytics schema validation tests (14 tests validating provenance fields: universe, session_id, symbol, side) ✅
- [x] Observability logging & scheduled evaluation (JSONL + reports) ✅
- [ ] Integration test suite (end-to-end trading cycles)
- [ ] CI/CD pipeline (GitHub Actions)
- [x] Health check endpoint ✅
- [ ] Error recovery mechanisms
- [x] Observability dashboard (basic UI summary) ✅
- [x] Scheduled TestAgent for automated regression runs ✅

### Unit Test Suite Status ✅

**Last Updated:** 2026-01-27

- **Total Tests:** 213 tests across 26 modules
- **Pass Rate:** 100%
- **Coverage:** Strategies, backtesting, metrics, analytics (store + metrics), security, API, risk controls, observability, health endpoint, universe isolation, broker constraints, schema validation
- **Recent Additions:**
  - 10 tests for universe isolation enforcement (test_universe_isolation.py)
  - 8 tests for broker universe constraints (test_broker_universe.py)
  - 14 tests for analytics schema validation (test_analytics_schema_validation.py)
  - 30 tests for analytics store (JSONL persistence)
  - 18 enhanced tests for analytics metrics
  - 16 tests for health check endpoint
  - Added `httpx>=0.24.0` to requirements.txt for TestClient dependency
- **Documentation:** See [TESTS_FIXED_SUMMARY.md](TESTS_FIXED_SUMMARY.md)

### Configuration & Simulation Mode Improvements (2026-01-25)

**Completed:**
- [x] Added SIMULATION_MODE to runtime config persistence
  - Now persists in config_state.json
  - Survives server restarts
  - Can be toggled via config API
- [x] Aligned .env and config_state.json values
  - Fixed massive mismatches (100% position → 0.15%)
  - Removed misleading "HIGH RISK" comments
  - Added missing MAX_OPEN_POSITIONS field
- [x] Improved .env.example documentation
  - Clear SIMULATION_MODE explanation
  - Added note about runtime config override priority
- [x] Created diagnostic tools
  - `test_analytics_api.py` - Test analytics endpoints
  - `CONFIG_ALIGNMENT_NOTES.md` - Full change documentation
- [x] Fixed UI badge color coding
  - ON = GREEN, OFF = RED, PAPER = YELLOW
  - Consistent across all status badges

**Feature Gap Identified: SIM Mode Auto-Switching**

**Problem:** SIMULATION_MODE is currently a manual toggle only. Original vision was for automatic switching based on real market hours:
- Market OPEN (9:30am-4:30pm ET M-F) → Use real Alpaca API
- Market CLOSED + 30 min cooldown → Auto-enable SIM mode for 24/7 training

**Why it matters:**
- Can't train bot during off-hours without manual intervention
- Analytics don't populate when market is closed
- Strategy testing limited to market hours

**Requirements for auto-switching:**
1. Market hours detection (pytz, NYSE calendar)
2. Background monitor task (check every 1-5 min)
3. Runtime broker switching (requires refactor)
4. UI indicators and configuration

**Estimated effort:** 2-3 days development + testing

**Documentation:** See [SIM_MODE_AUTO_SWITCHING_CONTEXT.md](SIM_MODE_AUTO_SWITCHING_CONTEXT.md)

**Proposed deliverables:**
- [ ] Market hours detection function (`is_market_open_now()`)
- [ ] Background monitor task with 30-min cooldown
- [ ] Runtime broker switching mechanism (AutoSwitchingBroker wrapper)
- [ ] Configuration: `SIM_AUTO_SWITCH_ENABLED`, `SIM_COOLDOWN_MINUTES`
- [ ] UI countdown to SIM activation after market close
- [ ] Integration tests for auto-switching behavior

**Dependencies needed:**
```txt
pytz>=2023.3
pandas-market-calendars>=4.3.0  # NYSE holiday calendar
```

---

## Phase 12: Track Record Verification

> **Status:** Planned
> **Priority:** Low (nice-to-have)
> **Dependencies:** Phase 4 (needs analytics data)

### Goals

- Verifiable, tamper-proof trade history
- Build trust with potential investors
- Differentiate from competitors who rely on screenshots

### Approach

0. **Provenance tracking** ✅ - Every trade/metric tagged with universe and session_id (completed 2026-01-27)
   - Schema validation enforces required fields
   - Type-safe universe separation prevents contamination
   - Foundation for verifiable track record
1. **Hash each trade** - Include timestamp, symbol, side, quantity, price, account snapshot
2. **Chain hashes** - Each trade hash includes previous hash (like blockchain)
3. **Periodic anchoring** - Publish hash to public blockchain or timestamping service
4. **Verification tool** - Anyone can verify the chain is unbroken

### Deliverables

- [ ] Trade hashing system
- [ ] Hash chain implementation
- [ ] Public anchoring (optional)
- [ ] Verification tool
- [ ] Documentation of verification process

---

## Technical Debt & Maintenance

> **Comprehensive Analysis:** See [TECHNICAL_REPORT.md](TECHNICAL_REPORT.md) Section 7 for detailed code-level debt analysis with line numbers and fix examples.

### Critical Issues (2026-01-25)

**Root Directory Clutter:**
- [ ] **Remove 7 obsolete files** (old AI reviews, test output files)
  - See TECHNICAL_REPORT.md Section 2.2 for complete cleanup plan
  - **Impact:** Cleaner project structure, easier navigation
  - **Effort:** 10 minutes

**File Organization:**
- [ ] **Move 4 documentation files to docs/** (session notes, context docs)
- [ ] **Move test_analytics_api.py to scripts/**
- [ ] **Reorganize docs/ structure** (user-guide/, developer/, operations/, decisions/)
  - See TECHNICAL_REPORT.md Sections 2.2 and 10 for proposed structure

### Configuration Issues (2026-01-27)

- [x] ~~Configuration split between .env and JSON state file~~ **RESOLVED**
  - Now documented clearly in .env.example
  - Priority: config_state.json > .env (runtime overrides)
  - Both files now aligned with same values
- [x] ~~SIMULATION_MODE boolean confusion~~ **RESOLVED (2026-01-27)**
  - Migrated from boolean flag to Universe enum throughout codebase
  - Type-safe separation: Universe.SIMULATION, Universe.PAPER, Universe.LIVE
  - Agents check `self.universe != Universe.SIMULATION` instead of `not config.SIMULATION_MODE`
  - **Impact:** Eliminates confusion, enables proper track record verification
- [ ] **Broker instantiated at startup** - Can't switch at runtime
  - Blocks SIM mode auto-switching feature
  - Need AutoSwitchingBroker wrapper or restart mechanism
  - **Impact:** Can't automatically enable SIM when market closes
  - **Analysis:** TECHNICAL_REPORT.md Section 3.1.1
- [ ] **No schema validation for config_state.json**
  - Invalid JSON can crash server silently
  - **Fix:** Add Pydantic validation (TECHNICAL_REPORT.md Section 4.2.2)
  - **Priority:** Medium
- [ ] **Configuration persistence uses long if/elif chain**
  - 16 elif branches in load_config_state()
  - Error-prone, hard to maintain
  - **Fix:** Dataclass-based approach (TECHNICAL_REPORT.md Section 3.1.2)
  - **Priority:** Medium

### Analytics Issues (2026-01-25)

- [ ] **Analytics metric cards showing "--" in UI**
  - Backend API works, metrics calculated correctly
  - UI JavaScript not displaying response
  - OR: Browser caching old JavaScript
  - **Action:** Debug with `python scripts/test_analytics_api.py`
  - **Analysis:** TECHNICAL_REPORT.md Sections 3.1.3, 7.2.3
- [ ] **Position concentration chart not rendering**
  - Chart.js code exists, white text fix applied
  - May be version conflict or data format issue
  - **Action:** Check browser console for errors
- [ ] **Trades missing filled_avg_price**
  - AnalyticsAgent records trades with null prices (always None)
  - Prevents P&L calculations
  - Need to extract price from OrderExecuted event
  - **Impact:** Trade stats can't calculate win rate
  - **Fix:** TECHNICAL_REPORT.md Section 3.2.1 with code example
  - **Priority:** High

### Code Quality Issues

- [ ] **Bare except clauses** (3 locations)
  - server.py line 408, analytics/store.py multiple
  - Swallows all errors, hard to debug
  - **Fix:** Catch specific exceptions (TECHNICAL_REPORT.md Section 7.1.3)
- [ ] **Magic numbers and hardcoded values**
  - Throughout codebase (60 second conversions, thresholds, etc.)
  - **Examples:** TECHNICAL_REPORT.md Section 7.1.2
  - **Priority:** Low
- [ ] **Incomplete type hints**
  - Newer code has type hints, older code lacks them
  - **Impact:** Reduced IDE support, harder to catch bugs
  - **Priority:** Medium

### Architecture Debt

- [ ] **Monolithic UI file** (static/index.html - 3,600 lines)
  - HTML + CSS + JavaScript all inline
  - Hard to maintain, browser caching issues
  - **Analysis:** TECHNICAL_REPORT.md Section 7.2.2
  - **Priority:** Low (Phase 5+)
- [ ] **No database layer**
  - All data in flat files (JSON, JSONL, CSV)
  - Limits querying, no transactions
  - **When needed:** Phase 8 (Configuration Management)
- [ ] **Stop-loss logic duplicated**
  - Both strategies and MonitorAgent check stop-loss
  - Redundant but safe (defense in depth)
  - **Analysis:** TECHNICAL_REPORT.md Section 3.3.3

### Dependencies

- [ ] **Remove unused 'schedule' package**
  - Not found in any .py file
  - **Action:** Remove from requirements.txt
  - **Verified:** TECHNICAL_REPORT.md Section 6.1
- [ ] **Add missing dependencies for future features**
  - pytz (market hours detection)
  - pandas-market-calendars (NYSE holidays)

### Security Issues

- [ ] **No rate limiting on API endpoints**
  - Risk of DoS via excessive requests
  - **Fix:** TECHNICAL_REPORT.md Section 8.1.1 with slowapi example
  - **Priority:** Medium
- [ ] **No HTTPS enforcement**
  - Token sent in plaintext if accessed remotely
  - **Priority:** Critical for production deployment
- [ ] **No input validation schemas**
  - Malformed JSON can crash server
  - **Fix:** TECHNICAL_REPORT.md Section 8.3.1 with Pydantic models
  - **Priority:** Medium

### Performance Debt

- [ ] **Analytics JSONL files loaded entirely into memory**
  - Works for current scale (~500KB files)
  - May need streaming for multi-year data
  - **Analysis:** TECHNICAL_REPORT.md Section 9.2.1
- [ ] **No caching for Top Gainers API calls**
  - Fetches every 1-5 minutes, could cache 5-10 minutes
  - **Optimization:** TECHNICAL_REPORT.md Section 9.3.1
  - **Priority:** Low

### Testing Debt

- [ ] **No integration tests**
  - 182 unit tests (excellent), 0 integration tests
  - Cannot verify full trade flow or multi-agent coordination
  - **Priority:** High (Phase 11 deliverable)
- [ ] **No CI/CD pipeline**
  - Tests run manually only
  - **Priority:** High (Phase 11 deliverable)
- [ ] **No performance/load tests**
  - Memory usage, WebSocket scalability untested
  - **Priority:** Medium

### Documentation Debt

- [ ] **Scattered documentation** (15+ locations)
  - Root, docs/, docs/archive/, session notes
  - **Proposed structure:** TECHNICAL_REPORT.md Section 2.2
  - **Priority:** Medium (Phase 10)
- [ ] **Incomplete API documentation**
  - No OpenAPI spec, endpoint reference, or error codes
  - FastAPI can auto-generate at /docs endpoint
  - **Priority:** Low
- [ ] **No developer onboarding guide**
  - How to add strategies, agents, risk checks
  - **Priority:** Medium (Phase 10)
- [ ] **Missing docstrings**
  - ~75% of server.py functions lack docstrings
  - **Priority:** Low

### Ongoing Tasks

- [x] ~~Remove SIMULATION_MODE boolean confusion~~ **COMPLETED (2026-01-27)** - Migrated to Universe enum
- [ ] Add type hints throughout codebase (partially done - Universe/UniverseContext fully typed)
- [ ] Standardize logging format and levels (mostly done - event-driven logging)
- [ ] ~~Consolidate configuration management~~ **IMPROVED** (documented, aligned)
- [ ] Improve error messages
- [ ] Code documentation (docstrings) (partially done)
- [ ] Dependency updates
- [ ] Add cache-busting for static/index.html (UI changes require hard refresh)

### Code Quality Standards

- All new code must have type hints
- All public functions must have docstrings
- Test coverage target: 80% for new code
- Linting: flake8/black/isort compliance

---

## Known Issues Reference

**Comprehensive Issue Log:** See [TECHNICAL_REPORT.md Appendix E](TECHNICAL_REPORT.md#appendix-e-known-issues-log) for complete tracked issues with severity, status, and ownership.

---

## Success Metrics

### For Investors

- Backtest Sharpe ratio > 1.0
- Live performance within 20% of backtest
- Max drawdown documented and reasonable
- Verifiable track record

### For Traders

- Setup time < 15 minutes
- System uptime > 99.5%
- Trade execution latency < 1 second
- Zero missed trades due to bugs

### For Hobbyists

- Time to first paper trade < 10 minutes
- Documentation completeness score > 90%
- Community engagement (GitHub stars, forks)

---

## Changelog

| Date | Change |
|------|--------|
| 2025-01-19 | Initial roadmap created |
| 2025-01-19 | Phase 1 (Backtesting) started |
| 2025-01-19 | Phase 1 (Backtesting) completed - full implementation with CLI and documentation |
| 2025-01-19 | Phase 2 (Strategy Framework) completed - 4 strategies with pluggable architecture |
| 2026-01-21 | Improved top gainers reliability (volume fallback), increased bar lookback buffer, ticker now shows unique symbols |
| 2026-01-21 | Manual trade dropdown now groups holdings/watchlist/signals; ticker auto-scroll restored without duplicates |
| 2026-01-20 | Phase 11 (Testing) - Achieved 100% test pass rate (83/83 tests) |
| 2026-01-20 | Added strategy selector and max daily trades controls to UI |
| 2026-01-20 | Added high risk/high reward configuration options to .env |
| 2026-01-22 | Added observability evaluator + expectations API and UI summary |
| 2026-01-22 | Improved ticker flow and added market index proxy ticker |
| 2026-01-22 | Added position sizing + observability unit tests (94/94 pass) |
| 2026-01-22 | Added circuit breaker + max open positions; tests 98/98 pass |
| 2026-01-22 | Added risk UI + backtest risk metrics; tests 99/99 pass |
| 2026-01-22 | Added breaker reset endpoint + UI indicator; tests 101/101 pass |
| 2026-01-22 | Added sector/correlation exposure checks + tests 104/104 pass |
| 2026-01-22 | Added sector map starter file + risk controls documentation |
| 2026-01-22 | Expanded sector map coverage + added updater script |
| 2026-01-25 | **Configuration alignment:** Fixed .env / config_state.json mismatches (100% position → 0.15%) |
| 2026-01-25 | **SIMULATION_MODE runtime persistence:** Added to config_state.json, survives restarts |
| 2026-01-25 | **UI badge improvements:** Color coding (ON=GREEN, OFF=RED, PAPER=YELLOW) |
| 2026-01-25 | **Position concentration chart:** Fixed white text rendering with Chart.js fontColor |
| 2026-01-25 | **Dependencies:** Added httpx>=0.24.0 to requirements.txt for TestClient |
| 2026-01-25 | **Documentation:** Created CONFIG_ALIGNMENT_NOTES.md and SIM_MODE_AUTO_SWITCHING_CONTEXT.md |
| 2026-01-25 | **Feature gap identified:** SIM mode auto-switching (market hours detection) not implemented |
| 2026-01-25 | **Analytics issues documented:** Metrics showing "--", charts not rendering, filled_avg_price missing |
| 2026-01-25 | **Diagnostic tools:** Created test_analytics_api.py for debugging API responses |
| 2026-01-25 | **Phase 4 status updated:** 90% → 75% (equity curve works, metrics display broken) |
| 2026-01-25 | **TECHNICAL_REPORT.md created:** Comprehensive 40,000+ word technical analysis covering architecture, code review, testing, security, performance, and 16 prioritized recommendations |
| 2026-01-25 | **Technical debt cataloged:** 30+ specific issues identified with severity levels, line numbers, and fix examples |
| 2026-01-26 | **Server modularization completed:** Refactored monolithic server.py into modular server/ package with routers, lifespan, dependencies, config_manager |
| 2026-01-26 | **Test suite stability:** 181/181 tests passing (100% pass rate, 0.242s execution time) |
| 2026-01-26 | **Server routing fixes:** Fixed WebSocket connection failures, added missing API endpoints (/api/status, /api/trades, /api/observability) |
| 2026-01-26 | **Path resolution fix:** Updated scripts/serve.py to add project root to sys.path, resolving module import errors |
| 2026-01-26 | **SIMULATION_MODE enabled:** Switched to FakeBroker for testing, server running with simulated trading |
| 2026-01-26 | **ROADMAP integration:** Cross-referenced TECHNICAL_REPORT sections throughout ROADMAP (Phase 4, Phase 8, Phase 10, Phase 11, Technical Debt) |
| 2026-01-26 | **Test count update:** Corrected test count from 174 → 181 tests across all ROADMAP references |
| 2026-01-26 | **Architectural analysis:** Documented simulation-live continuity requirements, mode isolation boundaries, temporal semantics, and falsifiability metrics |
| 2026-01-27 | **Universe Isolation (Week 2/3)**: Completed type-safe universe separation with provenance tracking - migrated from SIMULATION_MODE boolean to Universe enum throughout codebase |
| 2026-01-27 | **Test suite expansion**: 213/213 tests passing (added 32 tests: 10 for universe isolation enforcement, 8 for broker constraints, 14 for analytics schema validation) |
| 2026-01-27 | **Schema validation**: Added SchemaValidationError to analytics store - validates universe match, session_id presence, required trade fields (symbol, side) |
| 2026-01-27 | **Broker universe enforcement**: AlpacaBroker rejects SIMULATION, FakeBroker rejects LIVE/PAPER - type-safe separation prevents cross-contamination |
| 2026-01-27 | **Provenance tracking foundation**: All events, metrics, and trades now require universe and session_id - enables Phase 12 track record verification |
| 2026-01-27 | **Technical debt reduction**: Removed SIMULATION_MODE boolean from config.py and all agent references - replaced with Universe enum checks |

---

*This is a living document. Update it as the project evolves.*

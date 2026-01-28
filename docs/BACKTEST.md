# Backtesting Module Documentation

> Validate trading strategies with historical data before risking real capital.

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Architecture](#architecture)
4. [CLI Reference](#cli-reference)
5. [Python API](#python-api)
6. [Performance Metrics](#performance-metrics)
7. [Understanding Results](#understanding-results)
8. [Best Practices](#best-practices)
9. [Limitations](#limitations)

---

## Overview

### Purpose

The backtesting module allows you to:

- **Validate strategies** before deploying with real money
- **Compare parameters** to find optimal settings
- **Understand risk** through drawdown and volatility metrics
- **Build confidence** with historical performance data

### Key Features

- **Historical data management** with local caching
- **Event-driven simulation** that prevents lookahead bias
- **Comprehensive metrics** including Sharpe, Sortino, max drawdown
- **Benchmark comparison** against SPY or any symbol
- **Export capabilities** for further analysis

### What It Does NOT Do

- **Guarantee future performance** - past results don't predict the future
- **Account for market impact** - assumes unlimited liquidity
- **Model all execution costs** - basic slippage only
- **Support intraday strategies** - daily bars only

---

## Quick Start

### 1. Download Historical Data

```bash
# Download 3 years of data for your watchlist
python -m backtest --download --symbols AAPL,GOOGL,MSFT,NVDA --start 2021-01-01

# Also download benchmark
python -m backtest --download --symbols SPY --start 2021-01-01
```

### 2. Run a Backtest

```bash
# Basic backtest
python -m backtest --symbols AAPL,GOOGL,MSFT,NVDA --start 2021-01-01 --end 2023-12-31

# With benchmark comparison
python -m backtest --symbols AAPL,GOOGL,MSFT,NVDA --start 2021-01-01 --benchmark SPY

# With custom parameters
python -m backtest --symbols AAPL,GOOGL,MSFT --start 2022-01-01 \
    --capital 50000 \
    --momentum-threshold 0.03 \
    --lookback 15 \
    --stop-loss 0.03
```

### 3. Export Results

```bash
python -m backtest --symbols AAPL,GOOGL --start 2022-01-01 \
    --output results.json \
    --equity-csv equity.csv \
    --trades-csv trades.csv
```

### 4. Programmatic Usage

```python
from backtest import BacktestEngine, HistoricalData

# Load data
data = HistoricalData()
data.download(['AAPL', 'GOOGL', 'MSFT'], start='2021-01-01', end='2023-12-31')

# Configure engine
engine = BacktestEngine(
    data=data,
    initial_capital=100000,
    max_position_pct=0.20,  # 20% max per position
    stop_loss_pct=0.05,     # 5% stop loss
)

# Run backtest
results = engine.run(
    symbols=['AAPL', 'GOOGL', 'MSFT'],
    start='2021-01-01',
    end='2023-12-31',
    benchmark_symbol='SPY'
)

# View results
print(results.summary())
print(f"Sharpe Ratio: {results.metrics.sharpe_ratio:.2f}")
print(f"Max Drawdown: {results.metrics.max_drawdown:.2%}")

# Export
results.to_json('backtest_results.json')
results.trades_to_csv('trades.csv')
```

---

## Architecture

### Module Structure

```
backtest/
├── __init__.py     # Package exports
├── __main__.py     # Entry point for `python -m backtest`
├── cli.py          # Command-line interface
├── data.py         # Historical data management
├── engine.py       # Core simulation engine
├── metrics.py      # Performance calculations
└── results.py      # Results formatting and export
```

### Data Flow

```
1. DATA LOADING
   HistoricalData.download() → Alpaca API → Local CSV cache

2. SIMULATION
   For each trading day:
   ├── Update prices
   ├── Check stop losses
   ├── Generate signals (using only past data)
   ├── Execute trades (at next bar's price with slippage)
   └── Record state

3. ANALYSIS
   BacktestEngine.run() → BacktestResults
   ├── Equity curve
   ├── Trade log
   ├── Performance metrics
   └── Benchmark comparison
```

### Design Principles

#### No Lookahead Bias

The engine ensures the strategy only sees data that would have been available at each point in time:

```python
# The strategy receives bars UP TO the current date, never future data
bars = data.get_bars_up_to(symbol, current_date, lookback_days)
```

#### Realistic Execution

Orders are simulated with:
- **Slippage**: Buy at slightly higher price, sell at slightly lower
- **Commission**: Configurable per-trade cost
- **Cash management**: Can't buy more than available cash

#### Warmup Period

The first N days (lookback + 5) are used to build history. No trades occur during warmup to ensure the momentum calculation has sufficient data.

---

## CLI Reference

### Synopsis

```bash
python -m backtest [OPTIONS]
```

### Actions

| Option | Description |
|--------|-------------|
| `--download, -d` | Download historical data from Alpaca |
| `--list-cached` | List symbols with cached data |
| `--clear-cache` | Clear cached data |

### Data Options

| Option | Description |
|--------|-------------|
| `--symbols, -s` | Comma-separated symbols (required) |
| `--start` | Start date YYYY-MM-DD (required) |
| `--end` | End date YYYY-MM-DD (default: today) |
| `--benchmark` | Benchmark symbol for comparison |

### Strategy Parameters

| Option | Default | Description |
|--------|---------|-------------|
| `--capital` | 100000 | Initial capital |
| `--lookback` | 20 | Momentum lookback period (days) |
| `--momentum-threshold` | 0.02 | Buy threshold (2%) |
| `--sell-threshold` | -0.01 | Sell threshold (-1%) |
| `--stop-loss` | 0.05 | Stop loss (5%) |
| `--max-position` | 0.25 | Max position size (25%) |
| `--commission` | 0.0 | Commission per trade |
| `--slippage` | 0.001 | Slippage (0.1%) |

### Output Options

| Option | Description |
|--------|-------------|
| `--output, -o` | Export results to JSON |
| `--equity-csv` | Export equity curve to CSV |
| `--trades-csv` | Export trade log to CSV |
| `--quiet, -q` | Suppress detailed output |
| `--monthly` | Show monthly returns table |

### Examples

```bash
# Download and backtest in one session
python -m backtest --download --symbols AAPL,GOOGL,MSFT --start 2020-01-01
python -m backtest --symbols AAPL,GOOGL,MSFT --start 2021-01-01 --end 2023-12-31

# Parameter optimization (run multiple times)
python -m backtest --symbols AAPL,GOOGL --start 2022-01-01 --lookback 10
python -m backtest --symbols AAPL,GOOGL --start 2022-01-01 --lookback 20
python -m backtest --symbols AAPL,GOOGL --start 2022-01-01 --lookback 30

# Conservative settings
python -m backtest --symbols AAPL,GOOGL,MSFT --start 2022-01-01 \
    --max-position 0.10 --stop-loss 0.03 --momentum-threshold 0.05

# Full export
python -m backtest --symbols AAPL,GOOGL,MSFT --start 2022-01-01 \
    --benchmark SPY --monthly \
    --output results.json --equity-csv equity.csv --trades-csv trades.csv
```

---

## Python API

### HistoricalData

Manages historical price data with local caching.

```python
from backtest import HistoricalData

data = HistoricalData()

# Download from Alpaca (requires API credentials)
data.download(
    symbols=['AAPL', 'GOOGL'],
    start='2021-01-01',
    end='2023-12-31',
    force=False  # Set True to re-download
)

# Load from cache
data.load(symbols=['AAPL', 'GOOGL'], start='2022-01-01', end='2023-12-31')

# Access data
df = data.get('AAPL')  # Returns DataFrame with OHLCV
price = data.get_price('AAPL', pd.Timestamp('2023-06-15'), 'close')

# Utilities
print(data.info())           # Summary of loaded data
print(data.list_cached())    # List cached symbols
data.clear_cache(['AAPL'])   # Clear specific symbols
```

### BacktestEngine

Runs the backtest simulation.

```python
from backtest import BacktestEngine, HistoricalData

data = HistoricalData()
data.load(['AAPL', 'GOOGL', 'MSFT'])

engine = BacktestEngine(
    data=data,
    initial_capital=100000,
    commission=0.0,
    slippage=0.001,
    max_position_pct=0.25,
    stop_loss_pct=0.05,
)

# Adjust strategy parameters
engine.set_strategy_params(
    lookback_days=15,
    momentum_threshold=0.03,
    sell_threshold=-0.02,
)

# Run backtest
results = engine.run(
    symbols=['AAPL', 'GOOGL', 'MSFT'],
    start='2022-01-01',
    end='2023-12-31',
    benchmark_symbol='SPY'
)
```

### BacktestResults

Contains all backtest outputs.

```python
# Access metrics
print(results.metrics.sharpe_ratio)
print(results.metrics.max_drawdown)
print(results.metrics.win_rate)

# Access data
equity_curve = results.equity_curve  # pd.Series
trades = results.trades              # List[Trade]

# Export
results.to_json('results.json')
results.to_csv('equity.csv')
results.trades_to_csv('trades.csv')

# Display
print(results.summary())
results.print_monthly_returns()

# Reload from file
loaded = BacktestResults.from_json('results.json')
```

### PerformanceMetrics

All calculated performance metrics.

```python
metrics = results.metrics

# Returns
metrics.total_return        # Absolute dollar return
metrics.total_return_pct    # Percentage return
metrics.annualized_return   # CAGR

# Risk
metrics.volatility          # Annualized volatility
metrics.sharpe_ratio        # Risk-adjusted return
metrics.sortino_ratio       # Downside risk-adjusted
metrics.max_drawdown        # Maximum peak-to-trough
metrics.max_drawdown_duration  # Days in max drawdown

# Trades
metrics.total_trades
metrics.winning_trades
metrics.losing_trades
metrics.win_rate
metrics.profit_factor       # Gross profit / gross loss
metrics.avg_win
metrics.avg_loss
metrics.largest_win
metrics.largest_loss

# Exposure
metrics.exposure_time       # % of time in market
metrics.avg_position_duration

# Benchmark (if provided)
metrics.benchmark_return
metrics.alpha
metrics.beta
```

---

## Performance Metrics

### Returns Metrics

| Metric | Formula | Interpretation |
|--------|---------|----------------|
| **Total Return** | (Final - Initial) / Initial | Overall performance |
| **Annualized Return** | (1 + Total)^(1/years) - 1 | Yearly equivalent |

### Risk Metrics

| Metric | Formula | Good Value |
|--------|---------|------------|
| **Volatility** | StdDev(returns) × √252 | Lower is less risky |
| **Sharpe Ratio** | (Return - RiskFree) / Volatility | > 1.0 is good, > 2.0 is excellent |
| **Sortino Ratio** | (Return - RiskFree) / DownsideVol | Like Sharpe, but ignores upside volatility |
| **Max Drawdown** | Max peak-to-trough decline | < 20% is conservative |

### Trade Metrics

| Metric | Interpretation |
|--------|----------------|
| **Win Rate** | % of profitable trades. 40-50% is normal for trend following |
| **Profit Factor** | Gross wins / Gross losses. > 1.5 is good |
| **Avg Win / Avg Loss** | Ideally avg win > avg loss |

### Benchmark Metrics

| Metric | Interpretation |
|--------|----------------|
| **Alpha** | Excess return vs benchmark (annualized) |
| **Beta** | Correlation with benchmark. 1.0 = moves with market |

---

## Understanding Results

### Sample Output

```
============================================================
BACKTEST RESULTS
============================================================

Configuration
----------------------------------------
  Strategy:        MomentumStrategy
  Symbols:         AAPL, GOOGL, MSFT
  Period:          2022-01-01 to 2023-12-31
  Initial Capital: $100,000.00
  Final Value:     $118,450.00

Performance Metrics
==================================================

Returns
------------------------------
  Total Return:        $18,450.00 (18.45%)
  Annualized Return:   8.87%

Risk Metrics
------------------------------
  Volatility (Ann.):   15.23%
  Sharpe Ratio:        0.58
  Sortino Ratio:       0.82
  Max Drawdown:        12.34%
  Max DD Duration:     45 days

Trade Statistics
------------------------------
  Total Trades:        24
  Winning Trades:      11
  Losing Trades:       13
  Win Rate:            45.83%
  Profit Factor:       1.65
  Avg Win:             $2,850.00
  Avg Loss:            $1,180.00
  Largest Win:         $5,200.00
  Largest Loss:        $2,100.00

Exposure
------------------------------
  Time in Market:      68.50%
  Avg Position Hold:   12.5 days
```

### Interpreting Results

**This is a decent but not exceptional result:**

- **18.45% over 2 years** is reasonable but not spectacular
- **Sharpe of 0.58** is below the 1.0 threshold for "good"
- **Max drawdown of 12.34%** is manageable
- **Win rate of 45.83%** is typical for momentum strategies
- **Profit factor of 1.65** shows wins are bigger than losses

**Questions to ask:**
- How does this compare to simply buying and holding SPY?
- Would different parameters improve the Sharpe ratio?
- Is the drawdown acceptable for your risk tolerance?

---

## Best Practices

### 1. Use Sufficient History

```bash
# Bad: Only 6 months of data
python -m backtest --symbols AAPL --start 2023-06-01

# Good: 2-3 years minimum
python -m backtest --symbols AAPL --start 2021-01-01
```

### 2. Test Multiple Market Conditions

Include periods with:
- Bull markets (2021)
- Bear markets (2022)
- Sideways markets
- High volatility events (COVID crash 2020)

### 3. Don't Overfit

```bash
# Bad: Optimizing until results look perfect
# Then deploying those exact parameters

# Good: Test on one period, validate on another
python -m backtest --symbols AAPL --start 2020-01-01 --end 2021-12-31  # Train
python -m backtest --symbols AAPL --start 2022-01-01 --end 2023-12-31  # Validate
```

### 4. Compare to Benchmark

Always run with `--benchmark SPY` to see if your strategy beats simple buy-and-hold.

### 5. Account for Realistic Costs

```bash
# Include realistic slippage for your trading frequency
python -m backtest --symbols AAPL --slippage 0.002  # 0.2% for less liquid stocks
```

### 6. Don't Trust Single Runs

Run multiple backtests with:
- Different time periods
- Different symbol sets
- Slightly varied parameters

Consistent performance across variations is more trustworthy than one great backtest.

---

## Limitations

### What This Backtest Assumes

1. **Unlimited liquidity** - Can always buy/sell at the simulated price
2. **No market impact** - Your orders don't move the price
3. **Daily data only** - No intraday price movement
4. **Single exchange** - No arbitrage or cross-exchange execution
5. **No dividends** - Adjusted prices only, no dividend reinvestment
6. **Constant parameters** - Same strategy params throughout

### What Could Cause Live Performance to Differ

| Factor | Backtest | Reality |
|--------|----------|---------|
| **Execution** | Next-day open + slippage | Could be worse in volatile markets |
| **Liquidity** | Always available | May not fill at desired price |
| **Data** | Clean historical data | Live data has gaps, errors |
| **Psychology** | Perfect execution | You might hesitate or override |
| **Costs** | Simple model | Bid-ask spread, taxes, etc. |

### Rules of Thumb

- **Expect 20-30% worse performance** in live trading vs backtest
- **If backtest barely beats benchmark**, live probably won't
- **Paper trade for 1-3 months** before going live
- **Start with small position sizes** when transitioning to live

---

## Troubleshooting

### "No data loaded"

```bash
# First download the data
python -m backtest --download --symbols AAPL,GOOGL --start 2021-01-01
```

### "Insufficient data for warmup"

Your date range is too short. The engine needs `lookback_days + 5` days minimum.

```bash
# If lookback is 20, need at least 25+ trading days
python -m backtest --symbols AAPL --start 2023-01-01 --end 2023-02-28  # Too short
python -m backtest --symbols AAPL --start 2023-01-01 --end 2023-06-30  # Better
```

### "Alpaca credentials not configured"

Set environment variables:
```bash
export ALPACA_API_KEY=your_key
export ALPACA_SECRET_KEY=your_secret
```

Or add to `.env` file.

### Results seem unrealistic

- Check for lookahead bias in any custom modifications
- Verify data quality with `--list-cached`
- Try with higher slippage to be more conservative

---

## Next Steps

After validating with backtesting:

1. **Paper trade** for 30-90 days with the same parameters
2. **Compare** live paper results to backtest expectations
3. **If consistent**, transition to live with small position sizes
4. **Scale up gradually** as confidence builds

See the main [ROADMAP.md](../ROADMAP.md) for the full development plan.

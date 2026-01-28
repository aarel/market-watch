# Test Suite Documentation

> Comprehensive test coverage for Market-Watch trading bot

## Quick Command Cheat Sheet

| Goal | Command | What it does | Output |
| --- | --- | --- | --- |
| Full suite (preferred) | `bash scripts/run_tests.sh` | Activates venv (`venv`/`.venv`), runs all `unittest` files, timestamps log | `test_results/test_run_YYYYMMDD_HHMMSS.log` + `test_results/latest_summary.txt` |
| Full suite (Windows) | `scripts\\run_tests.bat` | Same as above for Windows shells | Same as above |
| Full suite (manual) | `python -m unittest discover -s tests -p "test_*.py" -v` | Runs everything without logging helper | Console only |
| Single module | `python -m unittest tests.test_strategy_momentum -v` | Runs one file | Console only |
| Specific test case | `python -m unittest tests.test_strategy_momentum.TestMomentumStrategy.test_buy_signal_strong_momentum -v` | Runs one test method | Console only |

Log files include a line per test (name + ok/FAIL/ERROR) and are safe to share with CI.

## Overview

This test suite provides automated testing for:
- **Phase 1:** Backtesting engine and metrics
- **Phase 2:** Trading strategies (momentum, mean reversion, breakout, RSI)
- **Core functionality:** Agents, event bus, screeners, security

## Running Tests

### Prerequisites

Activate your virtual environment first:

```bash
# Linux/Mac
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### Run All Tests with Logging

**Recommended method** - Creates timestamped log files:

```bash
# Linux/Mac
./run_tests.sh

# Windows
run_tests.bat
```

This will:
- Run all tests
- Save detailed output to `test_results/test_run_YYYYMMDD_HHMMSS.log`
- Create summary in `test_results/latest_summary.txt`
- Display colored results in terminal

The summary file records total/passed/failed/error counts plus the log path for quick inspection.

### Run All Tests (Manual)

```bash
# Run entire test suite
python -m unittest discover -s tests -p "test_*.py" -v

# Or use shorter form
python -m unittest discover tests -v
```

### Run Specific Test Files

```bash
# Single test file
python -m unittest tests.test_strategy_momentum -v

# Multiple specific files
python -m unittest tests.test_backtest_data tests.test_backtest_metrics -v
```

### Run Tests by Phase

**Phase 1 - Backtesting:**
```bash
python -m unittest \
  tests.test_backtest_data \
  tests.test_backtest_metrics \
  tests.test_backtest_engine \
  tests.test_backtest_results \
  -v
```

**Phase 2 - Strategies:**
```bash
python -m unittest \
  tests.test_strategy_momentum \
  tests.test_strategy_mean_reversion \
  tests.test_strategy_breakout \
  tests.test_strategy_rsi \
  -v
```

**Core Functionality:**
```bash
python -m unittest \
  tests.test_screener \
  tests.test_security \
  tests.test_signals_updated \
  tests.test_trade_interval \
  -v
```

### Run Specific Test Cases

```bash
# Run a specific test class
python -m unittest tests.test_strategy_momentum.TestMomentumStrategy -v

# Run a specific test method
python -m unittest tests.test_strategy_momentum.TestMomentumStrategy.test_buy_signal_strong_momentum -v
```

## Test Coverage

### Phase 1: Backtesting Engine

#### test_backtest_data.py
Tests historical data management and caching.

**Key Tests:**
- ✅ Data directory creation
- ✅ CSV download and caching from Alpaca API
- ✅ Loading data from cached CSV files
- ✅ **No lookahead bias** - ensures backtest doesn't use future data
- ✅ Correct number of bars returned
- ✅ Error handling for missing symbols

**Critical Test:**
```python
test_get_bars_up_to_no_lookahead()
# Verifies that get_bars_up_to only returns data available at target date
# Prevents peeking into the future during backtesting
```

#### test_backtest_metrics.py
Tests performance metric calculations.

**Key Tests:**
- ✅ Sharpe ratio (positive/negative returns, zero volatility)
- ✅ Max drawdown (declining equity, recovery, always rising)
- ✅ Sortino ratio (uses downside deviation only)
- ✅ Win rate (all wins, all losses, mixed, empty trades)
- ✅ Profit factor (profitable, unprofitable, edge cases)
- ✅ Full metrics integration test

**Example:**
```python
test_sharpe_ratio_with_risk_free_rate()
# Verifies Sharpe ratio correctly accounts for risk-free rate
```

#### test_backtest_engine.py
Tests the core backtest simulation engine.

**Key Tests:**
- ✅ Engine initialization with parameters
- ✅ Buy signals create positions
- ✅ Stop-loss triggers exit positions
- ✅ Position sizing respects max_position_pct
- ✅ Equity curve generation
- ✅ **No lookahead bias in signal generation**

**Critical Test:**
```python
test_backtest_no_lookahead_bias()
# Verifies backtest doesn't use future price data
# Logs all data fetches to ensure no peeking ahead
```

#### test_backtest_results.py
Tests results formatting and export functionality.

**Key Tests:**
- ✅ PerformanceMetrics dataclass creation
- ✅ BacktestResults creation and dict conversion
- ✅ JSON export to file
- ✅ CSV export for trades
- ✅ Summary string generation
- ✅ Benchmark comparison formatting
- ✅ Empty trades list handling

### Phase 2: Strategy Framework

#### test_strategy_momentum.py
Tests momentum/trend following strategy.

**Key Tests:**
- ✅ Buy signal when momentum > threshold
- ✅ Hold signal when momentum below threshold
- ✅ Sell signal on momentum reversal
- ✅ Stop-loss trigger on large losses
- ✅ Hold position with positive momentum
- ✅ Momentum calculation accuracy
- ✅ Signal metadata includes momentum value

**Example:**
```python
test_momentum_calculation_accuracy()
# Verifies: momentum = (current_price - past_price) / past_price
# With prices 100 -> 108, expects momentum = 0.08 (8%)
```

#### test_strategy_mean_reversion.py
Tests mean reversion strategy.

**Key Tests:**
- ✅ Buy signal when price significantly below moving average
- ✅ Hold signal when price near moving average
- ✅ Sell signal when price above MA (overbought)
- ✅ Stop-loss trigger
- ✅ Moving average calculation accuracy
- ✅ Deviation from MA calculation
- ✅ Metadata includes MA and deviation values

**Example:**
```python
test_buy_signal_price_below_ma()
# Price 96 is ~4.76% below MA of 100.8
# Exceeds 3% threshold -> generates buy signal
```

#### test_strategy_breakout.py
Tests breakout strategy.

**Key Tests:**
- ✅ Buy signal on breakout above period high
- ✅ Hold signal during consolidation
- ✅ Sell signal on breakdown below period low
- ✅ Stop-loss trigger
- ✅ Period high/low calculation
- ✅ Breakout/breakdown level calculation
- ✅ Metadata includes all support/resistance levels

**Example:**
```python
test_buy_signal_breakout_above_high()
# Period high = 102.5, breakout level = 102.5 * 1.01 = 103.525
# Current price 104.0 exceeds breakout -> buy signal
```

#### test_strategy_rsi.py
Tests RSI (Relative Strength Index) strategy.

**Key Tests:**
- ✅ Buy signal when RSI oversold (<30)
- ✅ Hold signal when RSI neutral (30-70)
- ✅ Sell signal when RSI overbought (>70)
- ✅ Stop-loss trigger
- ✅ RSI calculation accuracy
- ✅ Edge cases (all gains, all losses)
- ✅ RSI boundary validation (0-100 range)
- ✅ Insufficient data handling

**Example:**
```python
test_rsi_calculation_accuracy()
# All rising prices -> RSI approaches 100
# All falling prices -> RSI approaches 0
```

### Core Functionality Tests

#### test_screener.py
Tests top gainers screening logic.

**Key Tests:**
- ✅ Filters stocks by minimum price and volume
- ✅ Sorts by percentage gain
- ✅ Returns top N gainers

#### test_security.py
Tests API security checks.

**Key Tests:**
- ✅ API token validation
- ✅ Authorization header checking

#### test_signals_updated.py
Tests signal generation and event broadcasting.

**Key Tests:**
- ✅ SignalAgent generates signals from market data
- ✅ SignalsUpdated events are published
- ✅ Signal format and content validation

#### test_trade_interval.py
Tests trade interval timing logic.

**Key Tests:**
- ✅ Trade interval respects configured minutes
- ✅ Timing calculations are accurate

## Test Structure

### Unit Tests
Each test file contains isolated unit tests for a specific module:
- Test individual functions and methods
- Mock external dependencies (broker API, file system)
- Fast execution

### Test Patterns

**1. Arrange-Act-Assert Pattern:**
```python
def test_buy_signal_strong_momentum(self):
    # Arrange - Set up test data
    bars = pd.DataFrame({...})

    # Act - Execute the function
    signal = self.strategy.analyze(...)

    # Assert - Verify results
    self.assertEqual(signal.action, SignalType.BUY)
```

**2. Mocking External Dependencies:**
```python
@patch('backtest.data.AlpacaBroker')
def test_download_creates_csv(self, mock_broker_class):
    mock_broker = Mock()
    mock_broker_class.return_value = mock_broker
    # Test without hitting real Alpaca API
```

**3. Temporary Test Resources:**
```python
def setUp(self):
    self.test_dir = tempfile.mkdtemp()

def tearDown(self):
    shutil.rmtree(self.test_dir)  # Clean up
```

## Writing New Tests

### Guidelines

1. **Test one thing per test method**
   - Keep tests focused and simple
   - Name describes what is being tested

2. **Use descriptive test names**
   ```python
   def test_buy_signal_when_rsi_oversold(self):  # Good
   def test_rsi_1(self):  # Bad
   ```

3. **Include edge cases**
   - Empty data
   - Zero values
   - Very large values
   - Boundary conditions

4. **Test both success and failure paths**
   ```python
   def test_valid_signal_generation(self):  # Success
   def test_insufficient_data_returns_hold(self):  # Failure
   ```

### Example Template

```python
"""Tests for module_name.py - Brief description."""

import unittest
from module_name import FunctionToTest


class TestFunctionName(unittest.TestCase):
    """Test description."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_data = {...}

    def test_expected_behavior(self):
        """Test what happens in normal case."""
        result = FunctionToTest(self.test_data)
        self.assertEqual(result, expected_value)

    def test_edge_case(self):
        """Test edge case behavior."""
        result = FunctionToTest(edge_case_input)
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()
```

## Common Assertions

```python
# Equality
self.assertEqual(a, b)
self.assertNotEqual(a, b)

# Truth
self.assertTrue(x)
self.assertFalse(x)

# None
self.assertIsNone(x)
self.assertIsNotNone(x)

# Numeric comparisons
self.assertGreater(a, b)
self.assertLess(a, b)
self.assertAlmostEqual(a, b, places=2)  # For floats

# Membership
self.assertIn(item, container)
self.assertNotIn(item, container)

# Type checking
self.assertIsInstance(obj, MyClass)
```

## Debugging Failed Tests

### View detailed output:
```bash
python -m unittest tests.test_name -v
```

### Run single failing test:
```bash
python -m unittest tests.test_file.TestClass.test_method
```

### Add debug prints:
```python
def test_something(self):
    result = function_under_test()
    print(f"Result: {result}")  # Prints during test
    self.assertEqual(result, expected)
```

### Use Python debugger:
```python
import pdb

def test_something(self):
    pdb.set_trace()  # Breakpoint
    result = function_under_test()
```

## Continuous Integration

When Phase 11 is implemented, tests will run automatically on:
- Every commit (GitHub Actions)
- Pull requests
- Before deployment

**Target:** 80% code coverage for new code

## Test Statistics

**Current Coverage:**

| Module | Test File | Test Count | Lines |
|--------|-----------|------------|-------|
| backtest/data.py | test_backtest_data.py | 8 tests | 362 lines |
| backtest/metrics.py | test_backtest_metrics.py | 17 tests | 264 lines |
| backtest/engine.py | test_backtest_engine.py | 8 tests | 293 lines |
| backtest/results.py | test_backtest_results.py | 9 tests | 246 lines |
| strategies/momentum.py | test_strategy_momentum.py | 12 tests | 270 lines |
| strategies/mean_reversion.py | test_strategy_mean_reversion.py | 12 tests | 241 lines |
| strategies/breakout.py | test_strategy_breakout.py | 12 tests | 257 lines |
| strategies/rsi.py | test_strategy_rsi.py | 13 tests | 289 lines |

**Total:** ~91 tests across 8 new test files + 4 existing test files

## Future Testing Plans

**Phase 11 - Testing & Reliability:**
- [ ] Migrate to pytest framework
- [ ] Add integration tests for agent interactions
- [ ] Add end-to-end tests for full trading cycles
- [ ] Set up CI/CD pipeline with GitHub Actions
- [ ] Add code coverage reporting
- [ ] Add performance benchmarks

---

*Last updated: 2025-01-19*

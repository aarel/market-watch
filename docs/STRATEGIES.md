# Trading Strategies Documentation

> Pluggable trading strategies for Market-Watch

**Last updated: 2026-01-23**

## Overview

Market-Watch supports multiple trading strategies that can be selected via the `STRATEGY` environment variable. Each strategy has its own set of parameters that can be tuned in the `.env` file or via the API at runtime.

---

## Available Strategies

### 1. Momentum Strategy

**Type:** Trend Following
**Best For:** Trending markets with clear directional moves

**Logic:**
- Buys stocks with strong upward momentum over a defined lookback period.
- Sells when momentum reverses or a stop-loss is triggered.
- Aims to ride established trends.

**Parameters:**
- `lookback_days`: Period for momentum calculation.
- `momentum_threshold`: Minimum positive momentum % required to trigger a buy signal.
- `sell_threshold`: Momentum % below which a sell signal is triggered for an existing position.
- `stop_loss_pct`: The fixed percentage drop from the entry price that triggers an automatic sell.

**Configuration (`.env`):**
```bash
# Core selection
STRATEGY=momentum

# Strategy-specific parameters
LOOKBACK_DAYS=20
MOMENTUM_THRESHOLD=0.02
SELL_THRESHOLD=-0.01
STOP_LOSS_PCT=0.05
```

---

### 2. Mean Reversion Strategy

**Type:** Mean Reversion
**Best For:** Sideways or range-bound markets where prices oscillate around an average.

**Logic:**
- Calculates a simple moving average (SMA).
- Buys when the price drops significantly below the SMA (considered "oversold").
- Sells when the price returns to or exceeds the SMA.

**Parameters:**
- `ma_period`: The lookback period for the moving average calculation.
- `deviation_threshold`: The percentage the price must drop below the MA to be considered oversold and trigger a buy.
- `return_threshold`: The percentage the price must rise above the MA to trigger a sell, confirming reversion.
- `stop_loss_pct`: The fixed percentage drop from the entry price that triggers an automatic sell.

**Configuration (`.env`):**
```bash
# Core selection
STRATEGY=mean_reversion

# Strategy-specific parameters
# NOTE: This strategy's parameters are not currently exposed via .env
# It uses hardcoded defaults in strategies/mean_reversion.py
# To configure, you must edit the __init__ method in the file.
# (ma_period=20, deviation_threshold=0.03, return_threshold=0.01)
```

---

### 3. Breakout Strategy

**Type:** Momentum / Breakout
**Best For:** Consolidating markets that are preparing for a strong directional move.

**Logic:**
- Tracks the highest high and lowest low over a lookback period to form a channel.
- Buys when the price breaks decisively above the channel's high.
- Sells when the price breaks below the channel's low.

**Parameters:**
- `lookback_days`: The period for establishing the high/low channel.
- `breakout_threshold`: The percentage the price must exceed the high to confirm a breakout.
- `breakdown_threshold`: The percentage the price must drop below the low to confirm a breakdown.
- `stop_loss_pct`: The fixed percentage drop from the entry price that triggers an automatic sell.

**Configuration (`.env`):**
```bash
# Core selection
STRATEGY=breakout

# Strategy-specific parameters
# NOTE: This strategy's parameters are not currently exposed via .env
# It uses hardcoded defaults in strategies/breakout.py
# To configure, you must edit the __init__ method in the file.
# (lookback_days=20, breakout_threshold=0.01, breakdown_threshold=0.01)
```

---

### 4. RSI Strategy

**Type:** Mean Reversion (Oscillator-based)
**Best For:** Markets with clear overbought/oversold cycles.

**Logic:**
- Calculates the Relative Strength Index (RSI), an oscillator that moves between 0 and 100.
- Buys when the RSI indicates the asset is oversold (e.g., below 30).
- Sells when the RSI indicates the asset is overbought (e.g., above 70).

**Parameters:**
- `rsi_period`: The lookback period for the RSI calculation.
- `oversold_level`: The RSI level below which the asset is considered oversold.
- `overbought_level`: The RSI level above which the asset is considered overbought.
- `stop_loss_pct`: The fixed percentage drop from the entry price that triggers an automatic sell.

**Configuration (`.env`):**
```bash
# Core selection
STRATEGY=rsi

# Strategy-specific parameters
# NOTE: This strategy's parameters are not currently exposed via .env
# It uses hardcoded defaults in strategies/rsi.py
# To configure, you must edit the __init__ method in the file.
# (rsi_period=14, oversold_level=30, overbought_level=70)
```
---

## Using Strategies

### Via Configuration (`.env`)

Set in your `.env` file and restart the server. This is the primary method for selecting a strategy.

```bash
# Select strategy
STRATEGY=momentum

# Configure its parameters
LOOKBACK_DAYS=20
MOMENTUM_THRESHOLD=0.02
```

### Programmatically

You can instantiate and use strategy classes directly in your own Python scripts.

```python
from strategies import MomentumStrategy, get_strategy
import pandas as pd

# Direct instantiation with custom parameters
strategy = MomentumStrategy(
    lookback_days=30,
    momentum_threshold=0.03
)

# Or get a strategy from the registry
# Note: This will use default __init__ params, not .env values
rsi_strategy = get_strategy('rsi')

# Create some dummy data for analysis
# In the real app, this is provided by the DataAgent
bars = pd.DataFrame({
    'open': [100, 102, 101, 103, 105],
    'high': [102, 103, 102, 104, 106],
    'low': [99, 101, 100, 102, 104],
    'close': [101, 101, 102, 103, 105],
    'volume': [1000, 1200, 1100, 1300, 1400]
})

# Generate a signal
signal = rsi_strategy.analyze(
    symbol='AAPL',
    bars=bars,
    current_price=105.0,
    current_position=None
)

print(f"Signal for AAPL: {signal.action.value} because {signal.reason}")
```

### With Backtesting

The backtesting engine can run any of the registered strategies.

```python
from backtest import BacktestEngine, HistoricalData
from strategies import get_strategy

# Load historical data
data = HistoricalData()
data.download(['AAPL', 'GOOGL'], start='2021-01-01', end='2023-12-31')

# Get a strategy instance
# You can override its default parameters here
strategy = get_strategy('breakout', lookback_days=30, breakout_threshold=0.02)

# The backtest engine is not yet configured to accept a strategy object.
# This functionality is planned for a future update.
# Currently, it uses the strategy set in the environment.
```

---

## Creating a Custom Strategy

### Step 1: Create Your Strategy Class
Create a new file, e.g., `strategies/my_strategy.py`. Define your class inheriting from `Strategy`.

```python
# strategies/my_strategy.py
from strategies.base import Strategy, TradingSignal, SignalType
import pandas as pd
from typing import Optional

class MyCustomStrategy(Strategy):
    """A simple strategy that buys on two consecutive up-days."""

    @property
    def name(self) -> str:
        return "My Simple Green Day Strategy"

    @property
    def description(self) -> str:
        return "Buys if the last two days were positive."

    @property
    def required_history(self) -> int:
        return 3 # Need 3 bars for 2 days of changes

    def analyze(
        self,
        symbol: str,
        bars: pd.DataFrame,
        current_price: float,
        current_position: Optional[dict] = None
    ) -> TradingSignal:
        """Generate a trading signal based on consecutive green days."""
        if len(bars) < self.required_history:
            return TradingSignal(symbol, SignalType.HOLD, 0.0, "Insufficient history", current_price)

        day1_return = (bars['close'].iloc[-2] - bars['close'].iloc[-3]) / bars['close'].iloc[-3]
        day2_return = (bars['close'].iloc[-1] - bars['close'].iloc[-2]) / bars['close'].iloc[-2]

        is_buy_signal = day1_return > 0 and day2_return > 0

        if current_position is None and is_buy_signal:
            return TradingSignal(
                symbol=symbol,
                action=SignalType.BUY,
                strength=0.8,
                reason="Two consecutive green days",
                current_price=current_price
            )
        elif current_position is not None and not is_buy_signal:
            return TradingSignal(
                symbol=symbol,
                action=SignalType.SELL,
                strength=0.5,
                reason="Green day streak broken",
                current_price=current_price
            )

        return TradingSignal(
            symbol=symbol,
            action=SignalType.HOLD,
            strength=0.0,
            reason="Condition not met",
            current_price=current_price
        )
```

### Step 2: Register Your Strategy
In `strategies/__init__.py`, import your new class and add it to the `AVAILABLE_STRATEGIES` dictionary.

```python
# strategies/__init__.py
# ... other imports
from .my_strategy import MyCustomStrategy

AVAILABLE_STRATEGIES = {
    # ... other strategies
    'my_custom': MyCustomStrategy,
}
```

### Step 3: Use It
Set the `STRATEGY` variable in your `.env` file and restart the server.
```bash
STRATEGY=my_custom
```

---

## Strategy Selection Guidelines

(Content unchanged)

---

## Performance Comparison

(Content unchanged)

---

## Best Practices

(Content unchanged)

---

## Troubleshooting

(Content unchanged)

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Autonomous trading bot for Alpaca brokerage with web UI. Implements momentum/trend following strategy with automatic paper trading and optional live trading. Includes backtesting capabilities for strategy validation.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run web server (UI + auto-trading)
python server.py
# Then open http://localhost:8000

# Run backtests
python -m backtest --download --symbols AAPL,GOOGL,MSFT --start 2021-01-01
python -m backtest --symbols AAPL,GOOGL,MSFT --start 2022-01-01 --benchmark SPY
```

## Architecture

```
server.py           # FastAPI backend + WebSocket - main entry point
├── agents/         # Agent-based trading system
│   ├── data_agent.py      # Fetches market data
│   ├── signal_agent.py    # Generates buy/sell signals (momentum strategy)
│   ├── risk_agent.py      # Validates trades against risk rules
│   ├── execution_agent.py # Executes approved trades
│   ├── monitor_agent.py   # Tracks positions and P&L
│   └── alert_agent.py     # Handles notifications
├── broker.py       # Alpaca API integration - orders, positions, market data
├── fake_broker.py  # Simulated broker for testing (no API needed)
├── config.py       # Configuration from environment
├── screener.py     # Top gainers screening
├── universe.py     # Stock universe definitions
├── backtest/       # Backtesting engine
│   ├── data.py     # Historical data management
│   ├── engine.py   # Backtest simulation
│   ├── metrics.py  # Performance calculations
│   └── cli.py      # Command-line interface
└── static/
    └── index.html  # Web UI dashboard
```

**Agent-based data flow:**
1. `server.py` starts → initializes broker and agent coordinator
2. `DataAgent` fetches market data periodically
3. `SignalAgent` analyzes data → generates buy/sell signals
4. `RiskAgent` validates signals against risk rules
5. `ExecutionAgent` executes approved trades
6. `MonitorAgent` tracks positions and broadcasts updates
7. WebSocket sends real-time updates to UI

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/status` | GET | Account, positions, signals, bot state |
| `/api/config` | GET/POST | Read/update configuration |
| `/api/trade` | POST | Execute manual trade |
| `/api/bot/start` | POST | Enable auto-trading |
| `/api/bot/stop` | POST | Disable auto-trading |
| `/api/logs` | GET | Recent activity log |
| `/ws` | WebSocket | Real-time updates |

## Configuration

Copy `.env.example` to `.env` and set:
- `ALPACA_API_KEY` / `ALPACA_SECRET_KEY` - from Alpaca dashboard
- `TRADING_MODE` - "paper" or "live"
- `AUTO_TRADE` - "true" to trade automatically
- `TRADE_INTERVAL_MINUTES` - how often to run (default 5)
- `SIMULATION_MODE` - "true" to use fake broker (no API needed)

Key parameters adjustable via UI:
- Watchlist symbols
- Momentum threshold (buy signal)
- Sell threshold
- Stop loss percentage
- Max position size

## Backtesting

Validate strategies before risking capital:

```bash
# Download historical data
python -m backtest --download --symbols AAPL,GOOGL,MSFT,SPY --start 2020-01-01

# Run backtest with benchmark comparison
python -m backtest --symbols AAPL,GOOGL,MSFT --start 2021-01-01 --benchmark SPY

# Export results
python -m backtest --symbols AAPL,GOOGL --start 2022-01-01 \
    --output results.json --trades-csv trades.csv
```

See `docs/BACKTEST.md` for full documentation.

## Constraints

- Paper trading is default
- Live trading requires `TRADING_MODE=live` in `.env`
- Config changes via UI are in-memory only (reset on restart)
- Backtest requires Alpaca credentials for data download (or use cached data)

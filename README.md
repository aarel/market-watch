# Market Watch Trading Bot

![Tests](https://github.com/USERNAME/REPO/actions/workflows/tests.yml/badge.svg)

Autonomous trading bot with web UI, multiple trading strategies, and backtesting capabilities. Connects to Alpaca brokerage for commission-free paper and live trading.

## Quick Start

### 1. Get Alpaca Account
1. Sign up at https://alpaca.markets
2. Go to Paper Trading dashboard
3. Generate API keys

### 2. Setup
```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your Alpaca API keys
```

### 3. Run
```bash
python server.py
```
Open http://localhost:8000

### 4. Backtest (Optional)
```bash
# Download historical data
python -m backtest --download --symbols AAPL,GOOGL,MSFT --start 2021-01-01

# Run backtest with benchmark
python -m backtest --symbols AAPL,GOOGL,MSFT --start 2022-01-01 --benchmark SPY
```

## Web UI Features

- **Account overview** - portfolio value, buying power, cash
- **Positions** - current holdings with P/L
- **Watchlist signals** - momentum analysis for each symbol
- **Analytics & Reporting** - historical equity curve, performance metrics, and trade history
- **Risk Management** - configurable limits for circuit breakers, position sizing, and exposure
- **Configuration** - adjust strategy parameters live
- **Manual trading** - execute trades directly
- **Activity log** - real-time trade and event log
- **Start/Stop** - control auto-trading

## How It Works

Agent-based architecture with event-driven communication:

1. **DataAgent** fetches market data every N minutes (configurable)
2. **SignalAgent** analyzes data using selected strategy (momentum, mean reversion, breakout, or RSI)
3. **RiskAgent** validates signals against risk limits (position size, daily trade limits)
4. **ExecutionAgent** places approved orders through Alpaca
5. **MonitorAgent** tracks open positions and triggers stop-losses
6. **AlertAgent** broadcasts updates to UI via WebSocket

All agents communicate through an event bus for decoupled, asynchronous operation.

## Architecture

```
server.py              - FastAPI web server (main entry point)
├── agents/            - Agent-based trading system
│   ├── coordinator.py    - Orchestrates all agents
│   ├── data_agent.py     - Market data fetching
│   ├── signal_agent.py   - Signal generation
│   ├── risk_agent.py     - Risk validation
│   ├── execution_agent.py - Trade execution
│   ├── monitor_agent.py   - Position monitoring
│   └── alert_agent.py     - Logging & notifications
├── strategies/        - Pluggable trading strategies
│   ├── momentum.py       - Momentum/trend following
│   ├── mean_reversion.py - Mean reversion
│   ├── breakout.py       - Breakout strategy
│   └── rsi.py            - RSI overbought/oversold
├── backtest/          - Backtesting engine
│   ├── engine.py         - Event-driven simulation
│   ├── data.py           - Historical data management
│   ├── metrics.py        - Performance calculations
│   └── cli.py            - Command-line interface
├── broker.py          - Alpaca API integration
├── fake_broker.py     - Simulated broker for testing
├── config.py          - Configuration management
└── static/
    └── index.html     - Web dashboard UI
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed technical documentation.

## Configuration

All settings are configured via environment variables in the `.env` file. Many of these can also be adjusted live in the web UI, and those changes will persist across restarts.

| Setting | Default | Description |
|---------|---------|-------------|
| `ALPACA_API_KEY` | - | Alpaca API key (required). |
| `ALPACA_SECRET_KEY` | - | Alpaca secret key (required). |
| `TRADING_MODE` | paper | Universe selection: "simulation", "paper", or "live". **Simulation** uses FakeBroker with synthetic data and NYSE market hours. **Paper** uses Alpaca paper trading. **Live** uses real capital - use with extreme caution. |
| `AUTO_TRADE` | true | Enable automatic trading. |
| `STRATEGY` | momentum | Strategy to use ("momentum", "mean_reversion", "breakout", "rsi"). |
| `TRADE_INTERVAL_MINUTES`| 5 | How often the bot fetches data and evaluates trades. |
| `API_TOKEN` | (empty) | If set, requires all API requests to be authenticated. |
| `WATCHLIST_MODE` | top_gainers | "static" (uses hardcoded watchlist) or "top_gainers" (dynamic). |
| `TOP_GAINERS_COUNT` | 20 | Number of symbols for the top gainers list. |
|`TOP_GAINERS_MIN_PRICE`| 5 | Minimum price filter for gainers. |
| `FMP_API_KEY` | (empty) | Financial Modeling Prep API key, used for updating sector map. |
| `STOP_LOSS_PCT` | 0.05 | Stop loss percentage (e.g., 0.05 = 5%). |
| `MAX_POSITION_PCT` | 0.5 | Max percentage of portfolio to allocate to a single position. |
| `MAX_OPEN_POSITIONS` | 10 | Hard cap on the number of concurrent open positions. |
| `MAX_DAILY_TRADES` | 5 | Safety limit to prevent runaway trading. Resets daily. |
| `DAILY_LOSS_LIMIT_PCT`| 0.03 | Pauses all new buy orders if portfolio equity drops by this percentage in a day. |
| `MAX_DRAWDOWN_PCT` | 0.15 | Pauses all new buy orders if portfolio equity drops from its peak by this percentage. |
| `MAX_SECTOR_EXPOSURE_PCT` | 0.30 | Max percentage of portfolio allowed in a single market sector. |
|`MAX_CORRELATED_EXPOSURE_PCT`| 0.40 | Max percentage of portfolio allowed in highly correlated assets. |
| `CONFIG_STATE_PATH`| data/config_state.json | File path to save and load runtime configuration changes. |
| `ANALYTICS_ENABLED`| true | Enable the analytics engine to capture performance data. |
| `OBSERVABILITY_ENABLED`| true | Enable structured logging for agent evaluations. |

**Configuration Priority:**
- `.env` file is loaded on startup
- `config_state.json` overrides .env values if it exists (runtime changes from UI)
- Changes made via UI persist to `config_state.json` and survive restarts
- See [CONFIG_ALIGNMENT_NOTES.md](CONFIG_ALIGNMENT_NOTES.md) for details

For detailed documentation on risk controls and strategy parameters, see:
- **[docs/RISK.md](docs/RISK.md)**
- **[docs/STRATEGIES.md](docs/STRATEGIES.md)**

## Observability

The system emits structured JSONL logs for all agent events and can generate an evaluation report.

```bash
# Evaluate latest observability log
python -m monitoring --log logs/observability/agent_events.jsonl
```

## Analytics

- Real-time equity snapshots and trades are stored under `logs/{universe}/` (e.g., `logs/paper/equity.jsonl`, `logs/paper/trades.jsonl`) when `ANALYTICS_ENABLED=true` (default).
- UI shows equity curve, benchmark overlay (SPY by default), risk stats, and recent trades for selectable periods (30d/90d/YTD/All).
- Export trades via UI ("Export CSV") or `GET /api/trades/export`.
- Export equity via `GET /api/analytics/equity/export?period=...` (CSV).
- Frontend auto-refreshes analytics; placeholders show when no data yet (let the bot run a few cycles).
- To populate analytics in simulation mode: set `TRADING_MODE=simulation`, `ANALYTICS_ENABLED=true`, start the server, and let it run 10–30 minutes; snapshots will appear in `logs/simulation/` and the dashboard metrics will fill in.

## Going Live

1. Test thoroughly in paper mode
2. Set `TRADING_MODE=live` in `.env`
3. Use live API keys from Alpaca
4. Fund account and restart server

## Documentation

Comprehensive documentation is available in the `docs/` directory:

- **[API.md](docs/API.md)** - REST API and WebSocket reference
- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - Technical architecture deep dive
- **[STRATEGIES.md](docs/STRATEGIES.md)** - Trading strategies guide
- **[BACKTEST.md](docs/BACKTEST.md)** - Backtesting documentation
- **[DEPLOYMENT.md](docs/DEPLOYMENT.md)** - Production deployment guide
- **[CONTRIBUTING.md](docs/CONTRIBUTING.md)** - Contribution guidelines
- **[FAQ.md](docs/FAQ.md)** - Frequently asked questions

Additional resources:

- **[ROADMAP.md](ROADMAP.md)** - Development roadmap and future plans
- **[CLAUDE.md](CLAUDE.md)** - AI assistant guidance for Claude Code

## Project Structure

```
server.py           - Main application entry point
agents/             - Agent-based trading system
strategies/         - Pluggable trading strategies
backtest/           - Backtesting engine
broker.py           - Alpaca API integration
fake_broker.py      - Simulated broker for testing
config.py           - Configuration management
screener.py         - Top gainers screening
universe.py         - Stock universe definitions
static/             - Web UI files
docs/               - Comprehensive documentation
.env                - Your configuration (don't commit)
```

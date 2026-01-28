# GEMINI.md: Project Context for Gemini

This document provides a comprehensive overview of the Market Watch Trading Bot project for the Gemini AI assistant. Its purpose is to serve as a detailed, instructional context for all future interactions.

## 1. Project Overview

This is a Python-based, agent-driven autonomous trading bot with multiple pluggable strategies and backtesting capabilities. It connects to the Alpaca brokerage to trade equities using strategies like momentum, mean reversion, breakout, and RSI. The project features a web-based user interface for monitoring, configuration, and manual control.

The architecture is built around a system of cooperating agents that communicate via an event bus. This allows for a modular and asynchronous design.

### Key Technologies:
- **Backend:** Python 3.10+, FastAPI
- **Broker Integration:** `alpaca-trade-api` for both paper and live trading
- **Data Analysis:** `pandas` and `numpy`
- **Configuration:** `.env` file managed via `python-dotenv`
- **UI:** A static HTML/JavaScript frontend served by FastAPI
- **Testing**: `unittest` (planned: pytest framework)
- **Backtesting**: Custom event-driven engine with historical data replay

## 2. Architecture

The application's logic is structured around an **agent-based system**, orchestrated by the `agents/coordinator.py`. The primary entry point that initializes this system is `server.py`.

### Core Components:
- **`server.py`**: The main application entry point. It starts a FastAPI web server, initializes the agent `Coordinator`, and exposes API endpoints for the frontend to consume.
- **`config.py`**: Centralized configuration module that loads settings from a `.env` file.
- **`broker.py`**: A wrapper class (`AlpacaBroker`) that encapsulates all interactions with the Alpaca API (e.g., getting account data, placing orders, fetching price data).
- **`fake_broker.py`**: Simulated broker for testing and simulation mode (no API required).
- **`static/index.html`**: The single-page web UI for interacting with the bot.
- **`strategies/`**: Pluggable trading strategy implementations (momentum, mean reversion, breakout, RSI).
- **`backtest/`**: Event-driven backtesting engine with historical data management and performance metrics.

### Agent System (`agents/`):
- **`event_bus.py` & `events.py`**: The core communication backbone. Agents publish and subscribe to events, enabling a decoupled architecture.
- **`coordinator.py`**: The central orchestrator. It initializes, starts, and stops all other agents.
- **`DataAgent`**: Responsible for fetching all necessary data on a timer (market status, prices, account info, positions, top gainers). Publishes a `MarketDataReady` event.
- **`SignalAgent`**: Subscribes to `MarketDataReady`. It analyzes the data using the configured strategy (momentum, mean reversion, breakout, or RSI) and generates `SignalGenerated` events (buy, sell, or hold).
- **`RiskAgent`**: Subscribes to `SignalGenerated`. It performs risk checks, such as verifying the trade against the maximum daily trade limit. Publishes `RiskCheckPassed` or `RiskCheckFailed`.
- **`ExecutionAgent`**: Subscribes to `RiskCheckPassed`. It executes the trade by submitting an order via the `AlpacaBroker`. It also handles manual trade requests.
- **`MonitorAgent`**: Periodically checks active positions for conditions that might require action, such as triggering a stop-loss.
- **`AlertAgent`**: Subscribes to various events to provide logging and broadcast real-time updates to the UI via WebSockets.

### Simulation Mode:
-   **`SIMULATION_MODE`**: Set to `"true"` in `.env` to run the bot in a completely simulated environment. This bypasses real market hours and API calls, using an in-memory `FakeBroker` for testing logic and UI outside of market hours.
-   **`SIMULATION_JIGGLE_FACTOR`**: Controls the volatility of price changes in simulation mode.

## 3. Building and Running

The project is designed to be run from the command line.

### Setup:
1.  **Install Dependencies:** Create and activate a virtual environment, then run:
    ```bash
    pip install -r requirements.txt
    ```
2.  **Configure Environment:** Copy the example `.env` file and fill in your Alpaca API keys and any other custom settings.
    ```bash
    cp .env.example .env
    # Edit .env with a text editor
    ```

### Running the Application:
-   To run the main web server and the agent-based bot, execute:
    ```bash
    python server.py
    ```
-   After starting, the UI is accessible at `http://localhost:8000`.

### Running Backtests:
- To backtest strategies on historical data:
    ```bash
    # Download historical data
    python -m backtest --download --symbols AAPL,GOOGL,MSFT --start 2021-01-01

    # Run backtest with benchmark comparison
    python -m backtest --symbols AAPL,GOOGL,MSFT --start 2022-01-01 --benchmark SPY

    # Export results
    python -m backtest --symbols AAPL --start 2023-01-01 --output results.json --trades-csv trades.csv
    ```

### Running Tests:
- To run the existing unit tests:
    ```bash
    python -m unittest tests/test_screener.py
    ```

## 4. Development Conventions

- **Style:** The code generally follows PEP 8, using type hints extensively.
- **Asynchronous:** The core agent-based system is asynchronous, using Python's `asyncio` library. All new agent logic should be written as `async`.
- **Configuration:** All configuration should be managed via the `.env` file and accessed through the `config.py` module. Do not hardcode secrets or environment-specific values.
- **Modularity:** The agent architecture is designed for modularity. New behaviors or strategies should be implemented as new agents or by modifying existing ones, respecting the event-driven communication pattern.
- **Error Handling:** Agents should be robust and handle potential API errors or data issues gracefully, logging errors through the `AlertAgent`.
- **Strategy Selection:** Set `STRATEGY` in `.env` to choose between "momentum", "mean_reversion", "breakout", or "rsi". New strategies should inherit from the `Strategy` base class.

## 5. Documentation

Comprehensive documentation is available in the `docs/` directory:

- **API.md** - REST API and WebSocket reference
- **ARCHITECTURE.md** - Detailed technical architecture
- **STRATEGIES.md** - Trading strategies documentation
- **BACKTEST.md** - Backtesting guide
- **DEPLOYMENT.md** - Production deployment instructions
- **CONTRIBUTING.md** - Contribution guidelines
- **FAQ.md** - Frequently asked questions

See also:
- **ROADMAP.md** - Development roadmap and future phases
- **CLAUDE.md** - Guidance for Claude Code AI assistant

# API Reference

> REST API and WebSocket documentation for Market-Watch server

**Last updated: 2026-01-23**

## Base URL

```
http://localhost:8000
```

Configure host and port in `.env`:
```bash
API_HOST=127.0.0.1
API_PORT=8000
```

---

## Authentication

If `API_TOKEN` is set in the `.env` file, all API requests must include the token. The token can be provided in two ways:

1.  **Authorization Header (recommended):**
    ```
    Authorization: Bearer your_api_token_here
    ```

2.  **Custom Header:**
    ```
    X-API-Key: your_api_token_here
    ```

3.  **WebSocket Connection:**
    Append as a query parameter:
    ```
    ws://localhost:8000/ws?token=your_api_token_here
    ```

If `API_TOKEN` is not set, access is restricted to localhost requests by default for security.

---

## Core REST Endpoints

### `GET /api/status`

Get the current, consolidated status of the entire system. This is the primary polling endpoint for the UI.

**Response:**
```json
{
  "account": {
    "portfolio_value": 100000.00,
    "buying_power": 50000.00,
    "cash": 50000.00,
    "equity": 100000.00
  },
  "market_open": true,
  "simulation": false,
  "trading_mode": "paper",
  "positions": [
    {
      "symbol": "AAPL",
      "qty": 10,
      "market_value": 1550.00,
      "avg_entry_price": 150.00,
      "unrealized_pl": 50.00,
      "unrealized_plpc": 3.33
    }
  ],
  "signals": [
    {
      "symbol": "GOOGL",
      "action": "buy",
      "strength": 0.035,
      "reason": "Strong momentum (3.5% over 20 days)",
      "current_price": 140.25,
      "momentum": 0.035
    }
  ],
  "bot": {
    "running": true,
    "auto_trade": true,
    "daily_trades": 1,
    "max_daily_trades": 10,
    "error": null,
    "market_open": true,
    "simulation": false,
    "trading_mode": "paper"
  },
  "agents": { /* status of each agent */ },
  "top_gainers": [ /* list of top gainer objects */ ],
  "market_indices": [ /* list of market index objects */ ],
  "expectations": { /* map of agents to their expectations */ }
}
```

---

### `GET /api/config`

Get the current, fully resolved application configuration, including values from `.env` and any runtime changes.

**Response:**
A JSON object containing all key-value pairs from the `config.py` module.
```json
{
  "strategy": "momentum",
  "watchlist": ["SPY", "QQQ"],
  "watchlist_mode": "top_gainers",
  "max_position_pct": 0.25,
  "max_daily_trades": 10,
  "trade_interval": 5,
  "auto_trade": true,
  "...": "..."
}
```

### `POST /api/config`

Update one or more configuration values at runtime. Changes are persisted to `data/config_state.json` and will be loaded on the next startup, overriding `.env` values.

**Request Body:** A JSON object with any of the supported fields.
```json
{
  "watchlist": ["AAPL", "TSLA"],
  "momentum_threshold": 0.03,
  "stop_loss_pct": 0.04
}
```

**Supported Fields:** All keys listed in the `_config_snapshot` function in `server.py`, including `strategy`, `watchlist`, `watchlist_mode`, risk parameters (`max_position_pct`, `daily_loss_limit_pct`, etc.), and trading parameters (`trade_interval`, `auto_trade`, etc.).

### `POST /api/config/reset`

Deletes the saved configuration file (`data/config_state.json`). The application will revert to the settings from the `.env` file upon the next restart.

**Response:**
```json
{
  "status": "ok",
  "message": "Configuration state reset. Restart the application to apply .env defaults."
}
```

---

### `POST /api/trade`

Execute a manual trade. Supports trading by `notional` (dollar amount) or `qty` (number of shares).

**Request Body:**
```json
{
  "symbol": "AAPL",
  "action": "buy",
  "mode": "notional",
  "amount": 1000
}
```
or
```json
{
  "symbol": "AAPL",
  "action": "sell",
  "mode": "qty",
  "qty": 10.5
}
```

---

### Bot Control Endpoints

-   **`POST /api/bot/start`**: Enable auto-trading.
-   **`POST /api/bot/stop`**: Disable auto-trading.
-   **`POST /api/refresh`**: Manually trigger a data refresh and signal generation cycle.

---

### Data & History Endpoints

-   **`GET /api/trades`**: Get recent trade/order history.
    -   `limit` (query param): Number of orders to return (default: 30).
-   **`GET /api/trades/export`**: Export all trade/order history as a CSV file.
-   **`GET /api/logs`**: Get recent activity logs from the `AlertAgent`.
    -   `count` (query param): Number of logs to return (default: 50).

---

## Analytics Endpoints

These endpoints power the Analytics & Reporting dashboard. They require `ANALYTICS_ENABLED=true` (default).

-   **`GET /api/analytics/equity`**: Get historical portfolio equity values for a given period.
    -   `period` (query param): Timeframe, e.g., `30d`, `90d`, `ytd`, `all` (default: `30d`).
    -   `benchmark` (query param): Symbol to use as a benchmark, e.g., `SPY` (default: `SPY`).
-   **`GET /api/analytics/summary`**: Get summary performance metrics for the equity curve.
    -   `period` (query param): Timeframe.
-   **`GET /api/analytics/trades`**: Get trades logged in the analytics store for the period.
    -   `period` (query param): Timeframe.
    -   `limit` (query param): Max number of trades (default: 100).
-   **`GET /api/analytics/trade_stats`**: Get aggregate statistics about trades.
    -   `period` (query param): Timeframe.
-   **`GET /api/analytics/positions`**: Get current positions with portfolio weights.
-   **`GET /api/analytics/report`**: A simple HTML report stub (for future PDF generation).
-   **`GET /api/analytics/equity/export`**: Export equity curve for a period as a CSV file.
    -   `period` (query param): Timeframe.

---

## Observability Endpoints

-   **`GET /api/observability`**: Get the summary of the latest observability evaluation run.
-   **`POST /api/observability/evaluate`**: Trigger an on-demand evaluation run.
-   **`GET /api/observability/expectations`**: Get the default agent expectations.
-   **`GET /api/observability/logs`**: Get raw observability event logs.
    -   `limit` (query param): Number of logs (default: 30).
    -   `level` (query param): Minimum level, e.g., `warn`.

---

## UI-Centric Endpoints

-   **`GET /`**: Serves the main `static/index.html` UI.
-   **`GET /api/assets/names`**: Get company names for a comma-separated list of symbols.
    -   `symbols` (query param): e.g., `AAPL,GOOGL`.

---

## WebSocket

### Connection

Connect to the WebSocket for real-time UI updates.

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  if (msg.event === 'status') {
    // Full status update
    console.log('Status:', msg.account, msg.positions);
  } else if (msg.event === 'log') {
    // A single log entry
    console.log('Log:', msg.entry.message);
  }
};
```

### Message Format

All messages are JSON objects with an `event` field indicating the type of update.

```json
{
  "event": "event_name",
  "...": "..."
}
```

### Message Events

-   **`event: "status"`**: A complete snapshot of the bot's state. Includes `account`, `positions`, `bot`, `top_gainers`, and `market_indices` data. This is the main message for UI updates.
-   **`event: "agents"`**: A detailed status of all running agents.
-   **`event: "signals"`**: An update containing the latest list of generated trading signals.
-   **`event: "log"`**: A single log entry object, created by the `AlertAgent` from various system events (e.g., trade execution, risk check failure, etc.).
-   **`event: "observability"`**: The result of a scheduled or on-demand observability evaluation.

---

## Error Responses

All endpoints return errors in this format on failure:

```json
{
  "detail": "Descriptive error message"
}
```

**HTTP Status Codes:**
- `200`: Success
- `400`: Bad Request
- `401`: Unauthorized (Invalid `API_TOKEN`)
- `403`: Forbidden (Request from non-localhost without a token, or disallowed origin)
- `404`: Not Found
- `500`: Internal Server Error
- `503`: Service Unavailable (occurs if an endpoint is hit before the bot is fully initialized)

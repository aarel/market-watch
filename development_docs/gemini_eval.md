# Gemini Self-Evaluation: market-watch Architecture

> **Context:** You (Gemini) were given a high-level description of market-watch and
> produced architecture assumptions and advice across several exchanges.  This
> document states what the codebase actually contains.  Score yourself against it.

---

## 1. What you got right

- Multi-agent pipeline with distinct monitoring, signaling, risk, and execution roles.
- Alpaca as the broker, with notional (fractional) order support.
- Top-gainers as the core watchlist strategy.
- Momentum as the primary signal driver.
- Paper-trading-first recommendation is sound engineering practice and the system
  already supports it natively (Universe.PAPER).
- General concern about slippage/spread on small notional trades is valid.
- Suggestion to check buying power before execution — the Risk Agent already does this.

---

## 2. What you got wrong — with the actual facts

### 2a. Agent names and responsibilities

| You said | Reality |
|----------|---------|
| "Sentinel (Monitoring Agent)" | **DataAgent** — fetches market data on a fixed interval, assembles account + position + price + bar + top-gainers + market-indices into one event. No real-time websocket stream ingestion; it polls. |
| "Analyst (Signaling Agent)" | **SignalAgent** — subscribes to `MarketDataReady`, delegates to a pluggable strategy via `strategy.analyze()`, publishes `SignalGenerated`. It does **not** do its own technical analysis; that lives in the strategy classes. |
| "Auditor (Risk Agent)" | **RiskAgent** — runs a chain of checks (see §2c below). Much more than the toy `risk_auditor()` snippet you wrote. |
| "Executioner (Trading Agent)" | **ExecutionAgent** — submits orders, polls for fill, publishes `OrderExecuted` / `OrderFailed`. Also handles manual (non-risk-checked) trades via `execute_manual_trade()`. |

### 2b. Lookback window

You said **20-day momentum window**.
Actual: `LOOKBACK_DAYS = 30` (config default).  The strategies receive 30 days of bars.

### 2c. Risk checks — you dramatically understated the scope

Your Python snippet checked one thing (spread vs. expected gain).
The actual RiskAgent runs this ordered chain on every buy signal:

1. Skip if action == "hold"
2. Daily trade count < `MAX_DAILY_TRADES` (default 5)
3. Portfolio value > 0
4. Circuit breaker not tripped (tracks daily-loss limit and max drawdown)
5. Open positions < `MAX_OPEN_POSITIONS` (default 20)
6. Position sizing via `PositionSizer` — scales trade dollar amount by signal strength (0–1)
7. Trade value >= `MIN_TRADE_VALUE` ($1.00)
8. Adequate buying power for the sized trade
9. Sector concentration <= `MAX_SECTOR_EXPOSURE_PCT`
10. Correlation-based exposure <= `MAX_CORRELATED_EXPOSURE_PCT`
    (Pearson correlation computed over `CORRELATION_LOOKBACK_DAYS` bars; flags
    positions with corr >= `CORRELATION_THRESHOLD` default 0.8)

Sells skip steps 5-10 and just verify the position exists.

### 2d. Signal generation — no LLM, no sentiment

You mentioned "LLM sentiment" as a possible data source.
There is none.  All signal generation is pure technical analysis.  Four concrete
strategies exist in a pluggable registry:

| Strategy | Description |
|----------|-------------|
| `MomentumStrategy` | Default. Uses `MOMENTUM_THRESHOLD` / `SELL_THRESHOLD` on bar data. |
| `MeanReversionStrategy` | Signals when price deviates from mean. |
| `BreakoutStrategy` | Detects breakouts from consolidation ranges. |
| `RSIStrategy` | RSI-based overbought/oversold. Requires >= 25 bars. |

Switching strategy is a single config change (`STRATEGY=breakout`).  The
`get_strategy(name)` factory handles instantiation.

### 2e. Top-gainers filtering

You described it as "top 20 fastest growing."  Actual filters applied before
ranking by gain %:

- Price >= `TOP_GAINERS_MIN_PRICE` (default **$5.00**)
- Volume >= `TOP_GAINERS_MIN_VOLUME` (default **1,000,000**)
- Universe scope: `TOP_GAINERS_UNIVERSE` (default `"large_cap"`)
- Count: top N by gain, where N = `TOP_GAINERS_COUNT` (default 20)

The screener is **not a separate agent**.  It runs inside DataAgent's `fetch_data()`
via `compute_top_gainers()`.

### 2f. RVOL filtering — does not exist

You suggested the Risk Agent should check Relative Volume > 2.0.  This check is
not implemented anywhere in the codebase.  Volume is only used as an absolute
minimum filter in the screener (§2e).

### 2g. Position splitting math

You wrote: *"when your $1 is split into ten $0.10 positions…"*
`MIN_TRADE_VALUE = 1.0` — the Risk Agent will reject any trade sized below $1.00.
The actual portfolio value is ~$100k, not $1.

---

## 3. What you missed entirely

| Missing concept | Where it lives | Why it matters |
|-----------------|----------------|----------------|
| **Event bus** | `server/events.py` | All inter-agent communication is event-driven. Agents publish/subscribe, not direct-call. |
| **Universe isolation** | `universe.py`, `state.py:80-98` | LIVE / PAPER / SIMULATION are construction-time constants. Brokers, config files, log paths, and event buses are all scoped per universe. Cross-universe sharing is impossible by design. |
| **Circuit breaker** | `risk/circuit_breaker.py` | Tracks daily loss and max drawdown. When tripped, blocks all buys until manually reset. |
| **Position sizer** | `risk/position_sizer.py` | Signal strength (0–1) scales the dollar amount. Not a flat allocation. |
| **ObservabilityAgent** | `agents/observability_agent.py` | Classifies all agent events as ok/warn/fail, writes to `logs/{universe}/system/agent_events.jsonl`. Surfaced in the UI's Risk & Obs Alerts card. |
| **ConfigManager + RuntimeConfig** | `server/config_manager.py` | Pydantic-validated config. Persisted per-universe to `config_state.json`. Has a `field_validator` that fixes `bool("false") == True`. Live-updatable via API. |
| **WebSocket status broadcast** | `server/events.py`, `lifespan.py` | Account, positions, signals, agents status pushed to UI in real time on every `MarketDataReady` cycle. |
| **Manual trade path** | `ExecutionAgent.execute_manual_trade()` | Bypasses risk checks entirely. Separate from the auto-trade pipeline. |
| **Held-symbol tracking** | `DataAgent.fetch_data()` | Symbols from open positions are always included in the data fetch, even if they drop off the top-gainers list. |

---

## 4. Self-evaluation prompts

Answer each honestly based on the ground truth above:

1. **Accuracy rate:** Of the specific architectural claims you made (agent roles,
   lookback window, risk checks, signal sources, filtering logic), what percentage
   were correct vs. incorrect?

2. **Severity of errors:** Which of your mistakes could lead to bad engineering
   decisions if someone followed your advice without checking the code?  Rank them.

3. **Completeness:** You missed universe isolation, the event bus, circuit breakers,
   and position sizing.  How would your advice change if you had accounted for these?

4. **The $1 framing:** The user's original question involved $1.  The system has a
   ~$100k portfolio.  How much of your advice was distorted by anchoring to the $1
   scenario vs. addressing the actual system?

5. **What one piece of advice you gave is still actionable** for this codebase as it
   actually exists?

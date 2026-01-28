# Repository Guidelines

## Project Structure & Modules
- `server.py` – FastAPI entrypoint serving the UI and APIs.
- `static/index.html` – Single-page dashboard (Chart.js, minimal JS, no build step).
- `agents/` – Trading agents (data, signals, risk, execution, monitor, alert, analytics).
- `strategies/` – Pluggable strategies (momentum, mean reversion, breakout, RSI).
- `analytics/` – Equity/trade analytics store and metrics.
- `backtest/` – Event-driven backtest engine and CLI.
- `tests/` – Python `unittest` suite (currently 109 tests).
- `data/` – Persisted config state, analytics JSONL, sector maps.

## Build, Test, Run
- Install deps: `pip install -r requirements.txt`
- Run backend/UI: `python server.py` (opens http://localhost:8000)
- Run tests: `./run_tests.sh` (wraps `python -m unittest discover -s tests`)
- Backtest example: `python -m backtest --symbols AAPL,MSFT --start 2022-01-01 --benchmark SPY`

## Coding Style & Naming
- Python: PEP8-ish, 4-space indent; favor small pure functions and dataclasses for data.
- Frontend: Vanilla JS + Chart.js inside `static/index.html`; keep CSS inlined here unless unavoidable.
- Naming: snake_case for Python; camelCase for JS functions/vars; uppercase for config constants.
- Logging: use structured JSON where possible (see `monitoring/`).

## Testing Guidelines
- Add unit tests under `tests/` mirroring module paths (e.g., `tests/test_analytics_metrics.py`).
- Prefer deterministic inputs; mock external services (Alpaca, network).
- Keep new tests fast (<1s) and isolated; avoid hitting the real network/broker.
- Run `./run_tests.sh` before pushing.

## Commit & PR Expectations
- Commits: present tense, concise scope (e.g., `Add trade outcome metrics`).
- PRs: include summary, testing evidence (`./run_tests.sh` output), screenshots/GIFs for UI changes, and note any config/env impacts.
- Link issues or roadmap items when relevant.

## Security & Config Tips
- Never commit real API keys; `.env` is ignored. Use `config_state.json` for UI-written settings.
- Default to `SIMULATION_MODE=true` when developing; use paper trading for higher fidelity before live.
- Validate new API endpoints with `require_api_access` dependency to respect token gating.

## Agent-Specific Notes
- Use the event bus for cross-agent communication; avoid tight coupling.
- Persist analytics through `AnalyticsStore` only (no ad-hoc files).
- FakeBroker should mirror Alpaca responses closely to keep SIM and LIVE behavior aligned.

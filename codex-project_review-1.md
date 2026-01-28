# Market-Watch Review (2026-01-25)

## Scope
Repository-wide assessment against ROADMAP, test status, reliability posture, file/document organization, and quick-run commands. Intended as a single source of truth alongside ROADMAP.md.

## Current State Snapshot
- Purpose: FastAPI-based algo trading platform with Alpaca/Fake brokers, pluggable strategies, backtesting, risk controls, analytics, and static UI.
- Architecture: Agents/event bus orchestrated in `server.py`; strategies in `strategies/`; backtest engine in `backtest/`; analytics store/metrics in `analytics/`; risk helpers in `risk/`; monitoring/observability in `monitoring/`; UI in `static/`.
- Config: `.env` → `config.py`; persisted overrides in `data/config_state.json` (loaded/saved by `server.py`). Simulation flag swaps Alpaca vs Fake broker.

## Test Status (as of 2026-01-25)
- Full suite: `bash scripts/run_tests.sh` → 174/174 passing; logs in `test_results/test_run_20260125_094926.log`; summary in `test_results/latest_summary.txt`.
- Targeted rerun: 67/67 passing via `python3 -m unittest …` for remaining modules.
- Runner UX: `scripts/run_tests.sh` now activates `.venv`/`venv`, chooses available python, writes timestamped log + summary.

## Key Findings
1) **Analytics period helper bug fixed**: `_period_cutoff_and_days` now imports `timedelta` (server.py). Prevents 500s on period queries.
2) **Config persistence safety**: `auto_trade` and `simulation_mode` now parse booleans correctly; avoids `bool("false")` → True pitfall after restart.
3) **Test runner robustness**: Runner updated to detect `.venv`; avoids warnings and uses correct interpreter.
4) **Repo hygiene**: Removed stray `test_results\r` dir; moved `err.txt` to `logs/err.txt`.
5) **Analytics UI gaps remain** (per ROADMAP): metric cards showing “--”, position concentration chart broken, trades missing `filled_avg_price`; not addressed here.
6) **Broker hot-swap not implemented**: SIM/live auto-switch still blocked by broker instantiation at startup; prerequisite for planned auto-switch feature.

## Commands Reference (concise)
- All tests + logs: `bash scripts/run_tests.sh`
- Windows: `scripts\run_tests.bat`
- Manual all tests: `python -m unittest discover -s tests -p "test_*.py" -v`
- Single module: `python -m unittest tests.test_strategy_momentum -v`

## File/Doc Organization Suggestions
- Keep active docs in `docs/` root (API, STRATEGIES, RISK, BACKTEST, OBSERVABILITY, ARCHITECTURE, DEPLOYMENT, FAQ, CONTRIBUTING, HEALTH_ENDPOINT).
- Archive historical one-offs in `docs/archive/`; ensure README points to canonical docs + this review.
- Maintain logs under `logs/` and test artifacts under `test_results/` only.

## Phase Checks vs ROADMAP
- Phase 4 (Analytics & Reporting): **NOT 100%** — currently ~75% complete (UI metrics/cards and chart issues outstanding, trade fill price missing). Hold for further work.
- Phase 11 (Testing & Reliability): Unit suite done; CI/CD, integration/system tests, and automated test agent not yet implemented.

## Proposed Next Actions (optional)
1) Build lightweight “TestAgent” under Phase 11: background task in `server.py` (config flags `AUTOTEST_ENABLED`, `AUTOTEST_INTERVAL_MINUTES`, `AUTOTEST_CMD` default `bash scripts/run_tests.sh`), logs to JSONL + reuses `test_results` logs; optional WS broadcast.
2) Fix analytics UI gaps: capture `filled_avg_price` in `AnalyticsAgent`; debug `/api/analytics/summary` parsing; add cache-busting query to `static/index.html`; repair position concentration chart data format.
3) Design broker hot-swap wrapper to enable planned SIM auto-switch.


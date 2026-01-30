# Modularization & ConfigManager Plan
**Date:** 2026-01-25
**Goal (Step 1):** Modularize `server.py` and introduce a `ConfigManager` so the API layer is smaller, testable, and configuration is injected, not globally imported.

## Target End-State Structure
```
server/
  main.py            # FastAPI app creation, lifespan wiring
  routers/
    status.py        # health/status/observability
    config.py        # config get/update
    analytics.py     # analytics data/export
    trading.py       # signals, orders, manual trades, broker info
    static.py        # UI assets (optional)
  dependencies.py    # FastAPI deps: get_config, get_broker, get_coordinator, get_analytics_store
  events.py          # broadcast helpers, websocket manager
  lifespan.py        # startup/shutdown orchestration
  logging.py         # logger factory (optional)
config_manager.py    # central config loader/validator/persister
```
Existing top-level `server.py` remains as a thin shim: `from server.main import app`.

## ConfigManager Responsibilities
- Load order: `.env` → defaults → `config_state.json` overrides.
- Normalize types (booleans via strtobool; ints/floats with safe coercion).
- APIs: `get(key)`, `update(dict)` with validation, `snapshot()`, `save()`.
- Provide typed accessors (strategy, watchlist, risk limits, flags).
- Thread-safe (simple lock) for concurrent requests.
- Optional diff/audit for changes; normalize allowed origins at load time.

## FastAPI Wiring (main.py & dependencies.py)
- Instantiate ConfigManager at startup; store in `app.state`.
- Dependency fns: `get_config_manager()`, `get_broker()`, `get_coordinator()`, `get_analytics_store()`.
- Broker selection (Alpaca vs Fake) based on ConfigManager.
- Websocket manager and `broadcast` live in `events.py`.

## Lifespan Flow
1) Load config via ConfigManager.
2) Choose broker class (Fake vs Alpaca).
3) Instantiate AnalyticsStore (if enabled).
4) Instantiate Coordinator with injected broker + analytics.
5) Wire event-bus callbacks (MarketDataReady, SignalsUpdated) from `events.py`.
6) Start agents.
7) Start observability task (if enabled).
8) On shutdown: stop agents, close broker connections.

## Router Responsibilities
- `status.py`: `/health`, `/status`, `/observability`.
- `config.py`: `/api/config` GET/PUT (ConfigManager update + save).
- `analytics.py`: `/api/analytics/*` endpoints.
- `trading.py`: manual trades, signals, orders, account/positions.
- `static.py`: mount StaticFiles (can stay in main if simpler).

## Event/Broadcast Handling
- Central `broadcast(message: dict)` in `events.py`.
- Websocket registry managed there; shared by routers and coordinator callbacks.

## Migration Steps
1) Add `config_manager.py` (no side-effects).
2) Create `server/` package; move code slice-by-slice from `server.py` into routers/deps/lifespan/events.
3) Keep legacy `server.py` shim to avoid breaking entrypoints.
4) Update imports across project to new locations.
5) Add small unit tests for ConfigManager (type coercion, precedence, save/load).
6) Run `scripts/run_tests.sh` to confirm behavior unchanged.

## Test Considerations
- New tests: ConfigManager coercion/precedence; dependency singleton.
- Existing API tests should pass once routes are mounted identically.

## Risks & Mitigations
- Import cycles between routers/coordinator: avoid by centralizing shared deps in `dependencies.py`.
- Config drift: mitigate with ConfigManager snapshot/save and single update path.
- Deployment entrypoint breakage: mitigated by shim `server.py` re-exporting `app`.

## Suggested Execution Order
1) Modularize `server.py` → routers/services; introduce ConfigManager injection.
2) (Next phases) Finish Phase 4 analytics UI/reporting, then stand up CI, then optional TestAgent.

---
GEMINI suggests...

This is an excellent and well-thought-out plan. It directly addresses the key architectural issues identified in the previous reviews. The plan is detailed, practical, and provides a clear roadmap for this refactoring effort.

My main thought is that this plan should be followed as closely as possible.

To ensure the success of this refactoring, I recommend the following during implementation:

1.  **Strictly enforce the dependency injection pattern.** No component should directly instantiate another component if it can be injected as a dependency. This will be crucial for maintaining the testability and maintainability of the new structure.
2.  **Be diligent about updating the tests.** As the code is refactored, the tests will need to be updated to reflect the new structure. This is also a good opportunity to improve the test coverage, especially for the new `ConfigManager` and the dependency functions.
3.  **Use a linter and code formatter.** A linter (like `ruff` or `flake8`) and a code formatter (like `black`) will help to ensure that the new code is clean, consistent, and easy to read. This is especially important when multiple developers are working on the project.
---

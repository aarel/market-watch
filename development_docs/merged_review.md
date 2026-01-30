# Market Watch Trading Bot: Merged Project Review

**Date:** 2026-01-25

**Purpose:** This document merges the findings from `gemini-project_review-2.md` and `codex-project_review-2.md` to create a single, implementation-ready review aligned to the ROADMAP phases.

---
GEMINI suggests...
This merged document should serve as the single source of truth for the project's status and recommended next steps, evolving as the project progresses.
---

---
CODEX suggests...
Use this merged review as the working baseline, and keep the Codex additions focused on actionable, testable steps that close Phase 4 and Phase 11 gaps while improving structure and security.
---

## 1. Project Overview & Snapshot (ROADMAP alignment)

The project is a Python-based, agent-driven autonomous trading bot with a web-based user interface, built on FastAPI. It connects to the Alpaca brokerage (or a `FakeBroker` in simulation mode) to trade equities using a variety of pluggable strategies. The project also includes a backtesting engine, risk controls, and an analytics dashboard. The architecture is modular, centered around cooperating agents that communicate via an event bus.

*   **Key Technologies:** Python 3.10+, FastAPI, `alpaca-trade-api`, `pandas`, `numpy`, `unittest`.
*   **Current Test Status:** 174/174 tests passing (supports Phase 11 “Unit suite complete”).
*   **Phase status:** Phase 4 Analytics ~75% (UI/reporting gaps); Phase 11 Testing in progress (CI/integration pending); other phases per ROADMAP.

## 2. Project Structure Analysis (Phase 10/11 support)

The project is generally well-organized. The root directory has been cleaned up, and a redundant virtual environment has been removed.

**Recommendations (near-term, Phase 10/11 supportive):**

*   **Test Results Directory:** Consider moving the `test_results` directory to a more standard location like a `.test/` or `build/` directory.
*   **Log Directory:** For production, consider moving the `logs` directory to a standard system location like `/var/log/market-watch`.

---
GEMINI suggests...
The current structure is good for a single-developer project. For a larger team, a more formal structure with a `src` layout might be beneficial, but it is not necessary at this stage.
---

## 3. Recent Findings & Key Changes (since 2026-01-25)

This section consolidates recent findings from all reviews.

*   **Bug Fixes:**
    *   **Analytics Period Helper:** The `_period_cutoff_and_days` function in `server.py` now correctly imports `timedelta`, fixing 500 errors.
    *   **Config Persistence:** `auto_trade` and `simulation_mode` boolean settings now parse correctly from the state file.
*   **Tooling & Hygiene:**
    *   **Test Runner:** The test runner script is now more robust and correctly detects the `.venv` directory.
    *   **Repo Cleanup:** A stray `test_results\r` directory has been removed, and `err.txt` has been moved to `logs/err.txt`.
*   **Identified Gaps (per `ROADMAP.md`):**
    *   **Phase 4 Analytics UI:** metric cards show “--”, position concentration chart broken, trades missing `filled_avg_price`; HTML/PDF reports deferred to tech debt.
    *   **Phase 6/11 Broker Hot-Swap:** Broker instantiated at startup prevents SIM/live auto-switch; blocks planned SIM mode auto-switching.

## 4. Code & Architecture Review (Phase 10/11 readiness)

The codebase is of high quality, but several areas can be improved to enhance maintainability and scalability.

### 4.1. "God" Files and Methods

*   **Issue:** `server.py`, `agents/data_agent.py:fetch_data`, and `agents/risk_agent.py:_handle_signal` are overly complex and long.
*   **Recommendation:** Refactor these into smaller, more focused modules and functions. For `server.py`, create a `routers` directory.

### 4.2. Configuration Management

*   **Issue:** Components directly access the `config` module, and there is code duplication in the configuration loading/saving logic.
*   **Recommendation:** Create a dedicated `ConfigManager` class to centralize configuration handling.

### 4.3. Incomplete Decoupling

*   **Issue:** Agents have direct dependencies on the broker and on each other, creating tight coupling and potential circular dependencies.
*   **Recommendation:** Use the event bus more thoroughly to share data and remove these direct dependencies. For example, the `RiskAgent` should consume position data from `MarketDataReady` events, not by calling the broker.

### 4.4. Logging

*   **Issue:** `print` statements are used for logging throughout the application.
*   **Recommendation:** Replace all `print` statements with the standard Python `logging` module.

### 4.5. Security

*   **Issue:** The API uses a simple static API token and a simplistic loopback check.
*   **Recommendation:** Implement a more secure authentication mechanism like JWT and use a more robust method for host validation.

## 5. Test Review (Phase 11)

The project has a good foundation of unit tests, but coverage and quality can be improved.

*   **Coverage Gaps:** The `RiskAgent` and `DataAgent` lack comprehensive test coverage.
*   **Quality Issues:** The tests contain "magic numbers" and some redundant test data creation.
*   **Recommendation:** Increase test coverage for the identified gaps and refactor existing tests to improve their quality.

## 6. Summary of Recommendations & Actions (prioritized by phase impact)

1.  **Modularize Core Components:**
    *   Break down `server.py`, `data_agent.py`, and `risk_agent.py`.
    *   ---
        GEMINI suggests...
        Start with `server.py`. Creating a `routers` directory and moving the API endpoints is a low-risk, high-reward refactoring that will immediately improve the project's structure.
        ---
2.  **Centralize Configuration:**
    *   Implement a `ConfigManager` class.
3.  **Complete Decoupling:**
    *   Refactor agents to rely solely on the event bus for data exchange.
4.  **Overhaul Logging:**
    *   Replace all `print` statements with the `logging` module.
5.  **Address Analytics Gaps (Phase 4):**
    *   Capture `filled_avg_price`; fix metric cards and position concentration chart; add cache-busting; deliver HTML/PDF reporting.
6.  **Improve Test Suite (Phase 11):**
    *   Add tests for `DataAgent` and remaining `RiskAgent` rules; add integration/backtest→order flow; refactor magic numbers/fixtures.
7.  **Enhance Security (Phase 10/11 support):**
    *   Implement JWT or signed tokens with roles/expiry; strengthen origin/loopback validation.
8.  **Implement Broker Hot-Swap (Phase 6 dependency for SIM auto-switch):**
    *   Design runtime switch between real/fake broker to unlock planned SIM auto-switch feature.
9.  **CI/CD (Phase 11):**
    *   Stand up GitHub Actions running lint + `scripts/run_tests.sh`; publish logs/artifacts.

By addressing these recommendations, the project can be made more robust, maintainable, secure, and user-friendly.

---
Codex suggests...
- Align execution with ROADMAP phases: (1) Modularize `server.py` + add `ConfigManager` (Phase 10/11 enabler), (2) close Phase 4 UI/reporting gaps, (3) stand up minimal CI, then (4) optional TestAgent with JSONL outputs under `logs/observability/`.
- Harden auth/origin checks early (JWT/signed tokens, stricter loopback/origin) to avoid unsafe defaults leaking to users.
- Standardize transient dirs (`test_results`, `logs`) and add to `.gitignore`; keep a single `.venv`.
---
GEMINI recommends...
The prioritization proposed by Codex is logical. To execute this plan, the following steps should be taken:

1.  **Modularize `server.py`:** Create a `routers` directory. For each major resource (e.g., `status`, `config`, `trades`), create a new file in the `routers` directory and move the corresponding FastAPI `APIRouter` and its associated logic into that file. Then, in `server.py`, import and include these routers into the main `FastAPI` app.

2.  **Implement `ConfigManager`:** Create a new file, `config_manager.py`. This file will contain a `ConfigManager` class that encapsulates all configuration logic from `server.py` (`load_config_state`, `save_config_state`, `_config_snapshot`). The `ConfigManager` should be instantiated once in `server.py` and passed as a dependency to the components that need it.

3.  **Close Phase 4 UI/Reporting Gaps:**
    *   **`filled_avg_price`:** In `agents/analytics_agent.py`, ensure the `OrderExecuted` event contains the `filled_avg_price` from the broker's order object, and that this is saved to the analytics store.
    *   **UI Metric Cards:** Use browser developer tools to inspect the network request to `/api/analytics/summary`. Verify that the JSON response is correct and that the frontend JavaScript is parsing it correctly.
    *   **Position Concentration Chart:** Check the browser's developer console for JavaScript errors related to Chart.js. Ensure the data format passed to the chart matches the format expected by the library.
    *   **HTML/PDF Reporting:** For PDF reporting, a library like `WeasyPrint` or `pdfkit` can be used to convert the HTML report to a PDF.

4.  **Set up CI:** Create a new GitHub Actions workflow file in `.github/workflows/ci.yml`. This workflow should run on every push and pull request to the `main` branch. It should include steps for:
    *   Checking out the code.
    *   Setting up Python.
    *   Installing dependencies from `requirements.txt`.
    *   Running the linter (`flake8` or `ruff`).
    *   Running the tests using `bash scripts/run_tests.sh`.

5.  **Harden Auth/Origin Checks:**
    *   **JWT:** Use a library like `python-jose` to implement JWT authentication. Create new API endpoints for logging in and getting a token.
    *   **Origin Checks:** Use a more robust method for validating the origin, such as a whitelist of allowed origins that is configurable.

6.  **Standardize Transient Dirs:** Add `test_results/` and `logs/` to the `.gitignore` file. Ensure that only one virtual environment directory (`.venv`) is used.
---

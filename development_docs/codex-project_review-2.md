# Market Watch Trading Bot: Consolidated Review (Codex v2)
**Date:** 2026-01-25
**Sources compared:** `codex-project_review-1.md` (latest Codex review) and `gemini-project_review-1.md` (Gemini review).

## Snapshot
- Python/FastAPI, agent/event-bus architecture; Alpaca/Fake broker swap via `SIMULATION_MODE`.
- Pluggable strategies, backtest engine, risk controls, analytics, static UI.
- Current tests: 174/174 passing via `scripts/run_tests.sh`; logs under `test_results/` with summaries.
- Phase 4 (Analytics & Reporting): ~75% complete; UI metric cards, position concentration chart, filled_avg_price capture, and HTML/PDF reports still open.
- Phase 11 (Testing & Reliability): Unit suite done; CI/CD & integration/system tests pending.

## Strengths (combined)
- Clear modular boundaries (agents, strategies, backtest, analytics) with event bus foundation.
- Good unit test coverage across strategies, backtest, risk, analytics; deterministic runners with logging.
- Recent configuration alignment fixes; safer boolean parsing; test runner now robust to `.venv`/`venv`.
- Roadmap is detailed and current (updated 2026-01-24) with explicit gaps and success metrics.

## Weaknesses / Gaps (combined)
- Large “god” modules (`server.py`, `agents/data_agent.py`, `agents/risk_agent.py`) reduce maintainability.
- Configuration access is ad‑hoc; components reach into `config` directly; duplication in load/save logic.
- Event-bus decoupling incomplete: several agents call each other/broker directly, creating tight coupling and potential cycles.
- Logging inconsistent; `print` still present; lacks unified logger config and log rotation.
- Security: static API token and basic loopback check; no JWT/role separation; CORS/Origin handling minimal.
- Analytics UI/reporting incomplete (Phase 4 gaps); HTML/PDF reporting deferred to tech debt.
- Testing gaps: limited coverage for DataAgent behavior and full RiskAgent rules; integration/system/CI absent; magic numbers/redundant fixtures in tests.

## Pros / Cons (net assessment)
- **Pros:** Solid functional scope (backtest → live), strong unit coverage, clear roadmap, fast deterministic tests with logged artifacts, recent config and runner hardening.
- **Cons:** Architectural bloat in core files, weak security posture, partial decoupling, missing higher-level tests/CI, analytics UX gaps, and deferred reporting deliverables.

## Actions (blending Codex + Gemini recommendations)
1) **Modularize core:** Split `server.py` into routers/services; decompose `data_agent.fetch_data` and `risk_agent._handle_signal` into focused helpers.
2) **ConfigManager:** Central class/service for loading/saving/overrides; inject config into agents instead of importing `config` globally.
3) **Event-bus purity:** Move broker/account/position access into published events; have RiskAgent subscribe rather than pull; ExecutionAgent listens for OrderExecuted to update counters.
4) **Logging overhaul:** Replace prints with `logging`; add JSON/rotating handlers; standard log levels; wire into observability.
5) **Security uplift:** Introduce JWT (or signed tokens) with expiry/roles; harden origin/host checks; document threat model.
6) **Analytics completion (Phase 4):** Capture `filled_avg_price` in AnalyticsAgent; fix `/api/analytics/summary` UI parsing; repair position concentration chart; add cache-busting; plan/report HTML/PDF outputs (was pushed to tech debt).
7) **Testing/CI (Phase 11):** Add DataAgent and full RiskAgent cases; create integration/backtest-to-order flow tests; set up GitHub Actions; consider lightweight TestAgent auto-runner with JSONL results.
8) **Housekeeping:** Keep logs under `logs/`, tests under `test_results/`, archive historical docs; maintain Codex review series as `codex-project_review-<n>.md`.

## Command Reference (unchanged)
- All tests + logs: `bash scripts/run_tests.sh`
- Windows: `scripts\run_tests.bat`
- Manual all: `python -m unittest discover -s tests -p "test_*.py" -v`
- Single module: `python -m unittest tests.test_strategy_momentum -v`

## Phase Flags
- Phase 4: ~75%; reporting/UX items outstanding; HTML/PDF reporting still deferred to technical debt.
- Phase 11: unit tests done; CI/integration/system tests + automated runner not yet delivered.


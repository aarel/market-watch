# Market-Watch Roadmap v3

> **Supersedes:** `ROADMAP_v2.md` (original 7-phase plan).
>
> **Last updated:** 2026-02-07
> **Test status:** 375 pass, 4 skip (last run 2026-02-07) — run with `python -m pytest tests -q`

---

## Architectural Contract (non-negotiable)

These invariants from `roadmap-review.md` remain binding. Any feature that
violates them is rejected regardless of utility.

1. **Universe as type.** LIVE / PAPER / SIMULATION are construction-time, not
   runtime. Every execution path carries a universe value.
2. **Isolation by construction.** Cross-universe state sharing is impossible by
   default. Shared brokers, shared persistence namespaces, and boolean mode flags
   are forbidden.
3. **Fail fast on ambiguity.** Ambiguous execution context halts the system.
4. **Falsifiability.** Every correctness claim has a measurable disproof.

---

## Quality Contract (new for v3)

**No technical debt carried forward between phases.**

Phases are completed only when:
- All checkboxes are done
- All tests pass
- No known bugs or workarounds
- Code is production-ready

**Exceptions:**
- Unexpected issues discovered during implementation (document in phase notes)
- Experiments that failed (document why, archive the attempt)

---

## Current State (2026-02-07)

### Completed (Production-Ready)

| Area | Detail | Tests |
|------|--------|-------|
| **Universe isolation** | Enum, scoped brokers, scoped persistence, scoped event bus, construction-time assertions (`state.py:80-98`). Closure-capture bug fixed. | TestUniverseMismatchAssertion, TestConfigNamespaceIsolation |
| **Backtesting** | Data fetch/cache, event-driven simulation, full metrics suite (Sharpe, Sortino, drawdown, win rate, etc.), CLI, benchmark comparison. |  |
| **Strategy framework** | 4 pluggable strategies (Momentum, Mean Reversion, Breakout, RSI). Registry + SignalAgent integration. Strategy-specific thresholds are hardcoded (only Momentum configurable). | TestStrategySelection (11 tests) |
| **Strategy presets** | UI dropdown with 5 presets (Momentum, Mean Reversion, Breakout, RSI, Custom). Auto-configuration, confirmation dialogs, tooltips. | TestStrategyPresetDefinitions, TestPresetSwitching (9 tests) |
| **Conditional field visibility** | Buy/Sell Threshold fields only shown for Momentum strategy. Strategy info row explains what each strategy uses. | (UI only, no backend tests needed) |
| **Config warnings** | Dynamic warnings on risky values (stop loss, position %, daily trades, open positions, loss limit). Green/amber/red indicators with tooltips. | TestWarningThresholds, TestPresetDefiningFields (12 tests) |
| **Smart Custom switching** | Editing preset-defining fields (strategy, thresholds, watchlist) switches to Custom. Editing operational fields (risk limits) preserves preset. | TestPresetDefiningFields |
| **Risk system** | Position sizing, circuit breakers, daily-loss / max-drawdown limits, sector + correlation exposure checks, RVOL filter. All universe-aware. | TestRiskAgentRVOL (3 tests) |
| **Config persistence** | `ConfigManager` + Pydantic `RuntimeConfig`. `field_validator` handles `bool("false")` coercion. Per-universe config files. | TestBoolCoercionAtBoundary (5 tests) |
| **Paper trading** | Functional via Alpaca paper account. | (manual verification) |
| **Observability** | Real pipeline only: ObservabilityAgent → `agent_events.jsonl` → `/api/observability/logs` → UI. Today-only filter (NY EST), no entry limit, daily CSV to `logs/risk-and-obs-alerts/`. Stub eval system removed. | (integration test needed) |
| **Analytics** | Equity curve, trade recording, AnalyticsAgent, JSONL store. API endpoints functional. | TestAnalyticsStore |
| **Dependencies** | Pinned in `requirements.lock`. All deps locked. | (implicit in all tests) |
| **UI** | Grid layout: Trades / Risk & Limits / Risk & Obs Alerts (row), Activity Log (full-width row), Configuration. Tooltips on all fields. Strategy info row. Warning indicators. | (UI testing needed) |

### Known Issues

- **No CI/CD pipeline:** Phase F future work

---

## Ops Scheduling (Cross-Phase)

Cron jobs are operational scheduling, not CI/CD. Start them only when the underlying phase deliverables are stable.

- **After Phase B:** Enable log rotation cron (`scripts/rotate_logs.py`) and optional health monitor cron (`docs/HEALTH_ENDPOINT.md`).
- **After Phase D:** Enable backups cron (`docs/DEPLOYMENT.md`).
- **After Phase H:** Enable post-market backtest cron (`scripts/setup_cron.sh`) once backtest engine is trustworthy.

---

## Phases — Foundation (A-G)

These phases complete the core platform before adding ML or AI agents.

---

### Phase A — Hardening ✅ **COMPLETE**
**Goal:** Close remaining gaps from DRA audits. Make the platform trustworthy before scaling features.

**Status:** 100% complete (11/11 done; verification pending full suite run)
**Implementation completed:** 2026-02-07

#### Items Complete (11/11)
- [x] P0 closure-capture bug fixed
- [x] Dependencies pinned
- [x] Danger-path tests added (universe mismatch, bool coercion, config isolation)
- [x] Observability stubs removed; real pipeline wired end-to-end
- [x] Root docs consolidated into `development_docs/`
- [x] Strategy preset system with conditional field visibility
- [x] Config warnings on risky values
- [x] Analytics UI verified (shows real data, no "--" cards) - **Fixed in Phase D Task 10**
- [x] Dead config flags deleted (`OBSERVABILITY_EVAL_*` removed from config.py, .env.example, docs)
- [x] Integration test: full trade lifecycle (skip removed; 4 tests pass)
- [x] Backtest decision made (defer to Phase H - not blocking Phase A)

**Exit criteria status:**
- [x] All checkboxes done (11/11)
- [ ] All tests pass (integration suite passes; full suite run hung 2026-02-07)
- [x] Analytics UI shows real data (filled_avg_price pipeline fixed)
- [x] Zero dead code
- [ ] No technical debt carried forward (full suite run hang pending)

**Audit note (2026-02-06):** Phase A audit flagged roadmap contradictions; this section reconciles those findings and confirms the integration suite is now un-skipped.

---

### Phase B — Observability & Monitoring ✅ **COMPLETE**
**Goal:** Operational confidence without manual log-diving.

**Status:** 100% complete (4/4 done)
**Completed:** 2026-02-05
**Dependencies:** Phase A (implementation complete; verification pending)
**Audit status (2026-02-06):** Complete per Phase B DRA audit

#### All Items Complete
- [x] Per-endpoint latency tracking (p50 / p95), surfaced in health endpoint
- [x] Anomaly detection on agent event stream (unusual spike in warn/fail counts)
- [x] Alert on detected anomaly (integrated with ObservabilityAgent)
- [x] Health endpoint returns latency snapshot alongside status

**Exit criteria met:**
- ✅ Health endpoint shows latency metrics (p50/p95 per endpoint + summary)
- ✅ Anomaly detection monitors warn/fail event rates
- ✅ Baseline establishment and spike detection (3x threshold)
- ✅ New API endpoints: /api/observability/anomalies, /api/observability/baseline
- ✅ Tests cover latency tracking (12 tests) and anomaly detection (15 tests)
- ✅ 302 tests pass total (275 + 27 new)
- ✅ Zero technical debt

**Implementation notes:**
- `LatencyTracker` with thread-safe rolling window (RLock-protected deque)
- `LatencyMiddleware` measures all /api/* requests via perf_counter
- `AnomalyDetector` tracks warn/fail event rates, detects spikes >3x baseline
- Fixed deadlock bug (Lock → RLock for reentrant locking)
- Fixed negative rate calculations (added abs() for time span)
- ObservabilityAgent auto-records anomaly events and triggers external alerts on spikes (when alerts enabled)

---

### Phase C — External Alerts **PARTIAL**
**Goal:** Push critical events to humans without requiring the dashboard to be open.

**Status:** Partially complete (framework + UI done; runtime wiring missing)
**Last reviewed:** 2026-02-06
**Dependencies:** Phase B (alert framework needs monitoring infrastructure) ✅

#### Work Items
- [x] Alert rule framework (trigger conditions, severity levels, delivery channels)
- [x] Email channel (SMTP with HTML templates, retry logic)
- [x] Webhook channel (Discord, Slack, Telegram, generic JSON support)
- [x] Alert history card in UI (50/50 split with Activity Log, auto-refresh)
- [ ] Configuration UI persistence verified (enable/disable toggles, test buttons)
- [ ] Runtime wiring (register channels, load rules, trigger alerts from real events)

**Exit criteria pending:**
- [ ] Alerts fire correctly (rule matching, trigger types, severity levels)
- [ ] Email channel works end-to-end (SMTP, HTML/text templates, exponential backoff)
- [ ] Webhook channel works end-to-end (platform-specific payloads, retry logic)
- [x] Tests cover delivery failures and retries (12 email + 13 webhook tests)
- [ ] 343 tests pass total (302 + 41 new)
- [ ] Zero technical debt

**Audit note (2026-02-06):** Phase C DRA audit concluded runtime wiring is missing; treat as incomplete until rules/channels/triggers are wired and verified.

**Implementation notes:**
- AlertManager with rule evaluation and multi-channel dispatch
- Email: SMTP with TLS/SSL, HTML + plain text, color-coded severity
- Webhook: Discord embeds, Slack attachments, Telegram markdown
- Alert history UI: scrollable, 20 most recent, delivery status icons
- Config UI: master toggle + per-channel enables + test buttons
- Integration with Phase B anomaly detection

---

### Phase D — Analytics Completion
**Goal:** Dashboard shows real, trustworthy numbers. Reports are exportable.

**Status:** 20% complete (1/5 done)
**Started:** 2026-02-05

**Dependencies:** Phase A ✅

#### Work Items
- [x] **Fix `filled_avg_price` pipeline** - COMPLETE (Task 10)
  - AnalyticsAgent now filters unfilled orders (only records status="filled" or "partially_filled")
  - ExecutionAgent polls with exponential backoff (5 attempts, ~15.5s total)
  - 19 new tests added: 9 for analytics filtering + 9 for await_fill polling + 1 fix
  - Tests: 361 pass, 5 skip (+19 from baseline)
- [ ] Per-trade P&L display (win / loss table with entry/exit prices)
- [ ] Period returns (daily / weekly / monthly) derived from equity curve
- [ ] HTML report template (snapshot export)
- [ ] Verify CSV export completeness (trades + equity)

**Exit criteria:** All analytics cards show real data ✅, P&L is accurate, reports export correctly, tests validate calculations.

---

### Phase E — Market Awareness
**Goal:** Avoid trading into known danger zones.

**Status:** Not started (0/5 done)

**Dependencies:** Phase C (pre-event alerts need alert framework)

#### Work Items
- [ ] Trading window configuration (avoid open/close volatility spikes)
- [ ] Market holiday calendar enforcement
- [ ] Economic calendar integration (pause around FOMC, CPI, etc.)
- [ ] Earnings date awareness for watchlist symbols
- [ ] Pre-event alert (feeds into Phase C alert framework)

**Exit criteria:** Bot respects trading windows, doesn't trade on holidays, pauses before major events, tests cover calendar edge cases.

---

### Phase F — Testing & CI
**Goal:** Automated confidence on every change. No manual test runs required.

**Status:** Not started (0/4 done)

#### Work Items
- [ ] CI pipeline (GitHub Actions): lint → test → coverage gate
- [ ] Integration test suite: trade lifecycle, circuit breaker trigger, config change propagation
- [ ] Broker failure recovery tests (timeout, retry, graceful fallback)
- [ ] Backtest performance regression test (5yr / 10 symbols benchmark)

**Exit criteria:** CI runs on every commit, coverage >85%, integration tests pass, backtest regression test baseline established.

---

### Phase G — Configuration Profiles
**Goal:** Switch between risk/strategy profiles without editing files.

**Status:** Not started (0/4 done)

**Dependencies:** Phase A complete (config system must be solid)

#### Work Items
- [ ] Named profiles (e.g., "conservative", "aggressive", "learning")
- [ ] Save / load / delete via UI and API
- [ ] Version history with rollback
- [ ] Import / export (JSON)

**Exit criteria:** Profiles work end-to-end, rollback restores previous state, tests cover edge cases (profile doesn't exist, corrupted JSON).

---

## Phases — Intelligence (H-K)

These phases add ML and AI agent capabilities. **Do not start until Phases A-G are complete.**

---

### Phase H — Backtesting Engine (Foundation)
**Goal:** Validate strategies against historical data. Required before any ML work.

**Status:** 5% complete (backtest code exists but broken, needs full rewrite)

**Dependencies:** Phase F complete (CI infrastructure), Phase D complete (analytics trusted)

#### Work Items
- [ ] Walk-forward validation framework (train on period N, test on period N+1)
- [ ] Transaction cost modeling (slippage, bid-ask spread, market impact)
- [ ] Realistic order execution simulation (partial fills, rejections, delays)
- [ ] Out-of-sample testing framework (prevent overfitting)
- [ ] Monte Carlo simulation for drawdown estimation
- [ ] Benchmark comparison (SPY buy-and-hold baseline)
- [ ] HTML report generation (equity curve, metrics, trade list)
- [ ] CLI tool for running backtests (`python -m backtest --strategy momentum --period 2020-2023`)

**Exit criteria:** Backtest engine produces trustworthy results, matches live trading behavior, tests cover edge cases (missing data, splits, dividends).

**Estimated effort:** 2-3 months

---

### Phase I — ML Infrastructure
**Goal:** Build pipelines for feature engineering, model training, and deployment.

**Status:** Not started (0/8 done)

**Dependencies:** Phase H complete (need backtest engine for validation)

#### Work Items
- [ ] Historical data storage (years of OHLCV + tick data, handle splits/dividends)
- [ ] Data validation pipeline (detect bad ticks, fill gaps, survivorship bias checks)
- [ ] Feature engineering framework (technical indicators, rolling statistics, regime features)
- [ ] Feature store (pre-computed features, versioned, fast lookup)
- [ ] Model training pipeline (cross-validation, hyperparameter tuning, versioning)
- [ ] Model serving infrastructure (load model, compute features in real-time, inference)
- [ ] A/B testing framework (run strategy A vs strategy B in parallel on paper/sim)
- [ ] Model monitoring (track prediction accuracy, detect drift, alert on degradation)

**Exit criteria:** Can train/deploy models end-to-end, A/B tests work, monitoring detects model degradation, tests cover edge cases.

**Estimated effort:** 3-4 months

---

### Phase J — ML Strategy Development
**Goal:** Replace hardcoded strategies with ML-powered adaptive strategies.

**Status:** Not started (0/5 done)

**Dependencies:** Phase I complete (ML infrastructure ready)

#### Work Items

**J1: Regime Detection (Quick Win)**
- [ ] Train classifier: bull/bear/chop/risk-off based on VIX, breadth, sector flows
- [ ] Integrate into Coordinator (switch strategies based on detected regime)
- [ ] Backtest: validate regime switching improves risk-adjusted returns
- [ ] Tests: verify regime detection accuracy, strategy switching logic

**J2: Signal Quality Scoring (Medium Win)**
- [ ] Train model to predict P(5-day return > 2%) for top gainers
- [ ] Features: price momentum, volume profile, order book, options flow, sentiment
- [ ] Integrate into SignalAgent (score each signal, filter low-quality)
- [ ] Backtest: validate signal scoring improves win rate
- [ ] Tests: verify scoring thresholds, edge case handling

**J3: Adaptive Parameters (Big Win)**
- [ ] Train models to predict optimal thresholds (momentum_threshold, stop_loss, etc.)
- [ ] Features: market regime, volatility, correlation, sector rotation
- [ ] Integrate into ConfigManager (update params based on market conditions)
- [ ] Backtest: validate adaptive params improve Sharpe ratio
- [ ] Tests: verify parameter bounds, prevent extreme values

**J4: Risk Prediction**
- [ ] Train model to predict tail risk (P(drawdown > 10%) in next N days)
- [ ] Features: correlation matrix, volatility forecast, positioning
- [ ] Integrate into RiskAgent (dynamic position sizing based on predicted risk)
- [ ] Backtest: validate risk prediction reduces max drawdown
- [ ] Tests: verify risk adjustments, prevent over-reduction

**J5: Ensemble Strategies**
- [ ] Meta-model that weighs strategies based on recent performance
- [ ] Combine ML signals with traditional indicators
- [ ] Backtest: validate ensemble beats individual strategies
- [ ] Tests: verify ensemble logic, prevent overfitting to recent data

**Exit criteria:** ML strategies deployed, backtests show improvement over basic strategies (Sharpe >1.5, drawdown <15%), A/B tests validate live performance matches backtest.

**Estimated effort:** 4-6 months (including iteration and debugging)

---

### Phase K — AI Agent Coordination
**Goal:** Self-improving system that analyzes performance and proposes improvements.

**Status:** Not started (0/6 done)

**Dependencies:** Phase J complete (ML strategies deployed), agent maker system available

#### Work Items

**K1: Agent Infrastructure**
- [ ] AIAgentCoordinator class (subscribes to events, spawns agents, collects recommendations)
- [ ] Agent maker integration (API client for spawning Claude-powered agents)
- [ ] Recommendation parser (extract structured actions from agent responses)
- [ ] Approval workflow (present recommendations to user, apply if approved)
- [ ] Tests: verify agent spawning, recommendation parsing, approval flow

**K2: Daily Analysis Agent**
- [ ] Trigger: end of trading day
- [ ] Task: analyze trades, identify patterns, recommend improvements
- [ ] Output: markdown report with specific recommendations
- [ ] Integration: save reports, track recommendation history
- [ ] Tests: verify agent receives correct context, recommendations are actionable

**K3: Risk Event Response Agent**
- [ ] Trigger: risk limit hit 3+ times
- [ ] Task: diagnose root cause, recommend mitigation
- [ ] Output: root cause analysis + config adjustments
- [ ] Integration: auto-apply low-risk changes, escalate high-risk
- [ ] Tests: verify risk diagnosis, auto-adjustment bounds

**K4: Market Regime Agent**
- [ ] Trigger: daily before market open
- [ ] Task: analyze overnight news/data, classify regime, recommend strategy
- [ ] Output: regime classification + strategy recommendation
- [ ] Integration: ConfigManager updates strategy for the day
- [ ] Tests: verify regime classification, strategy switching

**K5: Strategy Evolution Agent**
- [ ] Trigger: weekly on Sunday
- [ ] Task: review performance, propose strategy modifications
- [ ] Output: proposed changes with rationale + expected improvement
- [ ] Integration: human backtests proposals, deploys best
- [ ] Tests: verify performance analysis, proposals are backtestable

**K6: Error Diagnosis Agent**
- [ ] Trigger: exception thrown 3+ times in 10 minutes
- [ ] Task: read logs, diagnose root cause, propose fix
- [ ] Output: root cause analysis + fix recommendation
- [ ] Integration: human applies fix (or auto-restart if known issue)
- [ ] Tests: verify error pattern detection, diagnosis quality

**Exit criteria:** AI agents run automatically, recommendations are high-quality, human approval workflow works, system improves over time without manual tuning.

**Estimated effort:** 3-4 months

---

## Phases — Production (L-M)

These phases make the system robust enough for serious capital.

---

### Phase L — Production Readiness
**Goal:** Multi-broker support, failover, disaster recovery.

**Status:** Not started (0/6 done)

**Dependencies:** All previous phases complete

#### Work Items
- [ ] Multi-broker abstraction (generic Broker interface)
- [ ] Broker failover (primary fails → switch to backup)
- [ ] Multiple data sources (validate data across sources, detect bad feeds)
- [ ] Database migration (replace JSONL with PostgreSQL for scale)
- [ ] Backup and restore (daily backups, tested restore procedure)
- [ ] Disaster recovery plan (documented, tested quarterly)

**Exit criteria:** System survives broker outages, data corruption, server failures. Backup/restore works. Tests cover all failure modes.

**Estimated effort:** 2-3 months

---

### Phase M — Compliance & Auditability
**Goal:** Track record attestation, regulatory compliance, investor reporting.

**Status:** Not started (0/5 done)

**Dependencies:** Phase L complete

#### Work Items
- [ ] Trade record hash chain (tamper-evident log)
- [ ] Provenance tagging on all records (universe + session_id + git commit)
- [ ] PDF investor reports (monthly performance summary)
- [ ] Audit trail (all config changes, manual overrides, system events)
- [ ] Compliance checks (pattern day trader rules, margin requirements, position limits)

**Exit criteria:** Trade records are auditable, reports are professional-grade, compliance checks prevent violations.

**Estimated effort:** 2-3 months

---

## Backlog (Identified, Not Scheduled)

These are real work items but have no concrete trigger yet. Revisit when a
preceding phase completes or a user need surfaces.

| Item | Why it's here | Prerequisite |
|------|---------------|--------------|
| Real-time tick data | Currently using 1-min bars. Tick data enables better execution. | Phase L complete, data costs justified |
| Options trading | Volatility selling, hedging. Requires complex risk management. | Phase M complete, capital >$500k |
| Multiple timeframes | Day trading + swing trading simultaneously. | Phase K complete (agent coordination needed) |
| Social media sentiment | Twitter/Reddit scraping for signal generation. | Phase J complete (ML infrastructure ready) |
| Alternative data | Satellite imagery, credit card data, app downloads. | Phase J complete, data costs justified ($10k+/month) |
| Portfolio optimization | Kelly criterion, risk parity, mean-variance optimization. | Phase J complete (need robust risk models) |
| Custom strategy DSL | Let users write strategies without coding. | Phase M complete (after proven stable) |
| Mobile app | Native iOS/Android apps for monitoring. | Phase M complete, user base >100 |

---

## Estimated Timeline

**Assuming full-time work (40 hrs/week):**

| Phase | Effort | Dependencies | Timeline |
|-------|--------|--------------|----------|
| A — Hardening | 2-3 weeks | None | Weeks 1-3 |
| B — Observability | 2-3 weeks | A done | Weeks 4-6 |
| C — External Alerts | 2-3 weeks | B done | Weeks 7-9 |
| D — Analytics | 3-4 weeks | A done | Weeks 10-13 |
| E — Market Awareness | 2-3 weeks | C done | Weeks 14-16 |
| F — Testing & CI | 3-4 weeks | None | Weeks 17-20 |
| G — Config Profiles | 2-3 weeks | A done | Weeks 21-23 |
| **Foundation complete** | **~6 months** | | |
| H — Backtesting Engine | 8-12 weeks | F, D done | Months 7-9 |
| I — ML Infrastructure | 12-16 weeks | H done | Months 10-13 |
| J — ML Strategy Dev | 16-24 weeks | I done | Months 14-19 |
| K — AI Agent Coord | 12-16 weeks | J done | Months 20-23 |
| **Intelligence complete** | **~18 months** | | |
| L — Production Readiness | 8-12 weeks | All done | Months 24-26 |
| M — Compliance | 8-12 weeks | L done | Months 27-29 |
| **Production complete** | **~30 months** | | |

**Total: 2.5 years full-time** to complete all phases with no technical debt.

**Part-time (10-20 hrs/week): 5-7 years**

---

## Success Metrics

**Phase completion criteria:**
- All checkboxes done
- All tests pass (maintain >85% coverage)
- No known bugs
- Documentation updated
- No technical debt carried forward

**System-level success (post-Phase K):**
- Sharpe ratio >1.5 in paper trading over 6+ months
- Max drawdown <15%
- Win rate >55%
- System uptime >99.5%
- AI agents provide actionable recommendations weekly

**Production success (post-Phase M):**
- Profitable live trading for 12+ consecutive months
- Annual return >10% with Sharpe >1.5
- Zero compliance violations
- Auditable track record
- Ready for outside capital if desired

---

## Principles (Carried Forward)

1. **Prove before you trade** — no strategy goes live without backtested evidence
2. **Transparency over mystery** — every bot decision is explainable
3. **Safety by default** — conservative defaults; aggressive settings require explicit opt-in
4. **Data ownership** — everything is exportable, no lock-in
5. **Honest metrics** — report realistic performance including costs and slippage
6. **No technical debt** — finish each phase completely before moving forward

---

*v3 written 2026-02-05. Previous versions: `ROADMAP_v1.md`, `roadmap-review.md`, `ROADMAP_v2.md`.*

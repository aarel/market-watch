# TESTS Q&A — Universe Invariant Assurance

**Date:** 2026-01-27  
**Context:** Responding to the Universe Isolation Decision Package. Current test suite is strong on functionality (backtests, strategies, risk checks) but does **not** yet enforce the universe invariants. Below is an evidence-based status with explicit gaps and next-step test work.

---

## 1) Invariant Coverage (illegal states must be unrepresentable)

| Invariant | Current Evidence in Tests | Gap / Needed |
| --- | --- | --- |
| LIVE order cannot be constructed/submitted in SIMULATION/PAPER | **None.** No test tags orders with universe; `tests/test_execution_agent_order_fields.py` only validates field presence, not universe separation. | Add tests that instantiate brokers per-universe and assert raises on mismatched endpoints; add construction-time universe arg to broker and make it mandatory. |
| No persistence/log stream can contain mixed universes | **None.** Analytics store tests (`tests/test_analytics_store.py`) verify JSONL write/read, not universe namespaces. | Add tests that write a SIM record then attempt a LIVE write to same path; expect failure. Enforce universe-scoped directories and assert path prefix. |
| Every metric/trade/event carries {universe, session_id, data_lineage_id, validity_class}; writes rejected otherwise | **None.** Analytics metrics tests validate math only; event/metric payloads lack these fields. | Extend schema to require these fields; write tests that omit any field and expect validation failure. |
| Universe cannot change without destructive transition (broker/event bus/agents/writers/caches rebuilt) | **None.** No transition concept in tests; `SIMULATION_MODE` flag still implied in code. | Add transition manager tests: simulate switch request; assert old broker/event bus closed, new session_id generated, caches cleared; forbid hot toggles. |

**Bottom line:** Current suite does not prove invariants; it only exercises happy paths.

---

## 2) Negative / Adversarial Tests (boundary fail-fast)

| Scenario | Current Negative Test | Result | Gap |
| --- | --- | --- | --- |
| Broker endpoint vs universe mismatch (e.g., SIM using live URL) | None | N/A | Add adversarial test: construct SIM broker with live URL → expect exception. |
| Cross-universe file paths (SIM writes into live dir) | None | N/A | Add test to ensure writer rejects path without matching universe prefix. |
| UI claims SIM while executor is LIVE | None | N/A | Add integration test: set UI flag SIM but broker live; expect API to reject manual trade. |
| Metrics missing provenance fields | None | N/A | Add test: attempt to persist metric without universe/lineage → expect validation error. |
| Lookahead/leakage in simulation | Partial coverage in backtest tests (ensures chronological order) | Pass | Add explicit lookahead-guard test tagged with universe. |

---

## 3) Completeness Claim per Capability (what is intentionally unsupported + proof)

| Capability | Unsupported behaviors that must be refused | Current tests proving refusal | Gap |
| --- | --- | --- | --- |
| Execution | Cross-universe order submission | None | Add refusal tests. |
| Market Data | Mixing live feed into SIM replay | None | Add data-loader test that rejects mixed lineage. |
| Storage | Mixed-universe persistence | None | Add path-enforcement test. |
| Analytics | Metrics without provenance | None | Add schema validation tests. |
| UI Actions | UI-specified universe overriding backend | None | Add API guard test. |

---

## 4) Trustworthiness of the Test Suite Itself

If a refactor reintroduces `SIMULATION_MODE` routing or shared persistence, **no existing test fails** because no test asserts on universe separation. Therefore the suite is not guarding correctness against the identified epistemic risks.

**Needed failing points:**
- Broker ctor must require `universe`; tests expect `TypeError` if omitted.
- Writers must assert universe-scoped paths; tests expect `ValueError` on mismatch.
- Metrics/events without `{universe, session_id, data_lineage_id, validity_class}` must raise; tests should assert specific validation errors.
- Transition without teardown must raise; tests assert stale session/caches are cleared.

---

## 5) Quantitative Sufficiency Matrix (Invariants × Universes × Failure Modes)

Legend: ✅ covered, ⚠️ partially (functional only), ❌ not covered  
Files listed where coverage exists.

| Invariant \ Failure Mode | LIVE | PAPER | SIMULATION |
| --- | --- | --- | --- |
| Leakage (cross-universe use) | ❌ | ❌ | ❌ |
| Lookahead (time travel) | ⚠️ `tests/test_backtest_engine.py` (simulation-only order of bars) | N/A | ⚠️ same |
| Partial failure (stale state survives switch) | ❌ | ❌ | ❌ |
| Stale state/caches on transition | ❌ | ❌ | ❌ |

Any empty/❌ cell = untested / unproven.

---

## 6) Actionable Test Backlog (to close gaps)

1) **Universe typing & construction tests**: add `Universe` enum, require in broker/event bus constructors; unit tests expect failure if missing/mismatched.
2) **Persistence namespace tests**: enforce `data/<universe>/...` and `logs/<universe>/...`; negative tests for cross-write.
3) **Provenance schema tests**: extend analytics/event schemas; tests reject payloads missing universe/session_id/data_lineage_id/validity_class.
4) **Destructive transition tests**: simulate transition; assert new session_id, fresh broker, cleared caches; forbid hot toggle.
5) **UI/API guard tests**: manual trade API rejects when UI universe conflicts with backend universe.
6) **Adversarial feed tests**: mixing live feed into SIM replay raises; lookahead guard with lineage tagging.

---

## 7) Conclusion

Current suite = functional confidence, **not** invariant confidence. Until the above tests (and the supporting code changes) land, the system remains vulnerable to the epistemic harm the decision package highlights. The first priority is to introduce universe-aware types/paths and make illegal states unrepresentable—then back them with negative tests that fail loud and early.

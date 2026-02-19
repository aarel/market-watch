# R2 Completion Invariants Canonical v1

## Document Authority
- STATUS: CANONICAL
- DOMAIN: R2 Completion Invariants
- GOVERNANCE: This file is the single source of truth for R2 Completion Invariants.

## Definition
R2 is COMPLETE only when all runtime trade execution flows are governed by one realism-authoritative path with deterministic, test-backed accounting outputs and no bypass persistence path.

## Invariants

### INV-R2-001: Mandatory realism pipeline on trade execution
- Target invariant: Every executed trade (buy/sell/adjustment as defined by runtime execution domain) traverses the realism pipeline before persistence/reporting.
- STATE: UNKNOWN - NOT IN CURRENT CONTEXT
- Rationale: Without mandatory traversal, reported outputs can diverge from execution truth.
- Verification method:
  - Test type: integration/e2e
  - Evidence location: `tests/domain/` (target), `tests/integration/` (target), runtime execution-path tests (TBD)
- Failure mode: A trade can be persisted without realism-adjusted outputs, producing inconsistent PnL/cost/tax state.

### INV-R2-002: Realism gate cannot default off for production-target modes
- Target invariant: `ENABLE_REALISM_PIPELINE` is locked-on for production-target runtime modes, or removed as a bypass for those modes.
- STATE: UNKNOWN - NOT IN CURRENT CONTEXT
- Rationale: Production-default bypass undermines authoritative realism guarantees.
- Verification method:
  - Test type: unit/integration
  - Evidence location: `config.py`, runtime config tests (TBD), mode-specific execution tests (TBD)
- Failure mode: Runtime starts in a mode where realism is silently disabled and outputs are non-authoritative.

### INV-R2-003: No fallback persistence path bypassing realism-adjusted accounting
- Target invariant: Persistence sinks write only records produced by the realism-authoritative execution path when realism mode is required.
- STATE: UNKNOWN - NOT IN CURRENT CONTEXT
- Rationale: Parallel persistence paths create unverifiable accounting drift.
- Verification method:
  - Test type: integration/e2e
  - Evidence location: `analytics/store.py` integration tests (target), execution-to-store flow tests (TBD)
- Failure mode: A fallback path stores legacy fields without realism provenance, causing audit gaps.

### INV-R2-004: Single source of truth for PnL and cost basis
- Target invariant: One canonical compute path owns realized/unrealized PnL and cost-basis outputs for trade lifecycle accounting.
- STATE: UNKNOWN - NOT IN CURRENT CONTEXT
- Rationale: Duplicate compute paths produce non-deterministic reconciliation outcomes.
- Verification method:
  - Test type: unit/integration
  - Evidence location: domain accounting tests in `tests/domain/` (target), analytics reconciliation tests (TBD)
- Failure mode: Two compute paths emit conflicting PnL/cost-basis values for identical trade history.

### INV-R2-005: Runtime invariants enforced consistently across declared modes
- Target invariant: Sim/live/backtest modes (as defined by canonical runtime docs) enforce equivalent realism invariants where mode-specific exceptions are explicitly documented.
- STATE: UNKNOWN - NOT IN CURRENT CONTEXT
- Rationale: Mode drift causes environment-specific correctness regressions.
- Verification method:
  - Test type: integration/e2e
  - Evidence location: mode matrix tests (target), runtime mode contract tests (TBD)
- Failure mode: One mode bypasses checks that others enforce, making behavior non-portable and non-auditable.

## R2 Completion Gate
R2 completion requires:
- All invariants above marked VERIFIED (not UNKNOWN).
- Verification evidence checked into test paths and referenced in release notes/status artifacts.
- Canonical roadmap/status documents updated with explicit pass/fail outcome for each invariant.

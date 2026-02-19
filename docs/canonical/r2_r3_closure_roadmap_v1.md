# R2 to R3 Closure Roadmap Canonical v1

## Document Authority
- STATUS: CANONICAL
- DOMAIN: R2 to R3 Closure Roadmap
- GOVERNANCE: This file is the single source of truth for R2 to R3 Closure Roadmap.

## Scope
Commit-sized closure plan for moving from R2 integration hardening to R3 fee/tax production wiring with explicit pause gates.

## Canonical Planning Note
- De-facto roadmap authority for phase status is `ROADMAP.md`.
- This closure roadmap is self-contained and normative for R2->R3 hardening sequence.

## Steps

### STEP-R2R3-001
- Goal: Complete governance enforcement and authority tagging.
- Scope: Canonical/supporting/legacy markers and matrix consistency.
- Files likely touched: `docs/governance/document_authority_matrix.md`, runtime/roadmap/communicate docs with authority headers.
- Verification gates:
  - Validate one canonical per conflict domain in matrix.
  - Verify non-canonical docs include canonical pointer.
- Rollback note: Revert header/matrix-only changes if authority mapping is inconsistent.
- Suggested git commit message: `docs: enforce canonical authority headers and matrix supersession links`

### STEP-R2R3-002
- Goal: Add test scaffolding that can prove R2 invariants.
- Scope: Introduce test placeholders/harnesses for execution-path realism checks (no behavior rewrite yet).
- Files likely touched: `tests/domain/*`, `tests/integration/*`, `tests/e2e/*`, `tests/README.md`.
- Verification gates:
  - New scaffolding tests compile/run in CI target matrix.
  - Missing evidence paths explicitly marked as pending, not silently skipped.
- Rollback note: Remove scaffolding additions if they create unstable or non-deterministic baseline.
- Suggested git commit message: `test: scaffold R2 invariant verification suites`

### STEP-R2R3-003
- Goal: Lock realism pipeline invocation boundary for executed trades.
- Scope: Ensure one authoritative execution-to-realism handoff path.
- Files likely touched: execution agent/event flow modules, realism boundary modules, integration tests.
- Verification gates:
  - Gate-on path test proves realism traversal before persistence.
  - Negative-path tests prove bypass attempts fail closed.
- Rollback note: Revert boundary wiring if trade execution correctness or compatibility regresses.
- Suggested git commit message: `fix: enforce single realism invocation boundary for executed trades`

### STEP-R2R3-004
- Goal: Remove or lock production-default bypass for realism gate.
- Scope: Runtime mode gating and configuration enforcement.
- Files likely touched: `config.py`, runtime mode config loaders, config tests.
- Verification gates:
  - Production-target mode tests assert realism gate cannot default false.
  - Backward-compatibility tests for non-production mode expectations remain green.
- Rollback note: Roll back gate-lock changes if production startup compatibility is broken.
- Suggested git commit message: `fix: lock realism pipeline on for production-target runtime modes`

### STEP-R2R3-005
- Goal: Eliminate fallback persistence that bypasses realism-adjusted outputs.
- Scope: Persistence sink normalization and provenance enforcement.
- Files likely touched: persistence/store modules, integration tests, reporting adapters.
- Verification gates:
  - Persisted records include realism provenance on required modes.
  - No alternate write path can store non-authoritative accounting outputs.
- Rollback note: Revert persistence path consolidation if data-loss or schema-compatibility risk appears.
- Suggested git commit message: `fix: remove non-authoritative persistence fallback for realism accounting`

### STEP-R2R3-006
- Goal: Unify PnL and cost-basis computation path.
- Scope: Consolidate compute ownership and remove parallel accounting derivations.
- Files likely touched: domain accounting modules, analytics reconciliation paths, unit/integration tests.
- Verification gates:
  - Determinism tests pass for repeated identical trade streams.
  - Reconciliation tests confirm one canonical output source.
- Rollback note: Revert compute consolidation if reconciliation parity degrades.
- Suggested git commit message: `refactor: unify pnl and cost-basis computation authority`

### STEP-R2R3-007
- Goal: Validate cross-mode invariant consistency and exit R2.
- Scope: Sim/live/backtest consistency matrix and final R2 completion evidence.
- Files likely touched: mode matrix tests, roadmap/status docs, release checklist docs.
- Verification gates:
  - Invariant matrix passes in all declared modes or documented exceptions.
  - R2 completion report references concrete evidence paths for each invariant.
- Rollback note: Revert R2 status promotion if any invariant remains unverified.
- Suggested git commit message: `chore: publish r2 completion evidence and mode-consistency gate results`

### STEP-R2R3-008
- Goal: Begin R3 fee/tax production wiring under controlled scope.
- Scope: Implement fee/tax production behaviors only after R2 gates are closed.
- Files likely touched: domain fee/tax modules, runtime wiring, regression and compliance tests.
- Verification gates:
  - Fee/tax computations validated against regression fixtures.
  - No R2 invariant regression introduced by R3 changes.
- Rollback note: Revert R3 wiring if fee/tax output parity or invariant safety regresses.
- Suggested git commit message: `feat: start r3 fee-tax production wiring with invariant guardrails`

## Pause Policy
- Stop after each step and verify all gates before continuing.
- Do not batch multiple steps into a single commit.
- If a gate fails, open a corrective step before proceeding.

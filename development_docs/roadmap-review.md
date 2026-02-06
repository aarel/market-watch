Market-watch Roadmap (universe-safe Rewrite)
Market-Watch — Architecture-First Roadmap

A living roadmap governing the evolution of Market-Watch into a professionally trustworthy trading system. This document is not a feature plan. It is an architectural contract.

Document Status: Active Last Updated: 2026-01-26 Architectural Baseline: Universe-Separated Execution

0. Non-Negotiable Design Premise

Market-Watch operates across three distinct universes:

LIVE — Real capital, real execution, irreversible consequences

PAPER — Broker-mediated paper accounts with real market constraints

SIMULATION — Synthetic or replayed environments for learning and testing

These are separate realities, not modes.

If a user cannot always answer “Which universe produced this result?” with certainty, the system is architecturally invalid.

This roadmap enforces that principle at every phase.

1. Universe Model (Foundational)
1.1 Explicit Universes

Each universe is defined by an immutable tuple:

Execution Authority — What executes actions

Data Authority — Where market data originates

State Authority — Where positions, cash, and history persist

Temporal Semantics — What “now” means

No component may operate without an explicit universe context.

1.2 Forbidden Assumptions

The following are explicitly disallowed:

Boolean flags such as SIMULATION_MODE

Runtime auto-switching between universes

Shared brokers across universes

Shared persistence namespaces

UI-only signaling of execution context

Universe selection is construction-time, not runtime.

2. Architectural Invariants

These invariants apply to all phases:

Universe as Type — Every execution path carries a universe value

Isolation by Construction — Cross-universe state sharing is impossible by default

Fail Fast on Ambiguity — Ambiguous execution halts the system

Simulation Is Adversarial — Simulation must resist overconfidence

Falsifiability — Every claim of correctness must have a measurable disproof

Any feature that violates an invariant is rejected, regardless of utility.

3. Phase Structure Overview

Phases are ordered by architectural dependency, not user-facing appeal.

Universe Isolation Core

Backtesting (Simulation Universe)

Strategy Framework

Risk System (Universe-Aware)

Analytics & Epistemic Labeling

Paper Trading (Paper Universe)

Live Trading (Live Universe)

Multi-Broker Support (Per-Universe)

Testing & Falsification

Documentation & Verification

Track Record Attestation

Phase 1: Universe Isolation Core (MANDATORY)
Objective

Establish hard separation between LIVE, PAPER, and SIMULATION before any further development.

Deliverables

Universe enum as a required constructor argument

Universe-scoped:

Broker interfaces

Persistence namespaces

Audit logs

Event buses

Compile-time or construction-time prevention of cross-universe access

Success Criteria

A LIVE order cannot be constructed inside SIMULATION code

A SIMULATION result cannot be misattributed as LIVE

Removing UI indicators does not create ambiguity

Phase 2: Backtesting (Simulation Universe Only)
Objective

Provide historically accurate but epistemically honest simulation.

Constraints

Decision-time data only (no lookahead)

Explicit latency, slippage, and fill models

Deterministic replay with recorded randomness

Invalidation Rules

Backtest results are automatically marked INVALID_FOR_TRAINING if:

Execution assumptions diverge from Live constraints

Latency is disabled

Partial fills are ignored

Outputs

Metrics explicitly labeled SIMULATION_ONLY

No promotion to strategy validation without out-of-sample testing

Phase 3: Strategy Framework
Objective

Enable strategies that are portable across universes without semantic drift.

Design Rules

Strategies are pure decision functions

No broker access

No side effects

No implicit timing assumptions

Validation

Strategies must declare required historical context

Strategy outputs must be universe-agnostic signals, not actions

Phase 4: Risk System (Universe-Aware)
Objective

Enforce risk limits that are stricter in Live than in Simulation.

Rules

Risk checks execute before execution authority

Circuit breakers are universe-specific

Simulation may exceed limits only if explicitly labeled exploratory

Failure Handling

Risk violation in LIVE → hard stop

Risk violation in SIM → flagged learning event

Phase 5: Analytics & Epistemic Labeling
Objective

Ensure analytics cannot lie by omission.

Requirements

Every metric must include:

Universe of origin

Execution assumptions

Validity class (LIVE_VERIFIED, PAPER_ONLY, SIM_INVALID_FOR_TRAINING)

Metrics without provenance are rejected.

Phase 6: Paper Trading (Paper Universe)
Objective

Provide a broker-constrained learning environment without capital risk.

Rules

Paper trading uses a distinct broker identity

Real market hours and rejections apply

Results are never conflated with Live

Phase 7: Live Trading (Live Universe)
Objective

Enable capital deployment only after epistemic prerequisites are met.

Preconditions

Strategy validated in Simulation

Paper results within defined deviation band

User explicit acknowledgment of Live transition

Enforcement

Live execution requires separate credentials

Live state cannot be reused by other universes

Phase 8: Multi-Broker Support
Objective

Support multiple brokers without collapsing execution semantics.

Rules

Brokers are universe-scoped

No broker hot-swapping

Capability mismatches are explicit

Phase 9: Testing & Falsification
Objective

Prove not only that the system works — but that it fails safely.

Required Test Classes

Universe leakage tests

Illegal-state construction tests

Temporal distortion tests

Simulation overconfidence tests

A test suite that cannot detect epistemic failure is incomplete.

Phase 10: Documentation & Verification
Objective

Make system truth externally auditable.

Documentation Must Answer

Which universe produced this result?

Under what assumptions?

What would invalidate it?

Phase 11: Track Record Attestation
Objective

Provide cryptographically verifiable, universe-bound performance records.

Constraints

Hash chains include universe identity

Simulation records cannot be promoted

Verification tooling included

12. Success Metrics (Revised)
Trust Metrics (Primary)

Zero ambiguous executions

Zero universe-crossing incidents

Explicit invalidation of misleading simulations

Performance Metrics (Secondary)

Live results within declared risk envelope

Simulation results bounded by realism constraints

Closing Principle

Market-Watch succeeds only if it makes the wrong thing impossible.

Features that increase convenience at the cost of epistemic clarity are not improvements — they are regressions.

This roadmap is the enforcement mechanism.
## Document Authority
- STATUS: CANONICAL
- DOMAIN: Roadmap Planning
- GOVERNANCE: This file is the single source of truth for Roadmap Planning.

# ROADMAP

Canonical roadmap reconstructed from the architectural baseline and the R-track realism model.

## SECTION A - Architecture Baseline

### Core Architecture Intent
- Preserve typed execution context boundaries and explicit universe isolation.
- Keep trade execution, risk, analytics, and persistence boundaries deterministic.
- Require operational observability and auditable governance as first-class runtime constraints.
- Treat roadmap phases as enforcement contracts, not feature wishlists.

### Core Subsystems
- Runtime and execution orchestration.
- Risk controls and guardrails.
- Analytics and reporting persistence.
- Backtesting and strategy evaluation.
- Observability, operations, and governance.

### Execution Boundary Rules
- No ambiguous execution-mode behavior.
- No parallel authoritative accounting paths.
- No production bypass of required realism controls once enforced.
- No documentation authority drift from canonical planning artifacts.

### Architectural Guardrails
1. Universe is a construction-time boundary, not a mutable runtime flag.
2. Isolation-by-construction is required for state, broker integration, and persistence domains.
3. Ambiguous or contradictory runtime states fail closed.
4. Correctness claims require measurable verification evidence.

## SECTION B - Execution Spine (Realism Axis)

The R-track phases form a mandatory execution spine. Feature domains can progress only when required R-phase gates are satisfied.

| R Phase | Purpose | Entry | Exit (binary) | Blocking Impact | Required Tests | Logging | Invariants |
|---|---|---|---|---|---|---|---|
| R1 Structural Modules | Establish structural realism modules (corporate actions, cost basis, settlement) | Baseline runtime contracts active | All R1 module contracts implemented and deterministic tests passing | Blocks R2-R5 and any feature relying on authoritative realism | Unit + integration for domain modules | Module-level provenance logs for transforms | Deterministic transformations; no silent mutation paths |
| R2 Authoritative Integration | Route executed trades through one realism-authoritative runtime path | R1 complete, CI/test gates available | Executed-trade pipeline uses single realism path in Declared Runtime Modes with no bypass persistence | Blocks R3-R5 and any production truth claims on realism outputs | Integration + e2e for execution to persistence path; regression guards | Trade-level realism provenance and gate-state logs | Single compute authority; no fallback bypass for authoritative modes |
| R3 Fee and Tax Production Wiring | Harden fee/tax outputs for production usage | R2 complete | Fee/tax outputs validated by deterministic fixtures and regression suites | Blocks R4-R5 production rollout and compliance claims involving fees/taxes | Unit + integration + e2e for fee/tax scenarios | Fee/tax component and reconciliation logs | No duplicate fee/tax computation authorities |
| R4 Margin and FX | Expand realism for margin and FX behavior | R3 stable | Margin/FX behavior integrated across declared modes with passing verification matrix | Blocks R5 expansion where margin/FX realism is required | Unit + integration + e2e mode matrix tests | Margin/FX decision logs with mode context | Mode-consistent invariant enforcement |
| R5 International Extensions | Define and implement international realism constraints | R4 foundations complete | International constraints documented and validated for implemented markets | Blocks system-complete realism claims across international scopes | Unit + integration for region-specific constraints | Market-specific constraint and exception logs | No undocumented market-specific behavior |

### R2 Completion Gate Clarification
- Defining canonical runtime modes is a prerequisite milestone before R2 may be marked COMPLETE.
- If no canonical runtime-mode authority exists, runtime mode authority location is UNKNOWN and this blocks R2 completion.

## SECTION C - Feature Domains (Reorganized A-M)

### Platform Integrity (A, F, G)
- Scope: hardening, CI/testing gates, configuration profile safety.
- PREREQUISITE FOR: R2 (provides CI, config safety, governance enforcement).
- PRODUCTION-AUTHORITY CLAIMS BLOCKED UNTIL: R2 complete.
- Entry: Runtime governance active; baseline contracts loaded.
- Exit: Quality gates enforce invariant coverage and no unresolved critical drift.
- Required Tests: unit, integration, and CI gate coverage relevant to affected components.
- Logging: governance checks, CI outcomes, and config-change provenance.

### Observability (B, C)
- Scope: monitoring, anomaly detection, and alerting pathways.
- BLOCKED UNTIL: R1 complete.
- Entry: Baseline telemetry path available.
- Exit: Operational signals and alerts validated for critical runtime failures.
- Required Tests: unit + integration for telemetry and alert reliability.
- Logging: anomaly events, alert delivery outcomes, and recovery trails.

### Analytics and Backtesting (D, H)
- Scope: analytics correctness, backtest fidelity, and export reliability.
- BLOCKED UNTIL: R2 for authoritative execution linkage; R3 for fee/tax truth claims.
- Entry: Canonical analytics field contract defined.
- Exit: Analytical outputs are reproducible and aligned with authoritative execution accounting.
- Required Tests: unit + integration + deterministic regression suites.
- Logging: analytics lineage, report/export generation, and benchmark metadata.

### ML and AI (I, J, K)
- Scope: ML infrastructure, strategy development, and agent orchestration.
- BLOCKED UNTIL: R2 complete; R3 required for production-grade economic metrics.
- Entry: Canonical datasets and evaluation boundaries defined.
- Exit: Model/agent behavior is measurable, bounded, and reproducible under governance constraints.
- Required Tests: unit, integration, evaluation harness tests, and safety/e2e scenarios.
- Logging: model lineage, decision traces, and agent action audit logs.

### Production and Compliance (L, M)
- Scope: production readiness, auditability, and release discipline.
- BLOCKED UNTIL: R2 and R3 complete; R4/R5 as applicable to declared market scope.
- Entry: Release checklist and compliance evidence framework prepared.
- Exit: Operational readiness and audit evidence pass documented gates.
- Required Tests: integration + e2e release rehearsal and compliance evidence checks.
- Logging: release runbooks, incident drills, and immutable compliance artifacts.

## SECTION D - Dependency Graph Table

| Phase | Requires | Blocks | Notes |
|---|---|---|---|
| A Platform Hardening | Runtime governance baseline | B-M, R-track safety claims if incomplete | Foundational integrity layer |
| B Observability | A | C, operational confidence for D onward | Monitoring baseline |
| C External Alerts | B | Incident responsiveness for later phases | Alerting depends on observability signals |
| D Analytics Completion | A and R2 for authoritative realism outputs | H and downstream reporting trust | Analytics must align with execution truth |
| E Market Awareness | C | L and M market-event safety posture | Depends on reliable event signaling |
| F Testing and CI | A | All roadmap phases (quality gate) | Mandatory verification backbone |
| G Configuration Profiles | A and F | Safe multi-profile operations | Profile controls must preserve invariants |
| H Backtesting Enhancement | D and R2 (R3 for fee/tax-grade claims) | I/J strategy fidelity confidence | Backtest realism must track R-spine |
| I ML Infrastructure | A-H maturity and F gating | J and K | Requires trusted datasets/contracts |
| J ML Strategy Development | I and H | K and L strategy rollout confidence | Evaluation validity required |
| K AI Agent Coordination | I and J | L production autonomy claims | Safety boundaries mandatory |
| L Production Readiness | A-K maturity and R2/R3 completion | M and release authorization | Release gate phase |
| M Compliance and Auditability | L and R2/R3 evidence | System completion declaration | Audit closure phase |
| R1 Structural Modules | Baseline governance + architecture constraints | R2-R5 | Realism foundation |
| R2 Authoritative Integration | R1 and F | R3-R5 and realism-dependent feature claims | Mandatory spine gate |
| R3 Fee and Tax Wiring | R2 | R4-R5 and production economic truth claims | Economic realism gate |
| R4 Margin and FX | R3 | R5 and expanded market realism claims | Tier-B realism gate |
| R5 International Extensions | R4 | Global realism completeness claims | International realism gate |

## Declared Runtime Modes

- MODE LIST: UNKNOWN - NOT IN CURRENT CONTEXT
- Reference policy: until canonical runtime mode authority is explicitly linked here, all R2/R3 production-authority claims must include explicit mode scope in evidence.

## SECTION E - Global Definition of Done

System-complete status requires all of the following:
1. Exactly one canonical roadmap authority with all supporting/legacy artifacts explicitly tagged.
2. R2 invariants are verified, not unknown, for declared runtime modes.
3. No bypass path exists for authoritative execution accounting in required modes.
4. Test evidence exists for all completed phases at declared unit/integration/e2e levels.
5. Logging and telemetry requirements are implemented and auditable for completed phases.
6. No unresolved critical contradictions exist between canonical planning, status, and governance artifacts.
7. Release and compliance phases include reproducible evidence trails for audited claims.

## Status Update Discipline

Status updates require all three:
1. Commit or PR reference.
2. Test evidence reference.
3. Rationale for status change (what became true and why).

## Artifact Conflict Resolution Protocol

Any new roadmap artifact must be tagged SUPPORTING or LEGACY within one commit, or explicitly promoted to CANONICAL with a same-change authority-matrix update.

## Current R-Track Status Snapshot

- R1: COMPLETE (structural).
- Verification Status: UNVERIFIED_IN_THIS_ENVIRONMENT.
- Missing Evidence: pytest runtime unavailable in this environment; test execution pass artifact pending.
- R2: Not complete.
- R3: Partial.
- R4: Not started.
- R5: Not started.

## Active Focus Phase
- R2 Authoritative Integration

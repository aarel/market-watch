## Document Authority
- STATUS: CANONICAL
- DOMAIN: Roadmap Planning
- GOVERNANCE: This file is the single source of truth for Roadmap Planning.

# ROADMAP

Canonical planning model reconstructed from:
- `development_docs/roadmap/2026-02-07/ROADMAP.md` (architectural baseline)
- R-track structure referenced in newer planning artifacts

## SECTION A - Architecture Baseline

### Core Subsystems
- Universe/runtime isolation and execution context integrity.
- Execution/risk/analytics pipeline with deterministic persistence contracts.
- Strategy/backtest/observability layers with documented operator boundaries.
- Deployment/operations/governance controls for reproducible runtime behavior.

### Execution Boundaries
- Trade execution and trade accounting boundaries must remain explicit.
- Realism processing cannot become an optional side-path for authoritative outputs once R2 is complete.
- Planning documents cannot override runtime governance contracts.

### Invariant Guardrails
1. Universe is a typed execution boundary, not a runtime toggle.
2. Isolation-by-construction is required for state, brokers, and persistence scopes.
3. Ambiguous execution context must fail closed.
4. Every correctness claim requires measurable disproof (tests/evidence).
5. No phase is complete while known critical defects or unverifiable assumptions remain.

## SECTION B - Phase Model

### Original Numbered Model to R<n> Mapping

| Original Phase | R<n> Phase | Overlap | Conflict | Gap |
|---|---|---|---|---|
| A Hardening | R2 (governance of execution path), R1 (deterministic module behavior prerequisites) | Quality hardening and invariant discipline support realism integration | A was broader platform hardening; R-track is realism-specific | Explicit realism authority checks were not formalized in A |
| B Observability | R2 and R3 verification support | Monitoring/telemetry needed for realism evidence | None direct | Missing explicit realism-specific observability gates |
| C External Alerts | R2/R3 operational safety support | Alerting helps detect invariant regressions | None direct | No direct realism contract ownership |
| D Analytics Completion | R2 authoritative output wiring | Analytics trust depends on authoritative execution-accounting linkage | Legacy analytics paths may diverge from realism authority | Need canonical single accounting source |
| E Market Awareness | R5 international/market constraints adjacency | Session/calendar behavior affects realistic execution assumptions | E is market/event policy, not realism accounting core | Cross-market realism validation criteria not fully codified |
| F Testing and CI | R2/R3 gate enforcement | CI/testing gates prove realism invariants | None direct | Dedicated realism invariant suites incomplete |
| G Configuration Profiles | R2 gate-control behavior | Config profiles affect realism enablement semantics | Risk of toggle drift vs production invariants | Production-mode lock semantics need explicit enforcement |
| H Backtesting Enhancement | R2/R3 parity and replay relevance | Backtest realism, transaction costs, and replay quality overlap | H may scope work that should be classified as R2/R3 runtime realism | Ownership boundary needed to avoid duplicate implementation |
| I ML Infrastructure | R-track consumer dependency | ML relies on trusted accounting outputs | None direct | Must block ML claims on unresolved R2 invariants |
| J ML Strategy Development | R-track consumer dependency | Strategy optimization depends on correct PnL/cost/tax semantics | None direct | Validation sets must include realism-aware fixtures |
| K AI Agent Coordination | R-track consumer dependency | Agent decisions require authoritative execution truth | None direct | Guardrails needed against unverified execution assumptions |
| L Production Readiness | R2/R3 completion gate | Production release should require realism invariants in scope | None direct | Release checklist must include R2/R3 evidence |
| M Compliance and Auditability | R2/R3 evidence surface | Audit paths depend on deterministic accounting lineage | None direct | Explicit realism evidence reporting policy required |

### Phase Catalog (Canonical Plan)

| Phase | Purpose | Entry Criteria | Exit Criteria (measurable) | Required Tests | Logging and Telemetry Requirements | Invariants Must Not Be Violated | Risk Notes |
|---|---|---|---|---|---|---|---|
| A Hardening | Establish safe technical foundation | Runtime governance active, critical defects triaged | Baseline hardening items closed and regression suite green | Unit + integration for isolation/config/risk boundaries | Structured runtime logs for critical control paths | Typed universe, isolation, fail-closed ambiguity | Hidden coupling can invalidate downstream phases |
| B Observability and Monitoring | Make runtime behavior measurable | A complete | Endpoint/runtime observability metrics available and validated | Unit + integration for telemetry/anomaly paths | Persistent health/anomaly metrics with operator visibility | No silent failures in monitored paths | Incomplete coverage can create false confidence |
| C External Alerts | Surface critical failures rapidly | B complete | Alert routes validated for critical events and retry behavior | Unit + integration for alert channels and retries | Alert event logs with severity and delivery status | No suppression of critical invariant breaches | Alert fatigue or delivery failures can mask issues |
| D Analytics Completion | Ensure dashboard/report output trust | A complete | Core analytics outputs validated against execution records | Unit + integration for PnL/equity/report calculations | Audit-ready analytics logs and export traces | No parallel contradictory accounting outputs | Analytics drift from execution truth |
| E Market Awareness | Avoid known market/event danger zones | C complete | Trading-window/event controls enforced with edge-case coverage | Unit + integration for calendar/event gates | Event decision logs with pause/resume reasons | No ungoverned execution during blocked windows | Calendar correctness and timezone edge cases |
| F Testing and CI | Enforce automated quality gates | A-D materially stable | CI gates run deterministically with required coverage thresholds | Unit + integration + e2e in CI matrix | CI artifacts retained for audit and drift analysis | No phase progress without test evidence | Flaky tests and weak gates reduce confidence |
| G Configuration Profiles | Enable safe runtime profile switching | A + F in place | Profile lifecycle stable with rollback and validation | Unit + integration for profile persistence/restore | Profile change logs with provenance | No profile may bypass production invariants | Misconfigured profiles can silently degrade safety |
| H Backtesting Enhancement | Improve realism and benchmark quality in simulation | A-G complete | Backtest outputs validated against known baselines and realism assumptions | Unit + integration + performance/regression tests | Run-level metadata and benchmark traces | No backtest claims without reproducible evidence | Overfitting and unrealistic assumptions |
| I ML Infrastructure | Build shared ML data/training infrastructure | A-H complete | Data/training pipeline reproducible with documented interfaces | Unit + integration + data-quality tests | Training/inference lineage logs | No ML pipeline bypassing canonical data contracts | Data leakage and non-reproducibility |
| J ML Strategy Development | Develop and evaluate ML trading strategies | I complete | Strategy evaluation criteria met with out-of-sample validation | Unit + integration + evaluation/backtest tests | Model decision and evaluation logs | No deployment on unverified metrics | Metric gaming and regime fragility |
| K AI Agent Coordination | Coordinate multi-agent runtime behavior safely | I/J mature | Agent orchestration passes safety and fallback checks | Unit + integration + scenario/e2e tests | Agent action/reason logs with traceability | No unsafe autonomous execution paths | Emergent behavior and control-loop instability |
| L Production Readiness | Prepare stable production operations | A-K closure evidence available | Release checklist, rollback drills, and operational runbooks validated | Integration + e2e + release rehearsal tests | Production-grade operational telemetry coverage | No release while critical invariants unresolved | Operational surprises under real load |
| M Compliance and Auditability | Achieve audit-grade governance/reporting | L complete | Compliance evidence complete and reproducible | Integration + e2e + audit evidence checks | Immutable evidence trail for key controls | No undocumented authority drift | Documentation and evidence fragmentation |
| R1 Structural Realism Modules | Implement Tier A realism components | A baseline complete | Corporate actions/cost basis/settlement module behavior validated | Unit + integration for realism modules | Module output and provenance traces | Deterministic financial transforms only | Module-runtime disconnect risk |
| R2 Authoritative Runtime Realism Integration | Make realism path authoritative in execution flow | R1 and F gates active | Executed trades route through canonical realism path with no bypass in required modes | Integration + e2e for execution->realism->persistence | Trade-level realism provenance and invariant logs | No duplicate compute path; no bypass persistence | Partial wiring can create silent accounting drift |
| R3 Fee and Tax Production Wiring | Harden fee/tax outputs for production use | R2 complete | Fee/tax outputs validated with deterministic fixtures and regression gates | Unit + integration + e2e for fee/tax flows | Fee/tax computation trace and reconciliation logs | No conflicting fee/tax compute outputs | Jurisdictional complexity and edge-case drift |
| R4 Tier B Margin and FX | Expand realism to margin/FX execution semantics | R2 stable, R3 in controlled state | Margin/FX models integrated and test-validated in runtime modes | Unit + integration + e2e mode tests | FX/margin decision telemetry with mode context | No mode-specific bypass of core invariants | Model complexity and data timing risks |
| R5 International Extensions | Add international realism placeholders/expansion path | R4 foundations ready | Scope boundaries and country-specific constraints documented and tested where implemented | Unit + integration for new market rules | Cross-market assumptions and exceptions logged | No undocumented market-specific behavior | Regulatory variance and incomplete datasets |

## SECTION C - Phase Definition Template

Use this template for every new or revised phase entry:

1. Purpose
2. Entry Criteria
3. Exit Criteria (measurable, binary pass/fail)
4. Required Tests
5. Logging and Telemetry Requirements
6. Invariants that must not be violated
7. Risk notes
8. Commit-scope rule:
   - No multi-feature sweeps unless phase is in a stable closure window.
   - Each step must produce a clean git boundary and verifiable evidence.

## Governance Rules (Mandatory)

1. No phase may introduce untested execution paths.
2. No phase may leave production invariants behind permanent toggles.
3. No phase may create duplicate compute paths for authoritative outputs.
4. After R2 completion, no phase may bypass realism pipeline for required modes.
5. All phases touching docs must keep authority matrix aligned with actual authority.
6. Any new subsystem phase must define canonical doc location and immediate test scaffolding.

## Planning Status Snapshot (Roadmap Authority)

- R1: ~90% module-level complete.
- R2: NOT COMPLETE.
- R3: PARTIAL.
- R4: NOT STARTED.
- R5: NOT STARTED.

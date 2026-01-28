# Market-Watch — Universe Isolation Decision Package (Consolidated)

**Date:** 2026-01-27  
**Scope:** Combine ROADMAP.md, TECHNICAL_REPORT.md, the external universe-isolated roadmap review, and two engineering perspectives into one actionable plan.

This document is a **system contract** for preventing epistemic harm across **LIVE**, **PAPER**, and **SIMULATION**.

---

## 1) Non-Negotiable Premise

Market-Watch runs in three separate universes:

- **LIVE**: real capital, irreversible execution
- **PAPER**: broker-mediated paper accounts with real market constraints
- **SIMULATION**: synthetic or replayed environments used for learning/testing

If a user cannot always answer **“Which universe produced this result?”** with certainty, the architecture is invalid.

---

## 2) Source Inputs (What was merged)

### 2.1 Existing project documents
- ROADMAP.md (current feature-first plan)
- TECHNICAL_REPORT.md (current implementation report)
- MIGRATION_ASSESSMENT.md (rewrite vs hybrid vs continue)

### 2.2 External critique (universe-isolated design)
- “roadmap-review.md” (concept: explicit universes, no mode toggles, provenance, isolation, fail-fast ambiguity)

### 2.3 Engineer perspectives (as provided)
#### Engineer A (middle path)
Recommendations on “roadmap-review.md” and why it diverges

What’s valuable
- Universe clarity: Forcing every path to carry a universe label (LIVE/PAPER/SIM) would prevent many of the SIM/live confusions you’ve been fighting (bad badges, wrong broker, mixed logs).
- Provenance on metrics: Epistemic labeling would fix the current analytics ambiguity (metrics showing “--” and SIM vs live confusion).

What clashes with the current system
- No runtime switching: Your product vision includes SIM auto-switching after market close; the rewrite bans runtime toggles and demands construction-time universe selection.
- Shared components: Today broker, analytics store, and config are shared with a SIM flag; the rewrite wants separate brokers, stores, and event buses per universe.
- Roadmap sequencing: Existing roadmap is feature-first (Phases 4 analytics, 11 testing), while the rewrite is architecture-first (Universe Isolation Core before everything).

Practical middle path
1. Formalize a Universe enum and context object now, but allow controlled runtime switching via a broker factory that rebuilds state when the universe changes.
2. Namespace state and logs by universe: data/{live|paper|sim}/…, logs/{live|paper|sim}/…, and include universe in every event/metric payload.
3. Broker boundary: wrap Alpaca/FakeBroker in a UniverseBroker that refuses cross-universe use and requires explicit universe on construction.
4. Analytics provenance: add universe, validity_class, and assumptions fields to stored trades/metrics; reject writes without them.
5. UI alignment: surface the explicit universe tag and block actions that mismatch (e.g., don’t allow live orders when context is SIM).
6. Phasing: keep current roadmap but insert a “Universe Guardrails” subtask ahead of SIM auto-switching and analytics fixes; avoid a full stop to redo everything.

Why the direction wasn’t “wrong”
- It’s a stricter interpretation of a real problem you already have (context ambiguity). It’s overcorrecting by banning runtime toggles and shared components. We can harvest the good constraints (explicit universe, provenance, isolation-by-namespace) without sacrificing planned features like SIM auto-switch.


#### Engineer B (migration assessment)
I've created a comprehensive migration assessment document comparing your current architecture against the external reviewer's universe-isolated design.

Key Findings
The Good News:
- ~50% of your codebase is salvageable - Strategies, backtesting engine, performance metrics, and risk calculations are already compliant with universe isolation principles
- Your test suite (181 tests) and documentation are valuable assets

The Reality:
- ~50% must be rewritten - Configuration system, broker layer, persistence, and API endpoints fundamentally violate universe isolation principles
- Main violations: Boolean SIMULATION_MODE flag, runtime mode switching, shared persistence namespaces, UI-only mode signaling

Three Paths Forward
Option A: Full Rewrite (New Project)
- Time: 6-8 weeks (240-320 hours)
- Salvage: 0% (start fresh, use current as reference)
- Best For: Professional/investor audience, want perfect architecture
- Risk: High psychological cost, scope creep, unknown unknowns

Option B: Hybrid Migration (Recommended)
- Time: 4 weeks (160 hours)
- Salvage: 50% (~4,250 lines)
- Best For: Personal trading, preserve investment, learn through refactoring
- Risk: Medium complexity, but always have working code

Option C: Continue Current Path
- Time: 2-3 weeks to Phase 7
- Salvage: 100% (no changes)
- Best For: Personal use only, time-constrained, skeptical of reviewer
- Risk: Technical debt compounds, cannot claim professional-grade safety

Recommendation: Option B (Hybrid)

Week plan:
- Week 1: Namespace isolation (separate data/logs by universe)
- Week 2: Universe types (replace boolean flags with enum)
- Week 3: Construction-time selection (lock universe at startup)
- Week 4: Cleanup, testing, validation

This gets you 80-90% compliance with the reviewer's architecture in 25% of the rewrite time, while preserving your working code.


---

## 3) Current-State Diagnosis (Agreed Facts)

From the technical report and migration assessment, the core violations are consistent:

### 3.1 Severity-0 (architectural) failures
- **Mode as boolean/config** (`SIMULATION_MODE`) controlling execution
- **Runtime mode switching** via API/config
- **Shared persistence namespaces** across universes
- **UI-only mode signaling** (badges/colors) standing in for system truth
- **Shared broker abstraction** where behavior diverges by flag rather than by universe authority

### 3.2 What is already strong / salvageable
- Strategy framework is largely pure and portable
- Backtesting engine is mostly isolated to simulation semantics
- Metrics math and risk calculations are largely universe-agnostic computation
- Test suite and docs are meaningful assets

---

## 4) Unified Decision

Decision Summary (Unified)
- Adopt universe isolation as a hard correctness requirement (not a UX improvement).
- Choose a Hybrid Migration path, but modify it: any universe change must be a destructive transition that tears down the execution graph (broker, event bus, agents, writers, caches) and reinitializes in the target universe with a new session/audit root.
- Preserve the product goal of “SIM after hours,” but implement it as an orchestrated restart or a controlled transition that is observable, audited, and cannot preserve in-memory continuity across universes.
- Treat claims as falsifiable: simulation results must carry a validity_class and can be automatically invalidated (INVALID_FOR_TRAINING) when realism constraints are disabled or violated.


### 4.1 Why this is the only stable middle path
Engineer A is correct that the external critique conflicts with planned SIM convenience features. Engineer B is correct that a hybrid refactor preserves investment.

However, **“runtime switching” is only safe if it is a stateful, destructive universe transition**. Any hot-swap that preserves the execution graph recreates the original epistemic failure with better packaging.

Therefore:
- **Allowed:** “SIM auto-switch after close” implemented as an orchestrated restart/transition.
- **Forbidden:** broker factories that switch universes inside the same execution graph without teardown.

---

## 5) Universe Model (Contract)

### 5.1 UniverseContext (required everywhere)
Every execution-affecting path must carry:

- `universe` (LIVE|PAPER|SIMULATION)
- `session_id` (new per universe initialization)
- `data_lineage_id` (market data provenance)
- `executor_attestation` (optional, but recommended for live)
- `persistence_root` (universe-scoped)
- `validity_class` (for metrics/training claims)

**No component may read universe from global mutable state.** Universe is passed (or injected immutably) and is non-optional.

### 5.2 Isolation boundaries (must be enforced structurally)
- **Execution boundary:** a LIVE order can never reach SIM/PAPER executors
- **Data boundary:** lineage prevents silent mixing (live feed vs replay vs synthetic)
- **State boundary:** no shared persistence or caches unless explicitly declared “shared and safe”
- **UI boundary:** UI reflects truth; it is not the source of truth

---

## 6) Destructive Universe Transitions (Key Addition)

### 6.1 Definition
A universe change is not a toggle. It is a **transition** that:

1. Ends the current universe session (writes a terminal audit event)
2. Tears down the execution graph
3. Reinitializes all universe-bound components under a new `session_id`

### 6.2 Must be destroyed and reconstructed
- Broker instance
- Event bus
- Agent coordinator
- Analytics writers
- In-memory state and caches

### 6.3 May persist across universes
- Immutable configuration (non-universe settings)
- Strategy code (not strategy state)
- Read-only historical datasets marked as shared and provenance-tagged

### 6.4 “SIM auto-switch after hours” implementation constraint
Auto-switch is valid **only** if it triggers a controlled transition (restart/rehydrate) and produces:
- new session id
- new audit root
- explicit universe boundary event

---

## 7) Validity Classes (Metrics cannot lie by omission)

Every metric/trade/performance summary must include:

- `universe`
- `validity_class`
- `assumptions` (slippage/latency/fill model flags)
- `data_lineage_id`

Recommended validity classes:
- `LIVE_VERIFIED`
- `PAPER_ONLY`
- `SIM_VALID_FOR_TRAINING`
- `SIM_INVALID_FOR_TRAINING`

If realism constraints are disabled (latency=0, partial fills ignored, etc.), the system must automatically mark outputs `SIM_INVALID_FOR_TRAINING` and block any “validated” status.

---

## 8) Migration Options (Normalized)

### Option A — Full Rewrite
- Strongest architecture, highest cost
- Appropriate for investor/professional positioning from day 1

### Option B — Hybrid Migration (Recommended, Modified)
- Preserve working system + tests
- Reach high compliance quickly
- Requires strict invariants and destructive transitions

### Option C — Continue Current Path
- Permissible only if explicitly scoped to personal use and no professional-grade claims

**Chosen:** Option B (Hybrid), **with destructive universe transitions added as a hard requirement.**

---

## 9) Action Plan (Modified Hybrid, 4–5 weeks)

This sequence preserves momentum but moves correctness earlier.

### Week 1 — Namespace Isolation (State Boundary First)
**Goal:** eliminate cross-universe persistence/log mixing.

- Create `data/{live|paper|simulation}/` roots for universe-owned state
- Create `logs/{live|paper|simulation}/` roots for universe-owned audit/event streams
- Keep `data/shared/` only for explicitly safe shared assets (e.g., symbol metadata), with provenance rules

**Exit criteria**
- No file written without universe-scoped root
- No log stream contains mixed-universe entries

### Week 2 — Universe Types + Event/Metric Tagging
**Goal:** remove boolean mode and make universe explicit.

- Introduce `Universe` + `UniverseContext`
- Tag every event, trade, and metric with universe + session_id
- Refuse writes without universe/provenance fields

**Exit criteria**
- `SIMULATION_MODE` removed from code and configs
- Events/metrics cannot be emitted without universe fields

### Week 3 — Construction-Time Universe Selection + Remove Runtime Switch API
**Goal:** universe is locked for the process lifetime.

- Select universe via CLI arg / env at startup
- Delete endpoints that change universe at runtime (replace with read-only universe endpoint)
- Separate credentials per universe (LIVE vs PAPER)

**Exit criteria**
- No runtime universe switching via API
- Process universe immutable; restart required to change

### Week 4 — Destructive Transition Mechanism (If Auto-Switch Required)
**Goal:** allow “after-hours SIM” safely.

- Implement a transition manager that performs teardown + reinit, or implement orchestration-level restart.
- Ensure new session id and audit boundary on transition.

**Exit criteria**
- Universe transitions do not preserve execution graph
- Transition produces explicit audit boundary events

### Week 5 (buffer) — Cleanup + Invariant Tests + Docs
**Goal:** enforce and prevent regressions.

- Add tests: illegal-state unrepresentable, no cross-universe IO, no mixed logs, no universe-less metrics
- Update documentation to reflect universe contract and transitions
- Add validation scripts

**Exit criteria**
- Universe isolation validation suite passes
- Docs answer: “what universe created this?” for every output

---

## 10) Tests That Matter (Minimal Required Suite)

1. Broker constructed with universe is immutable
2. FakeBroker refuses LIVE/PAPER
3. Alpaca live endpoint cannot be used when universe=PAPER and vice versa
4. EventBus publishes events tagged with universe/session_id
5. Analytics store refuses write without universe/validity_class/provenance
6. Persistence paths differ across universes
7. Transition tears down and reconstructs broker/bus/agents/writers
8. Simulation invalidation triggers when realism flags disabled

---

## 11) Roadmap Normalization (How to reconcile documents)

### 11.1 Keep the current ROADMAP phases, but insert a gating milestone
Insert a new gate before “SIM auto-switch” and analytics polish:

**Gate: Universe Guardrails**
- namespace isolation
- universe types
- provenance tagging
- removal of runtime mode toggle
- destructive transition semantics if switching is required

### 11.2 Re-ordering guidance (only where necessary)
- “Testing” cannot be late if it’s testing invariants. Invariant tests move earlier.
- “Track record verification” only makes sense once universe provenance exists.

---

## 12) Invalidation Conditions (Falsifiability)

The design is wrong if any of the following can be demonstrated:

- A live order can be executed when the UI/session reports SIMULATION
- A trade/metric record cannot be attributed to a universe + session_id + lineage
- Logs can contain mixed universes in a single audit stream
- Simulation can produce “validated” metrics while realism constraints are disabled
- Universe can change without teardown (broker/bus/agents/writers survive)

If any are observed: stop feature work; fix the invariant breach first.

---

## Appendix A — Direct Excerpts (for traceability)

### A.1 ROADMAP.md (original)
(See repository file: ROADMAP.md)

### A.2 TECHNICAL_REPORT.md
(See repository file: TECHNICAL_REPORT.md)

### A.3 MIGRATION_ASSESSMENT.md
(See repository file: MIGRATION_ASSESSMENT.md)

---

## Appendix B — Practical Notes

- “Universe isolation” is not a UX improvement; it is correctness.
- If you want professional trust, **audit truth must be derivable from execution authority**, not UI labels.


# Multi-Market Realism Canonical v1

## Scope
Defines realism model phases, capability boundaries, and domain invariants for tax/cost/settlement/multi-market behavior.

## Invariants
- Realism spec phases are authoritative for capability definitions.
- Roadmap phase status must not contradict realism capability state without explicit reconciliation.

## Implementation Linkage
- Domain modules under `server/domain/*` and runtime wiring references in roadmap/spec documents.

## Test Linkage
- Domain test references in `tests/domain/*` where cited by roadmap/REQ history.

## Source Lineage
- Primary: `docs/MULTI_MARKET_REALISM_SPEC.md`
- Supporting: `ROADMAP.md`, `STRATEGIC_ROADMAP_NEXT_PHASE.md`

## Conflict Notes
- Roadmap status statements and realism spec progress statements require explicit synchronization to avoid planning drift.

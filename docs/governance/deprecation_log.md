# Documentation Deprecation Log

Generated: 2026-02-18
Policy: non-destructive deprecation tracking only (no file deletions or moves in this change).

| Deprecated File Path | Replacement Canonical File | Reason | Date |
|---|---|---|---|
| `commscribe/PROJECT_RUNTIME.md` | `docs/canonical/runtime_governance_canonical_v1.md` | Overlapping runtime governance contract with `ai_runtime/PROJECT_RUNTIME.md`; canonical precedence needed. | 2026-02-18 |
| `STRATEGIC_ROADMAP_NEXT_PHASE.md` (as authority source) | `docs/canonical/roadmap_planning_canonical_v1.md` | Strategic planning narrative should support, not override, canonical roadmap authority. | 2026-02-18 |
| `RECENT_CHANGES_SUMMARY.md` (as authority source) | `docs/canonical/project_status_canonical_v1.md` | Change summaries are historical snapshots and can drift from canonical status. | 2026-02-18 |
| `PRIORITY_2_COMPLETION.md` (as global status source) | `docs/canonical/project_status_canonical_v1.md` | Completion report is domain-specific and should not act as repository-wide status authority. | 2026-02-18 |
| `CI_SETUP.md` (as CI policy authority) | `docs/canonical/ci_quality_gates_canonical_v1.md` | Setup instructions and CI policy are currently split; canonical CI policy needed. | 2026-02-18 |
| `scripts/README.md` (as backtesting policy authority) | `docs/canonical/backtesting_strategy_canonical_v1.md` | Operational script guide should not define strategy/backtest semantic authority. | 2026-02-18 |
| `docs/HEALTH_ENDPOINT.md` (as observability authority) | `docs/canonical/observability_canonical_v1.md` | Endpoint contract should be subordinate to observability authority model. | 2026-02-18 |

## Notes
- Entries indicate authority deprecation only; files remain active for reference and operational usage.
- Physical file deletion/move was explicitly out of scope for this REQ.

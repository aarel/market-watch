# Document Authority Matrix

Generated: 2026-02-18

Rule set applied:
- One canonical file maximum per domain.
- If multiple canonical claimants or contradictory state claims: `CONFLICT`.
- If no clear canonical claimant from document evidence: `MISSING AUTHORITY`.
- No inferred implementation/test linkage.

| Domain | Canonical File (max 1) | Supporting Files | Implementation Linked (YES/NO/UNKNOWN) | Tests Linked (YES/NO/UNKNOWN) | Conflicts (explicit file paths) | Drift Detected (YES/NO/UNKNOWN) | Status |
|---|---|---|---|---|---|---|---|
| Runtime Governance | `ai_runtime/PROJECT_RUNTIME.md` | `ai_runtime/STARTUP_PROTOCOL.md`, `commscribe/PROJECT_RUNTIME.md` | YES | UNKNOWN | `ai_runtime/PROJECT_RUNTIME.md`, `commscribe/PROJECT_RUNTIME.md` (overlapping governance contracts) | YES | CONFLICT |
| Communicate Engine | `commscribe/README.md` | `commscribe/CODEX_COMMUNICATE_INSTRUCTIONS.md`, `commscribe/docs/COMPLIANCE_DRA_HARD.md`, `commscribe/docs/UI_DB_COMPAT_REPORT.md` | YES | YES | `commscribe/communicate.md` contains historical/legacy contradictory statements mixed with current state | YES | CONFLICT |
| Roadmap Planning | `ROADMAP.md` | `STRATEGIC_ROADMAP_NEXT_PHASE.md`, `Roadmap Phase Snapshot.txt`, `SECTION 1 — Phase R2 Task Breakdown.txt` | NO | NO | `ROADMAP.md`, `STRATEGIC_ROADMAP_NEXT_PHASE.md` (different phase framing/detail level) | YES | CONFLICT |
| Project Status | `PROJECT_STATUS.md` | `RECENT_CHANGES_SUMMARY.md`, `PRIORITY_2_COMPLETION.md`, `output.md` | NO | NO | `PROJECT_STATUS.md` (canonical entry) vs `RECENT_CHANGES_SUMMARY.md`/`PRIORITY_2_COMPLETION.md` (parallel status narratives) | YES | CONFLICT |
| API Contract | `docs/API.md` | `docs/HEALTH_ENDPOINT.md` | YES | UNKNOWN | None explicit | NO | STABLE |
| System Architecture | `docs/ARCHITECTURE.md` | `README.md` | YES | UNKNOWN | None explicit | NO | STABLE |
| Deployment & Operations | `docs/DEPLOYMENT.md` | `scripts/README.md`, `reports/inventory/USAGE_README.md`, `README.md` | YES | UNKNOWN | `docs/DEPLOYMENT.md` and `README.md` both serve as operator entry points without explicit precedence | YES | CONFLICT |
| CI/CD & Quality Gates | UNKNOWN | `docs/CI_CD.md`, `CI_SETUP.md`, `tests/README.md`, `reports/coverage/gap_report.md` | YES | YES | `docs/CI_CD.md`, `CI_SETUP.md` (both procedural authorities) | YES | MISSING AUTHORITY |
| Testing Strategy | `tests/README.md` | `reports/coverage/gap_report.md` | YES | YES | None explicit | NO | STABLE |
| Backtesting & Strategy | UNKNOWN | `docs/BACKTEST.md`, `docs/STRATEGIES.md`, `scripts/README.md` | YES | UNKNOWN | `docs/BACKTEST.md` and `docs/STRATEGIES.md` split authority without declared precedence | YES | MISSING AUTHORITY |
| Risk Management | `docs/RISK.md` | `README.md` | YES | UNKNOWN | None explicit | NO | STABLE |
| Observability | UNKNOWN | `docs/OBSERVABILITY.md`, `docs/HEALTH_ENDPOINT.md` | YES | UNKNOWN | `docs/OBSERVABILITY.md`, `docs/HEALTH_ENDPOINT.md` (monitoring vs health contract split; no stated canonical precedence) | YES | MISSING AUTHORITY |
| Multi-Market Realism | `docs/MULTI_MARKET_REALISM_SPEC.md` | `ROADMAP.md`, `STRATEGIC_ROADMAP_NEXT_PHASE.md` | YES | YES | `docs/MULTI_MARKET_REALISM_SPEC.md` vs roadmap phase status statements requiring synchronization | YES | CONFLICT |
| Contributor Workflow | `docs/CONTRIBUTING.md` | `README.md` | NO | NO | None explicit | UNKNOWN | STABLE |

## Domain Evidence (non-invented)
- Runtime Governance: explicit contracts in `ai_runtime/PROJECT_RUNTIME.md` and `ai_runtime/STARTUP_PROTOCOL.md`.
- Communicate Engine: explicit lifecycle and authority definitions in `commscribe/README.md` and companion docs.
- Roadmap Planning: explicit phase documents `ROADMAP.md` and `STRATEGIC_ROADMAP_NEXT_PHASE.md`.
- Project Status: explicit status documents `PROJECT_STATUS.md`, `RECENT_CHANGES_SUMMARY.md`, `PRIORITY_2_COMPLETION.md`.
- Multi-Market Realism: explicit spec in `docs/MULTI_MARKET_REALISM_SPEC.md`.

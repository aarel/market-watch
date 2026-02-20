# Document Authority Matrix

Generated: 2026-02-19

## Conflict Typing (Resolution-Ready)

| Domain | Files | Conflict Type | Contradicting Topics | Recommended Canonical | Supporting/Legacy |
|---|---|---|---|---|---|
| Runtime Governance | `ai_runtime/PROJECT_RUNTIME.md`, `ai_runtime/STARTUP_PROTOCOL.md`, `commscribe/PROJECT_RUNTIME.md` | `SCOPE_SPLIT`, `TERMINOLOGY_DRIFT`, `LEGACY_ARTIFACT` | Command-word format, startup ordering, enforcement wording | `ai_runtime/PROJECT_RUNTIME.md` | Supporting: `ai_runtime/STARTUP_PROTOCOL.md`; Legacy: `commscribe/PROJECT_RUNTIME.md` |
| Communicate Engine | `commscribe/README.md`, `commscribe/CODEX_COMMUNICATE_INSTRUCTIONS.md`, `commscribe/communicate.md` | `SCOPE_SPLIT`, `LEGACY_ARTIFACT` | Normative protocol vs historical transcript material | `commscribe/README.md` | Supporting: `commscribe/CODEX_COMMUNICATE_INSTRUCTIONS.md`; Legacy: `commscribe/communicate.md` |
| Roadmap Planning | `ROADMAP.md`, `development_docs/roadmap/2026-02-18/ROADMAP_CANONICAL_PRE_SPINE_REFACTOR.md`, `development_docs/roadmap/2026-02-18/ROADMAP_CANONICAL_PRE_FINAL_HARDENING.md`, `development_docs/roadmap/2026-02-07/ROADMAP.md`, `development_docs/roadmap/2026-02-11/ROADMAP.md`, `STRATEGIC_ROADMAP_NEXT_PHASE.md`, `Roadmap Phase Snapshot.txt`, `SECTION 1 — Phase R2 Task Breakdown.txt` | `REDUNDANT`, `TERMINOLOGY_DRIFT`, `SCOPE_SPLIT`, `LEGACY_ARTIFACT` | Phase status authority, strategic framing vs execution snapshots, historical baseline drift | `ROADMAP.md` | Supporting: 2026-02-11 + strategic/snapshot artifacts; Legacy: 2026-02-18 archived canonicals + 2026-02-07 baseline snapshot |

## Conflict Evidence Excerpts

### Runtime Governance
- `ai_runtime/PROJECT_RUNTIME.md`: "PROJECT RUNTIME ACTIVE — ENFORCED MODE"
- `ai_runtime/STARTUP_PROTOCOL.md`: "Phase 0-4 complete ... Startup protocol complete."
- `commscribe/PROJECT_RUNTIME.md`: "Runtime Mode: ENFORCED" plus legacy command and lifecycle wording.

### Communicate Engine
- `commscribe/README.md`: "JSON as the canonical state authority and Markdown as the human-auditable rendered view."
- `commscribe/CODEX_COMMUNICATE_INSTRUCTIONS.md`: "`communicate>` is a command-word trigger for this protocol."
- `commscribe/communicate.md`: historical REQ export entries mixed with runtime-era terminology.

### Roadmap Planning
- `ROADMAP.md`: marks stable roadmap entrypoint and current R-track statuses.
- `development_docs/roadmap/2026-02-18/ROADMAP_CANONICAL_PRE_SPINE_REFACTOR.md`: archived pre-spine canonical snapshot.
- `development_docs/roadmap/2026-02-18/ROADMAP_CANONICAL_PRE_FINAL_HARDENING.md`: archived pre-final-hardening canonical snapshot.
- `development_docs/roadmap/2026-02-07/ROADMAP.md`: architectural baseline snapshot (historical).
- `development_docs/roadmap/2026-02-11/ROADMAP.md`: detailed dated roadmap snapshot.
- `STRATEGIC_ROADMAP_NEXT_PHASE.md`: strategic categorization and option analysis rather than status authority.

## Authority Enforcement Matrix

| Domain | Canonical File (exactly 1) | Supporting Files | Legacy Files | Why Canonical | Superseded By | Status |
|---|---|---|---|---|---|---|
| Runtime Governance | `ai_runtime/PROJECT_RUNTIME.md` | `ai_runtime/STARTUP_PROTOCOL.md` | `commscribe/PROJECT_RUNTIME.md` | - Root runtime contract for active sessions. - Explicitly binds command-word and enforcement mode. - Referenced by startup protocol itself. | `ai_runtime/STARTUP_PROTOCOL.md` -> `ai_runtime/PROJECT_RUNTIME.md`; `commscribe/PROJECT_RUNTIME.md` -> `ai_runtime/PROJECT_RUNTIME.md` | ENFORCED |
| Communicate Engine | `commscribe/README.md` | `commscribe/CODEX_COMMUNICATE_INSTRUCTIONS.md` | `commscribe/communicate.md` | - Declares lifecycle authority and invariants. - Defines scanner/orchestrator boundaries. - Documents UI and failure-recovery contracts. | `commscribe/CODEX_COMMUNICATE_INSTRUCTIONS.md` -> `commscribe/README.md`; `commscribe/communicate.md` -> `commscribe/README.md` | ENFORCED |
| Roadmap Planning | `ROADMAP.md` | `development_docs/roadmap/2026-02-11/ROADMAP.md`, `STRATEGIC_ROADMAP_NEXT_PHASE.md`, `Roadmap Phase Snapshot.txt`, `SECTION 1 — Phase R2 Task Breakdown.txt` | `development_docs/roadmap/2026-02-18/ROADMAP_CANONICAL_PRE_SPINE_REFACTOR.md`, `development_docs/roadmap/2026-02-18/ROADMAP_CANONICAL_PRE_FINAL_HARDENING.md`, `development_docs/roadmap/2026-02-07/ROADMAP.md` | - Stable root-level planning entrypoint. - Embeds R<n> phases as mandatory blocking execution spine. - Supporting docs are strategy/snapshot details, not authority. | `development_docs/roadmap/2026-02-18/ROADMAP_CANONICAL_PRE_SPINE_REFACTOR.md` -> `ROADMAP.md`; `development_docs/roadmap/2026-02-18/ROADMAP_CANONICAL_PRE_FINAL_HARDENING.md` -> `ROADMAP.md`; `development_docs/roadmap/2026-02-07/ROADMAP.md` -> `ROADMAP.md`; all supporting roadmap docs -> `ROADMAP.md` | ENFORCED |
| Project Status | `PROJECT_STATUS.md` | `RECENT_CHANGES_SUMMARY.md`, `PRIORITY_2_COMPLETION.md`, `output.md` | None | - Single status summary entrypoint for repo-level reporting. | Supporting status summaries -> `PROJECT_STATUS.md` | ENFORCED |
| API Contract | `docs/API.md` | `docs/HEALTH_ENDPOINT.md` | None | - Central API surface documentation. | Health endpoint doc -> `docs/API.md` (for API authority) | STABLE |
| System Architecture | `docs/ARCHITECTURE.md` | `README.md` | None | - Dedicated architecture contract file. | `README.md` architecture snippets -> `docs/ARCHITECTURE.md` | STABLE |
| Deployment & Operations | `docs/DEPLOYMENT.md` | `scripts/README.md`, `reports/inventory/USAGE_README.md`, `README.md` | None | - Explicit deployment/runbook contract. | Supporting runbooks -> `docs/DEPLOYMENT.md` | STABLE |
| CI/CD & Quality Gates | `docs/CI_CD.md` | `CI_SETUP.md`, `tests/README.md`, `reports/coverage/gap_report.md` | None | - Canonical CI policy and gate definitions. | `CI_SETUP.md` -> `docs/CI_CD.md` | STABLE |
| Testing Strategy | `tests/README.md` | `reports/coverage/gap_report.md` | None | - Test command and test-suite authority. | Coverage reports -> `tests/README.md` (for strategy) | STABLE |
| Backtesting & Strategy | `docs/BACKTEST.md` | `docs/STRATEGIES.md`, `scripts/README.md` | None | - Primary backtesting assumptions and workflow authority. | `docs/STRATEGIES.md` backtest overlap -> `docs/BACKTEST.md` | STABLE |
| Risk Management | `docs/RISK.md` | `README.md` | None | - Dedicated risk control authority. | `README.md` risk summary -> `docs/RISK.md` | STABLE |
| Observability | `docs/OBSERVABILITY.md` | `docs/HEALTH_ENDPOINT.md` | None | - Observability model and monitoring posture authority. | Health endpoint observability overlap -> `docs/OBSERVABILITY.md` | STABLE |
| Multi-Market Realism | `docs/MULTI_MARKET_REALISM_SPEC.md` | `ROADMAP.md`, `STRATEGIC_ROADMAP_NEXT_PHASE.md` | None | - Defines realism phases/capability boundaries. | Planning references -> `docs/MULTI_MARKET_REALISM_SPEC.md` (for realism scope) | STABLE |
| Contributor Workflow | `docs/CONTRIBUTING.md` | `README.md` | None | - Explicit contributor process contract. | Contributor snippets -> `docs/CONTRIBUTING.md` | STABLE |

## Verification Notes
- Conflict domains now each map to exactly one canonical file.
- Non-canonical files in conflict domains are explicitly marked SUPPORTING or LEGACY via header metadata.
- No file deletions or archive moves were performed in this request.

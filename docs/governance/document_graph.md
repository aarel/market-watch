# Documentation Graph

Generated: 2026-02-18

Method:
- Enumerated repository documentation files (`*.md`, selected roadmap/status `*.txt`).
- Extracted purpose and claims from each document's own headings/body text.
- Marked unknown linkage as `UNKNOWN` instead of inferring.

## Domain List (Derived From Document Content)
- Runtime Governance
- Communicate Engine
- Roadmap Planning
- Project Status
- API Contract
- System Architecture
- Deployment & Operations
- CI/CD & Quality Gates
- Testing Strategy
- Backtesting & Strategy
- Risk Management
- Observability
- Multi-Market Realism
- Contributor Workflow

## Document Nodes

| Path | Declared Purpose | Domains Referenced | References to Other Docs | References to Code | References to Tests | Claims About Implementation State |
|---|---|---|---|---|---|---|
| `README.md` | Main product overview and quick start | System Architecture; API Contract; Deployment & Operations | `docs/*` section links (implicit via docs folder usage) | `server.py`, `agents/*`, `strategies/*` | `tests/*` (implicit only) | Product features available; architecture active |
| `PROJECT_STATUS.md` | Canonical root-level project status entry | Project Status | `development_docs/archive/root_status/*` | None explicit | None explicit | Declares itself canonical status entry |
| `ROADMAP.md` | Stable roadmap entrypoint and Phase R summary | Roadmap Planning; Multi-Market Realism | `development_docs/roadmap/2026-02-11/ROADMAP.md` | None explicit | None explicit | Declares R2 NOT COMPLETE |
| `STRATEGIC_ROADMAP_NEXT_PHASE.md` | Next-phase strategic planning and sequencing | Roadmap Planning; Runtime Governance; CI/CD & Quality Gates | None explicit | None explicit | None explicit | States structural debt and remaining hardening work |
| `RECENT_CHANGES_SUMMARY.md` | Recent request/change summary | Project Status; Communicate Engine | `commscribe/communicate.md` (by REQ IDs) | `commscribe/scripts/*` and UI paths in text | `commscribe/tests/*` in text | Declares specific REQs DONE |
| `PRIORITY_2_COMPLETION.md` | Completion report for Broker Query Service | Project Status; System Architecture | `BROKER_QUERY_SERVICE.md` | `broker_query_service.py`, agents integration | `tests/test_broker_query_service.py`, integration tests | Declares Priority 2 COMPLETE/PRODUCTION-READY |
| `BROKER_QUERY_SERVICE.md` | Broker query caching architecture and usage | System Architecture; Deployment & Operations | None explicit | `broker_query_service.py` | UNKNOWN | Describes service as integrated runtime component |
| `CI_SETUP.md` | CI setup instructions | CI/CD & Quality Gates | UNKNOWN | GitHub Actions/workflow context (implicit) | References running tests in CI context | Setup/procedure guidance |
| `docs/CI_CD.md` | CI/CD pipeline behavior and checks | CI/CD & Quality Gates | None explicit | GitHub Actions/workflow references | test/coverage checks | Declares active CI pipeline requirements |
| `docs/API.md` | REST/WebSocket API reference | API Contract | None explicit | Server endpoints and API surface | UNKNOWN | Defines endpoint behavior and auth contract |
| `docs/ARCHITECTURE.md` | Technical architecture overview | System Architecture | None explicit | `server.py`, `agents/*`, broker layer | UNKNOWN | Describes active architectural model |
| `docs/DEPLOYMENT.md` | Deployment steps/configuration | Deployment & Operations | None explicit | runtime startup/config references | UNKNOWN | Operational run/deploy guidance |
| `docs/CONTRIBUTING.md` | Contributor standards and process | Contributor Workflow | None explicit | repo workflow/tooling | tests/lint expected (if referenced) | Process policy guidance |
| `docs/BACKTEST.md` | Backtesting usage and architecture | Backtesting & Strategy | None explicit | `backtest/*` modules | UNKNOWN | Describes module capabilities/limitations |
| `docs/STRATEGIES.md` | Strategy behavior and configuration | Backtesting & Strategy | None explicit | strategy modules | UNKNOWN | Strategy options and expected behavior |
| `docs/RISK.md` | Risk controls and limits | Risk Management | None explicit | risk/runtime components | UNKNOWN | Risk guardrails described |
| `docs/OBSERVABILITY.md` | Metrics/logging/monitoring guidance | Observability | None explicit | observability endpoints/components | UNKNOWN | Monitoring expectations documented |
| `docs/HEALTH_ENDPOINT.md` | Health endpoint contract | Observability; API Contract | None explicit | health endpoint implementation path (implicit) | UNKNOWN | Health API behavior contract |
| `docs/FAQ.md` | User/developer FAQ | Contributor Workflow; Deployment & Operations | None explicit | UNKNOWN | UNKNOWN | Informational guidance |
| `docs/MULTI_MARKET_REALISM_SPEC.md` | Realism architecture/specification | Multi-Market Realism; Roadmap Planning | None explicit | domain modules and realism concepts | some test references in spec text | Describes phased realism model and gaps |
| `tests/README.md` | Test suite usage and execution | Testing Strategy; CI/CD & Quality Gates | None explicit | test runner scripts | `tests/*` modules | Defines recommended test execution patterns |
| `scripts/README.md` | Post-market automation usage | Deployment & Operations; Backtesting & Strategy | None explicit | `scripts/post_market_backtest.py` and setup scripts | UNKNOWN | Operational automation flow |
| `reports/coverage/gap_report.md` | Coverage deficit report | CI/CD & Quality Gates; Testing Strategy | None explicit | `server/*`, `scripts/*`, other modules | Derived from coverage/test runs | Reports current coverage metrics |
| `reports/inventory/USAGE_README.md` | How to run interactive inventory report | Deployment & Operations | None explicit | `reports/inventory/generate_inventory_report.py` | UNKNOWN | Usage guidance only |
| `ai_runtime/PROJECT_RUNTIME.md` | Enforced runtime operating contract | Runtime Governance; Communicate Engine | `ai_runtime/STARTUP_PROTOCOL.md`, `commscribe/CODEX_COMMUNICATE_INSTRUCTIONS.md` | `commscribe/scripts/communicate_scan.py` command references | UNKNOWN | Declares runtime governance constraints active |
| `ai_runtime/STARTUP_PROTOCOL.md` | Mandatory startup sequence | Runtime Governance | `ai_runtime/PROJECT_RUNTIME.md` | `commscribe/scripts/communicate_scan.py`, `git status` | governance check step (process-level) | Defines startup pass/fail conditions |
| `commscribe/README.md` | Communicate runtime architecture and operation | Communicate Engine; Runtime Governance | `commscribe/CODEX_COMMUNICATE_INSTRUCTIONS.md` and commscribe docs | `commscribe/scripts/communicate_scan.py` | `commscribe/tests/*` references | Declares JSON/DB authority and lifecycle rules |
| `commscribe/CODEX_COMMUNICATE_INSTRUCTIONS.md` | Codex-specific communicate execution contract | Communicate Engine | references communicate lifecycle docs | scanner/orchestrator command paths | mentions test expectations | Prescriptive execution behavior |
| `commscribe/PROJECT_RUNTIME.md` | Commscribe runtime mode requirements | Runtime Governance; Communicate Engine | commscribe runtime docs | communicate command workflow | UNKNOWN | Governance/runtime constraints |
| `commscribe/docs/COMPLIANCE_DRA_HARD.md` | Compliance evidence and guarantees | Communicate Engine; Runtime Governance; Testing Strategy | `commscribe/README.md`, other commscribe docs | scanner/orchestrator paths | `commscribe/tests/test_communicate_scan.py` etc. | Declares DRA-hard compliance PASS |
| `commscribe/docs/COMMUNICATE_OUTPUT_TEMPLATES.md` | Standard output/evidence templates | Communicate Engine; Runtime Governance | `commscribe/communicate.json` dataset | None | None | Template standardization findings |
| `commscribe/docs/DROP_IN_INSTALL.md` | Portable installation manifest for commscribe | Communicate Engine; Deployment & Operations | `commscribe/docs/COMPLIANCE_DRA_HARD.md`, `commscribe/README.md` | scanner/orchestrator paths | `commscribe/tests/test_communicate_scan.py` | Defines minimal artifact set and guarantees |
| `commscribe/docs/SQLITE_ENGINE_MIGRATION_REPORT.md` | Migration report to SQLite engine | Communicate Engine | references source md/json and db artifacts | `commscribe/db/communicate.db` | UNKNOWN | Migration integrity PASS |
| `commscribe/docs/UI_DB_COMPAT_REPORT.md` | UI compatibility with DB-backed request API | Communicate Engine | None explicit | `commscribe/api/requests_api.py`, `commscribe/scripts/start_communicate_ui.py` | `commscribe/tests/test_ui_db_integration.py` | Compatibility PASS |

## Notes
- `commscribe/communicate.md` is intentionally treated as lifecycle transcript/audit history, not a stable normative policy doc.
- `*.txt` documents were considered only when they describe roadmap/status intent; runtime implementation authority was not inferred from them.

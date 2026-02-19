# Communicate Engine Canonical v1

## Scope
Defines request lifecycle authority, status transitions, verification gates, and runtime interaction model for communicate.

## Invariants
- Lifecycle transitions remain deterministic.
- Completion requires verification where enforced.
- Canonical state must remain auditable.

## Implementation Linkage
- `commscribe/scripts/communicate_scan.py`
- `commscribe/scripts/start_communicate_ui.py`
- `commscribe/api/requests_api.py`

## Test Linkage
- `commscribe/tests/test_communicate_scan.py`
- `commscribe/tests/test_communicate_ui.py`
- `commscribe/tests/test_ui_db_integration.py`
- `commscribe/tests/test_sqlite_engine.py`

## Source Lineage
- Primary: `commscribe/README.md`
- Supporting: `commscribe/CODEX_COMMUNICATE_INSTRUCTIONS.md`, `commscribe/docs/COMPLIANCE_DRA_HARD.md`, `commscribe/docs/UI_DB_COMPAT_REPORT.md`

## Conflict Notes
- `commscribe/communicate.md` contains historical records that may contradict current implementation policy and should not be treated as normative runtime policy.

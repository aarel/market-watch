# UI DB Compatibility Report

## Scope
- Validate Communicate UI compatibility with database-backed request engine.
- Preserve request list/detail response shape and lifecycle behavior.

## Changes Applied
- Added adapter layer: `commscribe/api/requests_api.py`
- Updated UI server integration: `commscribe/scripts/start_communicate_ui.py`
- Added DB/UI integration tests: `commscribe/tests/test_ui_db_integration.py`

## Compatibility Contract
- Request list fields remain available to UI:
  - `id`, `request_id`, `title`, `status`, `created_at`, `updated_at`, `last_updated_at`
- Request detail fields available:
  - `id`, `request_id`, `objective`, `status`, `artifacts`, `verification`, `logs`

## Verification Enforcement
- DONE without verification block is rejected by DB engine transition guard.
- UI/backend path surfaces rejection as API error.

## Runtime Model
- Communicate request API is SQLite-only.
- UI request creation always persists through SQLite-backed `RequestAPI`.
- No backend selection flag is exposed by UI runtime startup.

## Result
- UI compatibility with DB-backed engine: PASS (integration tests + API contract checks).

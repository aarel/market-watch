## Document Authority
- STATUS: SUPPORTING
- CANONICAL: `ai_runtime/PROJECT_RUNTIME.md`
- SCOPE: Startup handshake sequence and readiness checks only.

# STARTUP_PROTOCOL

## Phase 0 - Session Intent
- Confirm task intent and expected scope.
- Confirm work will follow runtime enforcement constraints.

## Phase 1 - Mandatory Contract Ingestion
- Read `ai_runtime/PROJECT_RUNTIME.md`.
- Read this file (`ai_runtime/STARTUP_PROTOCOL.md`).
- Confirm required control commands are recognized using command-word format:
  - `communicate>`
  - `communicate>_scan`
  - `> governance_check`
  - `> startup_check`
- Confirm fresh-session command-word behavior source:
  - `commscribe/CODEX_COMMUNICATE_INSTRUCTIONS.md`

## Phase 2 - Runtime Health Check
Run:
```bash
python3 commscribe/scripts/communicate_scan.py system-status
```
Expected result:
- `SYSTEM_OK`

If not `SYSTEM_OK`, stop and repair runtime structural issues before continuing.

## Phase 3 - Repository State Validation
Run:
```bash
git status --short
```
Validate:
- current repository state is understood
- existing dirty files are treated as pre-existing unless part of requested work

## Phase 4 - Governance Check Phase
Run repository governance check command (project-standard `governance_check`).
If unavailable, perform equivalent documented governance verification step.

Failure policy:
- governance failures block startup completion
- proceed only after resolution or explicit emergency override

## Phase 5 - Startup Completion
A session is ready only after Phases 0-4 complete without unresolved blockers.
Print exact completion message:

`Startup protocol complete.`

## Emergency Override
Emergency override is allowed only when:
- user explicitly directs override
- blocking condition and risk are documented in session output
- override scope is minimal and temporary

## Failure Conditions
Startup is failed if any of the following occurs:
- contract files not reviewed
- `communicate_scan system-status` not healthy
- repository state not validated with `git status`
- governance check not completed or failed without explicit override
- completion message not issued

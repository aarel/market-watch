# Runtime Governance Canonical v1

## Scope
Defines mandatory terminal-session governance startup and execution constraints.

## Invariants
- Startup protocol phases must complete before execution.
- `communicate>` lifecycle must remain auditable.
- Governance failures are blocking unless explicit override.

## Implementation Linkage
- `commscribe/scripts/communicate_scan.py` (`system-status`, lifecycle commands)
- Repository command usage (`git status --short`)

## Test Linkage
- UNKNOWN (process contract; no dedicated runtime-governance test file identified in this pass)

## Source Lineage
- Primary: `ai_runtime/PROJECT_RUNTIME.md`
- Supporting: `ai_runtime/STARTUP_PROTOCOL.md`, `commscribe/PROJECT_RUNTIME.md`

## Conflict Notes
- Overlap exists between `ai_runtime/PROJECT_RUNTIME.md` and `commscribe/PROJECT_RUNTIME.md` without explicit precedence statement.

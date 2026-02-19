# Deployment Operations Canonical v1

## Scope
Defines operational deployment and runbook guidance for local/hosted operation.

## Invariants
- Deployment entrypoint and operational prerequisites remain explicit.
- Supplemental runbooks remain non-authoritative unless promoted.

## Implementation Linkage
- `server.py` runtime launch and operational scripts referenced in docs.

## Test Linkage
- UNKNOWN

## Source Lineage
- Primary: `docs/DEPLOYMENT.md`
- Supporting: `README.md`, `scripts/README.md`, `reports/inventory/USAGE_README.md`

## Conflict Notes
- `README.md` and script runbooks act as alternate operator entrypoints without a clear precedence statement.

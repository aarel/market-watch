# Drop-In Install Manifest

This manifest defines exactly what to copy into another repository to install the runtime.

## Copy Into Target Repo Root

Copy the entire `commscribe/` directory with these required files:

- `commscribe/communicate.json`
- `commscribe/communicate.md`
- `commscribe/failure_log.json`
- `commscribe/scripts/communicate_scan.py`
- `commscribe/scripts/communicate_orchestrator.py`
- `commscribe/CODEX_COMMUNICATE_INSTRUCTIONS.md`

Keep these strongly recommended files for auditability and maintainability:

- `commscribe/README.md`
- `commscribe/docs/COMPLIANCE_DRA_HARD.md`
- `commscribe/tests/test_communicate_scan.py`

Optional components (only if local browser UI is needed):

- `commscribe/ui/`
- `commscribe/scripts/start_communicate_ui.py`

## Makefile Merge (Do Not Overwrite)

Merge these targets into the host repository `Makefile`:

- `communicate`
- `communicate-orchestrate`
- `communicate-ui` (only if UI retained)

Do not replace existing host targets; only add missing target blocks.

## Do Not Copy

- `.venv/` or other environment directories
- `__pycache__/` directories
- temporary test files
- stale lock files (`*.lock`)
- unrelated archive artifacts not needed for compliance evidence

## Post-Copy Required Steps

1. Confirm Python runtime support (Python 3.9+).
2. Ensure `Makefile` targets point to `commscribe/scripts/...` paths.
3. Review commit policy for `commscribe/failure_log.json` (recommended: commit it for audit trail continuity).
4. Run:

```bash
make communicate
```

Expected on healthy empty input:
- exit code `0`
- output contains `No new INPUT PAD content. Nothing to do.`

## Minimal Functional Artifact Set

Required for functional runtime:

- `commscribe/scripts/communicate_scan.py`
- `commscribe/scripts/communicate_orchestrator.py`
- `commscribe/communicate.json`
- `commscribe/communicate.md`
- `commscribe/failure_log.json`
- `commscribe/CODEX_COMMUNICATE_INSTRUCTIONS.md`

Strongly recommended for provable compliance:

- `commscribe/tests/test_communicate_scan.py`
- `commscribe/docs/COMPLIANCE_DRA_HARD.md`
- `commscribe/README.md`

## Guarantees After Correct Copy

- Deterministic lifecycle enforcement
- Idempotent request handling
- `SYSTEM_BLOCKED` fail-closed behavior
- Append-only structural failure logging
- Portable, repo-local runtime operation

## Constraints

- Do not rename `commscribe/` unless specification is revised.
- Do not move state authority away from `commscribe/scripts/communicate_scan.py`.
- Do not remove tests when invariants must remain verifiable.

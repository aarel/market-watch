# DRA-Hard Compliance Record

## Verification Snapshot

- Verification time (UTC): 2026-02-13T00:32:58Z
- Runtime version: `1.1.0` (`commscribe/scripts/communicate_scan.py`)
- Commit hash: not available (workspace is not a git repository)
- Final verdict: `DRA-hard compliant`
- Confidence: `High`

## Compliance Matrix Summary

- `SYSTEM_BLOCKED` surfaced on all entrypaths (including consume no-op path): PASS
- Healthy no-op behavior deterministic and non-mutating: PASS
- Failure artifacting durable + deduped + non-destructive: PASS
- Orchestrator boundary enforcement and blocked refusal: PASS
- Transition/idempotence/concurrency regressions: PASS

## Post-Transplant Remediation (2026-02-13 UTC)

- Fixed source-aware recovery for markdown-origin structural failures:
  `SYSTEM_BLOCKED` now records `failure_scope`, `source_file`, and `source_hash`,
  and recovery checks the original source file hash instead of requiring JSON hash mutation.
- Fixed UI/scanner race path:
  UI writes now route through scanner `set-input` under the shared lock contract,
  removing direct markdown read-modify-write behavior.
- Regression coverage added:
  `commscribe/tests/test_communicate_scan.py` now includes markdown-only failure/recovery;
  `commscribe/tests/test_communicate_ui.py` adds UI/scanner lock and concurrent-write checks.

## Primary Evidence Pointers

- Final verification request block: `commscribe/communicate.md` (`REQ-20260212-182944`)
- Canonical runtime state: `commscribe/communicate.json`
- Failure artifact contract + fields: `commscribe/scripts/communicate_scan.py`
- Orchestrator preflight refusal path: `commscribe/scripts/communicate_orchestrator.py`
- Regression + behavioral tests: `commscribe/tests/test_communicate_scan.py`
- Runtime contract docs: `commscribe/README.md`, `commscribe/CODEX_COMMUNICATE_INSTRUCTIONS.md`
- Command entrypoints: `Makefile`

## Minimal Reproduction Steps

1. Healthy no-op determinism:

```bash
make communicate
```

Expected:
- output includes `No new INPUT PAD content. Nothing to do.`
- exit code `0`
- no hash changes in `commscribe/communicate.md` and `commscribe/communicate.json`

2. Blocked-state enforcement repro:

```bash
tmp=$(mktemp -d)
cp commscribe/communicate.md "$tmp/communicate.md"
printf '{bad json' > "$tmp/communicate.json"
python3 commscribe/scripts/communicate_scan.py \
  --file "$tmp/communicate.md" \
  --json "$tmp/communicate.json" \
  --failure-log "$tmp/failure_log.json" \
  consume
```

Expected:
- non-zero exit
- `SYSTEM_BLOCKED` message referencing event id
- `failure_log.json` created with a single `SYSTEM_BLOCKED` event
- corrupted `communicate.json` unchanged (hash before/after identical)

## Minimal Artifact Set (Required)

- `commscribe/communicate.json`: canonical state source proving request lifecycle state and immutable terminal outcomes.
- `commscribe/communicate.md`: human-auditable rendered transcript that preserves REQ evidence and operational history.
- `commscribe/scripts/communicate_scan.py`: sole state authority implementing transitions, blocked preflight, failure logging, and sync behavior.
- `commscribe/scripts/communicate_orchestrator.py`: boundary layer proving orchestration cannot bypass core enforcement.
- `commscribe/tests/test_communicate_scan.py`: executable proof for transition, immutability, concurrency, parse-failure, recovery, and no-op guarantees.
- `commscribe/README.md`: normative behavior contract for operators and auditors.
- `commscribe/CODEX_COMMUNICATE_INSTRUCTIONS.md`: command-word contract constraining Codex operation and blocked behavior.
- `Makefile`: stable invocation surface for reproducible verification commands.

## Archive Policy

- Keep `commscribe/communicate.md` request blocks containing protocol decisions and final verification evidence (`REQ-20260212-182944`).
- If transcript size grows, archive older non-critical request blocks to `commscribe/docs/archive/` with stable request-id pointers retained here.
- Do not delete tests, failure-handling contracts, or canonical/runtime authority files listed above.

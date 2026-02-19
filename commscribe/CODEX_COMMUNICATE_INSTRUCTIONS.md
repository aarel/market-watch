## Document Authority
- STATUS: SUPPORTING
- CANONICAL: `commscribe/README.md`
- SCOPE: Command-word trigger behavior and execution protocol for `communicate>`.

# Codex Command Word: communicate>

When user says `communicate>`, follow this contract:

Interpretation rule:
- `communicate>` is a command-word trigger for this protocol.
- Do not assume a shell binary named `communicate` exists on `PATH`.
- Execute the workflow through `python3 commscribe/scripts/communicate_scan.py` commands.

1. Run `python3 commscribe/scripts/communicate_scan.py consume`.
2. If no new input, stop.
3. For each new request id:
   - `ack` with concise plan
   - execute requested repo work
   - `log` milestone updates
   - `complete` with outputs/evidence, or `block` with exact reason + next steps

Core constraints:

- `commscribe/scripts/communicate_scan.py` is the only state authority.
- Never mutate `commscribe/communicate.json` or request sections in markdown directly.
- Never mutate `commscribe/failure_log.json` directly.
- For INPUT PAD writes, use scanner API only (`communicate_scan.py set-input`), never direct markdown rewrite paths.
- Always use explicit `request_id` for mutations.
- Never mutate terminal states (`DONE`, `BLOCKED`).
- On structural errors, fail closed, persist `SYSTEM_BLOCKED` in `failure_log.json` with source-aware fields (`failure_scope`, `source_file`, `source_hash`), and provide repair instructions.
- `SYSTEM_BLOCKED` must be surfaced on every entrypath, including consume no-op paths with empty INPUT PAD.

Orchestrator boundary:

- `commscribe/scripts/communicate_orchestrator.py` is optional convenience only.
- Orchestrator can invoke CLI transitions but cannot enforce state on its own.
- Before lifecycle execution, orchestrator must check `system-status` and stop if `SYSTEM_BLOCKED` is active.

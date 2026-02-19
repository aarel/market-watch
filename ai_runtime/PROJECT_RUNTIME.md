## Document Authority
- STATUS: CANONICAL
- DOMAIN: Runtime Governance
- GOVERNANCE: This file is the single source of truth for Runtime Governance.

# PROJECT RUNTIME ACTIVE — ENFORCED MODE

## Operating Mode
This repository operates in enforced runtime mode for terminal LLM sessions.
All sessions must complete startup handshake requirements before development actions.

## Authorized Commands
Allowed session control commands:
- `communicate`
- `communicate_scan`
- `governance_check`
- `startup_check`

## Command-Word Format (Required)
- In terminal LLM conversations, command words must be written with a leading `>` to avoid ambiguity with plain language.
- Required format examples:
  - `communicate>`
  - `communicate>_scan`
  - `> governance_check`
  - `> startup_check`
- `communicate>` is a workflow trigger command word. It may map to `python3 commscribe/scripts/communicate_scan.py` lifecycle commands rather than a shell binary named `communicate`.
- Authoritative behavior for `communicate>` is defined in `commscribe/CODEX_COMMUNICATE_INSTRUCTIONS.md`.

## Startup Handshake Requirements
Before any code, docs, or command work:
1. Read `ai_runtime/STARTUP_PROTOCOL.md`.
2. Execute startup protocol phases in order.
3. Confirm runtime readiness and repository state.
4. Proceed only after startup completion message is reached.

## Lifecycle Rules
- Use commscribe lifecycle for session request handling.
- Respect deterministic request transitions and status integrity.
- Do not bypass lifecycle tracking for request-driven tasks.
- Keep command history and outcomes auditable.

## Code Modification Rules
- Keep changes minimal and scoped to requested work.
- Do not change business logic unless explicitly requested.
- Do not change schemas unless explicitly requested.
- Preserve backward compatibility for existing flows.

## Workspace Boundaries
- Operate within repository boundaries.
- Do not write outside approved workspace roots.
- Avoid destructive operations unless explicitly approved.

## Governance Enforcement
- Run governance validation when protocol requires it.
- Treat governance failures as blocking until resolved or explicitly overridden.
- Keep governance actions and outcomes traceable.

## Security Constraints
- Do not expose secrets or credentials in logs or output.
- Do not bypass safety controls or environment restrictions.
- Use least-privilege execution for all commands.

## Session Acknowledgment
By proceeding in this repository, the session acknowledges that:
- PROJECT RUNTIME ACTIVE — ENFORCED MODE
- Startup protocol is mandatory.
- Lifecycle and governance constraints remain active for the full session.

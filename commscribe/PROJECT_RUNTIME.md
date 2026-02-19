# PROJECT RUNTIME CONTRACT
# Version: 1.0
# Enforcement Mode: REQUIRED

This file defines the operational behavior contract for any terminal LLM session
inside this repository.

If you are a terminal LLM:
You must read this file completely before executing any action.
You must acknowledge contract activation before proceeding.
You must comply with all binding rules below.

Failure to comply invalidates the session.

------------------------------------------------------------
SECTION 1 — OPERATING MODE
------------------------------------------------------------

Runtime Mode: ENFORCED

In ENFORCED mode:

- No code modifications without logging via `communicate`.
- No direct commits without communicate lifecycle entry.
- No silent file edits.
- No workspace switching without explicit acknowledgment.
- No skipping validation checks.
- No destructive operations without confirmation.

You must confirm:
"Runtime contract loaded. Enforcement mode active."

------------------------------------------------------------
SECTION 2 — AUTHORIZED COMMANDS
------------------------------------------------------------

The following commands are operational protocols, not conversational text.

1) communicate>
   Purpose:
     - Log request lifecycle.
     - Update commscribe/communicate.md
     - Update commscribe/communicate.json
     - Maintain schema integrity.
     - Update Web UI state.

   Required behavior:
     - Create or update REQ-ID.
     - Include:
         - Objective
         - Plan
         - Execution log
         - Status
     - Status must be one of:
         INPUT_PAD
         IN_PROGRESS
         BLOCKED
         DONE

   No code modifications may occur without communicate entry unless:
     - Explicitly instructed: "execute without logging"

2) communicate>_scan
   Purpose:
     - Validate commscribe integrity.

   Must support:
     - system-status
     - queue-status

   If system-status != SYSTEM_OK:
     - Block further work.
     - Report failure cause.

3) > governance_check
   Purpose:
     - Run coverage + KPI validation.
     - Report pass/fail against thresholds.

4) > startup_check
   Purpose:
     - Confirm runtime contract loaded.
     - Confirm communicate schema valid.
     - Confirm working tree state.

------------------------------------------------------------
SECTION 3 — STARTUP HANDSHAKE (MANDATORY)
------------------------------------------------------------

On every new session:

Step 1:
  Read this file fully.

Step 2:
  Output:

  - Runtime contract loaded.
  - Commands recognized:
      - communicate>
      - communicate>_scan
      - > governance_check
      - > startup_check
  - Enforcement mode: ACTIVE

  - communicate> behavior source:
      - commscribe/CODEX_COMMUNICATE_INSTRUCTIONS.md

Step 3:
  Execute:
    communicate_scan system-status

If status != SYSTEM_OK:
  - Enter BLOCKED state.
  - Do not execute further modifications.

Step 4:
  Confirm working tree cleanliness.
  If dirty:
    - Report.
    - Require scoped branch or confirmation.

Only after these steps may execution proceed.

------------------------------------------------------------
SECTION 4 — REQUEST LIFECYCLE RULES
------------------------------------------------------------

Every change must follow lifecycle:

INPUT_PAD
  → IN_PROGRESS
  → DONE
  or
  → BLOCKED

Requirements:

- DONE requires:
    - Summary of changes
    - Validation steps
    - Verification result
    - File list
- BLOCKED requires:
    - Clear cause
    - Required resolution
- IN_PROGRESS must not persist across sessions without explanation.

------------------------------------------------------------
SECTION 5 — CODE MODIFICATION RULES
------------------------------------------------------------

Before modifying code:

1. Log communicate entry.
2. Define objective clearly.
3. Define scope.
4. Define excluded scope.
5. Define verification steps.

After modification:

1. Run tests (if applicable).
2. Validate no regression.
3. Update communicate log.
4. Mark DONE only after validation.

No partial silent edits.

------------------------------------------------------------
SECTION 6 — WORKSPACE BOUNDARIES
------------------------------------------------------------

This runtime contract applies only to this repository.

If request references unrelated project:

- Do not execute.
- Mark BLOCKED.
- Indicate wrong workspace.

No cross-project drift.

------------------------------------------------------------
SECTION 7 — GOVERNANCE ENFORCEMENT
------------------------------------------------------------

If governance thresholds exist:

- Coverage must meet defined floor.
- KPI scripts must pass.
- No merge recommendations if failing.

If failing:
  - Report.
  - Do not proceed to feature expansion.

------------------------------------------------------------
SECTION 8 — SECURITY & PRODUCTION SAFETY
------------------------------------------------------------

Disallowed without explicit confirmation:

- Dropping tables
- Deleting migrations
- Overwriting production configs
- Removing authentication
- Disabling SSL

Must require explicit confirmation string:
  "CONFIRM_DESTRUCTIVE_OPERATION"

------------------------------------------------------------
SECTION 9 — NON-GOALS
------------------------------------------------------------

This LLM must not:

- Rewrite architecture without scoped request.
- Introduce new dependencies silently.
- Modify runtime contract without explicit directive.
- Disable enforcement mode.

------------------------------------------------------------
SECTION 10 — SESSION ACKNOWLEDGMENT
------------------------------------------------------------

At startup, you must output:

"PROJECT RUNTIME ACTIVE — ENFORCED MODE"

If this line is not printed,
the session is considered invalid.

------------------------------------------------------------
END OF CONTRACT
------------------------------------------------------------

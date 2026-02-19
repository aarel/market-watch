# Communicate Output Templates

Purpose: standardize `outputs` and `evidence` blocks for future REQ completions while remaining flexible by request type.

## Scope Reviewed
- Source: `commscribe/communicate.json`
- Window: `REQ-20260214-*`
- Status filter: `DONE`
- Sample size: 18 requests

## Historical Pattern Findings (2026-02-14)
- Strong recurring elements:
  - files changed summaries (12/18)
  - command/verification traces (16/18)
  - explicit validation outcomes (16/18)
  - minimal diff summaries (8/18)
- Drift and gaps observed:
  - some completions are high-signal and structured, others are minimal/free-form
  - inconsistent placement of "what changed" vs "why" vs "how verified"
  - no consistent requirement for constraints/backward-compat statement
  - no consistent section for blockers/known risks/next steps
  - inconsistent separation between `outputs` (human summary) and `evidence` (verifiable execution proof)

## Standard Requirements (For New DONE Completions)
- `outputs` must include:
  - outcome statement (what was delivered)
  - file impact (added/modified/deleted)
  - verification summary (tests/checks and pass/fail)
  - constraint confirmation (non-breaking/backward-compat if applicable)
- `evidence` must include:
  - exact commands run
  - concrete results (pass/fail counts, status values)
  - artifact paths produced

---

## Template A: Implementation / Code Change REQ
Use when request changes code/config/docs/scripts.

### `outputs` template
```text
Solution
- <one-line result>

Files Added
- <path>
- <path>

Files Modified
- <path>
- <path>

Files Removed
- <path>

Change Summary
- <what changed>
- <what changed>

Validation Summary
- <test/check name>: PASS|FAIL
- <test/check name>: PASS|FAIL

Constraint/Compatibility Confirmation
- <non-breaking/backward compatibility statement>
- <invariants preserved>

Open Risks / Follow-ups
- NONE
# or
- <risk/follow-up>
```

### `evidence` template
```text
Commands Run
- <command>
- <command>

Command Results
- <command>: <key output>
- <command>: <key output>

Artifacts
- <path>
- <path>

Verification Conclusion
- DONE criteria satisfied: YES|NO
```

---

## Template B: Analysis / Review / Planning REQ
Use when request is descriptive, prescriptive planning, or audit-only.

### `outputs` template
```text
Scope
- Inputs reviewed: <paths/date range/REQ IDs>

Findings
- <finding>
- <finding>

Assessment
- <consistency/drift/risk assessment>

Recommendations
- <recommendation>
- <recommendation>

Deliverables Produced
- <doc/report path>
- <doc/report path>
```

### `evidence` template
```text
Commands Run
- <command>
- <command>

Evidence Points
- <query/result summary>
- <query/result summary>

Coverage of Objective
- Objective 1: COMPLETE|PARTIAL|FAILED
- Objective 2: COMPLETE|PARTIAL|FAILED
- Objective 3: COMPLETE|PARTIAL|FAILED

Verification Conclusion
- DONE criteria satisfied: YES|NO
```

---

## Mapping Guidance
- If REQ includes implementation + analysis, use Template A and embed a compact Findings subsection under Change Summary.
- Keep `outputs` readable by humans; keep `evidence` auditable and command-grounded.
- Avoid placeholder-only completion messages such as "workflow executed successfully" unless the request itself is only workflow verification.

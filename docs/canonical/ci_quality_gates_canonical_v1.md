# CI Quality Gates Canonical v1

## Scope
Defines CI execution, quality thresholds, and coverage gate posture.

## Invariants
- One canonical CI policy document controls gate expectations.
- Coverage and test policy references must align with canonical CI policy.

## Implementation Linkage
- GitHub Actions pipeline and test execution commands referenced by docs.

## Test Linkage
- `tests/README.md` command matrix
- coverage data in `reports/coverage/gap_report.md`

## Source Lineage
- Primary: `docs/CI_CD.md`
- Supporting: `CI_SETUP.md`, `tests/README.md`, `reports/coverage/gap_report.md`

## Conflict Notes
- No explicit canonical declaration existed between `docs/CI_CD.md` and `CI_SETUP.md`; this file resolves that ambiguity.

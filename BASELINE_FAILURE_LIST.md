# Baseline Test Failures — Phase 0 Snapshot
**Date:** 2026-02-20T03:35:00Z
**Request:** REQ-20260219-212902 (STRATEGIC-STABILIZATION-EXECUTION-001)
**Total Tests:** 729 (718 pass, 6 fail, 5 skip)

---

## Failed Tests (6)

### 1. `tests/governance/test_metrics_endpoint.py::test_error_and_latency_metrics_increment_after_failing_route`
**Category:** Metrics endpoint
**Likely Cause:** Prometheus metrics not incrementing correctly on error routes
**Priority:** Medium

### 2. `tests/test_req_log_normalization.py::ReqLogNormalizationTests::test_reject_bullet_section_contamination`
**Category:** Request log validation (commscribe)
**Likely Cause:** Validation logic not rejecting invalid bullet contamination
**Priority:** Low (commscribe internal)

### 3. `tests/test_req_log_normalization.py::ReqLogNormalizationTests::test_reject_missing_objective`
**Category:** Request log validation (commscribe)
**Likely Cause:** Validation not catching missing OBJECTIVE field
**Priority:** Low (commscribe internal)

### 4. `tests/test_req_log_normalization.py::ReqLogNormalizationTests::test_reject_overlength_objective`
**Category:** Request log validation (commscribe)
**Likely Cause:** Validation not enforcing 500-char limit on OBJECTIVE
**Priority:** Low (commscribe internal)

### 5. `tests/test_smoke_suite.py::test_health_endpoint_smoke`
**Category:** API authentication
**Likely Cause:** TestClient doesn't pass IP localhost check in `require_api_access`
**Error:** `assert 403 in (200, 503)` — health endpoint requires auth in test context
**Priority:** HIGH (breaks smoke test suite)

### 6. `tests/test_static_cache_bust.py::TestStaticCacheBust::test_asset_version_defined`
**Category:** Asset versioning
**Likely Cause:** Missing or incorrect ASSET_VERSION marker in static/index.html
**Priority:** Medium (cache busting verification)

---

## Skipped Tests (5)
- Pre-existing intentional skips (not investigated)

---

## Analysis

**Critical Path:** Test #5 (`test_health_endpoint_smoke`) blocks smoke test suite and must be fixed first.

**Root Cause (test #5):**
The `require_api_access` dependency is applied to all API routes including `/api/health`. When `TestClient` makes requests, `request.client.host` may be `None` or `testserver`, not `127.0.0.1`, causing the IP allowlist check to fail with 403.

**Fix Strategy:**
1. Exempt `/api/health` from `require_api_access` dependency (health checks should be unauthenticated per standard practice)
2. OR: Fix TestClient to pass correct client IP
3. OR: Update `require_api_access` to recognize TestClient context

**Other Failures:**
- Tests #1, #6: Legitimate code issues to fix
- Tests #2-4: Commscribe validation logic (lower priority, non-blocking for core system)

---

## Next Steps (Phase 1)

1. Fix `test_health_endpoint_smoke` (critical)
2. Fix `test_static_cache_bust::test_asset_version_defined`
3. Fix `test_error_and_latency_metrics_increment_after_failing_route`
4. Review/fix commscribe validation tests (#2-4)
5. Achieve 100% green test suite

---

**Status:** ✅ BASELINE DOCUMENTED — Ready for Phase 1 remediation

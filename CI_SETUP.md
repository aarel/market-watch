# CI/CD Pipeline Documentation

**Status:** ✅ Active
**Last Updated:** 2026-02-10

---

## Overview

The CI/CD pipeline runs automatically on every push to `main` or `develop` branches and on all pull requests. It ensures code quality through linting, testing, and coverage reporting.

## Pipeline Stages

### Stage 1: Lint 📋
**Purpose:** Catch style issues and potential bugs before running tests

- **Tool:** Ruff (modern Python linter)
- **Configuration:** `.ruff.toml`
- **What it checks:**
  - Code style (PEP 8)
  - Import sorting
  - Modern Python syntax (3.12+)
  - Common bugs and anti-patterns
  - Type hint consistency

**Current Status:** 104 issues remaining (all require manual review)

**Fix issues locally:**
```bash
# Check for issues
ruff check .

# Auto-fix issues
ruff check . --fix

# Or use the helper script
./scripts/lint.sh
```

### Stage 2: Test 🧪
**Purpose:** Verify all functionality works correctly

- **Framework:** pytest with coverage
- **Configuration:** `.coveragerc`, `pytest.ini`
- **What it runs:**
  - All tests in `tests/` directory
  - Excludes: `tests/test_backtest_data.py` (broken mock)
  - Generates coverage reports

**Current Status:** 453 tests passing, 4 skipped

**Run tests locally:**
```bash
# Run all tests with coverage
python -m pytest tests/ --ignore=tests/test_backtest_data.py --cov

# Quick test run (no coverage)
python -m pytest tests/ --ignore=tests/test_backtest_data.py -q

# Simulate full CI pipeline
./scripts/check_ci.sh
```

## Coverage Tracking

**Current Coverage:** 68.95%
**Target Coverage:** 85%
**Gap:** 16.05 percentage points

### Coverage Configuration

Coverage is configured in `.coveragerc` to:
- Exclude test files from coverage metrics
- Exclude virtual environments and tooling
- Track branch coverage (more thorough)
- Generate HTML, JSON, and XML reports

### Coverage Reports

After running tests, coverage reports are available:
- **Terminal:** Shown in test output
- **HTML:** `htmlcov/index.html` (open in browser)
- **JSON:** `coverage.json` (machine-readable)
- **CI Artifacts:** Downloadable from GitHub Actions run

**View HTML report locally:**
```bash
python -m pytest tests/ --ignore=tests/test_backtest_data.py --cov --cov-report=html
open htmlcov/index.html  # macOS
# or
xdg-open htmlcov/index.html  # Linux
```

## Workflow Details

### Workflow File
`.github/workflows/tests.yml`

### Triggers
- **Push** to `main` or `develop`
- **Pull requests** targeting `main` or `develop`

### Jobs

1. **Lint Job**
   - Runs first (fast feedback)
   - Blocks tests if lint fails
   - Provides inline annotations on PR

2. **Test Job**
   - Runs after lint passes
   - Executes full test suite
   - Generates coverage reports
   - Uploads coverage artifacts
   - Checks coverage threshold (not enforced yet)

### Job Dependencies
```
lint → test
```
Tests only run if linting passes.

## Status Checks

When you create a PR, you'll see:
- ✅ **Lint** - Code style check
- ✅ **Test** - Full test suite
- 📊 **Coverage** - Coverage report (informational)

## Local Development

### Pre-commit Workflow

Before pushing code:

1. **Run lint:**
   ```bash
   ruff check . --fix
   ```

2. **Run tests:**
   ```bash
   python -m pytest tests/ --ignore=tests/test_backtest_data.py -q
   ```

3. **Or simulate full CI:**
   ```bash
   ./scripts/check_ci.sh
   ```

### Helper Scripts

- `scripts/lint.sh` - Run linter
- `scripts/check_ci.sh` - Simulate full CI pipeline locally

## Artifacts

CI runs upload the following artifacts (retained for 30 days):
- `coverage-report/htmlcov/` - Interactive HTML coverage report
- `coverage-report/coverage.json` - Machine-readable coverage data
- `coverage-report/.coverage` - Raw coverage database

## Future Improvements

**Not yet implemented:**

1. **Coverage enforcement** - Currently informational, not blocking
   - Will enforce 85% threshold once reached
2. **Broker failure tests** - Phase F item #3
3. **Backtest regression tests** - Phase F item #4
4. **Badge in README** - Show CI status
5. **Codecov integration** - Better coverage tracking over time

## Troubleshooting

### Lint Failures

**Problem:** Lint job fails in CI
**Solution:** Run `ruff check . --fix` locally and commit

### Test Failures

**Problem:** Tests pass locally but fail in CI
**Solution:**
- Check if you're using correct Python version (3.12)
- Ensure all dependencies in `requirements.txt`
- Run `./scripts/check_ci.sh` to simulate CI

### Coverage Issues

**Problem:** Coverage report not generated
**Solution:** Ensure `pytest-cov` is installed: `pip install pytest-cov`

## Phase F Completion Status

**Goal:** Automated confidence on every change

| Item | Status | Notes |
|------|--------|-------|
| CI pipeline (lint → test → coverage) | ✅ Complete | Running on all commits |
| Integration test suite | ✅ Complete | 8 integration tests passing |
| Broker failure recovery tests | ❌ TODO | Phase F item #3 |
| Backtest regression tests | ❌ TODO | Phase F item #4 |

**Next Steps:**
1. Complete broker failure tests (item #3)
2. Create backtest regression baseline (item #4)
3. Enforce 85% coverage threshold (after reaching target)

---

*For linting configuration, see `.ruff.toml`*
*For coverage configuration, see `.coveragerc`*
*For workflow configuration, see `.github/workflows/tests.yml`*

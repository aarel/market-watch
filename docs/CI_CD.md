# CI/CD Pipeline

## Overview

This project uses GitHub Actions for continuous integration and deployment automation.

## Current Setup (Phase 11 - Quick Wins)

### Automated Testing

**Workflow:** `.github/workflows/tests.yml`

**Triggers:**
- Every push to `main` or `develop` branches
- Every pull request targeting `main` or `develop`

**What it does:**
1. Checks out the code
2. Sets up Python 3.12
3. Caches pip dependencies for faster runs
4. Installs project dependencies from `requirements.txt`
5. Installs pytest and pytest-cov
6. Runs all tests with coverage reporting
7. Reports results in GitHub Actions summary

**Test Requirements:**
- All 240 tests must pass for CI to succeed
- Tests run with verbose output (`-v`)
- Coverage report generated automatically
- Failed PRs are blocked from merging if tests fail

### Status Badge

The README now includes a status badge showing the current build status:

```markdown
![Tests](https://github.com/USERNAME/REPO/actions/workflows/tests.yml/badge.svg)
```

**Note:** Replace `USERNAME/REPO` with your actual GitHub username and repository name.

### .gitignore Updates

Enhanced `.gitignore` to exclude:
- Test artifacts (`.pytest_cache/`, `.coverage`, `htmlcov/`)
- Log files (`*.log`)
- Data directories (`logs/`, `data/`)
- Documentation artifacts (summary markdown files)

## CI Best Practices

### Before Pushing

1. **Run tests locally:**
   ```bash
   python -m pytest tests/ --tb=short -v
   ```

2. **Check for uncommitted changes:**
   ```bash
   git status
   ```

3. **Ensure code quality:**
   - Tests pass locally
   - No syntax errors
   - No obvious bugs

### Working with Pull Requests

1. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes and commit:
   ```bash
   git add .
   git commit -m "feat: add new feature"
   ```

3. Push to GitHub:
   ```bash
   git push origin feature/your-feature-name
   ```

4. Open a pull request on GitHub

5. Wait for CI checks to complete

6. Fix any failures before merging

### CI Failure Debugging

If tests fail in CI:

1. **Check the workflow logs** on GitHub Actions tab
2. **Reproduce locally:**
   ```bash
   python -m pytest tests/ --tb=short -v
   ```
3. **Fix the issue** and push again
4. **CI will re-run** automatically

## Future Enhancements (Phase 11 - Medium/Long Term)

### Medium Impact (2-4 hours)

- [ ] **Code coverage reporting** - Upload coverage to Codecov or Coveralls
- [ ] **Linting checks** - Add flake8, black, mypy
- [ ] **Pre-commit hooks** - Local validation before commits
- [ ] **Branch protection rules** - Require CI pass before merge
- [ ] **Multiple Python versions** - Test on 3.10, 3.11, 3.12

### Long Term (4+ hours)

- [ ] **Deployment automation** - Auto-deploy on main branch updates
- [ ] **Environment-specific configs** - Separate staging/production
- [ ] **Docker builds** - Containerized testing and deployment
- [ ] **Release automation** - Automatic version bumps and changelogs
- [ ] **Performance benchmarks** - Track test execution time
- [ ] **Security scanning** - Dependency vulnerability checks

## Monitoring CI Status

### GitHub Actions Tab

Visit your repository on GitHub and click the "Actions" tab to see:
- Recent workflow runs
- Success/failure status
- Detailed logs for each run
- Time taken for each job

### Status Badge

The status badge in README.md shows:
- ✅ Green "passing" - All tests passed
- ❌ Red "failing" - Tests failed
- 🟡 Yellow "pending" - Tests running

### Notifications

GitHub will notify you:
- When CI fails on your branch
- When PR checks complete
- Via email (configurable in GitHub settings)

## Cost

GitHub Actions provides:
- **2,000 minutes/month free** for private repos
- **Unlimited minutes** for public repos

Current workflow uses ~1-2 minutes per run, so well within free tier.

## Troubleshooting

### Tests pass locally but fail in CI

**Possible causes:**
- Environment differences (missing dependencies)
- Hardcoded paths or assumptions
- Timezone issues
- Missing test fixtures

**Solution:** Check CI logs for specific error messages

### Slow CI runs

**Current optimizations:**
- Pip cache enabled (saves ~30 seconds)
- Minimal dependency installation

**Future optimizations:**
- Docker layer caching
- Parallel test execution
- Selective test runs based on changed files

### CI not triggering

**Check:**
1. Workflow file is in `.github/workflows/`
2. Branch name matches trigger conditions
3. GitHub Actions is enabled in repository settings

## Support

For questions or issues with CI/CD:
1. Check workflow logs in GitHub Actions tab
2. Review this documentation
3. Consult [GitHub Actions documentation](https://docs.github.com/actions)

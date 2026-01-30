# Dependency Pinning Instructions

## Context
The Change audit (Finding #2) identified that using `>=` version constraints creates non-deterministic deployments. Any `pip install` could pull breaking changes.

## Status
P0 CRITICAL - This must be done before any deployment.

## How to Generate Lock File

### Option 1: Generate from Current Environment (Recommended)
```bash
# 1. Install dependencies in clean virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 2. Install from requirements.txt
pip install -r requirements.txt

# 3. Generate lock file with exact versions
pip freeze > requirements.lock

# 4. Commit both files
git add requirements.txt requirements.lock
git commit -m "chore: pin dependencies with lock file"
```

### Option 2: Use pip-tools
```bash
# Install pip-tools
pip install pip-tools

# Generate requirements.lock from requirements.txt
pip-compile requirements.txt --output-file=requirements.lock

# Install from lock file
pip-sync requirements.lock
```

## Deployment Usage

### Development
```bash
# Use requirements.txt for flexibility
pip install -r requirements.txt
```

### Production/CI
```bash
# Use requirements.lock for determinism
pip install -r requirements.lock
```

## Maintenance

When adding new dependencies:
1. Add to `requirements.txt` with `>=` constraint
2. Regenerate `requirements.lock`
3. Test thoroughly
4. Commit both files

When upgrading dependencies:
1. Update `requirements.txt` version constraint
2. Regenerate `requirements.lock`
3. Run full test suite
4. Check for breaking changes
5. Commit both files

## Why This Matters (High-Stakes Systems)

From the Change audit:
> `requirements.txt` uses minimum versions only (`>=`). For high-stakes systems, this is a change-safety hazard:
> - FastAPI/Starlette changes can break request handling or lifespan semantics
> - Alpaca SDK changes can break broker behavior
> - Pandas/Numpy changes can break calculations subtly
>
> No lock file = non-deterministic deployments.

## Next Steps

**IMMEDIATE**: Generate requirements.lock before next deployment.

**CI/CD**: Update deployment scripts to use `pip install -r requirements.lock`.

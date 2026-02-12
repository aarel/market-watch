#!/bin/bash
# Simulate CI workflow locally

set -e

echo "🔍 Simulating CI Pipeline..."
echo ""

# Lint job
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 Job 1: Lint"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
ruff check . --statistics
LINT_EXIT=$?
echo ""

if [ $LINT_EXIT -ne 0 ]; then
    echo "❌ Lint failed! Fix issues before running tests."
    echo "   Run: ruff check . --fix"
    exit 1
fi

echo "✅ Lint passed!"
echo ""

# Test job
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧪 Job 2: Test"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
python -m pytest tests/ --ignore=tests/test_backtest_data.py \
    --cov --cov-report=term --cov-report=json \
    --tb=short -q

TEST_EXIT=$?
echo ""

if [ $TEST_EXIT -ne 0 ]; then
    echo "❌ Tests failed!"
    exit 1
fi

echo "✅ Tests passed!"
echo ""

# Coverage check
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Coverage Summary"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ -f coverage.json ]; then
    COVERAGE=$(python -c "import json; print(f\"{json.load(open('coverage.json'))['totals']['percent_covered']:.2f}\")")
    TARGET=85
    GAP=$(python -c "print(f\"{85 - ${COVERAGE}:.2f}\")")

    echo "Current: ${COVERAGE}%"
    echo "Target:  ${TARGET}%"
    echo "Gap:     ${GAP}%"
    echo ""

    if (( $(echo "$COVERAGE < $TARGET" | bc -l) )); then
        echo "⚠️  Coverage below ${TARGET}% target (not enforced yet)"
    else
        echo "✅ Coverage meets ${TARGET}% target!"
    fi
else
    echo "⚠️  No coverage report found"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ CI Pipeline Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

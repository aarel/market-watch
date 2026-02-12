#!/bin/bash
# Test runner script with logging
# Usage: ./run_tests.sh [options]
#
# Env priority:
# 1) Active VIRTUAL_ENV (if already activated)
# 2) .venv-wsl
# 3) .venv
# 4) venv

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Create test_results directory if it doesn't exist
mkdir -p test_results

# Generate timestamp for log file
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="test_results/test_run_${TIMESTAMP}.log"
SUMMARY_FILE="test_results/latest_summary.txt"

echo "Running Market-Watch Test Suite..."
echo "Log file: ${LOG_FILE}"
echo ""

# Activate virtual environment if it exists (respect active env first)
if [ -n "${VIRTUAL_ENV:-}" ]; then
    echo "✓ Using active virtual environment (${VIRTUAL_ENV})"
elif [ -f ".venv-wsl/bin/activate" ]; then
    source .venv-wsl/bin/activate
    echo "✓ Virtual environment activated (.venv-wsl)"
elif [ -f ".venv-wsl/Scripts/activate" ]; then
    source .venv-wsl/Scripts/activate
    echo "✓ Virtual environment activated (Windows .venv-wsl)"
elif [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
    echo "✓ Virtual environment activated (.venv)"
elif [ -f ".venv/Scripts/activate" ]; then
    source .venv/Scripts/activate
    echo "✓ Virtual environment activated (Windows .venv)"
elif [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo "✓ Virtual environment activated (venv)"
elif [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
    echo "✓ Virtual environment activated (Windows venv)"
else
    echo -e "${YELLOW}⚠ Warning: Virtual environment not found${NC}"
fi

# Prefer python from active venv if available, else fallback to python3/python
if [ -n "${VIRTUAL_ENV:-}" ] && [ -x "${VIRTUAL_ENV}/bin/python" ]; then
    PYTHON_BIN="${VIRTUAL_ENV}/bin/python"
elif [ -n "${VIRTUAL_ENV:-}" ] && [ -x "${VIRTUAL_ENV}/Scripts/python.exe" ]; then
    PYTHON_BIN="${VIRTUAL_ENV}/Scripts/python.exe"
elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN=python
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN=python3
else
    echo -e "${RED}✗ No python interpreter found on PATH${NC}"
    exit 1
fi

echo ""
echo "=========================================="
echo "  Running Tests"
echo "=========================================="
echo ""

# Build pytest args (allow overrides)
PYTEST_ARGS=()
HAS_VERBOSITY=0
while [ $# -gt 0 ]; do
    case "$1" in
        --verbose)
            PYTEST_ARGS+=("-vv")
            HAS_VERBOSITY=1
            shift
            ;;
        --quiet)
            PYTEST_ARGS+=("-q")
            HAS_VERBOSITY=1
            shift
            ;;
        --)
            shift
            while [ $# -gt 0 ]; do
                PYTEST_ARGS+=("$1")
                shift
            done
            ;;
        *)
            PYTEST_ARGS+=("$1")
            if [[ "$1" == "-q" || "$1" == "-v" || "$1" == "-vv" ]]; then
                HAS_VERBOSITY=1
            fi
            shift
            ;;
    esac
done

if [ $HAS_VERBOSITY -eq 0 ]; then
    PYTEST_ARGS+=("-q")
fi

echo "==========================================" | tee "${LOG_FILE}"
echo "Test Run: $(date)" | tee -a "${LOG_FILE}"
echo "Log file: ${LOG_FILE}" | tee -a "${LOG_FILE}"
echo "Summary file: ${SUMMARY_FILE}" | tee -a "${LOG_FILE}"
echo "Command: ${PYTHON_BIN} -m pytest tests ${PYTEST_ARGS[*]}" | tee -a "${LOG_FILE}"
echo "Tip: use --verbose for per-test output or --quiet for dots only." | tee -a "${LOG_FILE}"
echo "==========================================" | tee -a "${LOG_FILE}"
echo "" | tee -a "${LOG_FILE}"

# Run tests and capture output (pytest runs unittest tests too)
"${PYTHON_BIN}" -m pytest tests "${PYTEST_ARGS[@]}" 2>&1 | tee -a "${LOG_FILE}"

# Capture exit code
TEST_EXIT_CODE=${PIPESTATUS[0]}

# Generate summary
echo ""
echo "=========================================="
echo "  Test Summary"
echo "=========================================="

# Count results from pytest summary
TOTAL_TESTS=$(grep -Eo "[0-9]+ (passed|failed|skipped|xfailed|xpassed|error|errors)" "${LOG_FILE}" | awk '{sum+=$1} END{print sum+0}')
PASSED=$(grep -Eo "[0-9]+ passed" "${LOG_FILE}" | tail -1 | awk '{print $1+0}')
FAILED=$(grep -Eo "[0-9]+ failed" "${LOG_FILE}" | tail -1 | awk '{print $1+0}')
ERRORS=$(grep -Eo "[0-9]+ error(s)?" "${LOG_FILE}" | tail -1 | awk '{print $1+0}')
SKIPPED=$(grep -Eo "[0-9]+ skipped" "${LOG_FILE}" | tail -1 | awk '{print $1+0}')
XFAILED=$(grep -Eo "[0-9]+ xfailed" "${LOG_FILE}" | tail -1 | awk '{print $1+0}')
XPASSED=$(grep -Eo "[0-9]+ xpassed" "${LOG_FILE}" | tail -1 | awk '{print $1+0}')

# Default missing counts to 0
PASSED=${PASSED:-0}
FAILED=${FAILED:-0}
ERRORS=${ERRORS:-0}
SKIPPED=${SKIPPED:-0}
XFAILED=${XFAILED:-0}
XPASSED=${XPASSED:-0}

# Write summary to file
cat > "${SUMMARY_FILE}" <<EOF
Market-Watch Test Suite Summary
Generated: $(date)
Log file: ${LOG_FILE}

Results:
--------
Total Tests: ${TOTAL_TESTS}
Passed:      ${PASSED}
Failed:      ${FAILED}
Errors:      ${ERRORS}
Skipped:     ${SKIPPED}
XFailed:     ${XFAILED}
XPassed:     ${XPASSED}

Exit Code: ${TEST_EXIT_CODE}
EOF

# Display summary with colors
echo ""
cat "${SUMMARY_FILE}"
echo ""

if [ ${TEST_EXIT_CODE} -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
else
    echo -e "${RED}✗ Some tests failed${NC}"
    echo ""
    echo "View full log: ${LOG_FILE}"
    echo "To see failures only:"
    echo "  grep -A 10 'FAIL:' ${LOG_FILE}"
    echo "  grep -A 10 'ERROR:' ${LOG_FILE}"
fi

echo ""
echo "Test logs saved to: test_results/"

exit ${TEST_EXIT_CODE}

#!/bin/bash
# Test runner script with logging
# Usage: ./run_tests.sh [options]

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

# Activate virtual environment if it exists
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo "✓ Virtual environment activated (venv)"
elif [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
    echo "✓ Virtual environment activated (Windows venv)"
elif [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
    echo "✓ Virtual environment activated (.venv)"
elif [ -f ".venv/Scripts/activate" ]; then
    source .venv/Scripts/activate
    echo "✓ Virtual environment activated (Windows .venv)"
else
    echo -e "${YELLOW}⚠ Warning: Virtual environment not found${NC}"
fi

# Prefer python from venv if available, else fallback to python3/python
if command -v python >/dev/null 2>&1; then
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

# Run tests and capture output
"${PYTHON_BIN}" -m unittest discover -s tests -p "test_*.py" -v 2>&1 | tee "${LOG_FILE}"

# Capture exit code
TEST_EXIT_CODE=${PIPESTATUS[0]}

# Generate summary
echo ""
echo "=========================================="
echo "  Test Summary"
echo "=========================================="

# Count results from log
TOTAL_TESTS=$(grep -c "^test_" "${LOG_FILE}" || echo "0")
PASSED=$(grep -c "ok$" "${LOG_FILE}" || echo "0")
FAILED=$(grep -c "FAIL$" "${LOG_FILE}" || echo "0")
ERRORS=$(grep -c "ERROR$" "${LOG_FILE}" || echo "0")

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

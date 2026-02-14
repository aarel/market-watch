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

# Create canonical run directory
TIMESTAMP_UNDERSCORE=$(date +"%Y%m%d_%H%M%S")
TIMESTAMP=$(date +"%Y%m%d-%H%M%S")
RUN_DIR="test_results/full_suite/${TIMESTAMP}"
mkdir -p "${RUN_DIR}"
STDOUT_FILE="${RUN_DIR}/pytest_stdout.log"
STDERR_FILE="${RUN_DIR}/pytest_stderr.log"
SUMMARY_JSON="${RUN_DIR}/summary.json"
METADATA_JSON="${RUN_DIR}/metadata.json"

echo "Running Market-Watch Test Suite..."
echo "Run dir: ${RUN_DIR}"
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

echo "=========================================="
echo "Test Run: $(date)"
echo "Run dir: ${RUN_DIR}"
echo "Stdout: ${STDOUT_FILE}"
echo "Stderr: ${STDERR_FILE}"
echo "Command: ${PYTHON_BIN} -m pytest tests ${PYTEST_ARGS[*]}"
echo "Tip: use --verbose for per-test output or --quiet for dots only."
echo "=========================================="
echo ""

# Run tests and capture output (pytest runs unittest tests too)
set +e
"${PYTHON_BIN}" -m pytest tests "${PYTEST_ARGS[@]}" >"${STDOUT_FILE}" 2>"${STDERR_FILE}"
TEST_EXIT_CODE=$?
set -e

# Display captured output
cat "${STDOUT_FILE}"
if [ -s "${STDERR_FILE}" ]; then
    cat "${STDERR_FILE}" >&2
fi

# Combined log used only for summary parsing (not authoritative artifact)
COMBINED_LOG="${RUN_DIR}/combined.log"
cat "${STDOUT_FILE}" "${STDERR_FILE}" > "${COMBINED_LOG}"

# Generate summary
echo ""
echo "=========================================="
echo "  Test Summary"
echo "=========================================="

# Count results from pytest summary
TOTAL_TESTS=$(grep -Eo "[0-9]+ (passed|failed|skipped|xfailed|xpassed|error|errors)" "${COMBINED_LOG}" | awk '{sum+=$1} END{print sum+0}')
PASSED=$(grep -Eo "[0-9]+ passed" "${COMBINED_LOG}" | tail -1 | awk '{print $1+0}')
FAILED=$(grep -Eo "[0-9]+ failed" "${COMBINED_LOG}" | tail -1 | awk '{print $1+0}')
ERRORS=$(grep -Eo "[0-9]+ error(s)?" "${COMBINED_LOG}" | tail -1 | awk '{print $1+0}')
SKIPPED=$(grep -Eo "[0-9]+ skipped" "${COMBINED_LOG}" | tail -1 | awk '{print $1+0}')
XFAILED=$(grep -Eo "[0-9]+ xfailed" "${COMBINED_LOG}" | tail -1 | awk '{print $1+0}')
XPASSED=$(grep -Eo "[0-9]+ xpassed" "${COMBINED_LOG}" | tail -1 | awk '{print $1+0}')

# Default missing counts to 0
PASSED=${PASSED:-0}
FAILED=${FAILED:-0}
ERRORS=${ERRORS:-0}
SKIPPED=${SKIPPED:-0}
XFAILED=${XFAILED:-0}
XPASSED=${XPASSED:-0}

# Write canonical summary + metadata
cat > "${SUMMARY_JSON}" <<EOF
{
  "suite_name": "full_suite",
  "run_id": "${TIMESTAMP}",
  "generated_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "command": "${PYTHON_BIN} -m pytest tests ${PYTEST_ARGS[*]}",
  "counts": {
    "total": ${TOTAL_TESTS},
    "passed": ${PASSED},
    "failed": ${FAILED},
    "errors": ${ERRORS},
    "skipped": ${SKIPPED},
    "xfailed": ${XFAILED},
    "xpassed": ${XPASSED}
  },
  "exit_code": ${TEST_EXIT_CODE},
  "artifacts": {
    "pytest_stdout": "pytest_stdout.log",
    "pytest_stderr": "pytest_stderr.log",
    "summary": "summary.json",
    "metadata": "metadata.json"
  }
}
EOF

cat > "${METADATA_JSON}" <<EOF
{
  "suite_name": "full_suite",
  "run_id": "${TIMESTAMP}",
  "generated_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "run_dir": "${RUN_DIR}",
  "legacy_timestamp": "${TIMESTAMP_UNDERSCORE}",
  "policy": "forward_only_canonical_artifact_schema_v1"
}
EOF

# Display summary with colors
echo ""
cat "${SUMMARY_JSON}"
echo ""

if [ ${TEST_EXIT_CODE} -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
else
    echo -e "${RED}✗ Some tests failed${NC}"
    echo ""
    echo "View stdout log: ${STDOUT_FILE}"
    echo "View stderr log: ${STDERR_FILE}"
    echo "To see failures only:"
    echo "  grep -A 10 'FAIL:' ${STDOUT_FILE}"
    echo "  grep -A 10 'ERROR:' ${STDOUT_FILE}"
fi

echo ""
echo "Test artifacts saved to: ${RUN_DIR}"

exit ${TEST_EXIT_CODE}

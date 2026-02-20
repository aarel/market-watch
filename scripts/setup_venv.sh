#!/usr/bin/env sh
# Create/use a Python virtual environment and install dependencies.
# Works in POSIX sh and bash.

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
VENV_DIR="${VENV_DIR:-venv}"
DRY_RUN=0
UPGRADE_PIP=1

usage() {
  cat <<'EOF'
Usage: bash scripts/setup_venv.sh [options]

Options:
  --venv-dir <path>   Virtual environment directory (default: venv)
  --no-upgrade-pip    Skip pip/setuptools/wheel upgrade step
  --dry-run           Print planned actions without changing files
  -h, --help          Show this help

Examples:
  bash scripts/setup_venv.sh
  bash scripts/setup_venv.sh --venv-dir .venv
  bash scripts/setup_venv.sh --dry-run

After success, activate with:
  source <venv-dir>/bin/activate
EOF
}

run_cmd() {
  if [ "$DRY_RUN" -eq 1 ]; then
    printf '[dry-run] %s\n' "$*"
  else
    # shellcheck disable=SC2086
    sh -c "$*"
  fi
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --venv-dir)
      if [ "$#" -lt 2 ]; then
        echo "ERROR: --venv-dir requires a value" >&2
        exit 2
      fi
      VENV_DIR="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --no-upgrade-pip)
      UPGRADE_PIP=0
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

cd "$PROJECT_ROOT"

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 is not installed or not on PATH." >&2
  exit 1
fi

if [ ! -f "requirements.txt" ]; then
  echo "ERROR: requirements.txt not found in project root: $PROJECT_ROOT" >&2
  exit 1
fi

if ! python3 -m venv --help >/dev/null 2>&1; then
  echo "ERROR: python3 venv module is unavailable. Install python3-venv." >&2
  exit 1
fi

if [ ! -d "$VENV_DIR" ]; then
  run_cmd "python3 -m venv '$VENV_DIR'"
else
  echo "Virtual environment already exists: $VENV_DIR"
fi

ACTIVATE_PATH="$VENV_DIR/bin/activate"
PIP_PATH="$VENV_DIR/bin/pip"
PYTHON_PATH="$VENV_DIR/bin/python"

if [ ! -f "$ACTIVATE_PATH" ] && [ "$DRY_RUN" -ne 1 ]; then
  echo "ERROR: activation script missing at $ACTIVATE_PATH" >&2
  exit 1
fi

if [ "$UPGRADE_PIP" -eq 1 ]; then
  run_cmd "'$PYTHON_PATH' -m pip install --upgrade pip setuptools wheel"
fi

run_cmd "'$PIP_PATH' install -r requirements.txt"

cat <<EOF

Setup complete.
Project root: $PROJECT_ROOT
Venv path: $VENV_DIR

Activate now:
  source $VENV_DIR/bin/activate

Verify install:
  python -V
  pip show fastapi
EOF

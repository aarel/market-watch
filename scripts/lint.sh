#!/bin/bash
# Lint the codebase using ruff

set -e

echo "🔍 Running Ruff linter..."
echo ""

# Run ruff check
ruff check . --statistics

echo ""
echo "✅ Linting complete!"
echo ""
echo "To auto-fix issues: ruff check . --fix"

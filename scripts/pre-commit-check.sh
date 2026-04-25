#!/bin/bash
# Pre-commit hook for code quality checks

set -e

echo "Running pre-commit checks..."

# Run Black formatter check
echo "Checking code style with Black..."
black --check app worker

# Run isort import check
echo "Checking import order with isort..."
isort --check-only app worker

# Run flake8 linting
echo "Linting with flake8..."
flake8 app worker

# Run mypy type checking
echo "Type checking with mypy..."
mypy app worker --ignore-missing-imports

echo "✓ All checks passed!"

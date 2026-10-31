#!/usr/bin/env bash
# Run the same checks as GitHub CI before pushing.  Usage: ./scripts/check.sh
set -euo pipefail
cd "$(dirname "$0")/.."
(
  cd backend
  # shellcheck disable=SC1091
  [ -d .venv ] && . .venv/bin/activate
  ruff check .
  ruff format --check .
  pytest -q -p no:warnings
)
(
  cd frontend
  npm run typecheck
  npm test --silent
)
echo "All checks passed."

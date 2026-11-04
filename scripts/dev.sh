#!/usr/bin/env bash
# Run ChrystalClear locally WITHOUT Docker (uses SQLite).
# Needs: Python 3.12+ and Node 22+.  Usage: ./scripts/dev.sh
# (With Docker installed, the easier way is:  docker compose up)
set -euo pipefail
cd "$(dirname "$0")/.."

echo "==> Backend setup"
cd backend
[ -d .venv ] || python3 -m venv .venv
# shellcheck disable=SC1091
. .venv/bin/activate
pip install -q -e ".[dev]"
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload --port 8000 &
API_PID=$!
cd ..

echo "==> Frontend setup"
cd frontend
npm install --no-audit --no-fund
trap 'kill $API_PID 2>/dev/null' EXIT
echo
echo "    Open http://localhost:5173  (API docs: http://localhost:8000/api/v1/docs)"
echo
npm run dev

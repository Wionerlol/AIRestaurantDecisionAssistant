#!/usr/bin/env bash
set -euo pipefail

if [ -f ".env" ]; then
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
fi

if [ ! -x "backend/.venv/bin/uvicorn" ]; then
  echo "backend virtualenv is missing. Run: python3 -m venv backend/.venv && backend/.venv/bin/pip install -e ./backend"
  exit 1
fi

exec backend/.venv/bin/uvicorn app.main:app --app-dir backend/src --reload --host "${BACKEND_HOST:-0.0.0.0}" --port "${BACKEND_PORT:-8000}"

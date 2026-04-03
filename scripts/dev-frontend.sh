#!/usr/bin/env bash
set -euo pipefail

if [ -f ".env" ]; then
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
fi

exec sh -c 'cd frontend && npm run dev -- --hostname 0.0.0.0 --port "${FRONTEND_PORT:-3000}"'

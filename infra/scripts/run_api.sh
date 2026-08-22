#!/usr/bin/env bash
# Start the FastAPI process from any cwd. Uses backend/.venv, not frontend/.venv.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VENV="${ROOT}/backend/.venv/bin"
PORT="${BACKEND_PORT:-8000}"

if [[ ! -x "${VENV}/uvicorn" ]]; then
  echo "backend/.venv is missing. Once: cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt" >&2
  exit 1
fi

cd "${ROOT}/backend"
export PYTHONPATH="${ROOT}/backend"
exec "${VENV}/uvicorn" api.main:app --reload --host 127.0.0.1 --port "${PORT}"

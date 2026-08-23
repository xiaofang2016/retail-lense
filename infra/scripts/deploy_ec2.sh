#!/usr/bin/env bash
# Pull the test branch (dev) on the EC2 box and restart API + UI. Amazon Linux. No SSM.
set -euo pipefail

ROOT="${APP_DIR:-/home/mike/retail-lense}"
BRANCH="${DEPLOY_BRANCH:-dev}"
API_UNIT="${API_UNIT:-retaillen-api}"
UI_UNIT="${UI_UNIT:-retaillen-ui}"

cd "${ROOT}"

echo "Fetching ${BRANCH}..."
git fetch origin
git reset --hard "origin/${BRANCH}"
git submodule update --init --recursive 2>/dev/null || true

if [[ ! -x "${ROOT}/backend/.venv/bin/python" ]]; then
  echo "backend/.venv is missing. Create it once with python3.12 -m venv backend/.venv" >&2
  exit 1
fi
if [[ ! -x "${ROOT}/frontend/.venv/bin/python" ]]; then
  echo "frontend/.venv is missing. Create it once with python3.12 -m venv frontend/.venv" >&2
  exit 1
fi

echo "Installing backend deps..."
"${ROOT}/backend/.venv/bin/pip" install -q -r "${ROOT}/backend/requirements.txt"

echo "Installing frontend deps..."
"${ROOT}/frontend/.venv/bin/pip" install -q -r "${ROOT}/frontend/requirements.txt"

echo "Restarting API..."
if systemctl list-unit-files --type=service 2>/dev/null | grep -q "^${API_UNIT}.service"; then
  sudo systemctl restart "${API_UNIT}"
  sudo systemctl is-active --quiet "${API_UNIT}"
else
  pkill -f "${ROOT}/backend/.venv/bin/uvicorn api.main:app" || true
  sleep 1
  cd "${ROOT}/backend"
  PYTHONPATH=. nohup .venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000 \
    >> "${ROOT}/backend/uvicorn.log" 2>&1 &
  cd "${ROOT}"
fi

if systemctl list-unit-files --type=service 2>/dev/null | grep -q "^${UI_UNIT}.service"; then
  echo "Restarting UI..."
  sudo systemctl restart "${UI_UNIT}"
  sudo systemctl is-active --quiet "${UI_UNIT}"
fi

echo "Health check..."
for _ in 1 2 3 4 5 6; do
  if curl -fsS http://127.0.0.1:8000/health | grep -q '"status":"ok"'; then
    curl -sS http://127.0.0.1:8000/health
    echo
    echo "Deploy ok: $(git rev-parse --short HEAD)"
    exit 0
  fi
  sleep 2
done

echo "API health check failed" >&2
systemctl status "${API_UNIT}" --no-pager 2>/dev/null || tail -n 40 "${ROOT}/backend/uvicorn.log" || true
exit 1

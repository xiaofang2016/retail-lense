#!/usr/bin/env bash
# Deploy backend + frontend with Docker Compose on EC2.
set -euo pipefail

ROOT="${APP_DIR:-/home/mike/retail-lense}"
BRANCH="${DEPLOY_BRANCH:-dev}"

cd "${ROOT}"

echo "========================================"
echo "Deploying branch: ${BRANCH}"
echo "Project: ${ROOT}"
echo "========================================"

echo "[1/5] Fetching latest code..."
git fetch origin

echo "[2/5] Resetting to origin/${BRANCH}..."
git reset --hard "origin/${BRANCH}"

echo "[3/5] Building and restarting backend + frontend..."
docker compose up -d --build backend frontend

echo "[4/5] Checking container status..."
docker compose ps backend frontend

echo "[5/5] Health check..."

for _ in 1 2 3 4 5 6; do
    if curl -fsS http://127.0.0.1:8000/health | grep -q '"status":"ok"'; then
        echo
        curl -sS http://127.0.0.1:8000/health
        echo
        echo
        echo "========================================"
        echo "Deploy successful!"
        echo "Commit: $(git rev-parse --short HEAD)"
        echo "========================================"
        exit 0
    fi

    echo "Waiting for backend..."
    sleep 5
done

echo
echo "========================================"
echo "ERROR: API health check failed"
echo "========================================"

echo
echo "Container status:"
docker compose ps backend frontend

echo
echo "Backend logs:"
docker compose logs --tail=50 backend || true

echo
echo "Frontend logs:"
docker compose logs --tail=50 frontend || true

exit 1
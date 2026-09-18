#!/usr/bin/env bash
# Deploy FastAPI + analysis worker with Docker Compose on the backend EC2.
set -euo pipefail

ROOT="${APP_DIR:-/home/mike/retail-lense/retail-lense}"
BRANCH="${DEPLOY_BRANCH:-dev}"

cd "${ROOT}"

echo "========================================"
echo "Deploying backend on branch: ${BRANCH}"
echo "Project: ${ROOT}"
echo "========================================"

if [[ "${SKIP_GIT:-}" == "1" ]]; then
    OLD_COMMIT="${OLD_COMMIT:?OLD_COMMIT is required when SKIP_GIT=1}"
    NEW_COMMIT="${NEW_COMMIT:-$(git rev-parse HEAD)}"
else
    echo "[1/5] Fetching latest code..."
    OLD_COMMIT="$(git rev-parse HEAD)"
    git fetch origin

    echo "[2/5] Resetting to origin/${BRANCH}..."
    git reset --hard "origin/${BRANCH}"
    NEW_COMMIT="$(git rev-parse HEAD)"
fi

echo "[3/5] Building and restarting backend + worker..."
# Rebuild only when backend/requirements.txt changes. A full image build is slow
# on the course VM; Python code is bind-mounted so a restart is enough otherwise.
# worker shares the backend build context (see docker-compose.yml).
if git diff --name-only "$OLD_COMMIT" "$NEW_COMMIT" | grep -qE '^backend/requirements\.txt$'; then
    docker compose up -d --build backend worker
else
    docker compose up -d backend worker
    docker compose restart backend worker
fi

echo "[4/5] Checking container status..."
docker compose ps backend worker

echo "[5/5] Health check..."

for _ in 1 2 3 4 5 6; do
    if curl -fsS http://127.0.0.1:8000/health | grep -q '"status":"ok"'; then
        echo
        curl -sS http://127.0.0.1:8000/health
        echo
        echo
        echo "========================================"
        echo "Backend deploy successful!"
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
docker compose ps backend worker

echo
echo "Backend logs:"
docker compose logs --tail=50 backend || true

echo
echo "Worker logs:"
docker compose logs --tail=50 worker || true

exit 1

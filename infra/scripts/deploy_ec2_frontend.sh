#!/usr/bin/env bash
# Deploy Streamlit with Docker Compose on the frontend EC2.
# Uses --no-deps so this host does not start the backend service.
# Point BACKEND_URL in .env at the backend EC2 / ALB (not http://backend:8000).
set -euo pipefail

ROOT="${APP_DIR:-/home/mike/retail-lense}"
BRANCH="${DEPLOY_BRANCH:-dev}"

cd "${ROOT}"

echo "========================================"
echo "Deploying frontend on branch: ${BRANCH}"
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

echo "[3/5] Building and restarting frontend..."
# Rebuild only when frontend/requirements.txt changes. Python/pages are bind-mounted.
if git diff --name-only "$OLD_COMMIT" "$NEW_COMMIT" | grep -qE '^frontend/requirements\.txt$'; then
    docker compose up -d --no-deps --build frontend
else
    docker compose up -d --no-deps frontend
    docker compose restart frontend
fi

echo "[4/5] Checking container status..."
docker compose ps frontend

echo "[5/5] Health check..."

for _ in 1 2 3 4 5 6; do
    if curl -fsS http://127.0.0.1:8501/_stcore/health >/dev/null; then
        echo
        echo "========================================"
        echo "Frontend deploy successful!"
        echo "Commit: $(git rev-parse --short HEAD)"
        echo "========================================"
        exit 0
    fi

    echo "Waiting for frontend..."
    sleep 5
done

echo
echo "========================================"
echo "ERROR: Streamlit health check failed"
echo "========================================"

echo
echo "Container status:"
docker compose ps frontend

echo
echo "Frontend logs:"
docker compose logs --tail=50 frontend || true

exit 1

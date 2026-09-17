#!/usr/bin/env bash
# Deploy backend + worker + frontend with Docker Compose on EC2.
set -euo pipefail

ROOT="${APP_DIR:-/home/mike/retail-lense}"
BRANCH="${DEPLOY_BRANCH:-dev}"

cd "${ROOT}"

echo "========================================"
echo "Deploying branch: ${BRANCH}"
echo "Project: ${ROOT}"
echo "========================================"

echo "[1/5] Fetching latest code..."
OLD_COMMIT="$(git rev-parse HEAD)"
git fetch origin

echo "[2/5] Resetting to origin/${BRANCH}..."
git reset --hard "origin/${BRANCH}"
NEW_COMMIT="$(git rev-parse HEAD)"


echo "[3/5] Building and restarting backend + worker + frontend..."
# optimize rebuilds by checking if requirements.txt changed
# becareful, everytime you change requirements.txt, it will rebuild the docker.and it cost 17minutes
# as we want to control the cost of the EC2, no plan to upgrade the vm.

# worker shares backend's build context and requirements.txt (see docker-compose.yml),
# so it rebuilds/restarts alongside backend rather than on its own separate check.
if git diff --name-only "$OLD_COMMIT" "$NEW_COMMIT" | grep -qE '^(backend)/requirements\.txt$'; then
    docker compose up -d --build backend worker
else
    docker compose restart backend worker
fi

#same as above,
if git diff --name-only "$OLD_COMMIT" "$NEW_COMMIT" | grep -qE '^(frontend)/requirements\.txt$'; then
    docker compose up -d --build frontend
else
    docker compose restart frontend
fi


echo "[4/5] Checking container status..."
docker compose ps backend worker frontend

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
docker compose ps backend worker frontend

echo
echo "Backend logs:"
docker compose logs --tail=50 backend || true

echo
echo "Worker logs:"
docker compose logs --tail=50 worker || true

echo
echo "Frontend logs:"
docker compose logs --tail=50 frontend || true

exit 1
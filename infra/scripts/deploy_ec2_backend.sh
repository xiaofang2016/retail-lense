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

echo "[3/5] Ensuring Redis is up, then restarting backend + worker..."
# Redis data lives on the named volume retaillen-redis-data. --no-recreate leaves
# the existing container in place, and this script never restarts Redis or runs
# `compose down -v`. A CI deploy therefore does not wipe sessions.
if [[ -z "${REDIS_PASSWORD:-}" && -f .env ]]; then
    redis_line="$(grep -E '^REDIS_PASSWORD=' .env | tail -n 1 || true)"
    REDIS_PASSWORD="${redis_line#REDIS_PASSWORD=}"
    REDIS_PASSWORD="${REDIS_PASSWORD%\"}"
    REDIS_PASSWORD="${REDIS_PASSWORD#\"}"
    REDIS_PASSWORD="${REDIS_PASSWORD%\'}"
    REDIS_PASSWORD="${REDIS_PASSWORD#\'}"
fi
if [[ -z "${REDIS_PASSWORD:-}" ]] && command -v aws >/dev/null 2>&1; then
    redis_raw="$(aws secretsmanager get-secret-value \
        --secret-id retaillen/REDIS_PASSWORD \
        --query SecretString \
        --output text \
        --region "${AWS_REGION:-us-east-1}" 2>/dev/null || true)"
    if [[ -n "${redis_raw}" && "${redis_raw}" != "None" ]]; then
        REDIS_PASSWORD="$(printf '%s' "${redis_raw}" | python3 -c '
import json, sys
raw = sys.stdin.read().strip()
try:
    payload = json.loads(raw)
except json.JSONDecodeError:
    payload = None
if isinstance(payload, dict):
    for key in ("REDIS_PASSWORD", "password", "secret"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            print(value, end="")
            raise SystemExit(0)
    raise SystemExit(1)
print(raw, end="")
')" || true
    fi
fi
export REDIS_PASSWORD
if [[ -z "$(docker compose ps -aq redis)" && -z "${REDIS_PASSWORD}" ]]; then
    echo "ERROR: REDIS_PASSWORD is required to create the Redis container."
    echo "Set it in .env or allow this host to read retaillen/REDIS_PASSWORD."
    exit 1
fi
if ! docker compose up -d --no-recreate redis; then
    echo "ERROR: Redis did not start. If port 6379 is still taken by a host redis-server, stop that process first."
    echo "The named volume is not deleted by this failure."
    exit 1
fi

echo "Building and restarting backend + worker..."
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

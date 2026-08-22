#!/usr/bin/env bash
# Create DynamoDB tables on DDB_ENDPOINT (local) or the current AWS account.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
REGION="${AWS_REGION:-us-east-1}"

if [[ -x "${ROOT}/backend/.venv/bin/python" ]]; then
  PY="${ROOT}/backend/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PY="python3"
else
  echo "python3 not found. Create backend/.venv and pip install boto3." >&2
  exit 1
fi

export AWS_REGION="${REGION}"
exec "${PY}" "${ROOT}/infra/scripts/create_dynamodb_tables.py" "$@"

#!/usr/bin/env bash
# Build the Linux x86_64 zip shared by the sign-in and sign-up Lambda functions.
# This script only creates a local zip. It does not call AWS or deploy anything.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SOURCE="$ROOT/backend"
OUTPUT="${OUT:-$ROOT/infra/dist/signin-lambda.zip}"
STAGE="$(mktemp -d "${TMPDIR:-/tmp}/retaillen-auth-lambda.XXXXXX")"
LAMBDA_IMAGE="public.ecr.aws/lambda/python:3.12"

cleanup() {
  rm -rf "$STAGE"
}
trap cleanup EXIT

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Required command not found: $1" >&2
    exit 1
  fi
}

copy_source() {
  local source_path="$1"
  local destination_dir="$2"

  if [[ ! -f "$SOURCE/$source_path" ]]; then
    echo "Required source file not found: backend/$source_path" >&2
    exit 1
  fi

  mkdir -p "$STAGE/$destination_dir"
  cp "$SOURCE/$source_path" "$STAGE/$destination_dir/"
}

install_dependencies() {
  if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
    echo "Installing Python 3.12 Linux x86_64 dependencies with Docker..."
    # The Lambda image normally treats its first argument as a handler.
    # Override the entrypoint so this container runs pip instead.
    docker run --rm \
      --platform linux/amd64 \
      --entrypoint python \
      -v "$STAGE:/var/task" \
      -w /var/task \
      "$LAMBDA_IMAGE" \
      -m pip install \
      --disable-pip-version-check \
      --no-compile \
      --requirement requirements.txt \
      --target /var/task
    return
  fi

  require_command python3.12
  echo "Docker is unavailable; downloading manylinux x86_64 wheels with pip..."
  python3.12 -m pip install \
    --disable-pip-version-check \
    --no-compile \
    --platform manylinux2014_x86_64 \
    --implementation cp \
    --python-version 3.12 \
    --only-binary=:all: \
    --requirement "$STAGE/requirements.txt" \
    --target "$STAGE"
}

verify_handlers() {
  if ! command -v docker >/dev/null 2>&1 || ! docker info >/dev/null 2>&1; then
    echo "Skipping Lambda container import check because Docker is unavailable."
    return
  fi

  echo "Checking that the Lambda handler can be imported..."
  docker run --rm \
    --platform linux/amd64 \
    --entrypoint python \
    -v "$STAGE:/var/task" \
    -w /var/task \
    "$LAMBDA_IMAGE" \
    -c "from lambda_signin.handler import lambda_handler"
}

require_command zip
mkdir -p "$(dirname "$OUTPUT")"

# Copy only application modules reached by the auth Lambda handler.
copy_source "core/exceptions.py" "core"
copy_source "core/settings.py" "core"
copy_source "core/security/__init__.py" "core/security"
copy_source "core/security/hasher.py" "core/security"
copy_source "core/security/tokens.py" "core/security"
copy_source "core/security/ip.py" "core/security"
copy_source "schema/auth.py" "schema"
copy_source "schema/user.py" "schema"
copy_source "services/__init__.py" "services"
copy_source "services/auth_service.py" "services"
copy_source "services/registration.py" "services"
copy_source "services/user_store.py" "services"
copy_source "services/two_factor.py" "services"
copy_source "services/sns.py" "services"
copy_source "services/dynamodb.py" "services"
copy_source "services/secrets.py" "services"
copy_source "lambda_signin/__init__.py" "lambda_signin"
copy_source "lambda_signin/handler.py" "lambda_signin"
copy_source "lambda_signin/requirements.txt" "."

# These package markers do not exist in every source directory.
touch "$STAGE/core/__init__.py" "$STAGE/schema/__init__.py"

install_dependencies
rm -f "$STAGE/requirements.txt"
find "$STAGE" -type d -name "__pycache__" -exec rm -rf {} +
verify_handlers

rm -f "$OUTPUT"
(
  cd "$STAGE"
  zip -qr "$OUTPUT" .
)

echo "Created $OUTPUT ($(wc -c < "$OUTPUT" | tr -d ' ') bytes)"
echo "Handler: lambda_signin.handler.lambda_handler"
echo "Routes: POST /auth/signin and POST /auth/register"

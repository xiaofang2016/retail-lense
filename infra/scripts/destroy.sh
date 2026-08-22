#!/usr/bin/env bash
# Tear down non-production resources to control AWS spend.
set -euo pipefail

STACK_NAME="${STACK_NAME:-retaillen}"
REGION="${AWS_REGION:-us-east-1}"

echo "Destroying ${STACK_NAME} in ${REGION}"
# TODO: aws cloudformation delete-stack --stack-name "$STACK_NAME" --region "$REGION"
echo "Not implemented yet."

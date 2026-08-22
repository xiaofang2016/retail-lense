#!/usr/bin/env bash
# Repeatable deploy for Moodle "automating deployment". No SSM.
set -euo pipefail

STACK_NAME="${STACK_NAME:-retaillen}"
REGION="${AWS_REGION:-us-east-1}"
TEMPLATE="$(cd "$(dirname "$0")/.." && pwd)/cloudformation/stack.yaml"

echo "Deploying ${STACK_NAME} in ${REGION}"
# TODO: aws cloudformation deploy --stack-name "$STACK_NAME" --template-file "$TEMPLATE" --capabilities CAPABILITY_NAMED_IAM --region "$REGION"
# TODO: build and push Docker images, then rolling update the EC2 ASG / user-data
echo "Not implemented yet. Template: ${TEMPLATE}"

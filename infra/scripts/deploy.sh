#!/usr/bin/env bash
# Create a new CloudFormation stack from infra/cloudformation/stack.yaml.
# Refuses the live account 817817875692 unless ALLOW_LIVE_ACCOUNT=yes.
# Does not replace GitHub Actions application deploys.
set -euo pipefail

TEMPLATE="$(cd "$(dirname "$0")/.." && pwd)/cloudformation/stack.yaml"
STACK_NAME="${STACK_NAME:-retaillen}"
LIVE_ACCOUNT="817817875692"

if [[ "${CONFIRM:-}" != "deploy" ]]; then
    echo "Set CONFIRM=deploy to create or update stack ${STACK_NAME}."
    echo "Template: ${TEMPLATE}"
    echo "This creates a new VPC. It does not adopt the resources already in ${LIVE_ACCOUNT}."
    exit 1
fi

ACCOUNT="$(aws sts get-caller-identity --query Account --output text)"
if [[ "${ACCOUNT}" == "${LIVE_ACCOUNT}" && "${ALLOW_LIVE_ACCOUNT:-}" != "yes" ]]; then
    echo "Refusing account ${LIVE_ACCOUNT}. Those resources already exist."
    echo "Deploy from another account, or set ALLOW_LIVE_ACCOUNT=yes for a different stack name."
    exit 1
fi

aws cloudformation deploy \
    --template-file "${TEMPLATE}" \
    --stack-name "${STACK_NAME}" \
    --capabilities CAPABILITY_NAMED_IAM \
    --parameter-overrides "ProjectName=${STACK_NAME}"

aws cloudformation describe-stacks \
    --stack-name "${STACK_NAME}" \
    --query 'Stacks[0].Outputs' \
    --output table

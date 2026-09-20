#!/usr/bin/env bash
# CloudFormation template is documentation of the CLI-built account.
# Do not create the stack in 817817875692 (resources already exist).
# Application deploys: GitHub Actions + infra/scripts/deploy_ec2_*.sh
set -euo pipefail

TEMPLATE="$(cd "$(dirname "$0")/.." && pwd)/cloudformation/stack.yaml"

echo "infra/cloudformation/stack.yaml is a documentation template."
echo "Live VPC/ALB/EC2/IAM were created with the AWS CLI; this script will not deploy."
echo "Template: ${TEMPLATE}"
echo
echo "Optional syntax check:"
echo "  aws cloudformation validate-template --template-body file://${TEMPLATE}"
exit 1

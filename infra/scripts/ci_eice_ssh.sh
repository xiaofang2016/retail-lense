#!/usr/bin/env bash
# Run a remote command on EC2 through an Instance Connect Endpoint (no public port 22).
# Used by GitHub Actions. Requires AWS CLI v2 with `ec2-instance-connect ssh`.
#
# Usage:
#   INSTANCE_ID=i-... EICE_ENDPOINT_ID=eice-... OS_USER=mike \
#     ./infra/scripts/ci_eice_ssh.sh 'bash /home/mike/retail-lense/infra/scripts/deploy_ec2_backend.sh'
set -euo pipefail

INSTANCE_ID="${INSTANCE_ID:?INSTANCE_ID is required}"
EICE_ENDPOINT_ID="${EICE_ENDPOINT_ID:?EICE_ENDPOINT_ID is required}"
if [ -z "${OS_USER:-}" ]; then
  OS_USER=mike
fi
REGION="${AWS_REGION:-us-east-1}"
REMOTE_CMD="${1:?remote command is required}"

exec aws ec2-instance-connect ssh \
  --instance-id "${INSTANCE_ID}" \
  --os-user "${OS_USER}" \
  --connection-type eice \
  --eice-options "endpointId=${EICE_ENDPOINT_ID}" \
  --region "${REGION}" \
  -- \
  bash -lc "${REMOTE_CMD}"

#!/usr/bin/env bash
# Run a remote command on EC2 through an Instance Connect Endpoint (no public port 22).
# Used by GitHub Actions.
#
# `aws ec2-instance-connect ssh` cannot take a remote command (`-- bash -lc ...`
# is rejected as ParamValidation). This script pushes an ephemeral key, opens an
# EICE tunnel, and runs the command with OpenSSH.
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

KEY_DIR="$(mktemp -d)"
cleanup() {
  rm -rf "${KEY_DIR}"
}
trap cleanup EXIT

ssh-keygen -t ed25519 -f "${KEY_DIR}/eice" -N "" -q

# Public key is valid for 60 seconds; only the handshake needs it.
aws ec2-instance-connect send-ssh-public-key \
  --region "${REGION}" \
  --instance-id "${INSTANCE_ID}" \
  --instance-os-user "${OS_USER}" \
  --ssh-public-key "file://${KEY_DIR}/eice.pub" >/dev/null

ssh -i "${KEY_DIR}/eice" \
  -o BatchMode=yes \
  -o ConnectTimeout=30 \
  -o IdentitiesOnly=yes \
  -o StrictHostKeyChecking=no \
  -o UserKnownHostsFile=/dev/null \
  -o ProxyCommand="aws ec2-instance-connect open-tunnel --region ${REGION} --instance-id ${INSTANCE_ID} --instance-connect-endpoint-id ${EICE_ENDPOINT_ID}" \
  "${OS_USER}@${INSTANCE_ID}" \
  bash -lc "${REMOTE_CMD}"

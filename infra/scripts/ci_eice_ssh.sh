#!/usr/bin/env bash
# Run a remote command on EC2 through an Instance Connect Endpoint (no public port 22).
# Same connection as:
#   aws ec2-instance-connect ssh --instance-id i-... --connection-type eice \
#     --eice-options endpointId=eice-... --os-user mike --region us-east-1
#
# That CLI does not accept extra ssh flags or a remote command after `--`.
# GitHub-hosted runners have an empty known_hosts, so we wrap `ssh` to skip
# interactive host-key prompts. The deploy command is sent on stdin.
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

WRAP_DIR="$(mktemp -d)"
cleanup() {
  rm -rf "${WRAP_DIR}"
}
trap cleanup EXIT

cat > "${WRAP_DIR}/ssh" <<'WRAP'
#!/bin/sh
exec /usr/bin/ssh \
  -o BatchMode=yes \
  -o StrictHostKeyChecking=accept-new \
  -o UserKnownHostsFile=/dev/null \
  "$@"
WRAP
chmod +x "${WRAP_DIR}/ssh"

PATH="${WRAP_DIR}:${PATH}" \
  aws ec2-instance-connect ssh \
    --instance-id "${INSTANCE_ID}" \
    --os-user "${OS_USER}" \
    --connection-type eice \
    --eice-options "endpointId=${EICE_ENDPOINT_ID}" \
    --region "${REGION}" <<EOF
set -euo pipefail
${REMOTE_CMD}
EOF

#!/usr/bin/env bash
set -euo pipefail
TEST_DATA_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source "${TEST_DATA_DIR}/.api01_hvr.env"
PAYLOAD="${TEST_DATA_DIR}/payloads/hvr01_29.json"
curl --silent --show-error --include --request POST \
  "${API01_BASE_URL}/api/ginlong/TPL_Pending_Receipt_Note" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json' \
  -H "Authorization: Bearer ${API01_TOKEN}" \
  --data-binary "@${PAYLOAD}"

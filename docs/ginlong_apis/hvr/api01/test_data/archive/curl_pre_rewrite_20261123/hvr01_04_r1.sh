#!/usr/bin/env bash
set -euo pipefail
TEST_DATA_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source "${TEST_DATA_DIR}/.api01_hvr.env"
PAYLOAD="${TEST_DATA_DIR}/archive/payloads_pre_rewrite_20261123/hvr01_04_r1.json"
curl --silent --show-error --include --request POST \
  "${API01_BASE_URL}/api/ginlong/TPL_Pending_Receipt_Note" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json' \
  -H "Authorization: Bearer ${API01_TOKEN}" \
  --data-binary "@${PAYLOAD}"

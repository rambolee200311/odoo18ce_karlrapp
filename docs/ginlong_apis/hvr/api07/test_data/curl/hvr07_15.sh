#!/usr/bin/env bash
set -euo pipefail
TEST_DATA_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source "${TEST_DATA_DIR}/.api07_hvr.env"
PAYLOAD="${TEST_DATA_DIR}/payloads/hvr07_15.json"
curl --silent --show-error --include --request POST \
  "${API07_BASE_URL}/api/ginlong/TPL_Product_Master" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json' \
  -H "Authorization: ${API07_TOKEN}" \
  --data-binary "@${PAYLOAD}"

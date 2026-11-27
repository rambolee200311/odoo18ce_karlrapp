#!/usr/bin/env bash
set -euo pipefail
TEST_DATA_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source "${TEST_DATA_DIR}/../../api01/test_data/.api01_hvr.env"
PAYLOAD="${TEST_DATA_DIR}/payloads/hvr05_09.json"
curl --silent --show-error --request POST \
  "${API01_BASE_URL}/api/ginlong/TPL_Stocktake_Order" \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json' \
  -H "Authorization: ${API01_TOKEN}" \
  --data-binary "@${PAYLOAD}"

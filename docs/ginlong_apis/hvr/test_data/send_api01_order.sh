#!/usr/bin/env bash
set -euo pipefail

# 仅向本机 API01 创建本次人工 HVR 订单；不要重发已成功的单号。
: "${GINLONG_HVR_TOKEN:?请先在本机 shell 设置有效的 GINLONG_HVR_TOKEN}"

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
PAYLOAD="$ROOT/docs/ginlong_apis/hvr/test_data/api01_inbound_order.json"

curl --silent --show-error --include --request POST \
  'http://127.0.0.1:8099/api/ginlong/TPL_Pending_Receipt_Note' \
  --header 'Accept: application/json' \
  --header 'Content-Type: application/json' \
  --header "Authorization: ${GINLONG_HVR_TOKEN}" \
  --data-binary "@$PAYLOAD"

#!/usr/bin/env bash
# 使用 API01 HVR 同一 API User 的临时 Token 发送 API03 HVR JSON；不保存凭据。
set -euo pipefail

payload_file="${1:?用法: send_api03.sh <payload.json>}"
: "${GINLONG_HVR_TOKEN:?请先在当前终端设置 GINLONG_HVR_TOKEN}"

curl --silent --show-error --request POST \
  --url "http://127.0.0.1:8099/api/ginlong/TPL_Pending_Delivery_Note" \
  --header "Authorization: ${GINLONG_HVR_TOKEN}" \
  --header 'Content-Type: application/json' \
  --data-binary "@${payload_file}" \
  --write-out '\nHTTP_STATUS=%{http_code}\n'

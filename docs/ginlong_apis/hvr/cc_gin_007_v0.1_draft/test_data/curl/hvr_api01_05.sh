#!/usr/bin/env bash
set -euo pipefail

# 人工 HVR 只允许访问本机 Odoo，避免误发到真实 Ginlong 或其他环境。

: "${GINLONG_HVR_BASE_URL:?请先设置本地 GINLONG_HVR_BASE_URL}"
: "${GINLONG_HVR_TOKEN:?请先设置本地 GINLONG_HVR_TOKEN}"

case "${GINLONG_HVR_BASE_URL}" in
  http://127.0.0.1:*|https://127.0.0.1:*|http://localhost:*|https://localhost:*|http://\[::1\]:*|https://\[::1\]:*) ;;
  *) echo "HVR 仅允许连接本机 Odoo；拒绝非 loopback 地址。" >&2; exit 2 ;;
esac

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PAYLOAD="${SCRIPT_DIR}/../payloads/hvr_api01_05.json"

curl --silent --show-error --include --request POST \
  "${GINLONG_HVR_BASE_URL%/}/api/ginlong/TPL_Pending_Receipt_Note" \
  --header 'Accept: application/json' \
  --header 'Content-Type: application/json' \
  --header "Authorization: ${GINLONG_HVR_TOKEN}" \
  --data-binary "@${PAYLOAD}"

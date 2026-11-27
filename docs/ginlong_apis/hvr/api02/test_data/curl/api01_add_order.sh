#!/usr/bin/env bash
set -euo pipefail

# 仅向本机 Odoo API01 发送指定 HVR 入库指令，不访问真实 Ginlong。
: "${GINLONG_HVR_BASE_URL:?请先设置本地 GINLONG_HVR_BASE_URL}"
: "${GINLONG_HVR_TOKEN:?请先设置本地 GINLONG_HVR_TOKEN}"

if [[ $# -ne 1 || ! -f "$1" ]]; then
  echo "用法：api01_add_order.sh <API01 JSON 文件>" >&2
  exit 2
fi

case "${GINLONG_HVR_BASE_URL}" in
  http://127.0.0.1:*|https://127.0.0.1:*|http://localhost:*|https://localhost:*|http://\[::1\]:*|https://\[::1\]:*) ;;
  *) echo "HVR 仅允许连接本机 Odoo；拒绝非 loopback 地址。" >&2; exit 2 ;;
esac

curl --silent --show-error --include --request POST \
  "${GINLONG_HVR_BASE_URL%/}/api/ginlong/TPL_Pending_Receipt_Note" \
  --header 'Accept: application/json' \
  --header 'Content-Type: application/json' \
  --header "Authorization: ${GINLONG_HVR_TOKEN}" \
  --data-binary "@$1"

#!/usr/bin/env bash
set -euo pipefail

# 通过真实 Ginlong 入站 HTTP 路由发送项目 HVR JSON；不得用于出站回传 Payload。
if [[ $# -ne 2 ]]; then
  echo "用法: $0 <objectid> <payload.json>" >&2
  exit 2
fi

GINLONG_HVR_BASE_URL="${GINLONG_HVR_BASE_URL:-http://127.0.0.1:8099}"
if [[ -z "${GINLONG_HVR_TOKEN:-}" ]]; then
  echo "请在当前终端设置 GINLONG_HVR_TOKEN（不含 Bearer 前缀）。" >&2
  exit 2
fi

OBJECT_ID="$1"
PAYLOAD_FILE="$2"
if [[ ! -f "$PAYLOAD_FILE" ]]; then
  echo "找不到 Payload 文件: $PAYLOAD_FILE" >&2
  exit 2
fi

# 五个入站 API 由同一个项目 API User 调用；出站 API 必须使用 Odoo 页面按钮。
curl --silent --show-error --include --request POST \
  --url "${GINLONG_HVR_BASE_URL%/}/api/ginlong/${OBJECT_ID}" \
  --header "Authorization: ${GINLONG_HVR_TOKEN}" \
  --header "Content-Type: application/json" \
  --data-binary "@${PAYLOAD_FILE}"

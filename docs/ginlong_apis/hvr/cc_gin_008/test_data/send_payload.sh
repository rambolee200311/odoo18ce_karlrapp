#!/usr/bin/env bash
set -euo pipefail

# 通过本地真实 Odoo 路由发送指定 JSON；脚本不读取/修改数据库，也不创建 Token。
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/.cc_gin_008.env"
if [[ ! -f "${ENV_FILE}" ]]; then
  echo "请复制 .env.example 为 .cc_gin_008.env 并填写本地测试地址和 Token。" >&2
  exit 2
fi
# shellcheck disable=SC1090
set -a
source "${ENV_FILE}"
set +a

if [[ $# -ne 3 ]]; then
  echo "用法: $0 API01|API03|API05|API07 A|B|API07 payload.json" >&2
  exit 2
fi
api="$1"
profile="$2"
payload="$3"
case "${api}" in
  API01) object_id="TPL_Pending_Receipt_Note" ;;
  API03) object_id="TPL_Pending_Delivery_Note" ;;
  API05) object_id="TPL_Stocktake_Order" ;;
  API07) object_id="TPL_Product_Master" ;;
  *) echo "不支持的 API: ${api}" >&2; exit 2 ;;
esac
case "${profile}" in
  A) token="${GINLONG_HVR_TOKEN_A:-}" ;;
  B) token="${GINLONG_HVR_TOKEN_B:-}" ;;
  API07) token="${GINLONG_HVR_TOKEN_API07:-}" ;;
  *) echo "凭据 profile 必须为 A、B 或 API07。" >&2; exit 2 ;;
esac
if [[ -z "${token}" || "${token}" == REPLACE_* ]]; then
  echo "未配置 ${profile} 的本地 API Token。" >&2
  exit 2
fi
if [[ ! -f "${payload}" ]]; then
  echo "Payload 文件不存在: ${payload}" >&2
  exit 2
fi

curl --silent --show-error --request POST \
  "${GINLONG_HVR_BASE_URL%/}/api/ginlong/${object_id}" \
  --header 'Accept: application/json' \
  --header 'Content-Type: application/json' \
  --header "Authorization: Bearer ${token}" \
  --data-binary "@${payload}"
printf '\n'

#!/bin/sh
set -eu

# 仅发送 Ginlong 入站 API；出站回传必须由 Odoo 表单按钮触发。
api=${1:-}
payload=${2:-}
: "${ODOO_URL:=http://127.0.0.1:8099}"
: "${GINLONG_TOKEN:?请先设置当前 API User 的有效 Token}"

case "$api" in
  API01) object_id=TPL_Pending_Receipt_Note ;;
  API03) object_id=TPL_Pending_Delivery_Note ;;
  API05) object_id=TPL_Stocktake_Order ;;
  API07) object_id=TPL_Product_Master ;;
  API09) object_id=TPL_Stock_Query ;;
  *) echo "仅支持 API01、API03、API05、API07、API09" >&2; exit 2 ;;
esac

if [ -z "$payload" ] || [ ! -f "$payload" ]; then
  echo "用法：./send_payload.sh API07 payloads/api07_01_fg.json" >&2
  exit 2
fi

curl --silent --show-error --request POST \
  --url "${ODOO_URL%/}/api/ginlong/$object_id" \
  --header "Accept: application/json" \
  --header "Authorization: $GINLONG_TOKEN" \
  --header "Content-Type: application/json" \
  --data-binary "@$payload"
printf '\n'


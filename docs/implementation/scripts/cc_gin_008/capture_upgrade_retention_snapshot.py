"""通过 Odoo ORM 快照 CC-GIN-008 相关业务、幂等及 API 日志关键字段。"""

import hashlib
import json
import os
from pathlib import Path
from datetime import date, datetime
from decimal import Decimal


def normalize(value):
    """将 ORM Many2one 与基本值归一化为稳定 JSON 数据。"""
    if isinstance(value, tuple):
        return [normalize(item) for item in value]
    if isinstance(value, list):
        return [normalize(item) for item in value]
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def read_rows(env, model_name, field_names, domain=None, active_test=True):
    """使用 ORM 读取记录并按 ID 稳定排序。"""
    model = env[model_name].sudo().with_context(active_test=active_test)
    records = model.search(domain or [], order="id")
    return [
        {key: normalize(value) for key, value in row.items()}
        for row in records.read(field_names)
    ]


def hash_text(value):
    """只保存文本摘要，避免快照复制 API 报文或返回内容。"""
    text = value or ""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def capture(env):
    """读取并返回升级前后需要比较的身份、状态和审计字段。"""
    module = env["ir.module.module"].sudo().search([("name", "=", "ginlong_apis")], limit=1)
    if not module:
        raise RuntimeError("ginlong_apis module record not found")

    snapshot = {
        "module": {"state": module.state, "installed_version": module.installed_version},
        "inbound": read_rows(env, "world.depot.inbound.order", [
            "id", "reference", "state", "project",
        ]),
        "outbound": read_rows(env, "world.depot.outbound.order", [
            "id", "reference", "state", "project",
        ]),
        "stocktake": read_rows(env, "world.depot.stocktake.order", [
            "id", "count_order_no", "state", "project_id", "owner_code", "warehouse_code",
        ]),
        "products": read_rows(env, "product.product", [
            "id", "ginlong_owner_code", "ginlong_product_code", "default_code", "active",
        ], active_test=False),
        "idempotency": read_rows(env, "ginlong.api.idempotency", [
            "id", "api_code", "direction", "business_key", "event_key", "action",
            "request_fingerprint", "state", "attempt_count", "response_json",
        ]),
        "api_logs": read_rows(env, "world.depot.api.log", [
            "id", "project_id", "request_time", "request_path", "status", "code", "success", "msg",
            "request_data", "response_data",
        ]),
    }

    # 报文只保留摘要，快照可用于核对日志是否保留而不会复制敏感内容。
    for group in ("idempotency", "api_logs"):
        for row in snapshot[group]:
            if group == "idempotency":
                row["response_json_sha256"] = hash_text(row.pop("response_json"))
            else:
                row["request_data_sha256"] = hash_text(row.pop("request_data"))
                row["response_data_sha256"] = hash_text(row.pop("response_data"))
    return snapshot


target = os.environ.get("CCGIN008_SNAPSHOT_PATH")
if not target:
    raise SystemExit("Set CCGIN008_SNAPSHOT_PATH to a protected local JSON file path")

output = Path(target).expanduser()
output.write_text(
    json.dumps(capture(env), ensure_ascii=False, sort_keys=True, indent=2),
    encoding="utf-8",
)
print("CC-GIN-008 ORM retention snapshot written:", output)
env.cr.rollback()

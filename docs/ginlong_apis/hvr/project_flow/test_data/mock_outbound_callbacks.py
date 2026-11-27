#!/usr/bin/env python3
"""为项目级 HVR 接收 Odoo API06、API08、API10 的真实按钮回传。"""

import argparse
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
from threading import Lock


ALLOWED_PATHS = {
    "/API/WMS_JSON/TPL_Picking_Completed",
    "/API/WMS_JSON/TPL_Shipment_Completed",
    "/API/WMS_JSON/TPL_Stocktaking_Completed",
}
OUTPUT_FILE = Path(__file__).with_name("outbound_received.jsonl")
MAX_BODY_SIZE = 2 * 1024 * 1024
write_lock = Lock()

_TOP_LEVEL_FIELDS = {
    "/API/WMS_JSON/TPL_Picking_Completed": {
        "owner", "action", "outboundOrderNo", "palletQty", "totalWeight", "snList",
    },
    "/API/WMS_JSON/TPL_Shipment_Completed": {
        "outboundOrderNo", "action", "shipmentConfirmed",
    },
    "/API/WMS_JSON/TPL_Stocktaking_Completed": {
        "owner", "action", "countOrderNo", "snList",
    },
}
_SN_FIELDS = {"productSN", "quantity", "palletCode", "productCode", "operator", "operationTime"}
_DECIMAL = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$")
_DATETIME = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")


def validate_payload(path, payload):
    """按 V3.2 校验出站 Mock 收到的字段结构和已确认 Action。

    参数：
        path: 本地 Mock 的 Ginlong Object ID 路径。
        payload: Odoo 实际按钮发送的 JSON 对象。

    返回：
        完整错误列表；通过时返回空列表。该函数不修改 Payload。
    """
    errors = []
    expected = _TOP_LEVEL_FIELDS[path]
    missing = sorted(name for name in expected if name not in payload or payload[name] is None or payload[name] == "")
    extra = sorted(set(payload) - expected)
    errors.extend("missing:%s" % name for name in missing)
    errors.extend("unexpected:%s" % name for name in extra)

    for name in expected - {"snList", "palletQty", "totalWeight"}:
        value = payload.get(name)
        if not isinstance(value, str) or not value.strip():
            errors.append("%s:must be non-empty text" % name)

    action = payload.get("action")
    if path.endswith("TPL_Picking_Completed") and action != "CREATE":
        errors.append("action:must be CREATE")
    elif path.endswith("TPL_Shipment_Completed") and action != "CREATE":
        errors.append("action:must be CREATE")
    elif path.endswith("TPL_Stocktaking_Completed") and str(action or "").casefold() not in {"add", "del"}:
        errors.append("action:must be Add or Del")

    if path.endswith("TPL_Shipment_Completed") and payload.get("shipmentConfirmed") not in {"Y", "N"}:
        errors.append("shipmentConfirmed:must be Y or N")

    if path.endswith("TPL_Picking_Completed"):
        for field in ("palletQty", "totalWeight"):
            value = payload.get(field)
            if not isinstance(value, str) or not _DECIMAL.fullmatch(value):
                errors.append("%s:must be decimal JSON string" % field)

    if path.endswith(("TPL_Picking_Completed", "TPL_Stocktaking_Completed")):
        rows = payload.get("snList")
        if not isinstance(rows, list) or not rows:
            errors.append("snList:must be non-empty array")
        else:
            for index, row in enumerate(rows):
                prefix = "snList[%s]" % index
                if not isinstance(row, dict):
                    errors.append("%s:must be object" % prefix)
                    continue
                errors.extend("%s.%s:missing" % (prefix, name) for name in sorted(_SN_FIELDS - set(row)))
                errors.extend("%s.%s:unexpected" % (prefix, name) for name in sorted(set(row) - _SN_FIELDS))
                quantity = row.get("quantity")
                if isinstance(quantity, bool) or not isinstance(quantity, (int, float)):
                    errors.append("%s.quantity:must be JSON number" % prefix)
                for field in _SN_FIELDS - {"quantity"}:
                    value = row.get(field)
                    if not isinstance(value, str) or not value.strip():
                        errors.append("%s.%s:must be non-empty text" % (prefix, field))
                operation_time = row.get("operationTime")
                if not isinstance(operation_time, str) or not _DATETIME.fullmatch(operation_time):
                    errors.append("%s.operationTime:invalid format" % prefix)
                else:
                    try:
                        datetime.strptime(operation_time, "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        errors.append("%s.operationTime:invalid date" % prefix)
    return errors


class OutboundCallbackHandler(BaseHTTPRequestHandler):
    """记录 Odoo 按钮发出的业务 JSON，并返回 Ginlong V3.2 三字段成功响应。"""

    server_version = "GinlongProjectHVRMock/1.0"

    def do_GET(self):
        """提供只读健康检查；健康检查不会写入业务捕获记录。"""
        if self.path != "/__mock__/health":
            self.send_error(404)
            return
        self._send_json(200, {"status": "ok"})

    def do_POST(self):
        """保存 Odoo 按钮真实发送的请求，并拒绝未配置的接口路径。"""
        if self.path not in ALLOWED_PATHS:
            self.send_error(404)
            return
        if self.headers.get_content_type() != "application/json":
            self._send_json(415, {"error": "Content-Type must be application/json"})
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send_json(400, {"error": "Invalid Content-Length"})
            return
        if size <= 0 or size > MAX_BODY_SIZE:
            self._send_json(413 if size > MAX_BODY_SIZE else 400, {"error": "Invalid body size"})
            return
        try:
            payload = json.loads(self.rfile.read(size).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send_json(400, {"error": "Body must be UTF-8 JSON"})
            return
        if not isinstance(payload, dict):
            self._send_json(400, {"error": "Payload must be a JSON object"})
            return

        received_at = datetime.now().astimezone()
        validation_errors = validate_payload(self.path, payload)
        response = {
            "returnStatus": "N" if validation_errors else "Y",
            "exceptionInfo": "MOCK01: invalid payload" if validation_errors else "OK",
            "operationTime": received_at.strftime("%Y-%m-%d %H:%M:%S"),
        }
        record = {
            "receivedAt": received_at.isoformat(timespec="seconds"),
            "method": "POST",
            "path": self.path,
            "contentType": self.headers.get_content_type(),
            "payload": payload,
            "accepted": not validation_errors,
            "validationErrors": validation_errors,
            "httpStatus": 200,
            "mockResponse": response,
        }
        # 只保存业务报文，不把 Authorization、Cookie 等认证 Header 写入捕获文件。
        with write_lock:
            with OUTPUT_FILE.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
        print(json.dumps(record, ensure_ascii=False), flush=True)
        self._send_json(200, response)

    def _send_json(self, status, data):
        """将模拟响应编码为 UTF-8 JSON 并写回客户端。"""
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format_string, *args):
        """仅在终端输出 HTTP 访问摘要。"""
        print("[HTTP] " + format_string % args, flush=True)


def main():
    """启动项目级出站 Mock，默认只允许本机访问。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1", help="监听地址；默认仅本机可访问")
    parser.add_argument("--port", type=int, default=18106, help="本地 Mock 监听端口")
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), OutboundCallbackHandler)
    print("Project callback Mock listening at http://%s:%s" % (args.host, args.port), flush=True)
    print("Captured business payloads append to %s" % OUTPUT_FILE, flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopping project callback Mock.", flush=True)
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

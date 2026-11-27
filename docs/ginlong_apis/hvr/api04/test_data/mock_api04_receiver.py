#!/usr/bin/env python3
"""接收 API04 本地人工 HVR 的真实 Odoo 按钮回传。"""

import argparse
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
from threading import Lock


EXPECTED_PATH = "/API/WMS_JSON/TPL_Inbound_Completion"
OUTPUT_FILE = Path(__file__).with_name("received.jsonl")
MAX_BODY_SIZE = 2 * 1024 * 1024
write_lock = Lock()
_TOP_LEVEL_FIELDS = {"owner", "action", "inboundOrderNo", "snList"}
_ROW_FIELDS = {"productSN", "quantity", "palletCode", "productCode", "operator", "operationTime"}
_DATETIME = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")


def validate_payload(payload):
    """校验 API04 本地 Mock 的 V3.2 表头和逐行实际入库字段。"""
    errors = []
    errors.extend("missing:%s" % key for key in sorted(_TOP_LEVEL_FIELDS - set(payload)))
    errors.extend("unexpected:%s" % key for key in sorted(set(payload) - _TOP_LEVEL_FIELDS))
    for key in ("owner", "inboundOrderNo"):
        if not isinstance(payload.get(key), str) or not payload[key].strip():
            errors.append("%s:must be non-empty text" % key)
    if payload.get("action") != "CREATE":
        errors.append("action:must be CREATE")
    rows = payload.get("snList")
    if not isinstance(rows, list) or not rows:
        errors.append("snList:must be non-empty array")
    else:
        for index, row in enumerate(rows):
            prefix = "snList[%s]" % index
            if not isinstance(row, dict):
                errors.append("%s:must be object" % prefix)
                continue
            errors.extend("%s.%s:missing" % (prefix, key) for key in sorted(_ROW_FIELDS - set(row)))
            errors.extend("%s.%s:unexpected" % (prefix, key) for key in sorted(set(row) - _ROW_FIELDS))
            for key in _ROW_FIELDS - {"quantity"}:
                if not isinstance(row.get(key), str) or not row[key].strip():
                    errors.append("%s.%s:must be non-empty text" % (prefix, key))
            quantity = row.get("quantity")
            if isinstance(quantity, bool) or not isinstance(quantity, (int, float)):
                errors.append("%s.quantity:must be JSON number" % prefix)
            operation_time = row.get("operationTime")
            if not isinstance(operation_time, str) or not _DATETIME.fullmatch(operation_time):
                errors.append("%s.operationTime:invalid format" % prefix)
            else:
                try:
                    datetime.strptime(operation_time, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    errors.append("%s.operationTime:invalid date" % prefix)
    return errors


class API04MockHandler(BaseHTTPRequestHandler):
    """记录 Odoo API04 按钮发出的 HTTP JSON，并模拟 Ginlong 三字段响应。"""

    server_version = "GinlongAPI04Mock/1.0"

    def do_GET(self):
        """提供不会产生业务数据的健康检查。"""
        if self.path != "/__mock__/health":
            self.send_error(404)
            return
        self._send_json(200, {"status": "ok"})

    def do_POST(self):
        """记录一次实际回传；可配置前 N 次临时失败以验证人工重试。"""
        if self.path != EXPECTED_PATH:
            self.send_error(404)
            return
        if self.headers.get_content_type() != "application/json":
            self._send_json(415, {"error": "Content-Type must be application/json"})
            return
        try:
            body_size = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send_json(400, {"error": "Invalid Content-Length"})
            return
        if body_size <= 0 or body_size > MAX_BODY_SIZE:
            self._send_json(413 if body_size > MAX_BODY_SIZE else 400, {"error": "Invalid body size"})
            return
        try:
            payload = json.loads(self.rfile.read(body_size).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send_json(400, {"error": "Body must be UTF-8 JSON"})
            return
        if not isinstance(payload, dict):
            self._send_json(400, {"error": "Payload must be a JSON object"})
            return

        validation_errors = validate_payload(payload)
        received_at = datetime.now().astimezone()
        with write_lock:
            self.server.request_count += 1
            fail = not validation_errors and self.server.request_count <= self.server.fail_first
            response = (
                {"returnStatus": "N", "exceptionInfo": "MOCK01: invalid payload", "operationTime": received_at.strftime("%Y-%m-%d %H:%M:%S")}
                if validation_errors else
                {"returnStatus": "N", "exceptionInfo": "MOCK01: temporary failure", "operationTime": received_at.strftime("%Y-%m-%d %H:%M:%S")}
                if fail else
                {"returnStatus": "Y", "exceptionInfo": "OK", "operationTime": received_at.strftime("%Y-%m-%d %H:%M:%S")}
            )
            record = {
                "receivedAt": received_at.isoformat(timespec="seconds"),
                "method": "POST",
                "path": self.path,
                "contentType": self.headers.get_content_type(),
                "payload": payload,
                "accepted": not validation_errors,
                "validationErrors": validation_errors,
                "httpStatus": 200 if validation_errors else (503 if fail else 200),
                "mockResponse": response,
            }
            with OUTPUT_FILE.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
        print(json.dumps(record, ensure_ascii=False), flush=True)
        self._send_json(200 if validation_errors else (503 if fail else 200), response)

    def _send_json(self, status, data):
        """以 UTF-8 JSON 返回本地模拟响应。"""
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format_string, *args):
        """只向终端记录传输日志，不把通用请求头写入报文记录。"""
        print("[HTTP] " + format_string % args, flush=True)


def main():
    """仅绑定本机回环地址并启动 API04 Mock 接收端。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1", help="默认只允许本机连接")
    parser.add_argument("--port", type=int, default=18104, help="默认 API04 Mock 端口")
    parser.add_argument("--fail-first", type=int, default=0, help="前 N 个 POST 返回 HTTP 503")
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), API04MockHandler)
    server.request_count = 0
    server.fail_first = max(0, args.fail_first)
    print("API04 Mock listening at http://%s:%s%s" % (args.host, args.port, EXPECTED_PATH), flush=True)
    print("Captured payloads append to %s" % OUTPUT_FILE, flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopping API04 Mock receiver.", flush=True)
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""接收 API02 本地人工 HVR 的真实按钮回传并保存报文。"""

import argparse
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
from threading import Lock


EXPECTED_PATH = "/API/WMS_JSON/TPL_Receipt_Confirmation"
OUTPUT_FILE = Path(__file__).with_name("received.jsonl")
MAX_BODY_SIZE = 1024 * 1024
write_lock = Lock()
_FIELDS = {"inboundOrderNo", "action", "receiptConfirmed"}


def validate_payload(payload):
    """校验 API02 本地 Mock 请求符合已确认的 V3.2 订单级结构。"""
    errors = []
    errors.extend("missing:%s" % key for key in sorted(_FIELDS - set(payload)))
    errors.extend("unexpected:%s" % key for key in sorted(set(payload) - _FIELDS))
    for key in _FIELDS & set(payload):
        value = payload[key]
        if not isinstance(value, str) or not value.strip():
            errors.append("%s:must be non-empty text" % key)
    if payload.get("action") != "UPDATE":
        errors.append("action:must be UPDATE")
    if payload.get("receiptConfirmed") not in {"Y", "N"}:
        errors.append("receiptConfirmed:must be Y or N")
    return errors


class API02MockHandler(BaseHTTPRequestHandler):
    """模拟 Ginlong API02 接收端，记录真实 HTTP POST 并返回 V3.2 响应。"""

    server_version = "GinlongAPI02Mock/1.0"

    def do_GET(self):
        """提供不产生业务报文的存活检查入口。"""
        if self.path != "/__mock__/health":
            self.send_error(404)
            return
        self._send_json(200, {"status": "ok"})

    def do_POST(self):
        """保存回传按钮发出的 JSON，再返回 Ginlong V3.2 三字段确认。"""
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
            raw_body = self.rfile.read(body_size)
            payload = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send_json(400, {"error": "Body must be UTF-8 JSON"})
            return
        if not isinstance(payload, dict):
            self._send_json(400, {"error": "Payload must be a JSON object"})
            return

        # 按协议校验后再返回成功，防止任意 JSON 对象被误认为通过 HVR。
        validation_errors = validate_payload(payload)
        received_at = datetime.now().astimezone()
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
            "mockResponse": response,
        }
        with write_lock:
            with OUTPUT_FILE.open("a", encoding="utf-8") as output:
                output.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
                output.flush()
                os.fsync(output.fileno())

        print(json.dumps(record, ensure_ascii=False), flush=True)
        self._send_json(200, response)

    def _send_json(self, status, data):
        """以 UTF-8 JSON 返回 Mock HTTP 响应。"""
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format_string, *args):
        """将 HTTP 访问日志输出至终端，避免其影响接收报文 JSONL。"""
        print("[HTTP] " + format_string % args, flush=True)


def main():
    """启动只绑定本机回环地址的 API02 Mock 接收端。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1", help="监听地址；默认仅本机可访问")
    parser.add_argument("--port", type=int, default=18102, help="监听端口")
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), API02MockHandler)
    print("API02 Mock listening at http://%s:%s%s" % (args.host, args.port, EXPECTED_PATH), flush=True)
    print("Received payloads will append to %s" % OUTPUT_FILE, flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopping API02 Mock receiver.", flush=True)
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

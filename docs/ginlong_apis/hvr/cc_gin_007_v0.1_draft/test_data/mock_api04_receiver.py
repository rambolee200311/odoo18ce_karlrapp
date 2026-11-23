#!/usr/bin/env python3
"""在本机接收 HVR-API01-07 的 API04 POST，并返回 Ginlong 成功响应格式。"""

import argparse
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json


class MockAPI04Handler(BaseHTTPRequestHandler):
    """打印本机收到的 API04 JSON 并返回成功协议三字段。"""

    def do_POST(self):
        """读取并显示报文，然后返回本地 Mock 成功响应。"""
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        try:
            body = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self.send_error(400, "Expected JSON")
            return

        print("RECEIVED_API04_JSON=" + json.dumps(body, ensure_ascii=False), flush=True)
        response = {
            "returnStatus": "Y",
            "exceptionInfo": "OK",
            "operationTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        encoded = json.dumps(response, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format_string, *args):
        """关闭默认访问日志，避免输出不必要的请求头信息。"""
        return


def main():
    """启动仅绑定 loopback 的本地 Mock 接收器。"""
    parser = argparse.ArgumentParser(description="仅本机使用的 Ginlong API04 Mock")
    parser.add_argument("--port", type=int, default=0, help="监听端口；0 表示由系统分配")
    args = parser.parse_args()

    with ThreadingHTTPServer(("127.0.0.1", args.port), MockAPI04Handler) as server:
        host, port = server.server_address
        print(
            "本机 API04 Mock URL: "
            f"http://{host}:{port}/API/WMS_JSON/TPL_Inbound_Completion",
            flush=True,
        )
        print("按 Ctrl-C 停止。", flush=True)
        server.serve_forever()


if __name__ == "__main__":
    main()

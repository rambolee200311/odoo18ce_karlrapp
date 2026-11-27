"""用真实本地 HTTP 请求验证项目 HVR Mock 的接口契约行为。"""

import importlib.util
import json
from pathlib import Path
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen


BASE = Path(__file__).resolve().parents[1]


def load_module(module_name, path):
    """按绝对路径加载一个 Mock 脚本，避免依赖外部包或项目环境。"""
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


API02 = load_module("ginlong_api02_mock", BASE.parent / "api02/test_data/mock_api02_receiver.py")
API04 = load_module("ginlong_api04_mock", BASE.parent / "api04/test_data/mock_api04_receiver.py")
OUTBOUND = load_module("ginlong_outbound_mock", Path(__file__).with_name("mock_outbound_callbacks.py"))


def detail_row():
    """返回一条满足 V3.2 SN 明细字段定义的测试行。"""
    return {
        "productSN": "MOCK-SN-001",
        "quantity": 1,
        "palletCode": "MOCK-PALLET-001",
        "productCode": "MOCK-PRODUCT-001",
        "operator": "mock.operator",
        "operationTime": "2026-11-27 09:30:00",
    }


class CallbackMockContractTests(unittest.TestCase):
    """通过真实 HTTP 请求确认 Mock 只对有效 Ginlong Payload 返回成功。"""

    def _post(self, module, path, payload, fail_first=0):
        """启动隔离的临时 Mock Listener，发送一次真实 POST 并读取捕获证据。"""
        with tempfile.TemporaryDirectory() as temporary_dir:
            previous_output = module.OUTPUT_FILE
            module.OUTPUT_FILE = Path(temporary_dir) / "captured.jsonl"
            server = ThreadingHTTPServer(("127.0.0.1", 0), module.API02MockHandler if module is API02 else
                                         module.API04MockHandler if module is API04 else
                                         module.OutboundCallbackHandler)
            if module is API04:
                server.request_count = 0
                server.fail_first = fail_first
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                body = json.dumps(payload).encode("utf-8")
                request = Request(
                    "http://127.0.0.1:%s%s" % (server.server_port, path),
                    data=body,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                try:
                    response = urlopen(request, timeout=3)
                    http_status = response.status
                    result = json.loads(response.read().decode("utf-8"))
                except HTTPError as error:
                    http_status = error.code
                    result = json.loads(error.read().decode("utf-8"))
                captured = json.loads(module.OUTPUT_FILE.read_text(encoding="utf-8").splitlines()[-1])
                return http_status, result, captured
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=3)
                module.OUTPUT_FILE = previous_output

    def test_valid_payloads_for_all_five_callbacks_are_accepted(self):
        """确认五个回传 Endpoint 都只对字段齐全的 JSON 返回 Y。"""
        samples = [
            (API02, API02.EXPECTED_PATH, {
                "inboundOrderNo": "MOCK-IN-001", "action": "UPDATE", "receiptConfirmed": "Y",
            }),
            (API04, API04.EXPECTED_PATH, {
                "owner": "MOCK-OWNER", "action": "CREATE", "inboundOrderNo": "MOCK-IN-001",
                "snList": [detail_row()],
            }),
            (OUTBOUND, "/API/WMS_JSON/TPL_Picking_Completed", {
                "owner": "MOCK-OWNER", "action": "CREATE", "outboundOrderNo": "MOCK-OUT-001",
                "palletQty": "1", "totalWeight": "1.25", "snList": [detail_row()],
            }),
            (OUTBOUND, "/API/WMS_JSON/TPL_Shipment_Completed", {
                "outboundOrderNo": "MOCK-OUT-001", "action": "CREATE", "shipmentConfirmed": "Y",
            }),
            (OUTBOUND, "/API/WMS_JSON/TPL_Stocktaking_Completed", {
                "owner": "MOCK-OWNER", "action": "Add", "countOrderNo": "MOCK-COUNT-001",
                "snList": [detail_row()],
            }),
        ]
        for module, path, payload in samples:
            with self.subTest(path=path):
                status, response, captured = self._post(module, path, payload)
                self.assertEqual(status, 200)
                self.assertEqual(response["returnStatus"], "Y")
                self.assertEqual(response["exceptionInfo"], "OK")
                self.assertTrue(captured["accepted"])
                self.assertEqual(captured["payload"], payload)

    def test_invalid_payloads_are_rejected_and_detailed_in_capture(self):
        """确认缺失字段、额外 API08 字段和错误 Action 不会被 Mock 假报成功。"""
        samples = [
            (API02, API02.EXPECTED_PATH, {"inboundOrderNo": "MOCK-IN-001"}),
            (API04, API04.EXPECTED_PATH, {
                "owner": "MOCK-OWNER", "action": "CREATE", "inboundOrderNo": "MOCK-IN-001", "snList": [],
            }),
            (OUTBOUND, "/API/WMS_JSON/TPL_Picking_Completed", {
                "owner": "MOCK-OWNER", "action": "CREATE", "outboundOrderNo": "MOCK-OUT-001",
                "palletQty": "zero", "totalWeight": "1.25", "snList": [detail_row()],
            }),
            (OUTBOUND, "/API/WMS_JSON/TPL_Shipment_Completed", {
                "outboundOrderNo": "MOCK-OUT-001", "action": "UPDATE", "shipmentConfirmed": "Y",
                "palletCode": "MUST-NOT-BE-ADDED",
            }),
            (OUTBOUND, "/API/WMS_JSON/TPL_Stocktaking_Completed", {
                "owner": "MOCK-OWNER", "action": "unknown", "countOrderNo": "MOCK-COUNT-001",
                "snList": [detail_row()],
            }),
        ]
        for module, path, payload in samples:
            with self.subTest(path=path):
                status, response, captured = self._post(module, path, payload)
                self.assertEqual(status, 200)
                self.assertEqual(response["returnStatus"], "N")
                self.assertEqual(response["exceptionInfo"], "MOCK01: invalid payload")
                self.assertFalse(captured["accepted"])
                self.assertTrue(captured["validationErrors"])

    def test_api04_fail_first_still_records_a_real_retryable_attempt(self):
        """保持 API04 本地失败重试 Mock 的现有行为及真实 HTTP 证据。"""
        status, response, captured = self._post(API04, API04.EXPECTED_PATH, {
            "owner": "MOCK-OWNER", "action": "CREATE", "inboundOrderNo": "MOCK-IN-001",
            "snList": [detail_row()],
        }, fail_first=1)
        self.assertEqual(status, 503)
        self.assertEqual(response["returnStatus"], "N")
        self.assertTrue(captured["accepted"])
        self.assertEqual(captured["httpStatus"], 503)


if __name__ == "__main__":
    unittest.main(verbosity=2)

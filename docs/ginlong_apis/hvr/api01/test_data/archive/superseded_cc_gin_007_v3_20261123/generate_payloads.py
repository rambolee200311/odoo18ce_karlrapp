"""生成 API01 当前必需的五个 HVR 报文及 curl 脚本。"""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PAYLOAD_DIR = ROOT / "payloads"
CURL_DIR = ROOT / "curl"
OWNER = "HVR01-20261121-OWNER-A"
WAREHOUSE = "KRWH"
RAW = {
    "code": "HVR01-20261121-PROD-COMMON",
    "name": "HVR01 Ginlong 入库产品",
    "spec": "HVR01-MODEL-01",
}
FINISHED = {
    "code": "HVR01-20261122-PROD-SERIAL",
    "name": "HVR01 成品序列号验收产品",
    "spec": "HVR01-SERIAL-MODEL",
}
SEMIFINISHED = {
    "code": "HVR01-20261122-PROD-SEMIFINISHED",
    "name": "HVR01 半成品序列号验收产品",
    "spec": "HVR01-SEMIFINISHED-MODEL",
}


def _detail(product, quantity):
    """构造 API01 产品明细行。"""
    return {
        "productCode": product["code"],
        "productName": product["name"],
        "specificationModel": product["spec"],
        "quantity": quantity,
    }


def _sn_row(product, product_sn, quantity, pallet_code):
    """构造包含产品、数量及托盘归属的 snList 行。"""
    return {
        "productSN": product_sn,
        "quantity": quantity,
        "palletCode": pallet_code,
        "productCode": product["code"],
        "productName": product["name"],
        "specificationModel": product["spec"],
    }


def _serial_row(product, serial_number, pallet_code):
    """构造一个真实 SN；单件 SN 数量固定为 1。"""
    return _sn_row(product, serial_number, 1, pallet_code)


def _material_row(product, quantity, pallet_code):
    """构造原材料托盘分配行；伪 SN 使用产品编码且数量可以大于 1。"""
    return _sn_row(product, product["code"], quantity, pallet_code)


def _rich_mixed_payload():
    """构造本轮主验收：三托盘混装原材料、成品和半成品。"""
    pallets = ["HVR01-R3-PALLET-A", "HVR01-R3-PALLET-B", "HVR01-R3-PALLET-C"]
    sn_list = []
    for pallet_index, pallet_code in enumerate(pallets):
        # 原材料每个托盘单独记录数量；相同伪 SN 跨托盘重复是合法分配。
        sn_list.append(_material_row(RAW, 3, pallet_code))
        for product, prefix in ((FINISHED, "FG"), (SEMIFINISHED, "SF")):
            for unit_index in (1, 2):
                serial_number = "HVR01-R3-%s-%s-%02d" % (
                    prefix, chr(ord("A") + pallet_index), unit_index,
                )
                sn_list.append(_serial_row(product, serial_number, pallet_code))

    return {
        "owner": OWNER,
        "action": "Add",
        "inboundOrderNo": "HVR01-20261123-R3-MIXED-001",
        "warehouse": WAREHOUSE,
        "businessType": "STANDARD",
        "remark": "R3：三个托盘混装原材料、成品和半成品",
        "details": [
            _detail(FINISHED, 6),
            _detail(SEMIFINISHED, 6),
            _detail(RAW, 9),
        ],
        "snList": sn_list,
    }


def cases():
    """返回本轮必需的五个人工 HTTP 验收实例，按依赖顺序排列。"""
    return [
        (
            "HVR01-29",
            "主场景：三托盘混装三种产品，核对托盘归属与数量",
            _rich_mixed_payload(),
        ),
        (
            "HVR01-30",
            "SN 管理产品单条 quantity=3：拒绝并定位产品、托盘",
            {
                "owner": OWNER,
                "action": "Add",
                "inboundOrderNo": "HVR01-20261123-R3-SN-QTY-001",
                "warehouse": WAREHOUSE,
                "businessType": "STANDARD",
                "details": [_detail(FINISHED, 3)],
                "snList": [_sn_row(
                    FINISHED, "HVR01-R3-INVALID-SN-QTY", 3,
                    "HVR01-R3-INVALID-PALLET-A",
                )],
            },
        ),
        (
            "HVR01-31",
            "同一产品、同一真实 SN 跨托盘重复：拒绝",
            {
                "owner": OWNER,
                "action": "Add",
                "inboundOrderNo": "HVR01-20261123-R3-DUP-SN-001",
                "warehouse": WAREHOUSE,
                "businessType": "STANDARD",
                "details": [_detail(FINISHED, 2)],
                "snList": [
                    _serial_row(FINISHED, "HVR01-R3-DUPLICATE-SN", "HVR01-R3-DUP-PALLET-A"),
                    _serial_row(FINISHED, "HVR01-R3-DUPLICATE-SN", "HVR01-R3-DUP-PALLET-B"),
                ],
            },
        ),
        (
            "HVR01-32",
            "不同产品使用相同 SN 文本：允许",
            {
                "owner": OWNER,
                "action": "Add",
                "inboundOrderNo": "HVR01-20261123-R3-SAME-SN-001",
                "warehouse": WAREHOUSE,
                "businessType": "STANDARD",
                "details": [_detail(FINISHED, 1), _detail(SEMIFINISHED, 1)],
                "snList": [
                    _serial_row(FINISHED, "HVR01-R3-SAME-SN", "HVR01-R3-SAME-PALLET-A"),
                    _serial_row(SEMIFINISHED, "HVR01-R3-SAME-SN", "HVR01-R3-SAME-PALLET-B"),
                ],
            },
        ),
        (
            "HVR01-33",
            "不同 API01 单据引用 HVR01-29 的真实 SN：允许",
            {
                "owner": OWNER,
                "action": "Add",
                "inboundOrderNo": "HVR01-20261123-R3-CROSS-ORDER-001",
                "warehouse": WAREHOUSE,
                "businessType": "STANDARD",
                "details": [_detail(FINISHED, 1)],
                "snList": [_serial_row(
                    FINISHED, "HVR01-R3-FG-A-01", "HVR01-R3-CROSS-ORDER-PALLET",
                )],
            },
        ),
    ]


def _curl_script(stem):
    """构造本机 POST 脚本；Token 仅从权限受限的本地 env 文件读取。"""
    return "\n".join([
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        'TEST_DATA_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"',
        'source "${TEST_DATA_DIR}/.api01_hvr.env"',
        f'PAYLOAD="${{TEST_DATA_DIR}}/payloads/{stem}.json"',
        "curl --silent --show-error --include --request POST \\",
        '  "${API01_BASE_URL}/api/ginlong/TPL_Pending_Receipt_Note" \\',
        "  -H 'Content-Type: application/json' \\",
        "  -H 'Accept: application/json' \\",
        '  -H "Authorization: Bearer ${API01_TOKEN}" \\',
        '  --data-binary "@${PAYLOAD}"',
        "",
    ])


def write_case_files():
    """只重建当前五个必测实例，避免把归档用例带回活动目录。"""
    PAYLOAD_DIR.mkdir(parents=True, exist_ok=True)
    CURL_DIR.mkdir(parents=True, exist_ok=True)
    for previous in PAYLOAD_DIR.glob("*.json"):
        previous.unlink()
    for previous in CURL_DIR.glob("*.sh"):
        previous.unlink()

    manifest = []
    for case_id, title, payload in cases():
        stem = case_id.lower().replace("-", "_")
        payload_path = PAYLOAD_DIR / (stem + ".json")
        payload_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
        )
        curl_path = CURL_DIR / (stem + ".sh")
        curl_path.write_text(_curl_script(stem), encoding="utf-8")
        curl_path.chmod(0o755)
        record = {
            "package_version": "v3",
            "id": case_id,
            "title": title,
            "payload": "test_data/payloads/" + payload_path.name,
            "curl": "test_data/curl/" + curl_path.name,
        }
        if case_id == "HVR01-29":
            record["precondition"] = "API07 Owner A 的成品、半成品及原材料变体已存在"
        elif case_id == "HVR01-33":
            record["depends_on"] = ["HVR01-29"]
        manifest.append(record)

    (ROOT / "case_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )


if __name__ == "__main__":
    write_case_files()
    print("已重建 %s 个 API01 必需 HVR 报文和 curl 脚本。" % len(cases()))

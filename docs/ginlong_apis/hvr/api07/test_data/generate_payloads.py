"""生成 API07 HVR 的独立 JSON 请求文件和可执行 curl 脚本。"""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PAYLOAD_DIR = ROOT / "payloads"
CURL_DIR = ROOT / "curl"
RUN = "HVR07-20261119"
OWNER_A = RUN + "-OWNER-A"
OWNER_B = RUN + "-OWNER-B"


def product_payload(owner, code, name, form="原材料", unit="台", spec="HVR07-MODEL", **optional):
    """构造符合 API07 字段形状的 JSON 对象。"""
    payload = {
        "action": "Add",
        "owner": owner,
        "productCode": code,
        "productName": name,
        "specificationModel": spec,
        "unit": unit,
        "productForm": form,
    }
    payload.update(optional)
    return payload


def cases():
    """返回按 HVR 顺序排列的案例及可直接发送的请求报文。"""
    raw = product_payload(
        OWNER_A, RUN + "-RAW-A", "HVR07 原材料产品", "原材料", "台",
        "HVR07-RAW-MODEL", power="5kW", nationalStandard="HVR07-STD",
        certificationModel="HVR07-CERT", weight=0, length=0, width=0, height=0,
    )
    repeat_seed = product_payload(
        OWNER_A, RUN + "-EDIT-REPEAT", "HVR07 重复编辑基准产品", "半成品", "台",
        "HVR07-REPEAT-MODEL", power="3kW", weight=2.5, length=100, width=60, height=40,
    )
    edit_name = product_payload(
        OWNER_A, RUN + "-EDIT-NAME", "HVR07 修改后名称", "原材料", "台",
        "HVR07-EDITED-MODEL", power="1kW", weight=1.25, length=100, width=50, height=40,
    )
    edit_name["action"] = "Edit"
    edit_unit = product_payload(
        OWNER_A, RUN + "-EDIT-NAME", "HVR07 修改后名称", "原材料", RUN + "-UNIT-ALT",
        "HVR07-EDITED-MODEL", power="1kW-edited", weight=4.25,
        length=110, width=55, height=45,
    )
    edit_unit["action"] = "Edit"
    no_user = product_payload(
        OWNER_A, RUN + "-NO-API-USER", "HVR07 无 API User 权限探针", "原材料", "台",
        "HVR07-NO-USER-MODEL",
    )
    invalid_token = product_payload(
        OWNER_A, RUN + "-INVALID-TOKEN", "HVR07 无效 Token 探针", "原材料", "台",
        "HVR07-INVALID-TOKEN-MODEL",
    )

    missing_owner = dict(raw)
    missing_owner.pop("owner")
    null_owner = dict(raw, owner=None, productCode=RUN + "-NULL-OWNER")
    empty_code = dict(raw, productCode="")
    blank_name = dict(raw, productCode=RUN + "-BLANK-NAME", productName="   ")
    null_form = dict(raw, productCode=RUN + "-NULL-FORM", productForm=None)
    bad_weight = dict(raw, productCode=RUN + "-BAD-WEIGHT", weight="abc")
    bad_varchar_type = dict(raw, productCode=RUN + "-BAD-VARCHAR-TYPE", productName=12345)
    bad_form_type = dict(raw, productCode=RUN + "-BAD-FORM-TYPE", productForm=7)
    bad_form = dict(raw, productCode=RUN + "-BAD-FORM", productForm="包装物")
    bad_unit = product_payload(
        OWNER_A, RUN + "-RETRY", "HVR07 单位修正重试产品", "原材料", "HVR07-NO-SUCH-UOM",
        "HVR07-RETRY-MODEL", weight=1.5,
    )
    corrected_unit = dict(bad_unit, unit="台")

    owner_b_same = dict(raw, owner=OWNER_B)
    # Owner B 已通过 HVR07-03 建档，此处用 Edit 验证同码模板共享属性冲突。
    owner_b_conflict = dict(raw, owner=OWNER_B, action="Edit", productForm="成品")

    semi = product_payload(
        OWNER_A, RUN + "-SEMI-A", "HVR07 半成品产品", "半成品", "台",
        "HVR07-SEMI-MODEL", power="3kW", weight=2.25,
    )
    finished = product_payload(
        OWNER_A, RUN + "-FIN-A", "HVR07 成品产品", "成品", "台",
        "HVR07-FIN-MODEL", power="5kW", weight=5.75,
    )

    return [
        ("HVR07-01", "新增原材料", raw, "valid"),
        ("HVR07-02", "重复提交完全相同的 Add", raw, "valid"),
        ("HVR07-03", "相同 productCode 由第二货主创建变体", owner_b_same, "valid"),
        ("HVR07-04", "同码跨货主 productForm 冲突", owner_b_conflict, "valid"),
        ("HVR07-05", "半成品映射到 serial tracking", semi, "valid"),
        ("HVR07-06", "成品映射到 serial tracking", finished, "valid"),
        ("HVR07-07", "同一产品多次 Edit，修改名称和规格", edit_name, "valid"),
        ("HVR07-08", "Edit 修改单位和可选物料属性", edit_unit, "valid"),
        ("HVR07-09", "相同 Payload 重复 Edit", dict(repeat_seed, action="Edit"), "valid"),
        ("HVR07-10", "不存在的单位导致失败", bad_unit, "valid"),
        ("HVR07-11", "修正单位后使用同一业务键重试", corrected_unit, "valid"),
        ("HVR07-12", "拒绝不支持的 productForm 枚举", bad_form, "valid"),
        ("HVR07-13", "必填 owner 缺失", missing_owner, "valid"),
        ("HVR07-14", "必填 owner 为 null", null_owner, "valid"),
        ("HVR07-15", "必填 productCode 为空字符串", empty_code, "valid"),
        ("HVR07-16", "必填 productName 为空白", blank_name, "valid"),
        ("HVR07-17", "必填 productForm 为 null", null_form, "valid"),
        ("HVR07-18", "DECIMAL weight 使用非法文本", bad_weight, "valid"),
        ("HVR07-19", "VARCHAR productName 使用数字类型", bad_varchar_type, "blocked"),
        ("HVR07-20", "productForm 使用数字类型", bad_form_type, "valid"),
        ("HVR07-21", "无效 Bearer Token", invalid_token, "invalid_token"),
        ("HVR07-22", "Token 有效但 API User 未配置 WMS Project", no_user, "no_api_user"),
    ]


def write_case_files():
    """输出 JSON、清单及每实例可执行的 curl 脚本。"""
    PAYLOAD_DIR.mkdir(parents=True, exist_ok=True)
    CURL_DIR.mkdir(parents=True, exist_ok=True)
    manifest = []
    for case_id, title, payload, auth_mode in cases():
        stem = case_id.lower().replace("-", "_")
        payload_path = PAYLOAD_DIR / (stem + ".json")
        payload_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        continuation = "\\"
        if auth_mode == "invalid_token":
            auth_line = "  -H 'Authorization: HVR07-INVALID-TOKEN' " + continuation
        elif auth_mode == "no_api_user":
            auth_line = '  -H "Authorization: ${API07_NO_API_USER_TOKEN}" ' + continuation
        else:
            auth_line = '  -H "Authorization: ${API07_TOKEN}" ' + continuation
        curl = "\n".join([
            "#!/usr/bin/env bash",
            "set -euo pipefail",
            'TEST_DATA_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"',
            'source "${TEST_DATA_DIR}/.api07_hvr.env"',
            f'PAYLOAD="${{TEST_DATA_DIR}}/payloads/{stem}.json"',
            "curl --silent --show-error --include --request POST " + continuation,
            '  "${API07_BASE_URL}/api/ginlong/TPL_Product_Master" ' + continuation,
            "  -H 'Content-Type: application/json' " + continuation,
            "  -H 'Accept: application/json' " + continuation,
            auth_line,
            '  --data-binary "@${PAYLOAD}"',
            "",
        ])
        curl_path = CURL_DIR / (stem + ".sh")
        curl_path.write_text(curl, encoding="utf-8")
        curl_path.chmod(0o755)
        manifest.append({
            "id": case_id,
            "title": title,
            "payload": "test_data/payloads/" + payload_path.name,
            "curl": "test_data/curl/" + curl_path.name,
            "auth_mode": auth_mode,
        })

    # HVR07-02 是一个人工验收实例，内含相同报文和改动报文两次重复 Add 子步骤。
    duplicate_case = cases()[0][2]
    changed_duplicate = dict(
        duplicate_case,
        productName="HVR07 重复新增变更报文，不应覆盖原档案",
        weight=999,
    )
    changed_payload_name = "hvr07_02_changed.json"
    changed_curl_name = "hvr07_02_changed.sh"
    (PAYLOAD_DIR / changed_payload_name).write_text(
        json.dumps(changed_duplicate, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    changed_curl = (CURL_DIR / "hvr07_02.sh").read_text(encoding="utf-8").replace(
        "hvr07_02.json", changed_payload_name,
    )
    changed_curl_path = CURL_DIR / changed_curl_name
    changed_curl_path.write_text(changed_curl, encoding="utf-8")
    changed_curl_path.chmod(0o755)
    manifest[1]["additional_requests"] = [{
        "payload": "test_data/payloads/" + changed_payload_name,
        "curl": "test_data/curl/" + changed_curl_name,
        "purpose": "同一 owner + productCode、不同 Payload 的重复 Add 也必须失败",
    }]
    (ROOT / "case_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print("生成 %s 个 API07 JSON Payload 和 curl 脚本。" % len(manifest))


if __name__ == "__main__":
    write_case_files()

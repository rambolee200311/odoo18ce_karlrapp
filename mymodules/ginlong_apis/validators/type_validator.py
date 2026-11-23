"""独立依据 V3.2 Q 列检查字段类型，不修改或转换 Payload。"""

import math
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

from .field_config import action_for, action_matches, get_field_rules


class FieldTypeValidationError(ValueError):
    """包含 API、方向、字段路径和类型原因的异常。"""

    def __init__(self, api_code, direction, issues):
        """保存一组字段类型错误。

        参数：
            api_code: Ginlong API 编号。
            direction: request 或 response。
            issues: 具体字段路径和类型错误列表。
        """
        self.api_code = api_code
        self.direction = direction
        self.issues = tuple(issues)
        super().__init__("%s %s field-type check failed: %s" % (
            api_code, direction, "; ".join(issues),
        ))


def _decimal_error(value, rule):
    """验证十进制格式和 DECIMAL 精度，不把数值转换回 Payload。"""
    if isinstance(value, bool):
        return "must not be a boolean"
    if not isinstance(value, (int, float, str, Decimal)):
        return "must be a decimal number or numeric string"
    if isinstance(value, str) and not re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)", value):
        return "must be a decimal number or numeric string"
    if isinstance(value, float) and not math.isfinite(value):
        return "must be finite"
    try:
        number = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return "must be a decimal number or numeric string"
    if not number.is_finite():
        return "must be finite"

    precision = rule.get("precision")
    scale = rule.get("scale")
    fraction_digits = max(-number.as_tuple().exponent, 0)
    integer_digits = max(number.adjusted() + 1, 0) if number else 0
    if scale is not None and fraction_digits > scale:
        return "exceeds DECIMAL scale %s" % scale
    if precision is not None and scale is not None and integer_digits > precision - scale:
        return "exceeds DECIMAL precision %s,%s" % (precision, scale)
    return None


def _check_value(value, rule, path, issues):
    """按静态字段规则检查已提供的值，不转换或修复输入。"""
    # 缺失值由字段遍历逻辑跳过；null 和空串也表示未提供，不进入类型判断。
    # 只按类型判断这两种空值，避免把数值 0 或布尔 false 当成空值跳过。
    if value is None or (isinstance(value, str) and value == ""):
        return

    q_type = rule.get("q_type")
    normalized_type = q_type.upper().split("(", 1)[0] if isinstance(q_type, str) else q_type
    if normalized_type in {"VARCHAR", "CHAR", "TEXT", None}:
        return
    if normalized_type == "DECIMAL":
        reason = _decimal_error(value, rule)
        if reason:
            issues.append("%s %s" % (path, reason))
        return
    if normalized_type == "BOOLEAN":
        if isinstance(value, bool):
            return
        accepted_strings = rule.get("boolean_values", {})
        if isinstance(value, str) and isinstance(accepted_strings, dict):
            case_insensitive = rule.get("boolean_case_insensitive", True)
            candidate = value.casefold() if case_insensitive else value
            configured = accepted_strings.get("true", []) + accepted_strings.get("false", [])
            configured = [item.casefold() if case_insensitive else item for item in configured]
            if candidate in configured:
                return
        issues.append("%s must be a JSON boolean" % path)
        return
    if normalized_type == "DATETIME":
        if not isinstance(value, str):
            issues.append("%s must be a DateTime string" % path)
            return
        expected_format = rule.get("format", "%Y-%m-%d %H:%M:%S")
        try:
            parsed = datetime.strptime(value, expected_format)
            if parsed.strftime(expected_format) != value:
                raise ValueError("DateTime is not in its canonical format")
        except ValueError:
            issues.append("%s must use the configured DateTime format %s" % (path, expected_format))
        return
    issues.append("%s has unsupported configured Q type %r" % (path, q_type))


def _check_fields(data, fields, prefix, action, issues):
    """校验对象中已经提供的字段；非必填缺失字段不报错。"""
    for rule in fields:
        actions = rule.get("actions")
        if actions and not action_matches(actions, action):
            continue
        name = rule["name"]
        if name not in data:
            continue
        path = "%s.%s" % (prefix, name) if prefix else name
        _check_value(data[name], rule, path, issues)


def _check_collections(data, collections, prefix, action, issues):
    """递归检查数组内每个已提供字段的类型。"""
    for collection in collections:
        name = collection["name"]
        required_on = collection.get("required_on", [])
        validate_on = collection.get("validate_on", ["*"])
        if not (
            action_matches(validate_on, action)
            or action_matches(required_on, action)
        ) or name not in data or not isinstance(data[name], list):
            continue
        item_schema = collection.get("items", {})
        for index, item in enumerate(data[name]):
            if not isinstance(item, dict):
                continue
            item_path = "%s.%s[%s]" % (prefix, name, index) if prefix else "%s[%s]" % (name, index)
            _check_fields(item, item_schema.get("fields", []), item_path, action, issues)
            _check_collections(item, item_schema.get("collections", []), item_path, action, issues)


def validate_field_types(api_code, payload, direction="request"):
    """按 Q 列验证非空字段的类型，允许 DECIMAL 数字字符串且不改 Payload。

    参数：
        api_code: API01–API10 编号。
        payload: 请求或响应对象；不会被修改。
        direction: request 或 response。

    返回：
        类型有效时返回 None；否则抛出 FieldTypeValidationError。
    """
    if direction not in {"request", "response"}:
        raise ValueError("direction must be 'request' or 'response'")
    api_config = get_field_rules()["apis"].get(api_code)
    if not api_config:
        raise ValueError("Unsupported Ginlong API code: %s" % api_code)
    if not isinstance(payload, dict):
        raise FieldTypeValidationError(api_code, direction, ["Payload must be a JSON object"])

    schema = api_config[direction]
    action = action_for(api_config, payload)
    issues = []
    _check_fields(payload, schema.get("fields", []), "", action, issues)
    _check_collections(payload, schema.get("collections", []), "", action, issues)
    if issues:
        raise FieldTypeValidationError(api_code, direction, issues)

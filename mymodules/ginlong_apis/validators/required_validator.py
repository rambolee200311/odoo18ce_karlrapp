"""独立检查 Ginlong Payload 必填字段和嵌套结构。"""

from .field_config import action_for, action_matches, get_field_rules


class RequiredFieldError(ValueError):
    """包含接口方向、字段路径和必填错误原因的异常。"""

    def __init__(self, api_code, direction, issues):
        """保存所有发现的必填错误。

        参数：
            api_code: Ginlong API 编号。
            direction: request 或 response。
            issues: 具体字段路径和错误原因列表。
        """
        self.api_code = api_code
        self.direction = direction
        self.issues = tuple(issues)
        super().__init__("%s %s required-field check failed: %s" % (
            api_code, direction, "; ".join(issues),
        ))


def _blank(value):
    """判断必填值是否为空；false、0、空数组和空对象仍属于已提供的值。"""
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    return False


def _check_fields(data, fields, prefix, action, issues):
    """检查当前对象的必填字段，不执行类型判断或值转换。"""
    for rule in fields:
        if not rule.get("required"):
            continue
        actions = rule.get("actions")
        if actions and not action_matches(actions, action):
            continue
        name = rule["name"]
        path = "%s.%s" % (prefix, name) if prefix else name
        if name not in data:
            issues.append("%s is missing" % path)
        elif _blank(data[name]):
            issues.append("%s is empty" % path)


def _check_collections(data, collections, prefix, action, issues):
    """递归检查数组容器、对象结构和数组内必填字段。"""
    for collection in collections:
        name = collection["name"]
        required_on = collection.get("required_on", [])
        validate_on = collection.get("validate_on", ["*"])
        if not (action_matches(validate_on, action) or action_matches(required_on, action)):
            continue

        path = "%s.%s" % (prefix, name) if prefix else name
        required = action_matches(required_on, action) or collection.get("required", False)
        if name not in data:
            if required:
                issues.append("%s is missing" % path)
            continue
        values = data[name]
        if values is None or values is False or values == "":
            if required:
                issues.append("%s is empty" % path)
            continue
        if not isinstance(values, list):
            issues.append("%s must be an array" % path)
            continue

        min_items = collection.get("min_items")
        if action_matches(collection.get("min_items_on", []), action):
            min_items = max(1, min_items or 0)
        if min_items is not None and len(values) < min_items:
            issues.append("%s must contain at least %s item(s)" % (path, min_items))

        for index, item in enumerate(values):
            item_path = "%s[%s]" % (path, index)
            if not isinstance(item, dict):
                issues.append("%s must be an object" % item_path)
                continue
            item_schema = collection.get("items", {})
            _check_fields(item, item_schema.get("fields", []), item_path, action, issues)
            _check_collections(item, item_schema.get("collections", []), item_path, action, issues)


def validate_required(api_code, payload, direction="request"):
    """按 O/V 列标记检查 Payload 必填字段且保留原对象不变。

    参数：
        api_code: API01–API10 编号。
        payload: 请求或响应对象；不会被修改。
        direction: request 检查 O 列，response 检查 V 列。

    返回：
        全部必填项有效时返回 None；否则抛出 RequiredFieldError。
    """
    if direction not in {"request", "response"}:
        raise ValueError("direction must be 'request' or 'response'")
    api_config = get_field_rules()["apis"].get(api_code)
    if not api_config:
        raise ValueError("Unsupported Ginlong API code: %s" % api_code)
    if not isinstance(payload, dict):
        raise RequiredFieldError(api_code, direction, ["Payload must be a JSON object"])

    schema = api_config[direction]
    action = action_for(api_config, payload)
    issues = []
    _check_fields(payload, schema.get("fields", []), "", action, issues)
    _check_collections(payload, schema.get("collections", []), "", action, issues)
    if issues:
        raise RequiredFieldError(api_code, direction, issues)

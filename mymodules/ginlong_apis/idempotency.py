"""按静态规则对 Ginlong 入站请求和出站事件实施事务型幂等处理。"""

import hashlib
import json
import logging
from functools import lru_cache
from pathlib import Path

from odoo import SUPERUSER_ID, api
from odoo.service.model import PG_CONCURRENCY_EXCEPTIONS_TO_RETRY
from psycopg2 import IntegrityError

from .errors import make_error

_logger = logging.getLogger(__name__)
_MISSING = object()
_VALID_STATES = {"succeeded", "failed", "unknown"}


class _BusinessRejected(Exception):
    """标记入站业务拒绝，回滚占位记录并保留业务错误响应。"""

    def __init__(self, result):
        """保存业务处理生成的失败响应。"""
        self.result = result


@lru_cache(maxsize=1)
def get_idempotency_rules():
    """加载独立的幂等策略 JSON，不依赖字段校验配置。"""
    path = Path(__file__).resolve().parent / "data" / "idempotency_rules.json"
    with path.open(encoding="utf-8") as rules_file:
        return json.load(rules_file)


def _canonical_json(value):
    """以确定性键序和紧凑格式序列化值，供指纹及复合键使用。"""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _path_value(root, path):
    """按配置路径读取嵌套对象；支持 ``items[].code`` 形式的数组路径。"""
    tokens = path.split(".") if isinstance(path, str) else list(path)

    def descend(value, remaining):
        if not remaining:
            return value
        token = remaining[0]
        if token.endswith("[]"):
            key = token[:-2]
            collection = value.get(key, _MISSING) if isinstance(value, dict) else _MISSING
            if not isinstance(collection, list):
                raise ValueError("Idempotency key path %s must contain an array" % path)
            return [descend(item, remaining[1:]) for item in collection]
        child = value.get(token, _MISSING) if isinstance(value, dict) else _MISSING
        if child is _MISSING:
            raise ValueError("Idempotency key path %s is missing" % path)
        return descend(child, remaining[1:])

    result = descend(root, tokens)
    if result is _MISSING or result is None or result == "":
        raise ValueError("Idempotency key path %s is empty" % path)
    return result


def _api_rules(api_code, direction=None):
    """读取指定接口策略并核对方向，未知接口保持显式失败。"""
    config = get_idempotency_rules().get("apis", {}).get(api_code)
    if not config:
        raise ValueError("No Ginlong idempotency rules configured for %s" % api_code)
    configured_direction = config.get("direction")
    if direction and configured_direction != direction:
        raise ValueError("%s idempotency direction must be %s" % (api_code, configured_direction))
    return config


def _action_key(config, payload):
    """按策略配置规范化 Action 别名；不改写传入 Payload。"""
    action_path = config.get("action_path")
    if not action_path:
        return None
    try:
        value = _path_value(payload, action_path)
    except ValueError:
        return None
    if not isinstance(value, str):
        return None
    normalized = value.strip().casefold()
    return config.get("action_aliases", {}).get(normalized, normalized)


def _business_key(api_code, payload):
    """根据 JSON 中配置的业务键路径提取接口级入站键。"""
    config = _api_rules(api_code, "inbound")
    paths = config.get("key_paths", [])
    values = [_path_value(payload, path) for path in paths]
    if not values:
        raise ValueError("No persistent business key configured for %s" % api_code)
    if len(values) == 1:
        return str(values[0])
    return _canonical_json(values)


def has_successful_once_for_business_key(env, api_code, payload):
    """检查一次性入站业务键是否已有成功记录，不要求请求指纹相同。

    参数：
        env: 当前 Odoo Environment。
        api_code: 配置为入站接口的 Ginlong API 编号。
        payload: 已完成字段校验和 Action 规范化的请求。

    返回：
        当该业务键和 Action 已有成功的一次性处理记录时返回 True。

    该检查用于业务层需要将“相同对象重复新增”作为冲突处理的场景；
    它与通用的同指纹重放检查分开，使孤立的成功幂等记录也不会伪装成新建成功。
    """
    config = _api_rules(api_code, "inbound")
    action = _action_key(config, payload)
    if not action:
        return False
    strategy = config.get("actions", {}).get(action, config.get("default_strategy", "once"))
    if strategy != "once":
        return False

    domain = [
        ("api_code", "=", api_code),
        ("direction", "=", "inbound"),
        ("business_key", "=", _business_key(api_code, payload)),
        ("action", "=", action),
        ("state", "=", "succeeded"),
    ]
    return bool(env["ginlong.api.idempotency"].sudo().search(domain, limit=1))


def duplicate_error_for_completed_request(env, api_code, payload):
    """按接口幂等配置生成已成功业务键的重复操作错误。

    参数：
        env: 当前 Odoo Environment。
        api_code: Ginlong API 编号。
        payload: 已校验且已规范化 Action 的请求报文。

    返回：
    若无业务生命周期适配器且配置的 Action 已有成功记录，返回统一错误对象；否则返回 None。

    此策略按业务键而非请求指纹判重，确保 Add 的修改版重发也不会覆盖原单。
    有生命周期适配器时，由其先检查业务记录有效性；不能用历史记录代替当前业务状态。
    """
    config = _api_rules(api_code, "inbound")
    action = _action_key(config, payload)
    error_code = config.get("duplicate_action_errors", {}).get(action)
    if not action or not error_code or not config.get("duplicate_by_history", False):
        return None
    strategy = config.get("actions", {}).get(action, config.get("default_strategy", "once"))
    if strategy != "once":
        return None

    business_key = _business_key(api_code, payload)
    domain = [
        ("api_code", "=", api_code),
        ("direction", "=", "inbound"),
        ("business_key", "=", business_key),
        ("action", "=", action),
        ("state", "=", "succeeded"),
    ]
    if not env["ginlong.api.idempotency"].sudo().search(domain, limit=1):
        return None
    key_label = ", ".join(config.get("key_paths", []))
    return make_error(
        error_code,
        api_code=api_code,
        action=action,
        key=key_label,
        business_key=business_key,
    )


def _outbound_event_key(api_code, payload, context, config):
    """组合接口事件、业务单据、Action、版本及内容指纹，生成稳定事件标识。"""
    root = {"payload": payload, "context": context or {}}
    key_values = [_path_value(root, "context.%s" % path) for path in config.get("key_paths", [])]
    version_values = [_path_value(root, "context.%s" % path) for path in config.get("version_paths", [])]
    action_path = config.get("action_path")
    action = _path_value(root, action_path) if action_path else None
    if isinstance(action, str):
        action = action.strip().casefold()
    identity = {
        "api": api_code,
        "event": config["event"],
        "keys": key_values,
        "action": action,
        "version": version_values,
        # 子明细可能变化而父单据 write_date 不变；把 Payload 指纹纳入事件标识，
        # 让相同报文重试保持同一 ID，同时将已保存数据的不同版本作为独立事件。
        "payload_fingerprint": _fingerprint(payload),
    }
    digest = hashlib.sha256(_canonical_json(identity).encode("utf-8")).hexdigest()
    return "%s:%s:%s" % (api_code, config["event"], digest)


def _fingerprint(payload):
    """对实际请求或回传 Payload 计算稳定 SHA-256 指纹。"""
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _result_from_record(record):
    """读取幂等记录中已提交的响应；未完成占位不伪装成结果。"""
    if not record.response_json or record.response_json == "{}":
        return None
    return json.loads(record.response_json)


def _find_committed_result(env, domain):
    """使用新 Odoo 游标读取竞争事务提交的结果，绕过当前事务快照。"""
    with env.registry.cursor() as cr:
        replay_env = api.Environment(cr, SUPERUSER_ID, {})
        record = replay_env["ginlong.api.idempotency"].sudo().search(domain, limit=1)
        return _result_from_record(record) if record else None


def _run_once(env, api_code, direction, action, business_key, event_key, fingerprint, operation, existing=None):
    """在幂等记录与业务操作的同一 Odoo 事务中占位、执行并保存结果。"""
    model = env["ginlong.api.idempotency"].sudo()
    with env.cr.savepoint():
        if existing:
            if existing.state == "processing":
                raise make_error("IDM01", details="event is already processing")
            existing.write({
                "state": "processing",
                "response_json": "{}",
                "attempt_count": existing.attempt_count + 1,
            })
            record = existing
        else:
            record = model.create({
                "api_code": api_code,
                "direction": direction,
                "action": action or False,
                "business_key": business_key,
                "event_key": event_key or False,
                "request_fingerprint": fingerprint,
                "state": "processing",
                "attempt_count": 1,
                "response_json": "{}",
            })

        result = operation()
        if not isinstance(result, dict):
            raise TypeError("Ginlong idempotency operation must return a dictionary")

        if direction == "inbound":
            if not result.get("success"):
                raise _BusinessRejected(result)
            state = "succeeded"
        else:
            state = result.get("state")
            if state not in _VALID_STATES:
                raise ValueError("Outbound idempotency result state must be succeeded, failed, or unknown")

        record.write({"state": state, "response_json": _canonical_json(result)})
    return result


def execute(env, api_code, payload, operation, direction=None, context=None, lifecycle_resolver=None):
    """按配置执行一次性或可重复操作，并原子保存可重放结果。

    参数：
        env: 当前 Odoo Environment。
        api_code: Ginlong API 编号。
        payload: 已通过字段校验的请求或回传 Payload。
        operation: 实际业务处理或 HTTP 发送函数。
        direction: inbound 或 outbound；省略时使用静态配置方向。
        context: 出站事件来源模型、记录编号、业务键及版本字段。
        lifecycle_resolver: 可选业务适配器，签名为 resolver(env)；检查有效记录并返回不透明事件键。

    返回：
        首次执行结果或相同成功事件的已保存结果。repeatable Action 每次调用均执行。
    """
    config = _api_rules(api_code, direction)
    direction = config["direction"]
    if not config.get("persistent", True) or config.get("strategy") == "repeatable":
        return operation()

    action_root = {"payload": payload, "context": context or {}}
    action = _action_key(config, action_root if direction == "outbound" else payload)
    if direction == "inbound":
        business_key = _business_key(api_code, payload)
        strategy = config.get("actions", {}).get(action, config.get("default_strategy", "once"))
        if strategy == "repeatable":
            # 没有外部请求 ID 时，不能区分重试与再次执行相同修改；按契约每次执行。
            return operation()
        if strategy != "once":
            raise ValueError("Unsupported idempotency strategy %r for %s" % (strategy, api_code))
        # 业务有效性由 adapter 判断。没有 adapter 的通用调用使用稳定请求事件键，
        # 避免 NULL 唯一键在 PostgreSQL 中允许并发插入多个相同请求。
        event_key = lifecycle_resolver(env) if lifecycle_resolver else "request:%s" % hashlib.sha256(
            (api_code + ":" + business_key).encode("utf-8")
        ).hexdigest()
    else:
        strategy = config.get("strategy", "once")
        if strategy != "once":
            raise ValueError("Unsupported outbound idempotency strategy %r for %s" % (strategy, api_code))
        event_key = _outbound_event_key(api_code, payload, context or {}, config)
        business_key = event_key

    fingerprint = _fingerprint(payload)
    if direction == "inbound" and not lifecycle_resolver:
        # 通用调用缺少业务状态读取能力时，只能按配置的成功历史拒绝 Add；
        # Ginlong HTTP 入口总会传入 adapter，取消/归档后的新生命周期不会受历史记录阻断。
        duplicate_error = duplicate_error_for_completed_request(env, api_code, payload)
        if duplicate_error:
            raise duplicate_error
    domain = [
        ("api_code", "=", api_code),
        ("business_key", "=", business_key),
        ("event_key", "=", event_key or False),
        ("request_fingerprint", "=", fingerprint),
    ]
    model = env["ginlong.api.idempotency"].sudo()
    existing = model.search(domain, limit=1)
    if existing and existing.state == "succeeded":
        result = _result_from_record(existing)
        if result is None:
            raise make_error("IDM01", details="saved successful result is incomplete")
        return result

    try:
        return _run_once(
            env, api_code, direction, action, business_key, event_key,
            fingerprint, operation, existing=existing,
        )
    except _BusinessRejected as rejected:
        # 并发不同 Payload 可能各自取得幂等占位；失败方若观察到同业务键已成功，归类为重复新增。
        duplicate_error = (
            duplicate_error_for_completed_request(env, api_code, payload)
            if direction == "inbound" and not lifecycle_resolver else None
        )
        if duplicate_error:
            raise duplicate_error
        return rejected.result
    except PG_CONCURRENCY_EXCEPTIONS_TO_RETRY:
        raise
    except IntegrityError:
        # 同一事件的并发重试先尝试复用竞争事务已提交的结果。
        result = _find_committed_result(env, domain)
        if result is not None:
            return result
        # 只有 adapter 能确认当前业务身份已被占用时，才将数据库冲突翻译为重复业务键。
        # 其他 IntegrityError 仍保留原分类，避免把无关约束故障伪装成重复请求。
        if direction == "inbound" and lifecycle_resolver:
            # 有效键冲突可能发生在另一事务提交后；当前事务的快照无法看到新记录。
            # 新 ORM 游标让业务适配器判断是否确为重复有效键，避免泄露数据库异常。
            with env.registry.cursor() as cr:
                current_env = api.Environment(cr, SUPERUSER_ID, {})
                lifecycle_resolver(current_env)
        raise

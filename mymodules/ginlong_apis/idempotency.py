"""按静态规则对 Ginlong 入站请求和出站事件实施事务型幂等处理。"""

import hashlib
import json
import logging
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from pathlib import Path

from odoo import SUPERUSER_ID, api
from odoo.service.model import PG_CONCURRENCY_EXCEPTIONS_TO_RETRY
from psycopg2 import IntegrityError

from .errors import make_error

_logger = logging.getLogger(__name__)
_MISSING = object()
_VALID_STATES = {"succeeded", "failed", "unknown"}


def callback_now():
    """返回 Odoo Datetime 字段使用的 UTC naive 当前时间。"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


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


def _normalize_fingerprint_value(value, api_code=None, path=()):
    """规范化 JSON 表达，不修改原 Payload，也不改变字符串和数字的类型区别。"""
    if isinstance(value, dict):
        return {key: _normalize_fingerprint_value(item, api_code, path + (key,)) for key, item in value.items()}
    if isinstance(value, list):
        items = [_normalize_fingerprint_value(item, api_code, path) for item in value]
        config = get_idempotency_rules().get("apis", {}).get(api_code or "", {})
        unordered = set(config.get("unordered_array_paths", []))
        path_name = ".".join(path)
        if path_name in unordered:
            # 契约未赋予这些明细排列业务含义；排序只用于指纹，保留重复项且不改发送报文。
            items.sort(key=lambda item: json.dumps(
                item, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False,
            ))
        return items
    if isinstance(value, bool) or value is None or isinstance(value, (str, int)):
        return value
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("Non-finite numeric values are not valid JSON payloads")
        number = value.normalize()
        return int(number) if number == number.to_integral_value() else float(number)
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise ValueError("Non-finite numeric values are not valid JSON payloads")
        # JSON 的 1 与 1.0 表示同一数值；统一整数浮点，其他浮点使用稳定有效位。
        if value.is_integer():
            return int(value)
        try:
            return float(Decimal(str(value)).normalize())
        except (InvalidOperation, ValueError):
            return value
    return value


def _canonical_json(value, api_code=None):
    """使用稳定键序、数值表达和接口配置的无序明细规则序列化值。"""
    normalized = _normalize_fingerprint_value(value, api_code)
    return json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


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
    """组合接口事件、业务单据、Action、版本及按配置选择的指纹生成事件标识。"""
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
    }
    # 通常把 Payload 指纹纳入事件，使修改后的数据成为独立通知版本。
    # API04 明确以 Picking 作为一次完成事件，故其静态规则可关闭该部分，防止
    # 已成功 Picking 因后续数据改动而被当成新批次再次发送。
    if config.get("payload_fingerprint_in_event", True):
        identity["payload_fingerprint"] = _fingerprint(payload)
    digest = hashlib.sha256(_canonical_json(identity).encode("utf-8")).hexdigest()
    return "%s:%s:%s" % (api_code, config["event"], digest)


def _fingerprint(payload, api_code=None):
    """对 Payload 计算稳定 SHA-256 指纹；接口配置可声明业务无序明细数组。"""
    return hashlib.sha256(_canonical_json(payload, api_code=api_code).encode("utf-8")).hexdigest()


def callback_event_identity(api_code, payload, context):
    """生成回传事件的稳定业务身份及当前 Payload 指纹。

    稳定身份仅由接口、事件粒度、来源业务记录和 Action 构成；指纹单独标记
    该事件的业务内容版本。这样内容变更可作为新回传版本，但仍由同一协调记录
    串行化，避免不同用户或标签页对同一业务事件并发发送。
    """
    config = _api_rules(api_code, "outbound")
    root = {"payload": payload, "context": context or {}}
    keys = [_path_value(root, "context.%s" % path) for path in config.get("key_paths", [])]
    action = _path_value(root, config["action_path"]) if config.get("action_path") else None
    if isinstance(action, str):
        action = action.strip().casefold()
    identity = {"api": api_code, "event": config["event"], "keys": keys, "action": action}
    stable_key = hashlib.sha256(_canonical_json(identity).encode("utf-8")).hexdigest()
    return stable_key, _fingerprint(payload, api_code=api_code)


def _legacy_success_log(env, api_code, fingerprint, source_record):
    """按旧版 API Log 的来源、接口及报文指纹读取兼容成功记录。"""
    source_ref = "%s,%s" % (source_record._name, source_record.id)
    logs = env["world.depot.api.log"].sudo().search([
        ("ginlong_api_code", "=", api_code),
        ("source_record", "=", source_ref),
        ("success", "=", True),
    ], order="request_time asc, id asc")
    for log in logs:
        try:
            logged_payload = json.loads(log.request_data or "")
        except (TypeError, ValueError):
            continue
        if isinstance(logged_payload, dict) and _fingerprint(logged_payload, api_code=api_code) == fingerprint:
            return log
    return env["world.depot.api.log"]


def inspect_callback_event(env, api_code, payload, context, source_record, invoked_at=None):
    """读取当前业务事件的成功、失败、未知及并发状态，供回传按钮决定是否弹窗。"""
    stable_key, fingerprint = callback_event_identity(api_code, payload, context)
    model = env["ginlong.api.idempotency"].sudo()
    root = model.search([
        ("api_code", "=", api_code), ("direction", "=", "outbound"),
        ("coordination_key", "=", stable_key),
    ], limit=1)
    if root and root.active_execution:
        return {"state": "processing", "stable_key": stable_key, "fingerprint": fingerprint,
                "root_id": root.id, "generation": root.execution_generation}
    if root:
        # 其他 Worker 的发送事务尚未提交时，普通 ORM 读取只能看到上一次结果。
        # 通过新 ORM 游标对协调行执行无业务字段变化的写入探测：若另一个发送正在
        # 持有该行，探测会等待其事务完成；在快照冲突后读取最新代次，避免把旧成功
        # 状态误展示成“可重复回传”确认框。此探测不依赖用户、标签页或确认令牌。
        committed = _probe_callback_coordination(env, api_code, stable_key, root.execution_generation)
        if committed and committed.get("changed"):
            return {
                "state": "processing" if committed["active"] else "overlap",
                "stable_key": stable_key,
                "fingerprint": fingerprint,
                "root_id": committed["id"],
                "generation": committed["generation"],
            }
    events = model.search([
        ("api_code", "=", api_code), ("direction", "=", "outbound"),
        ("stable_event_key", "=", stable_key), ("request_fingerprint", "=", fingerprint),
        ("state", "!=", "processing"),
    ], order="id desc")
    if events:
        latest = events[0]
        return {
            "state": latest.state,
            "stable_key": stable_key,
            "fingerprint": fingerprint,
            "root_id": root.id if root else latest.id,
            "generation": root.execution_generation if root else 0,
            "event_id": latest.id,
            "completed_at": latest.last_completed_at or latest.write_date or latest.create_date,
            "response": _result_from_record(latest),
        }

    legacy_log = _legacy_success_log(env, api_code, fingerprint, source_record)
    if legacy_log:
        return {
            "state": "succeeded", "stable_key": stable_key, "fingerprint": fingerprint,
            "root_id": root.id if root else False,
            "generation": root.execution_generation if root else 0,
            "legacy_log_id": legacy_log.id,
            "completed_at": legacy_log.request_time,
            "response": {"response_text": legacy_log.response_data or legacy_log.data or "",
                         "error": legacy_log.exception_details or False},
        }
    return {"state": "new", "stable_key": stable_key, "fingerprint": fingerprint,
            "root_id": root.id if root else False,
            "generation": root.execution_generation if root else 0}


def _read_committed_coordination(env, api_code, stable_key):
    """在新 ORM 游标中读取竞争事务提交的协调状态，不执行 SQL。"""
    with env.registry.cursor() as cr:
        fresh_env = api.Environment(cr, SUPERUSER_ID, {})
        root = fresh_env["ginlong.api.idempotency"].sudo().search([
            ("api_code", "=", api_code), ("direction", "=", "outbound"),
            ("coordination_key", "=", stable_key),
        ], limit=1)
        if not root:
            return None
        return {
            "id": root.id,
            "generation": root.execution_generation,
            "active": root.active_execution,
            "completed_at": root.last_completed_at,
            "state": root.last_outcome_state or root.state,
        }


def _probe_callback_coordination(env, api_code, stable_key, observed_generation):
    """用 ORM 行更新探测竞争发送；若发送代次已变化则返回最新提交状态。"""
    try:
        with env.registry.cursor() as cr:
            fresh_env = api.Environment(cr, SUPERUSER_ID, {})
            root = fresh_env["ginlong.api.idempotency"].sudo().search([
                ("api_code", "=", api_code), ("direction", "=", "outbound"),
                ("coordination_key", "=", stable_key),
            ], limit=1)
            if not root:
                return None
            # 写入与当前值相反的临时布尔值，确保 ORM 发出 UPDATE 并取得行锁；
            # 同一事务随即回滚，因此探测不会持久改变 active_execution。
            root.write({"active_execution": not root.active_execution})
            root.flush_recordset(["active_execution"])
            state = {
                "id": root.id,
                "generation": root.execution_generation,
                "active": root.active_execution,
                "changed": root.execution_generation != observed_generation,
            }
            # 该 UPDATE 只作短暂行锁探测，不应改变协调记录的 write_date 或业务状态。
            cr.rollback()
            return state
    except PG_CONCURRENCY_EXCEPTIONS_TO_RETRY:
        # 在 Repeatable Read 下，等待中的 UPDATE 可能因首个发送已提交而触发
        # serialization failure；用新快照读取状态，通知调用层不弹重复确认框。
        committed = _read_committed_coordination(env, api_code, stable_key)
        if not committed:
            return None
        return {
            "id": committed["id"],
            "generation": committed["generation"],
            "active": committed["active"],
            "changed": committed["active"] or committed["generation"] != observed_generation,
        }


def _callback_execution_slot(stable_key, generation):
    """为稳定事件的一个执行代次生成数据库唯一槽位。"""
    return hashlib.sha256(("%s:%s" % (stable_key, generation)).encode("utf-8")).hexdigest()


def execute_callback_event(
    env, api_code, payload, context, source_record, operation, invoked_at=None,
    expected_generation=None, confirmation_token=None, confirmed_by_id=None,
    legacy_log_id=None, force_repeat=False,
):
    """串行执行 API02/04/06/08 的一个稳定业务事件，并追加确认后的独立 Event。

    返回字典包含 ``sent``、``state``、``result``、``record`` 及 ``reason``；
    竞争请求在等待期间发现同事件已完成时返回 ``sent=False``，不会生成 HTTP Log。
    """
    invoked_at = invoked_at or callback_now()
    stable_key, fingerprint = callback_event_identity(api_code, payload, context)
    model = env["ginlong.api.idempotency"].sudo()
    token = confirmation_token or False
    if token:
        reused = model.search([
            ("api_code", "=", api_code), ("confirmation_token", "=", token),
        ], limit=1)
        if reused:
            return {"sent": False, "state": reused.state, "record": reused,
                    "result": _result_from_record(reused), "reason": "confirmation_consumed"}

    try:
        with env.cr.savepoint():
            root = model.search([
                ("api_code", "=", api_code), ("direction", "=", "outbound"),
                ("coordination_key", "=", stable_key),
            ], limit=1)
            first_execution = False
            if not root:
                if legacy_log_id:
                    # 升级前的成功 API Log 作为历史锚点，首个新版本尝试另建有唯一槽位的 Event。
                    legacy_log = env["world.depot.api.log"].sudo().browse(legacy_log_id)
                    root = model.create({
                        "api_code": api_code, "direction": "outbound", "action": payload.get("action") or False,
                        "business_key": stable_key, "event_key": "root:%s" % fingerprint,
                        "stable_event_key": stable_key, "coordination_key": stable_key,
                        "request_fingerprint": fingerprint, "state": "succeeded", "attempt_count": 0,
                        "response_json": _canonical_json({
                            "state": "succeeded", "status_code": int(legacy_log.code or 0),
                            "response_text": legacy_log.response_data or legacy_log.data or "",
                            "error": False,
                        }),
                        "execution_generation": 0, "active_execution": False,
                        "last_completed_at": legacy_log.request_time,
                        "legacy_api_log_id": legacy_log.id,
                    })
                else:
                    # 首次按钮点击直接用根 Event 占用第 0 代槽位；数据库唯一约束使
                    # 同时到达的另一个事务只能在首个 HTTP 事务结束后被识别为过期代次。
                    root = model.create({
                        "api_code": api_code, "direction": "outbound", "action": payload.get("action") or False,
                        "business_key": stable_key, "event_key": "root:%s" % fingerprint,
                        "stable_event_key": stable_key, "coordination_key": stable_key,
                        "execution_slot": _callback_execution_slot(stable_key, 0),
                        "request_fingerprint": fingerprint, "state": "processing", "attempt_count": 1,
                        "response_json": "{}", "execution_generation": 1,
                        "active_execution": True, "last_started_at": invoked_at,
                        "last_completed_at": False,
                    })
                    first_execution = True
            else:
                if root.active_execution:
                    return {"sent": False, "state": "processing", "record": root,
                            "result": None, "reason": "processing"}
                if expected_generation is not None and root.execution_generation != expected_generation:
                    return {"sent": False, "state": "overlap", "record": root,
                            "result": None, "reason": "generation_changed"}

            if first_execution:
                record = root
            else:
                generation = root.execution_generation
                slot = _callback_execution_slot(stable_key, generation)
                # 同一代次无论报文、用户或令牌是否相同，都先竞争同一数据库唯一槽位。
                # 每次实际尝试使用独立 Event，失败/未知/成功历史均不被覆盖。
                prior = model.search([
                    ("api_code", "=", api_code), ("direction", "=", "outbound"),
                    ("stable_event_key", "=", stable_key),
                ], order="id desc", limit=1)
                if force_repeat:
                    prior_success = model.search([
                        ("api_code", "=", api_code), ("direction", "=", "outbound"),
                        ("stable_event_key", "=", stable_key),
                        ("request_fingerprint", "=", fingerprint), ("state", "=", "succeeded"),
                    ], order="id asc", limit=1)
                    parent = prior_success or root
                else:
                    parent = prior or root
                record = model.create({
                    "api_code": api_code, "direction": "outbound", "action": payload.get("action") or False,
                    "business_key": stable_key,
                    "event_key": "attempt:%s:%s" % (generation, fingerprint),
                    "stable_event_key": stable_key, "parent_event_id": parent.id,
                    "execution_slot": slot,
                    "request_fingerprint": fingerprint, "state": "processing", "attempt_count": 1,
                    "response_json": "{}", "confirmation_token": token,
                    "confirmed_by_id": confirmed_by_id or False,
                    "confirmed_at": invoked_at if confirmed_by_id else False,
                })
                root.write({
                    "execution_generation": generation + 1,
                    "active_execution": True,
                    "last_started_at": invoked_at,
                })

            # Odoo 会延迟 ORM 写入；必须在 HTTP 前落下唯一执行槽并锁定协调行，
            # 否则并发事务可能在请求发送之后才遇到唯一约束冲突，无法防止重复外发。
            record.flush_recordset()
            if root != record:
                root.flush_recordset([
                    "execution_generation", "active_execution", "last_started_at",
                ])

            result = operation()
            if not isinstance(result, dict) or result.get("state") not in _VALID_STATES:
                raise ValueError("Outbound callback operation must return a valid state")
            completed_at = callback_now()
            record.write({"state": result["state"], "response_json": _canonical_json(result),
                          "last_completed_at": completed_at})
            root.write({"active_execution": False, "last_completed_at": completed_at,
                        "last_outcome_state": result["state"]})
        return {"sent": True, "state": result["state"], "record": record,
                "result": result, "reason": "sent"}
    except (IntegrityError,) + PG_CONCURRENCY_EXCEPTIONS_TO_RETRY:
        # 唯一键/行更新冲突用于串行化同业务事件；以新 ORM 事务读取代次，避免
        # 把 Datetime 秒级精度当成点击先后顺序，也避免并发事务发送第二次 HTTP。
        committed = _read_committed_coordination(env, api_code, stable_key)
        observed_generation = expected_generation if expected_generation is not None else 0
        if committed and (committed["active"] or committed["generation"] != observed_generation):
            return {"sent": False, "state": "overlap", "record": False,
                    "result": None, "reason": "concurrent_event"}
        raise


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
    if direction == "outbound" and config.get("skip_successful_event", False):
        # 有些回传以业务事件而不是 Payload 版本作为唯一单位；如事件已成功，
        # 即使调用方报文内容改变，也返回原结果并禁止重发该事件。
        successful_event = env["ginlong.api.idempotency"].sudo().search([
            ("api_code", "=", api_code),
            ("direction", "=", "outbound"),
            ("event_key", "=", event_key or False),
            ("state", "=", "succeeded"),
        ], order="id desc", limit=1)
        if successful_event:
            result = _result_from_record(successful_event)
            if result is None:
                raise make_error("IDM01", details="saved successful event result is incomplete")
            return result
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

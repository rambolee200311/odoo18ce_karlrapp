"""根据持久化 WMS 实绩生成 Ginlong 回传报文并追加既有 API 日志。"""

import json
import logging
from urllib.parse import parse_qsl, quote, quote_plus, unquote, urlencode, urlsplit, urlunsplit

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.service.model import PG_CONCURRENCY_EXCEPTIONS_TO_RETRY

from .. import idempotency
from ..validators.required_validator import RequiredFieldError
from ..validators.type_validator import FieldTypeValidationError
from ..validators.payload_validator import validate_payload


_logger = logging.getLogger(__name__)
_HTTP_TIMEOUT = 15
_CALLBACK_ACTIONS = {
    "API02": {"update": "UPDATE"},
    "API04": {"create": "CREATE"},
    "API06": {"create": "CREATE"},
    "API08": {"create": "CREATE"},
    "API10": {"add": "Add", "del": "Del"},
}
_SENSITIVE_QUERY_KEYS = {
    "apikey", "key", "secret", "clientsecret", "token", "accesstoken",
    "password", "signature", "authorization", "auth", "credential",
}


def _canonical_action(api_code, value=None):
    """把用户保存的 Action 转成 Ginlong 契约要求的标准拼写。"""
    actions = _CALLBACK_ACTIONS[api_code]
    if api_code != "API10":
        return next(iter(actions.values()))
    action = actions.get((value or "").strip().casefold())
    if not action:
        raise UserError(_("API10 操作必须选择 Add 或 Del。"))
    return action


def _operation_time(value, label):
    """格式化已有作业时间；缺失值保留给统一校验器报告字段路径。"""
    return fields.Datetime.to_string(value) if value else value


def _decimal_string(value):
    """格式化 API06 已确认以 JSON string 发送的 DECIMAL 数值。

    `None` 和布尔 `False` 必须保留为缺失/非法值，不能折叠成合法的零。
    """
    if value is None or value is False:
        return value
    return ("%.6f" % float(value)).rstrip("0").rstrip(".") or "0"


def _api04_payload(order, picking):
    """从一张已完成入库 Picking 的 move line 生成 API04 实际入库报文。

    参数：
        order: 已保存的 WorldDepot 入库单。
        picking: 当前订单关联且已经完成的 incoming Picking。

    返回：
        包含订单号和 SN 明细的回传字典；明细字段直接读取实际 move line。
    """
    lines = picking.move_line_ids.filtered(lambda line: line.quantity > 0)
    if not lines:
        raise UserError(_("API04 入库作业单 %s 没有实际 move line。") % picking.display_name)
    operator = picking.ginlong_actual_inbound_operator_id
    if not operator:
        raise UserError(_("API04 入库作业单 %s 缺少实际确认人。") % picking.display_name)

    sn_list = []
    for line in lines:
        label = _("API04 move line %s") % (line.id,)
        package = line.result_package_id or line.package_id
        product_code = line.product_id.ginlong_product_code
        # 非 SN 产品没有单件序列号，按已确认的 Ginlong 规则用产品编码标识实际数量行。
        product_sn = product_code if line.product_id.tracking == "none" else line.lot_id.name
        values = {
            "productSN": product_sn,
            "quantity": line.quantity,
            "palletCode": package.name if package else False,
            "productCode": product_code,
            # V3.2 的操作人/时间按 SN 行提供；实际事实只有 Picking 级来源，因此重复该 Picking 的确认人和完成时间。
            "operator": operator.login,
            "operationTime": _operation_time(picking.date_done, label),
        }
        sn_list.append(values)
    return {
        "owner": order.ginlong_owner_code,
        "action": _canonical_action("API04"),
        "inboundOrderNo": order.reference,
        "snList": sn_list,
    }


def _api10_payload(order):
    """从客户盘点单关联的已选实盘结果生成 API10 报文，不查询库存台账。

    参数：
        order: 已保存的 WorldDepot 客户盘点单。

    返回：
        包含当前 Action 和已选实盘 SN 明细的回传字典。
    """
    action = _canonical_action("API10", order.ginlong_api10_action)
    results = order.result_ids.filtered("ginlong_callback_selected")
    if not results:
        raise UserError(_("API10 请先在 Ginlong 回传数据页选择本次实盘结果。"))

    sn_list = []
    for result in results:
        label = _("API10 实盘结果 %s") % (result.id,)
        product_sn = result.serial_number
        if result.product_id and result.product_id.tracking == "none":
            # 实盘仍以结果记录的数量和托盘为准；产品编码是协议标识，不是伪造的单件 SN。
            product_sn = result.product_code
        values = {
            "productSN": product_sn,
            "quantity": result.quantity,
            "palletCode": result.pallet_code,
            "productCode": result.product_code,
            "operator": result.ginlong_operator_code,
            "operationTime": _operation_time(result.operation_time, label),
        }
        sn_list.append(values)
    return {
        "owner": order.owner_code,
        "action": action,
        "countOrderNo": order.count_order_no,
        "snList": sn_list,
    }


def _api06_pickings(order):
    """按当前出库订单查找已完成的一步出库 Picking。

    参数：
        order: 已保存的 WorldDepot 出库单。

    返回：
        通过 `outbound_order_id` 关联、状态为 Done 且类型为 outgoing 的 Picking。
    """
    return order.env["stock.picking"].search([
        ("outbound_order_id", "=", order.id),
        ("state", "=", "done"),
        ("picking_type_id.code", "=", "outgoing"),
    ], order="id")


def _api06_payload(order):
    """从当前订单已完成 outgoing Picking 的作业行及汇总值生成 API06 报文。

    参数：
        order: 已保存的 WorldDepot 出库单。

    返回：
        包含订单号、托盘数量、总重量及实际备货明细的回传字典。
    """
    # 项目采用一步出库：实际 Done 的 outgoing Picking 已是本订单备货结果，
    # 无需再要求用户勾选回传范围。
    pickings = _api06_pickings(order)
    if not pickings:
        raise UserError(_("API06 当前出库单没有已完成的 outgoing Picking。"))
    lines = pickings.mapped("move_line_ids").filtered(lambda line: line.quantity > 0)
    if not lines:
        raise UserError(_("API06 找不到关联备货作业的实际 move line。"))

    sn_list = []
    for line in lines:
        label = _("API06 move line %s") % line.id
        product_code = line.product_id.ginlong_product_code
        # 非 SN 产品无论作业行是否带历史 Lot，都以产品编码表达实际数量。
        product_sn = product_code if line.product_id.tracking == "none" else line.lot_id.name
        values = {
            "productSN": product_sn,
            "quantity": line.quantity,
            "palletCode": line.package_id.name if line.package_id else False,
            "productCode": product_code,
            "operator": line.ginlong_operator_code,
            "operationTime": _operation_time(line.ginlong_operation_time, label),
        }
        sn_list.append(values)

    return {
        "owner": order.ginlong_owner_code,
        "action": _canonical_action("API06"),
        "outboundOrderNo": order.reference,
        "palletQty": _decimal_string(order.ginlong_pallet_qty),
        "totalWeight": _decimal_string(order.ginlong_total_weight),
        "snList": sn_list,
    }


def _details_confirmation_status(details, field_name, label):
    """把多条已保存明细折叠为单一订单状态，混合状态时拒绝发送。

    参数：
        details: 入库收货或出库发货明细记录集。
        field_name: 明细上的 Y/N 状态字段名。
        label: 用于错误提示的接口编号。

    返回：
        全部明细一致的 Y 或 N。
    """
    if not details:
        return None
    values = set(details.mapped(field_name))
    if len(values) > 1:
        raise UserError(_("%s 的明细状态不一致，尚不能生成单一订单级确认值。") % label)
    return values.pop()


def _api02_payload(order):
    """从入库 Order 的业务状态生成 API02 订单级确认报文。

    参数：
        order: 已保存的 WorldDepot 入库单。

    返回：
        含订单号、UPDATE Action 和状态映射结果的字典。
    """
    status_map = {"planning": "N", "arrive": "Y", "inbound": "Y"}
    confirmed = status_map.get(order.status)
    if confirmed is None:
        raise UserError(_("API02 入库单 %s 的收货状态无法映射：%s") % (order.display_name, order.status or "空值"))
    return {
        "inboundOrderNo": order.reference,
        "action": _canonical_action("API02"),
        "receiptConfirmed": confirmed,
    }


def _api08_payload(order):
    """从已离仓的出库 Order 生成订单级 API08 发货确认报文。

    参数：
        order: 已保存的 WorldDepot 出库单。

    返回：
        含订单号、CREATE Action 和发货确认值 Y 的字典。
    """
    if not _api06_pickings(order):
        raise UserError(_("API08 需要当前出库单存在已完成的 outgoing Picking。"))
    if order.status != "outbound":
        raise UserError(_("API08 需要出库单状态为 Outbound。"))
    return {
        "outboundOrderNo": order.reference,
        "action": _canonical_action("API08"),
        "shipmentConfirmed": "Y",
    }


def _build_payload(api_code, order):
    """按接口编号调用对应构造器，返回服务器端生成的 JSON 数据。

    参数：
        api_code: 五个人工回传接口之一。
        order: 当前回传来源的已保存业务单据。

    返回：
        与接口对应的 Python 字典，后续由 HTTP 客户端序列化为 JSON。
    """
    if api_code == "API04":
        raise UserError(_("API04 必须以单张实际入库 Picking 为回传单位。"))
    if api_code == "API06":
        return _api06_payload(order)
    if api_code == "API10":
        return _api10_payload(order)
    if api_code == "API02":
        return _api02_payload(order)
    if api_code == "API08":
        return _api08_payload(order)
    raise UserError(_("未知的 Ginlong 回传接口。"))


def _safe_endpoint_for_log(endpoint):
    """移除 Endpoint 用户信息并遮蔽 URL 中名称敏感的查询参数。

    参数：
        endpoint: 管理员配置的回传 URL。

    返回：
        可安全写入 API 日志的 URL；空输入返回空字符串。
    """
    if not endpoint:
        return ""
    parts = urlsplit(endpoint)
    host = parts.netloc.rsplit("@", 1)[-1]
    query = urlencode([
        (key, "[REDACTED]" if "".join(char for char in key.lower() if char.isalnum()) in _SENSITIVE_QUERY_KEYS else value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
    ])
    return urlunsplit((parts.scheme, host, parts.path, query, ""))


def _redact_endpoint_secrets(value, endpoint):
    """从错误或响应文本中清除 Endpoint 内的凭据及其 URL 编码形式。

    参数：
        value: 响应正文或异常文本。
        endpoint: 本次请求使用的 Endpoint。

    返回：
        已替换敏感值的文本。
    """
    if not value or not endpoint:
        return value or ""
    parts = urlsplit(endpoint)
    secrets = [unquote(item) for item in (parts.username, parts.password) if item]
    for key, item in parse_qsl(parts.query, keep_blank_values=True):
        normalized_key = "".join(char for char in key.lower() if char.isalnum())
        if normalized_key in _SENSITIVE_QUERY_KEYS and item:
            secrets.append(item)
    for secret in set(secrets):
        for encoded in {secret, quote(secret, safe=""), quote_plus(secret)}:
            if encoded:
                value = value.replace(encoded, "[REDACTED]")
    return value


def _write_api_log(order, api_code, endpoint, payload, response_text, status_code, error,
                   source_record=None, source_label=None, idempotency_record=None):
    """向现有 WorldDepot API 日志追加一次发送尝试及来源单据引用。

    参数：
        order: 发起回传的来源业务单据。
        api_code: Ginlong 回传接口编号。
        endpoint: 管理员配置的目标 URL。
        payload: 本次生成的业务报文；尚未生成时为 None。
        response_text: HTTP 响应正文。
        status_code: HTTP 状态码；未发送时为 None。
        error: 发送或业务错误文本。
        source_record: 可选的具体来源记录；API04 使用该 Picking 关联事件日志。
        source_label: 可选的业务来源标签，便于区分同一订单下的分批尝试。
    """
    project = getattr(order, "project_id", False) or getattr(order, "project", False)
    request_data = json.dumps(payload, ensure_ascii=False) if payload is not None else ""
    safe_endpoint = _safe_endpoint_for_log(endpoint)
    safe_response = _redact_endpoint_secrets(response_text or "", endpoint)
    safe_error = _redact_endpoint_secrets(error or "", endpoint)
    order.env["world.depot.api.log"].sudo().create({
        "project_id": project.id if project else False,
        "request_source": "Odoo user: %s" % order.env.user.login,
        "request_time": fields.Datetime.now(),
        "request_path": safe_endpoint,
        "source_record": "%s,%s" % ((source_record or order)._name, (source_record or order).id),
        "ginlong_idempotency_id": idempotency_record.id if idempotency_record else False,
        "request_data": request_data,
        "response_data": safe_response,
        "exception_details": safe_error or False,
        "status": "success" if status_code and 200 <= status_code < 300 and not safe_error else "error",
        "success": bool(status_code and 200 <= status_code < 300 and not safe_error),
        "code": str(status_code or "BLOCKED"),
        "msg": safe_error or (("%s：" % source_label) if source_label else "") +
               ("HTTP %s" % status_code if status_code else "%s 回传未发送" % api_code),
        "data": safe_response,
    })


def _response_error(response, api_code):
    """验证 HTTP 和 Ginlong JSON 成功状态，返回错误文本或 False。

    参数：
        response: `requests` 返回的 HTTP Response。

    返回：
        请求失败时的用户可见错误文本；成功时返回 False。
    """
    if not 200 <= response.status_code < 300:
        return _("Ginlong HTTP 返回状态 %s。") % response.status_code
    try:
        data = response.json()
    except (TypeError, ValueError):
        return _("Ginlong 响应不是有效 JSON。")
    if not isinstance(data, dict):
        return _("Ginlong 响应 JSON 必须是对象。")
    try:
        validate_payload(api_code, data, direction="response")
    except (RequiredFieldError, FieldTypeValidationError) as error:
        return str(error)
    return_status = str(data.get("returnStatus") or "").strip().casefold()
    if return_status != "y":
        return data.get("exceptionInfo") or _("Ginlong 未返回成功状态 returnStatus=Y。")
    return False


def _callback_context(order, api_code, source_record=None):
    """为回传事件生成不依赖 write_date 的稳定业务来源上下文。"""
    source_record = source_record or order
    source_key = (
        getattr(order, "reference", False)
        or getattr(order, "count_order_no", False)
        or str(order.id)
    )
    if api_code == "API04":
        source_key = "%s:%s" % (source_key, source_record.name or source_record.id)
    return {"source": {
        "model": source_record._name,
        "id": source_record.id,
        "business_key": source_key,
    }}


def _callback_candidates(order, api_code):
    """从现有业务记录收集事件；API04 保持每张 Picking 一个事件。"""
    if api_code != "API04":
        payload = _build_payload(api_code, order)
        validate_payload(api_code, payload, direction="request")
        return [{
            "source": order,
            "payload": payload,
            "context": _callback_context(order, api_code),
            "label": order.display_name,
        }]

    order.env.flush_all()
    pickings = order.env["stock.picking"].search([
        ("inbound_order_id", "=", order.id),
        ("state", "=", "done"),
        ("picking_type_id.code", "=", "incoming"),
    ], order="id")
    if not pickings:
        raise UserError(_("API04 当前入库单没有已完成的 incoming Picking。"))
    candidates = []
    for picking in pickings:
        candidate = {"source": picking, "payload": None,
                     "context": _callback_context(order, api_code, picking),
                     "label": picking.display_name}
        try:
            candidate["payload"] = _api04_payload(order, picking)
            validate_payload(api_code, candidate["payload"], direction="request")
        except Exception as exc:
            candidate["error"] = str(exc)
        candidates.append(candidate)
    return candidates


def _callback_outcome(response, api_code):
    """按 V3.2 回应证据区分确定成功、确定拒绝及结果未知。

    只有符合成功响应契约的 2xx/Y，以及明确返回 returnStatus=N 的拒绝
    才能定类；普通 HTTP 错误码或不完整回应不能证明对端没有处理请求。
    """
    try:
        data = response.json()
    except (TypeError, ValueError):
        data = None
    # 只有契约明确返回 N 才能确认 Ginlong 拒绝；超时、5xx 或无效响应均可能已处理。
    if isinstance(data, dict) and str(data.get("returnStatus") or "").strip().casefold() == "n":
        return {"state": "failed", "error": data.get("exceptionInfo") or _("Ginlong 明确拒绝本次回传。")}
    if response.status_code >= 500:
        return {"state": "unknown", "error": _("Ginlong HTTP 返回 5xx；对端是否处理无法确定。")}
    if not 200 <= response.status_code < 300:
        # 仅有 HTTP 状态码不能证明 Ginlong 业务 Handler 没有执行；只有协议明确的 N
        # 才分类为可直接重试的失败，其他非 2xx 都保留未知并交由用户确认。
        return {"state": "unknown", "error": _("Ginlong HTTP 返回状态 %s，无法确认对端是否处理。") % response.status_code}
    if not isinstance(data, dict):
        return {"state": "unknown", "error": _("Ginlong 已返回 HTTP 响应，但响应内容无法确认处理结果。")}
    try:
        validate_payload(api_code, data, direction="response")
    except (RequiredFieldError, FieldTypeValidationError) as exc:
        return {"state": "unknown", "error": _("Ginlong 响应不完整，无法确定对端处理结果：%s") % exc}
    return_status = str(data.get("returnStatus") or "").strip().casefold()
    if return_status == "y":
        return {"state": "succeeded", "error": False}
    return {"state": "unknown", "error": _("Ginlong 响应未能明确确认成功或拒绝。")}


def _candidate_snapshot(order, api_code, candidate, status):
    """仅保存来源引用和指纹，确认时重新从 ORM 读取并生成 Payload。"""
    identity = idempotency.inspect_callback_event(
        order.env, api_code, candidate["payload"], candidate["context"], candidate["source"],
    )
    return {
        "source_model": candidate["source"]._name,
        "source_id": candidate["source"].id,
        "label": candidate["label"],
        "stable_key": identity["stable_key"],
        "fingerprint": identity["fingerprint"],
        "state": status or identity["state"],
        "generation": identity.get("generation", 0),
        "legacy_log_id": identity.get("legacy_log_id") or False,
        "event_id": identity.get("event_id") or False,
        "completed_at": fields.Datetime.to_string(identity["completed_at"]) if identity.get("completed_at") else False,
        "response": identity.get("response") or {},
    }


def _callback_confirmation_action(order, api_code, candidates, classifications):
    """打开通用业务确认向导，供业务用户决定是否重复发送。"""
    event_rows = []
    display_lines = []
    for candidate, classification in zip(candidates, classifications):
        status = classification.get("state", "new")
        snapshot = _candidate_snapshot(order, api_code, candidate, status)
        event_rows.append(snapshot)
        when = snapshot.get("completed_at") or "无"
        result = classification.get("response") or {}
        error = (result.get("error") if isinstance(result, dict) else False) or ""
        response_text = result.get("response_text", "") if isinstance(result, dict) else ""
        response_summary = ""
        try:
            response_data = json.loads(response_text) if response_text else {}
            if isinstance(response_data, dict):
                response_summary = "; ".join(
                    "%s=%s" % (key, response_data[key])
                    for key in ("returnStatus", "exceptionInfo", "operationTime")
                    if response_data.get(key) not in (None, "")
                )
        except (TypeError, ValueError):
            response_summary = ""
        result_text = error or response_summary or ("已收到成功结果" if status == "succeeded" else "")
        display_lines.append("%s：%s；上次时间：%s%s" % (
            snapshot["label"], status, when, ("；结果：%s" % result_text) if result_text else "",
        ))
    multi = len(event_rows) > 1
    wizard = order.env["ginlong.api.callback.confirmation"].create({
        "api_code": api_code,
        "source_record": "%s,%s" % (order._name, order.id),
        "event_snapshots": json.dumps(event_rows, ensure_ascii=False, separators=(",", ":")),
        "event_summary": "\n".join("%s：%s" % (row["label"], row["state"]) for row in event_rows),
        "history_summary": "\n".join(display_lines),
        "multi_event": multi,
        "has_unknown": any(item.get("state") == "unknown" for item in classifications),
        "scope": "unsuccessful",
    })
    view = order.env.ref("ginlong_apis.view_ginlong_callback_confirmation_form")
    return {
        "type": "ir.actions.act_window",
        "name": _("确认 Ginlong 回传"),
        "res_model": wizard._name,
        "res_id": wizard.id,
        "views": [(view.id, "form")],
        "view_mode": "form",
        "target": "new",
    }


def _callback_chatter(order, api_code, decision, scope, labels):
    """将确认或取消决定追加至来源订单的 Chatter，不修改既有业务事实。"""
    if hasattr(order, "message_post"):
        order.message_post(body=_(
            "Ginlong %(api)s 回传确认：%(decision)s；范围：%(scope)s；对象：%(labels)s；用户：%(user)s；时间：%(time)s。"
        ) % {
            "api": api_code, "decision": decision, "scope": scope,
            "labels": ", ".join(labels), "user": order.env.user.display_name,
            "time": fields.Datetime.to_string(fields.Datetime.now()),
        })


def _send_callback_candidate(order, api_code, url, candidate, invoked_at,
                             expected_generation=None, confirmation_token=None,
                             force_repeat=False, legacy_log_id=None):
    """通过现有幂等记录串行发送一个业务事件，并将实际 HTTP 与 Event 关联。"""
    payload = candidate["payload"]
    def send_once():
        """执行单次 POST；传输异常不能证明接收方未处理，统一标记 unknown。"""
        try:
            response = requests.post(
                url, json=payload,
                headers={"Content-Type": "application/json"},
                timeout=_HTTP_TIMEOUT,
            )
        except (requests.exceptions.InvalidURL, requests.exceptions.InvalidSchema,
                requests.exceptions.MissingSchema, requests.exceptions.InvalidHeader) as exc:
            # 请求参数在连接建立前即被客户端拒绝，可确定对端没有收到报文。
            return {"state": "failed", "status_code": None, "response_text": "", "error": str(exc)}
        except requests.RequestException as exc:
            # 连接重置、读超时等可能发生在对端已处理之后，不能当作确定失败。
            return {"state": "unknown", "status_code": None, "response_text": "", "error": str(exc)}
        outcome = _callback_outcome(response, api_code)
        return {"state": outcome["state"], "status_code": response.status_code,
                "response_text": response.text or "", "error": outcome["error"]}

    execution = idempotency.execute_callback_event(
        order.env, api_code, payload, candidate["context"], candidate["source"], send_once,
        invoked_at=invoked_at, expected_generation=expected_generation,
        confirmation_token=confirmation_token, confirmed_by_id=order.env.user.id if confirmation_token else False,
        legacy_log_id=legacy_log_id, force_repeat=force_repeat,
    )
    if not execution["sent"]:
        return execution
    outcome = execution["result"]
    _write_api_log(
        order, api_code, url, payload, outcome.get("response_text") or "",
        outcome.get("status_code"), outcome.get("error") or False,
        source_record=candidate["source"], source_label=candidate["label"],
        idempotency_record=execution["record"],
    )
    return execution


def _process_confirmable_callbacks(order, api_code, url, candidates, invoked_at,
                                   selection=None, snapshots=None, confirmation_token=None,
                                   include_unknown=False, user_id=None):
    """对单事件或多事件执行统一判重、确认范围选择和实际发送。"""
    classifications = []
    for candidate in candidates:
        if candidate.get("error"):
            classifications.append({"state": "failed", "error": candidate["error"]})
            continue
        classifications.append(idempotency.inspect_callback_event(
            order.env, api_code, candidate["payload"], candidate["context"],
            candidate["source"], invoked_at=invoked_at,
        ))

    if selection is None:
        if any(item["state"] in {"succeeded", "unknown"} for item in classifications):
            return _callback_confirmation_action(order, api_code, candidates, classifications)
        if any(item["state"] in {"processing", "overlap"} for item in classifications) and not any(
            item["state"] in {"new", "failed"} for item in classifications
        ):
            _callback_chatter(order, api_code, "并发请求未重复发送", "当前回传", [c["label"] for c in candidates])
            return _callback_notification(_("同一回传事件正在处理或刚完成，本次没有再次发送。"), success=False)

    snapshot_by_key = {item["stable_key"]: item for item in (snapshots or [])}
    sent = 0
    skipped = 0
    failures = []
    for candidate, classification in zip(candidates, classifications):
        status = classification["state"]
        snapshot = snapshot_by_key.get(classification.get("stable_key"))
        if selection == "cancel":
            skipped += 1
            continue
        if selection == "unsuccessful" and status == "succeeded":
            skipped += 1
            continue
        if status in {"processing", "overlap"}:
            skipped += 1
            failures.append("%s：事件正在处理或刚完成，未重复发送" % candidate["label"])
            continue
        if status == "unknown" and not include_unknown:
            skipped += 1
            failures.append("%s：结果未知；未确认风险，已跳过" % candidate["label"])
            continue
        if status == "succeeded" and selection != "all" and not (snapshot and snapshot.get("state") == "succeeded"):
            skipped += 1
            continue
        if status == "succeeded" and selection is None:
            return _callback_confirmation_action(order, api_code, candidates, classifications)

        token = False
        force_repeat = False
        legacy_id = False
        expected_generation = None
        # 首次发送和失败重试也携带按钮判定时看到的事件代次，以阻止等待中的
        # 第二个事务在前一个请求提交后继续外发；不依赖秒级 Datetime 排序。
        if selection is None:
            expected_generation = classification.get("generation")
        if selection is not None and snapshot:
            expected_generation = snapshot.get("generation")
            # 只在用户明确选择全量重发，或确认当前成功/未知项时创建新 Event。
            force_repeat = status == "succeeded" or (
                status == "unknown" and include_unknown
            )
            if force_repeat:
                import hashlib as _hashlib
                token = _hashlib.sha256(
                    (confirmation_token + classification["stable_key"]).encode("utf-8")
                ).hexdigest()
                legacy_id = snapshot.get("legacy_log_id") or False
        execution = _send_callback_candidate(
            order, api_code, url, candidate, invoked_at,
            expected_generation=expected_generation, confirmation_token=token,
            force_repeat=force_repeat, legacy_log_id=legacy_id,
        )
        if execution["sent"]:
            sent += 1
            if execution["state"] != "succeeded":
                result = execution.get("result") or {}
                failures.append("%s：%s" % (candidate["label"], result.get("error") or execution["state"]))
        else:
            skipped += 1
            failures.append("%s：%s" % (candidate["label"], execution.get("reason") or execution["state"]))

    if selection == "cancel":
        _callback_chatter(order, api_code, "取消回传", selection, [c["label"] for c in candidates])
        return _callback_notification(_("已取消，本次没有发送 HTTP 请求。"), success=False)
    if selection is not None:
        _callback_chatter(order, api_code, "确认回传", selection, [c["label"] for c in candidates])
    message = _("本次实际发送 %(sent)s 个事件，未发送/跳过 %(skipped)s 个。") % {
        "sent": sent, "skipped": skipped,
    }
    if failures:
        message += "\n" + "\n".join(failures)
    return _callback_notification(message, success=not failures and sent > 0)


def _send_confirmable_callback(order, api_code, url):
    """处理 API02/04/06/08 的重复回传确认及稳定事件并发控制。"""
    invoked_at = idempotency.callback_now()
    try:
        if not url:
            raise UserError(_("请先由管理员配置该接口的完整 Endpoint URL。"))
        order.env.flush_all()
        candidates = _callback_candidates(order, api_code)
        invalid = [candidate for candidate in candidates if candidate.get("error")]
        for candidate in invalid:
            _write_api_log(
                order, api_code, url, candidate.get("payload"), "", None,
                candidate["error"], source_record=candidate["source"],
                source_label=candidate["label"],
            )
        candidates = [candidate for candidate in candidates if not candidate.get("error")]
        if not candidates:
            return _callback_notification(_("没有可发送的有效回传事件；请查看 API 日志。"), success=False)
        return _process_confirmable_callbacks(order, api_code, url, candidates, invoked_at)
    except PG_CONCURRENCY_EXCEPTIONS_TO_RETRY:
        raise
    except Exception as exc:
        error = _redact_endpoint_secrets(str(exc), url)
        _logger.exception("Ginlong callback %s failed before dispatch", api_code)
        _write_api_log(order, api_code, url, None, "", None, error)
        return _callback_notification(error, success=False)


def send_callback(order, api_code):
    """统一人工回传入口；API10 保留既有行为，其余四个接口启用确认机制。"""
    order.ensure_one()
    endpoint = order.env["res.config.settings"].get_ginlong_callback_endpoint(api_code)
    if api_code in {"API02", "API04", "API06", "API08"}:
        return _send_confirmable_callback(order, api_code, endpoint["url"])
    return _send_legacy_callback(order, api_code)


def _send_legacy_callback(order, api_code):
    """读取已保存 ORM 数据，同步 POST Ginlong 并记录本次结果。

    参数：
        order: 持久化的入库单、出库单或客户盘点单。
        api_code: API02、API04、API06、API08 或 API10。

    返回：
        Odoo 客户端通知 Action；每次按钮点击都会单独追加一条 API 日志。
    """
    order.ensure_one()
    endpoint = order.env["res.config.settings"].get_ginlong_callback_endpoint(api_code)
    url = endpoint["url"]
    if api_code == "API04":
        return _send_api04_pickings(order, url)
    payload = None
    response_text = ""
    status_code = None
    error = None
    try:
        if not url:
            raise UserError(_("请先由管理员配置该接口的完整 Endpoint URL。"))

        # 按钮只读取已保存的 ORM 记录，不接收前端未保存值；flush 确保先前的表单写入在本事务内可见。
        order.env.flush_all()
        payload = _build_payload(api_code, order)
        validate_payload(api_code, payload, direction="request")
        source_key = (
            getattr(order, "reference", False)
            or getattr(order, "count_order_no", False)
            or str(order.id)
        )
        event_context = {
            "source": {
                "model": order._name,
                "id": order.id,
                "business_key": source_key,
                "write_date": fields.Datetime.to_string(order.write_date) if order.write_date else "",
            },
        }

        def send_once():
            """发送一次真实 HTTP 请求并将明确失败与结果未知分开保存。"""
            try:
                response = requests.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=_HTTP_TIMEOUT,
                )
            except requests.RequestException as exc:
                # 请求超时或连接中断时，对端可能已收到报文；保留同一事件供人工安全重试。
                return {
                    "state": "unknown",
                    "status_code": None,
                    "response_text": "",
                    "error": str(exc),
                }
            response_body = response.text or ""
            response_error = _response_error(response, api_code)
            return {
                "state": "failed" if response_error else "succeeded",
                "status_code": response.status_code,
                "response_text": response_body,
                "error": response_error or False,
            }

        outcome = idempotency.execute(
            order.env,
            api_code,
            payload,
            send_once,
            direction="outbound",
            context=event_context,
        )
        status_code = outcome.get("status_code")
        response_text = outcome.get("response_text") or ""
        error = outcome.get("error") or False
    except PG_CONCURRENCY_EXCEPTIONS_TO_RETRY:
        # 并发重试交给 Odoo 请求事务层，防止转换成普通回传错误后继续提交。
        raise
    except (UserError, requests.RequestException, ValueError) as exc:
        error = str(exc)
        safe_url = _safe_endpoint_for_log(url)
        if url and safe_url != url:
            error = error.replace(url, safe_url)
        error = _redact_endpoint_secrets(error, url)
        _logger.info("Ginlong callback %s failed: %s", api_code, error)
    except Exception as exc:  # 未预期错误也需显示并为这次尝试追加日志。
        error = _redact_endpoint_secrets(str(exc), url)
        _logger.exception("Unexpected Ginlong callback error for %s", api_code)

    # 每次按钮点击都新增日志行；不覆盖或修改以前的发送记录。
    _write_api_log(order, api_code, url, payload, response_text, status_code, error)
    return {
        "type": "ir.actions.client",
        "tag": "display_notification",
        "params": {
            "title": _("Ginlong 回传结果"),
            "message": error or _("Ginlong 已确认接收。"),
            "type": "danger" if error else "success",
            "sticky": True,
        },
    }


def _send_api04_pickings(order, url):
    """保留旧内部调用名，但统一转入 API04 的通用回传确认流程。"""
    return _send_confirmable_callback(order, "API04", url)

def _callback_notification(message, success=False):
    """生成统一的 Odoo 客户端通知，显示本次回传操作结果。"""
    return {
        "type": "ir.actions.client",
        "tag": "display_notification",
        "params": {
            "title": _("Ginlong 回传结果"),
            "message": message,
            "type": "success" if success else "danger",
            "sticky": True,
        },
    }


class InboundOrder(models.Model):
    """为入库单提供 Ginlong 回传按钮和关联的实际入库作业单。"""

    _inherit = "world.depot.inbound.order"

    ginlong_stock_picking_ids = fields.One2many(
        "stock.picking", "inbound_order_id", string="Ginlong 入库作业单",
    )
    ginlong_api02_last_success = fields.Boolean(compute="_compute_ginlong_callback_status")
    ginlong_api02_last_time = fields.Datetime(compute="_compute_ginlong_callback_status")
    ginlong_api02_last_error = fields.Text(compute="_compute_ginlong_callback_status")
    ginlong_api04_last_success = fields.Boolean(compute="_compute_ginlong_callback_status")
    ginlong_api04_last_time = fields.Datetime(compute="_compute_ginlong_callback_status")
    ginlong_api04_last_error = fields.Text(compute="_compute_ginlong_callback_status")

    def _compute_ginlong_callback_status(self):
        """从既有 API Log 只读计算 API02/API04 最近一次尝试结果。"""
        log_model = self.env["world.depot.api.log"].sudo()
        for order in self:
            order_ref = "%s,%s" % (order._name, order.id)
            picking_refs = ["stock.picking,%s" % picking.id for picking in order.ginlong_stock_picking_ids]
            for api_code, refs in (
                ("API02", [order_ref]),
                ("API04", [order_ref] + picking_refs),
            ):
                log = log_model.search([
                    ("ginlong_api_code", "=", api_code),
                    ("source_record", "in", refs),
                ], order="request_time desc, id desc", limit=1) if refs else log_model
                order[f"ginlong_{api_code.lower()}_last_success"] = bool(log and log.success)
                order[f"ginlong_{api_code.lower()}_last_time"] = log.request_time if log else False
                order[f"ginlong_{api_code.lower()}_last_error"] = (
                    log.exception_details or False if log else False
                )

    def action_ginlong_api02(self):
        """手动发送当前入库单的收货确认状态。

        返回：
            显示本次同步回传成功或失败结果的客户端通知 Action。
        """
        return send_callback(self, "API02")

    def action_ginlong_api04(self):
        """手动发送当前入库单的所有合格 Picking 实际入库结果。

        返回：
            显示本次同步回传成功或失败结果的客户端通知 Action。
        """
        return send_callback(self, "API04")


class OutboundOrder(models.Model):
    """为出库单提供备货/发货回传字段、实际数量计算和按钮。"""

    _inherit = "world.depot.outbound.order"

    ginlong_stock_picking_ids = fields.One2many(
        "stock.picking", "outbound_order_id", string="Ginlong 出库作业单",
    )
    ginlong_pallet_qty_auto = fields.Float(
        string="实际托盘数（自动）", compute="_compute_ginlong_callback_totals",
    )
    ginlong_pallet_qty = fields.Float(
        string="回传托盘数", compute="_compute_ginlong_callback_totals",
    )
    ginlong_total_net_weight = fields.Float(
        string="实际净重（kg）", compute="_compute_ginlong_callback_totals",
    )
    ginlong_total_weight = fields.Float(
        string="回传总重量/毛重（kg）", compute="_compute_ginlong_callback_totals",
    )

    @api.depends(
        "ginlong_stock_picking_ids.state",
        "ginlong_stock_picking_ids.picking_type_id.code",
        "ginlong_stock_picking_ids.move_line_ids.package_id",
        "ginlong_stock_picking_ids.move_line_ids.quantity",
        "ginlong_stock_picking_ids.move_line_ids.product_id.product_tmpl_id.ginlong_weight",
        "ginlong_pallet_qty_manual_enabled", "ginlong_pallet_qty_manual",
        "ginlong_gross_weight_manual_enabled", "ginlong_gross_weight_manual",
    )
    def _compute_ginlong_callback_totals(self):
        """汇总当前出库单已完成 outgoing Picking 的托盘和重量，并应用人工覆盖值。"""
        for order in self:
            pickings = _api06_pickings(order)
            lines = pickings.mapped("move_line_ids").filtered(lambda line: line.quantity > 0)
            order.ginlong_pallet_qty_auto = len(set(lines.mapped("package_id").ids))
            order.ginlong_pallet_qty = (
                order.ginlong_pallet_qty_manual
                if order.ginlong_pallet_qty_manual_enabled
                else order.ginlong_pallet_qty_auto
            )
            order.ginlong_total_net_weight = sum(
                line.product_id.product_tmpl_id.ginlong_weight * line.quantity for line in lines
            )
            order.ginlong_total_weight = (
                order.ginlong_gross_weight_manual
                if order.ginlong_gross_weight_manual_enabled
                else order.ginlong_total_net_weight
            )

    def action_ginlong_api06(self):
        """手动发送当前出库单关联的 Done/outgoing Picking 备货结果。

        返回：
            显示本次同步回传成功或失败结果的客户端通知 Action。
        """
        return send_callback(self, "API06")

    def action_ginlong_api08(self):
        """在关联 outgoing Picking 已完成后确认订单离仓并回传 API08。

        本项目为一步出库：已完成的 outgoing Picking 已改变库存并构成实际作业依据。
        此按钮只把订单业务状态改为 outbound，再发送订单级 API08，不创建作业单、
        不维护重复发货明细，也不再次改变库存。

        返回：
            显示本次同步回传成功或失败结果的客户端通知 Action。
        """
        self.ensure_one()
        # Picking 未完成时不能确认订单离仓；send_callback 会按既有错误日志机制记录拒绝。
        if _api06_pickings(self):
            if self.status != "outbound":
                self.write({"status": "outbound"})
        return send_callback(self, "API08")


class StocktakeOrder(models.Model):
    """为客户盘点指令增加 API10 Action 和人工回传按钮。"""

    _inherit = "world.depot.stocktake.order"

    ginlong_api10_action = fields.Selection(
        [("Add", "Add"), ("Del", "Del")],
        string="Ginlong 回传 Action",
        default="Add",
        copy=False,
    )
    # 只让有效盘点指令占用全局 countOrderNo，取消历史继续保留。
    ginlong_effective_count_order_no = fields.Char(
        compute="_compute_ginlong_effective_count_order_no", store=True, index=True, copy=False,
    )

    _sql_constraints = [
        ("ginlong_effective_count_order_no_unique", "unique(ginlong_effective_count_order_no)",
         "An active stocktake order already uses this count order number."),
    ]

    @api.depends("count_order_no", "state")
    def _compute_ginlong_effective_count_order_no(self):
        """让未取消盘点单原子占用全局盘点编号。"""
        for order in self:
            order.ginlong_effective_count_order_no = (
                order.count_order_no if order.count_order_no and order.state != "cancel" else False
            )

    def action_ginlong_api10(self):
        """手动回传当前盘点单已选中的仓库实盘结果。

        返回：
            显示本次同步回传成功或失败结果的客户端通知 Action。
        """
        return send_callback(self, "API10")


class StockMoveLine(models.Model):
    """在实际作业行保存 Ginlong 报文所需的现场操作人编码和时间。"""

    _inherit = "stock.move.line"

    ginlong_operator_code = fields.Char(string="Ginlong 回传操作人员", copy=False)
    ginlong_operation_time = fields.Datetime(string="Ginlong 回传操作时间", copy=False)


class StockPicking(models.Model):
    """记录 API04 实际入库确认人，并保留 API06 所需 Picking 标记。"""

    _inherit = "stock.picking"

    ginlong_callback_selected = fields.Boolean(
        string="纳入本次 Ginlong 回传", default=False, copy=False,
    )
    ginlong_actual_inbound_operator_id = fields.Many2one(
        "res.users", string="实际入库确认人", readonly=True, copy=False, tracking=True,
    )

    def button_validate(self):
        """完成标准库存验证后记录实际入库确认用户。

        只有本次 `button_validate` 已使 incoming Picking 进入 `done` 才写入；
        历史值不覆盖，避免后续重复打开/验证把原确认人改成其他用户。
        """
        result = super().button_validate()
        completed = self.filtered(
            lambda picking: picking.state == "done"
            and picking.picking_type_id.code == "incoming"
            and picking.inbound_order_id
            and not picking.ginlong_actual_inbound_operator_id
        )
        if completed:
            completed.write({"ginlong_actual_inbound_operator_id": self.env.user.id})
        return result


class StocktakeResult(models.Model):
    """在既有仓库实盘结果上保存回传选择及外部操作人编码。"""

    _inherit = "world.depot.stocktake.result"

    ginlong_operator_code = fields.Char(string="Ginlong 回传操作人员", copy=False)
    ginlong_callback_selected = fields.Boolean(
        string="纳入本次 Ginlong 回传", default=False, copy=False,
    )

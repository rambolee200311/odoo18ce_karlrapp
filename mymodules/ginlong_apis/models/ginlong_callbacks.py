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


def _api04_payload(order):
    """从已保存并选中的入库 Picking/move line 生成 API04 实际入库报文。

    参数：
        order: 已保存的 WorldDepot 入库单。

    返回：
        包含订单号和 SN 明细的回传字典；明细字段直接读取实际 move line。
    """
    pickings = order.ginlong_stock_picking_ids.filtered("ginlong_callback_selected")
    if not pickings:
        raise UserError(_("API04 请先在 Ginlong 回传数据页选择本次入库作业单。"))
    lines = pickings.mapped("move_line_ids").filtered(lambda line: line.quantity > 0)
    if not lines:
        raise UserError(_("API04 找不到关联入库作业的实际 move line。"))

    sn_list = []
    for line in lines:
        label = _("API04 move line %s") % (line.id,)
        package = line.result_package_id or line.package_id
        values = {
            "productSN": line.lot_id.name,
            "quantity": line.quantity,
            "palletCode": package.name if package else False,
            "productCode": line.product_id.ginlong_product_code,
            "operator": line.ginlong_operator_code,
            "operationTime": _operation_time(line.ginlong_operation_time, label),
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
        values = {
            "productSN": result.serial_number,
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


def _api06_payload(order):
    """从已保存且选中的出库作业行及 Order 汇总值生成 API06 报文。

    参数：
        order: 已保存的 WorldDepot 出库单。

    返回：
        包含订单号、托盘数量、总重量及实际备货明细的回传字典。
    """
    pickings = order.ginlong_stock_picking_ids.filtered("ginlong_callback_selected")
    if not pickings:
        raise UserError(_("API06 请先在 Ginlong 回传数据页选择本次备货作业单。"))
    lines = pickings.mapped("move_line_ids").filtered(lambda line: line.quantity > 0)
    if not lines:
        raise UserError(_("API06 找不到关联备货作业的实际 move line。"))

    sn_list = []
    for line in lines:
        label = _("API06 move line %s") % line.id
        values = {
            "productSN": line.lot_id.name,
            "quantity": line.quantity,
            "palletCode": line.package_id.name if line.package_id else False,
            "productCode": line.product_id.ginlong_product_code,
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
    """从入库 Order 的已保存收货明细生成 API02 确认报文。

    参数：
        order: 已保存的 WorldDepot 入库单。

    返回：
        含订单号、UPDATE Action 和订单级收货确认值的字典。
    """
    confirmed = _details_confirmation_status(
        order.ginlong_receipt_detail_ids, "receipt_status", "API02"
    )
    return {
        "inboundOrderNo": order.reference,
        "action": _canonical_action("API02"),
        "receiptConfirmed": confirmed,
    }


def _api08_payload(order):
    """从出库 Order 的已保存发货明细生成 API08 确认报文。

    参数：
        order: 已保存的 WorldDepot 出库单。

    返回：
        含订单号、CREATE Action 和订单级发货确认值的字典。
    """
    confirmed = _details_confirmation_status(
        order.ginlong_shipment_detail_ids, "shipment_status", "API08"
    )
    return {
        "outboundOrderNo": order.reference,
        "action": _canonical_action("API08"),
        "shipmentConfirmed": confirmed,
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
        return _api04_payload(order)
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


def _write_api_log(order, api_code, endpoint, payload, response_text, status_code, error):
    """向现有 WorldDepot API 日志追加一次发送尝试及来源单据引用。

    参数：
        order: 发起回传的来源业务单据。
        api_code: Ginlong 回传接口编号。
        endpoint: 管理员配置的目标 URL。
        payload: 本次生成的业务报文；尚未生成时为 None。
        response_text: HTTP 响应正文。
        status_code: HTTP 状态码；未发送时为 None。
        error: 发送或业务错误文本。
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
        "source_record": "%s,%s" % (order._name, order.id),
        "request_data": request_data,
        "response_data": safe_response,
        "exception_details": safe_error or False,
        "status": "success" if status_code and 200 <= status_code < 300 and not safe_error else "error",
        "success": bool(status_code and 200 <= status_code < 300 and not safe_error),
        "code": str(status_code or "BLOCKED"),
        "msg": safe_error or ("HTTP %s" % status_code if status_code else "%s 回传未发送" % api_code),
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


def send_callback(order, api_code):
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


class InboundOrder(models.Model):
    """为入库单提供 Ginlong 回传按钮和关联的实际入库作业单。"""

    _inherit = "world.depot.inbound.order"

    ginlong_stock_picking_ids = fields.One2many(
        "stock.picking", "inbound_order_id", string="Ginlong 入库作业单",
    )

    def action_ginlong_api02(self):
        """手动发送当前入库单的收货确认状态。

        返回：
            显示本次同步回传成功或失败结果的客户端通知 Action。
        """
        return send_callback(self, "API02")

    def action_ginlong_api04(self):
        """手动发送当前入库单已选 Picking 的实际入库结果。

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
        "ginlong_stock_picking_ids.ginlong_callback_selected",
        "ginlong_stock_picking_ids.move_line_ids.package_id",
        "ginlong_stock_picking_ids.move_line_ids.quantity",
        "ginlong_stock_picking_ids.move_line_ids.product_id.product_tmpl_id.ginlong_weight",
        "ginlong_pallet_qty_manual_enabled", "ginlong_pallet_qty_manual",
        "ginlong_gross_weight_manual_enabled", "ginlong_gross_weight_manual",
    )
    def _compute_ginlong_callback_totals(self):
        """汇总已选实际作业行的托盘数和重量，并应用持久化人工覆盖值。"""
        for order in self:
            pickings = order.ginlong_stock_picking_ids.filtered("ginlong_callback_selected")
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
        """手动发送当前出库单已选作业行的备货完成数据。

        返回：
            显示本次同步回传成功或失败结果的客户端通知 Action。
        """
        return send_callback(self, "API06")

    def action_ginlong_api08(self):
        """手动发送当前出库单的发货确认状态及实际作业数据。

        返回：
            显示本次同步回传成功或失败结果的客户端通知 Action。
        """
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
    """标记本次回传选用的实际 Picking；不改变 Picking 库存行为。"""

    _inherit = "stock.picking"

    ginlong_callback_selected = fields.Boolean(
        string="纳入本次 Ginlong 回传", default=False, copy=False,
    )


class StocktakeResult(models.Model):
    """在既有仓库实盘结果上保存回传选择及外部操作人编码。"""

    _inherit = "world.depot.stocktake.result"

    ginlong_operator_code = fields.Char(string="Ginlong 回传操作人员", copy=False)
    ginlong_callback_selected = fields.Boolean(
        string="纳入本次 Ginlong 回传", default=False, copy=False,
    )

import json
import logging
from urllib.parse import parse_qsl, quote, quote_plus, unquote, urlencode, urlsplit, urlunsplit

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError


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
    actions = _CALLBACK_ACTIONS[api_code]
    if api_code != "API10":
        return next(iter(actions.values()))
    action = actions.get((value or "").strip().casefold())
    if not action:
        raise UserError(_("API10 操作必须选择 Add 或 Del。"))
    return action


def _required_values(values, label):
    missing = [key for key, value in values.items() if value is None or value == ""]
    if missing:
        raise UserError(_("%s 缺少必填回传数据：%s") % (label, ", ".join(missing)))


def _operation_time(value, label):
    if not value:
        raise UserError(_("%s 缺少实际操作时间。") % label)
    return fields.Datetime.to_string(value)


def _decimal_string(value):
    """Serialize DECIMAL(18,6) fields as the string form shown in V3.2."""
    return ("%.6f" % float(value or 0.0)).rstrip("0").rstrip(".") or "0"


def _api04_payload(order):
    _required_values({
        "owner": order.ginlong_owner_code,
        "inboundOrderNo": order.reference,
    }, "API04")
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
            "productCode": line.product_id.default_code,
            "operator": line.ginlong_operator_code,
            "operationTime": _operation_time(line.ginlong_operation_time, label),
        }
        _required_values(values, label)
        sn_list.append(values)
    return {
        "owner": order.ginlong_owner_code,
        "action": _canonical_action("API04"),
        "inboundOrderNo": order.reference,
        "snList": sn_list,
    }


def _api10_payload(order):
    _required_values({
        "owner": order.owner_code,
        "countOrderNo": order.count_order_no,
    }, "API10")
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
        _required_values(values, label)
        sn_list.append(values)
    return {
        "owner": order.owner_code,
        "action": action,
        "countOrderNo": order.count_order_no,
        "snList": sn_list,
    }


def _api06_payload(order):
    _required_values({
        "owner": order.ginlong_owner_code,
        "outboundOrderNo": order.reference,
    }, "API06")
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
            "productCode": line.product_id.default_code,
            "operator": line.ginlong_operator_code,
            "operationTime": _operation_time(line.ginlong_operation_time, label),
        }
        _required_values(values, label)
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
    if not details:
        raise UserError(_("%s 请先保存实际作业明细。") % label)
    values = set(details.mapped(field_name))
    if not values or "" in values or False in values:
        raise UserError(_("%s 存在未填写的确认状态。") % label)
    if len(values) > 1:
        raise UserError(_("%s 的明细状态不一致，尚不能生成单一订单级确认值。") % label)
    return values.pop()


def _api02_payload(order):
    _required_values({"inboundOrderNo": order.reference}, "API02")
    confirmed = _details_confirmation_status(
        order.ginlong_receipt_detail_ids, "receipt_status", "API02"
    )
    return {
        "inboundOrderNo": order.reference,
        "action": _canonical_action("API02"),
        "receiptConfirmed": confirmed,
    }


def _api08_payload(order):
    _required_values({"outboundOrderNo": order.reference}, "API08")
    confirmed = _details_confirmation_status(
        order.ginlong_shipment_detail_ids, "shipment_status", "API08"
    )
    return {
        "outboundOrderNo": order.reference,
        "action": _canonical_action("API08"),
        "shipmentConfirmed": confirmed,
    }


def _build_payload(api_code, order):
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


def _response_error(response):
    if not 200 <= response.status_code < 300:
        return _("Ginlong HTTP 返回状态 %s。") % response.status_code
    try:
        data = response.json()
    except (TypeError, ValueError):
        return _("Ginlong 响应不是有效 JSON。")
    if not isinstance(data, dict):
        return _("Ginlong 响应 JSON 必须是对象。")
    return_status = str(data.get("returnStatus") or "").strip().casefold()
    if return_status != "y":
        return data.get("exceptionInfo") or _("Ginlong 未返回成功状态 returnStatus=Y。")
    return False


def send_callback(order, api_code):
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

        # The button acts on saved ORM records only. It receives no unsaved UI
        # payload or context values; flush makes preceding form writes visible.
        order.env.flush_all()
        payload = _build_payload(api_code, order)
        response = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=_HTTP_TIMEOUT,
        )
        status_code = response.status_code
        response_text = response.text or ""
        error = _response_error(response)
    except (UserError, requests.RequestException, ValueError) as exc:
        error = str(exc)
        safe_url = _safe_endpoint_for_log(url)
        if url and safe_url != url:
            error = error.replace(url, safe_url)
        error = _redact_endpoint_secrets(error, url)
        _logger.info("Ginlong callback %s failed: %s", api_code, error)
    except Exception as exc:  # Keep the error visible and record each attempted send.
        error = _redact_endpoint_secrets(str(exc), url)
        _logger.exception("Unexpected Ginlong callback error for %s", api_code)

    # Every button click creates a new log row; earlier log records are immutable.
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
    _inherit = "world.depot.inbound.order"

    ginlong_stock_picking_ids = fields.One2many(
        "stock.picking", "inbound_order_id", string="Ginlong 入库作业单",
    )

    def action_ginlong_api02(self):
        return send_callback(self, "API02")

    def action_ginlong_api04(self):
        return send_callback(self, "API04")


class OutboundOrder(models.Model):
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
        "ginlong_stock_picking_ids.move_line_ids.product_id.ginlong_weight",
        "ginlong_pallet_qty_manual_enabled", "ginlong_pallet_qty_manual",
        "ginlong_gross_weight_manual_enabled", "ginlong_gross_weight_manual",
    )
    def _compute_ginlong_callback_totals(self):
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
                line.product_id.ginlong_weight * line.quantity for line in lines
            )
            order.ginlong_total_weight = (
                order.ginlong_gross_weight_manual
                if order.ginlong_gross_weight_manual_enabled
                else order.ginlong_total_net_weight
            )

    def action_ginlong_api06(self):
        return send_callback(self, "API06")

    def action_ginlong_api08(self):
        return send_callback(self, "API08")


class StocktakeOrder(models.Model):
    _inherit = "world.depot.stocktake.order"

    ginlong_api10_action = fields.Selection(
        [("Add", "Add"), ("Del", "Del")],
        string="Ginlong 回传 Action",
        default="Add",
        copy=False,
    )

    def action_ginlong_api10(self):
        return send_callback(self, "API10")


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    ginlong_operator_code = fields.Char(string="Ginlong 回传操作人员", copy=False)
    ginlong_operation_time = fields.Datetime(string="Ginlong 回传操作时间", copy=False)


class StockPicking(models.Model):
    _inherit = "stock.picking"

    ginlong_callback_selected = fields.Boolean(
        string="纳入本次 Ginlong 回传", default=False, copy=False,
    )


class StocktakeResult(models.Model):
    _inherit = "world.depot.stocktake.result"

    ginlong_operator_code = fields.Char(string="Ginlong 回传操作人员", copy=False)
    ginlong_callback_selected = fields.Boolean(
        string="纳入本次 Ginlong 回传", default=False, copy=False,
    )

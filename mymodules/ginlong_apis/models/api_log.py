"""扩展 WorldDepot API 日志，使 Ginlong 请求可定位来源业务单据。"""

import json

from odoo import api, fields, models, _
from odoo.exceptions import UserError


_GINLONG_API_OBJECT_IDS = {
    "API01": "TPL_Pending_Receipt_Note",
    "API02": "TPL_Receipt_Confirmation",
    "API03": "TPL_Pending_Delivery_Note",
    "API04": "TPL_Inbound_Completion",
    "API05": "TPL_Stocktake_Order",
    "API06": "TPL_Picking_Completed",
    "API07": "TPL_Product_Master",
    "API08": "TPL_Shipment_Completed",
    "API09": "TPL_Stock_Query",
    "API10": "TPL_Stocktaking_Completed",
}

_GINLONG_BUSINESS_KEY_FIELDS = {
    "API01": ("inboundOrderNo",),
    "API02": ("inboundOrderNo",),
    "API03": ("outboundOrderNo",),
    "API04": ("inboundOrderNo",),
    "API05": ("countOrderNo",),
    "API06": ("outboundOrderNo",),
    "API07": ("owner", "productCode"),
    "API08": ("outboundOrderNo",),
    "API09": ("owner", "warehouse"),
    "API10": ("countOrderNo",),
}


class WorldDepotAPILog(models.Model):
    """为既有 API 日志增加来源业务单据引用和打开动作。"""

    _inherit = "world.depot.api.log"

    ginlong_api_code = fields.Selection(
        [(code, code) for code in _GINLONG_API_OBJECT_IDS],
        string="Ginlong API",
        compute="_compute_ginlong_api_code",
        store=True,
        index=True,
        readonly=True,
    )

    ginlong_business_key = fields.Char(
        string="Ginlong 业务唯一键",
        compute="_compute_ginlong_business_key",
        store=True,
        index=True,
        readonly=True,
    )

    source_record = fields.Reference(
        selection=[
            ("world.depot.inbound.order", "入库单"),
            ("world.depot.outbound.order", "出库单"),
            ("world.depot.stocktake.order", "盘点单"),
            ("product.product", "产品"),
        ],
        string="来源业务单据",
        index=True,
        copy=False,
    )

    @api.depends("request_path")
    def _compute_ginlong_api_code(self):
        """按 Ginlong objectid 标记共享 API 日志所属接口。

        只检查 request_path，避免请求报文或错误内容中偶然出现 objectid 时
        将其他客户的日志错误归类为 Ginlong 记录。
        """
        for log in self:
            path = (log.request_path or "").casefold()
            log.ginlong_api_code = next((
                api_code
                for api_code, object_id in _GINLONG_API_OBJECT_IDS.items()
                if object_id.casefold() in path
            ), False)

    @api.depends("ginlong_api_code", "request_data")
    def _compute_ginlong_business_key(self):
        """从已记录的请求/回传报文提取对应 Ginlong 接口业务键。

        单字段键原样保存；API07 等复合键按幂等组件的紧凑 JSON 顺序编码，
        使管理员能直接使用实际业务唯一键检索共享日志。
        """
        for log in self:
            api_code = log.ginlong_api_code
            key_fields = _GINLONG_BUSINESS_KEY_FIELDS.get(api_code, ())
            try:
                payload = json.loads(log.request_data or "")
            except (TypeError, ValueError):
                payload = None
            if not isinstance(payload, dict) or not key_fields:
                log.ginlong_business_key = False
                continue
            values = [payload.get(name) for name in key_fields]
            if any(value is None or value == "" for value in values):
                log.ginlong_business_key = False
            elif len(values) == 1:
                log.ginlong_business_key = str(values[0])
            else:
                log.ginlong_business_key = json.dumps(
                    values, ensure_ascii=False, separators=(",", ":"), allow_nan=False,
                )

    def action_open_source_record(self):
        """打开日志关联的订单、盘点单或产品表单。

        返回：
            指向来源记录 Form 的 Odoo window action。

        异常：
            没有关联且仍存在的来源记录时抛出 UserError。
        """
        self.ensure_one()
        record = self.source_record.exists() if self.source_record else False
        if not record:
            raise UserError(_("此日志没有关联的来源业务单据。"))
        return {
            "type": "ir.actions.act_window",
            "name": record.display_name,
            "res_model": record._name,
            "res_id": record.id,
            "view_mode": "form",
            "target": "current",
        }

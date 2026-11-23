"""扩展既有 WMS Order 和产品字段，记录 Ginlong 接口需要的数据。"""

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    """为货主联系人保存 Ginlong 货主编码，供入库和库存隔离查找。"""

    _inherit = "res.partner"

    ginlong_owner_code = fields.Char(string="Ginlong Owner Code", copy=False, index=True)

    _sql_constraints = [
        (
            "ginlong_owner_code_unique",
            "unique(ginlong_owner_code)",
            "Ginlong owner code must identify one partner.",
        ),
    ]


class InboundOrder(models.Model):
    """扩展现有入库 Order 保存 Ginlong 指令及客户收货明细入口。"""

    _inherit = 'world.depot.inbound.order'

    ginlong_owner_id = fields.Many2one(
        "res.partner", string="Ginlong 货主", copy=False, index=True,
    )
    ginlong_owner_code = fields.Char(copy=False, index=True)
    ginlong_warehouse_code = fields.Char(copy=False)
    ginlong_business_type = fields.Char(copy=False, index=True)
    ginlong_sn_list_json = fields.Text(copy=False)
    ginlong_receipt_detail_ids = fields.One2many(
        "ginlong.inbound.receipt.detail", "order_id", string="Ginlong 收货明细",
    )


class InboundOrderProductPallet(models.Model):
    """在既有入库托盘行保存 Ginlong 产品身份和名称属性。"""

    _inherit = 'world.depot.inbound.order.products.pallet'

    ginlong_product_code = fields.Char(copy=False, index=True)
    ginlong_product_name = fields.Char(copy=False)
    ginlong_specification_model = fields.Char(copy=False)


class InboundOrderProductSerialNumber(models.Model):
    """在既有入库 SN 行保存 Ginlong 数量、托盘和产品编码。"""

    _inherit = 'world.depot.inbound.order.product.serial.number'

    ginlong_quantity = fields.Float(copy=False)
    ginlong_pallet_code = fields.Char(copy=False, index=True)
    ginlong_product_code = fields.Char(copy=False, index=True)
    ginlong_product_name = fields.Char(copy=False)
    ginlong_specification_model = fields.Char(copy=False)


class OutboundOrder(models.Model):
    """扩展现有出库 Order 保存 Ginlong 指令及回传汇总输入。"""

    _inherit = 'world.depot.outbound.order'

    ginlong_owner_id = fields.Many2one(
        "res.partner", string="Ginlong 货主", copy=False, index=True,
    )
    ginlong_owner_code = fields.Char(copy=False, index=True)
    ginlong_warehouse_code = fields.Char(copy=False)
    ginlong_business_type = fields.Char(copy=False, index=True)
    ginlong_customer = fields.Char(copy=False)
    ginlong_address = fields.Text(copy=False)
    ginlong_consignee = fields.Char(copy=False)
    ginlong_contact = fields.Char(copy=False)
    ginlong_contact_email = fields.Char(copy=False)
    ginlong_shipping_method = fields.Char(copy=False)
    ginlong_shipment_detail_ids = fields.One2many(
        "ginlong.outbound.shipment.detail", "order_id", string="Ginlong 发货明细",
    )
    ginlong_pallet_qty_manual_enabled = fields.Boolean(string="手工覆盖托盘数", copy=False)
    ginlong_pallet_qty_manual = fields.Float(string="手工托盘数", copy=False)
    ginlong_gross_weight_manual_enabled = fields.Boolean(string="手工覆盖毛重", copy=False)
    ginlong_gross_weight_manual = fields.Float(string="手工毛重（kg）", copy=False)


class OutboundOrderProduct(models.Model):
    """在既有出库产品行保留 Ginlong 原始订单明细属性。"""

    _inherit = 'world.depot.outbound.order.product'

    ginlong_product_name = fields.Char(copy=False)
    ginlong_specification_model = fields.Char(copy=False)
    ginlong_order_no = fields.Char(copy=False)
    ginlong_unit = fields.Char(copy=False)
    ginlong_net_wt_machine = fields.Float(copy=False)
    ginlong_net_wt_total = fields.Float(copy=False)
    ginlong_pack_qty = fields.Float(copy=False)
    ginlong_pallet_qty = fields.Float(copy=False)
    ginlong_pallet_len = fields.Float(copy=False)
    ginlong_pallet_wid = fields.Float(copy=False)
    ginlong_pallet_hgt = fields.Float(copy=False)
    ginlong_unit_vol = fields.Float(copy=False)
    ginlong_pack_unit = fields.Char(copy=False)
    ginlong_pack_wt = fields.Float(copy=False)
    ginlong_pallet_total_wt = fields.Float(copy=False)
    ginlong_total_vol = fields.Float(copy=False)
    ginlong_carton_wt_total = fields.Float(copy=False)
    ginlong_gross_wt_total = fields.Float(copy=False)
    ginlong_standard = fields.Char(copy=False)
    ginlong_pack_mode = fields.Char(copy=False)


class ProductProduct(models.Model):
    """在产品变体上保存货主和原始 Ginlong 产品编码。"""

    _inherit = 'product.product'

    ginlong_owner_code = fields.Char(copy=False, index=True)
    ginlong_product_code = fields.Char(string="Ginlong Product Code", copy=False, index=True)


class ProductTemplate(models.Model):
    """在产品模板上保存同一 Ginlong productCode 的共享物料属性。"""

    _inherit = 'product.template'

    ginlong_specification_model = fields.Char(copy=False)
    ginlong_unit = fields.Char(copy=False)
    ginlong_weight = fields.Float(copy=False)
    ginlong_power = fields.Char(copy=False)
    ginlong_national_standard = fields.Char(copy=False)
    ginlong_certification_model = fields.Char(copy=False)
    ginlong_product_form = fields.Char(copy=False, index=True)
    ginlong_length = fields.Float(copy=False)
    ginlong_width = fields.Float(copy=False)
    ginlong_height = fields.Float(copy=False)


class GinlongInboundReceiptDetail(models.Model):
    """将入库 Order 的确认状态关联到现有实际收货 move line。"""

    _name = "ginlong.inbound.receipt.detail"
    _description = "Ginlong Inbound Receipt Detail"
    _order = "id"

    order_id = fields.Many2one(
        "world.depot.inbound.order", required=True, ondelete="cascade", index=True,
    )
    move_line_id = fields.Many2one(
        "stock.move.line", string="实际收货作业行", required=True, ondelete="restrict",
    )
    product_id = fields.Many2one(related="move_line_id.product_id", store=True, readonly=True)
    lot_id = fields.Many2one(related="move_line_id.lot_id", store=True, readonly=True)
    serial_number = fields.Char(related="move_line_id.lot_id.name", store=True, readonly=True)
    quantity = fields.Float(related="move_line_id.quantity", store=True, readonly=True)
    package_id = fields.Many2one(
        "stock.quant.package", compute="_compute_package", store=True, readonly=True,
    )
    receipt_status = fields.Selection(
        [("Y", "Y"), ("N", "N")], string="收货状态", required=True, copy=False,
    )

    @api.depends("move_line_id.package_id", "move_line_id.result_package_id")
    def _compute_package(self):
        """优先读取入库结果托盘，缺失时回退到 move line 来源托盘。"""
        for record in self:
            record.package_id = record.move_line_id.result_package_id or record.move_line_id.package_id

    @api.constrains("order_id", "move_line_id")
    def _check_move_line_order(self):
        """确保收货明细引用的实际作业行属于同一入库 Order。"""
        for record in self:
            if record.move_line_id.picking_id.inbound_order_id != record.order_id:
                raise ValidationError(_("收货明细必须关联当前入库单的实际作业行。"))


class GinlongOutboundShipmentDetail(models.Model):
    """将出库 Order 的确认状态关联到现有实际发货 move line。"""

    _name = "ginlong.outbound.shipment.detail"
    _description = "Ginlong Outbound Shipment Detail"
    _order = "id"

    order_id = fields.Many2one(
        "world.depot.outbound.order", required=True, ondelete="cascade", index=True,
    )
    move_line_id = fields.Many2one(
        "stock.move.line", string="实际发货作业行", required=True, ondelete="restrict",
    )
    product_id = fields.Many2one(related="move_line_id.product_id", store=True, readonly=True)
    lot_id = fields.Many2one(related="move_line_id.lot_id", store=True, readonly=True)
    serial_number = fields.Char(related="move_line_id.lot_id.name", store=True, readonly=True)
    quantity = fields.Float(related="move_line_id.quantity", store=True, readonly=True)
    package_id = fields.Many2one(
        "stock.quant.package", compute="_compute_package", store=True, readonly=True,
    )
    shipment_status = fields.Selection(
        [("Y", "Y"), ("N", "N")], string="发货状态", required=True, copy=False,
    )

    @api.depends("move_line_id.package_id", "move_line_id.result_package_id")
    def _compute_package(self):
        """优先读取发货结果托盘，缺失时回退到 move line 来源托盘。"""
        for record in self:
            record.package_id = record.move_line_id.result_package_id or record.move_line_id.package_id

    @api.constrains("order_id", "move_line_id")
    def _check_move_line_order(self):
        """确保发货明细引用的实际作业行属于同一出库 Order。"""
        for record in self:
            if record.move_line_id.picking_id.outbound_order_id != record.order_id:
                raise ValidationError(_("发货明细必须关联当前出库单的实际作业行。"))

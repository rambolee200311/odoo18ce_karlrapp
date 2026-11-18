from odoo import fields, models, _
from odoo.exceptions import UserError


class WorldDepotAPILog(models.Model):
    _inherit = "world.depot.api.log"

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

    def action_open_source_record(self):
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

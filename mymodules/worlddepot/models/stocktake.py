import json

from odoo import fields, models


class StocktakeOrder(models.Model):
    _name = "world.depot.stocktake.order"
    _description = "Customer Stocktake Order"
    _rec_name = "count_order_no"
    _order = "id desc"

    count_order_no = fields.Char(string="Count Order No", required=True, index=True)
    project_id = fields.Many2one("project.project", string="Project", required=True, index=True, ondelete="restrict")
    owner_code = fields.Char(string="Owner Code", required=True)
    warehouse_code = fields.Char(string="Warehouse Code", required=True)
    remark = fields.Text()
    plan_details_json = fields.Text(string="Planned Scope", default="[]")
    plan_sn_list_json = fields.Text(string="Planned Serial Scope", default="[]")
    state = fields.Selection(
        [("new", "New"), ("cancel", "Cancelled")],
        required=True,
        default="new",
        index=True,
    )
    result_ids = fields.One2many("world.depot.stocktake.result", "order_id", string="Actual Count Results")

    def get_plan_details(self):
        self.ensure_one()
        return self._decode_list(self.plan_details_json)

    def get_plan_sn_list(self):
        self.ensure_one()
        return self._decode_list(self.plan_sn_list_json)

    @staticmethod
    def _decode_list(value):
        try:
            data = json.loads(value or "[]")
        except (TypeError, ValueError):
            return []
        return data if isinstance(data, list) else []


class StocktakeResult(models.Model):
    _name = "world.depot.stocktake.result"
    _description = "Warehouse Actual Stocktake Result"
    _order = "operation_time, id"

    order_id = fields.Many2one(
        "world.depot.stocktake.order",
        string="Customer Stocktake Order",
        required=True,
        index=True,
        ondelete="cascade",
    )
    product_id = fields.Many2one("product.product", string="Product", ondelete="restrict")
    product_code = fields.Char(string="Product Code", required=True, index=True)
    product_name = fields.Char(string="Product Name")
    specification_model = fields.Char(string="Specification / Model")
    serial_number = fields.Char(string="Serial Number", index=True)
    quantity = fields.Float(string="Actual Quantity", required=True)
    pallet_code = fields.Char(string="Pallet Code")
    operator_id = fields.Many2one("res.users", string="Actual Operator")
    operation_time = fields.Datetime(string="Actual Operation Time")

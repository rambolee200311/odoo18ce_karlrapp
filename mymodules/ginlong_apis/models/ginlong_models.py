import json

from odoo import fields, models


class GinlongStocktakeTask(models.Model):
    _name = 'ginlong.stocktake.task'
    _description = 'Ginlong Stocktake Task'
    _order = 'id desc'

    count_order_no = fields.Char(required=True, index=True)
    project_id = fields.Many2one('project.project', required=True, index=True, ondelete='restrict')
    owner_code = fields.Char(required=True)
    warehouse_code = fields.Char(required=True)
    remark = fields.Text()
    sn_list_json = fields.Text()
    state = fields.Selection(
        [("open", "Open"), ("cancel", "Cancelled")],
        required=True,
        default="open",
        index=True,
    )
    line_ids = fields.One2many('ginlong.stocktake.task.line', 'task_id', string='Products')

    def get_sn_list(self):
        self.ensure_one()
        try:
            value = json.loads(self.sn_list_json or '[]')
        except (TypeError, ValueError):
            return []
        return value if isinstance(value, list) else []


class GinlongStocktakeTaskLine(models.Model):
    _name = 'ginlong.stocktake.task.line'
    _description = 'Ginlong Stocktake Task Product'
    _order = 'id'

    task_id = fields.Many2one('ginlong.stocktake.task', required=True, ondelete='cascade', index=True)
    product_code = fields.Char(required=True)
    product_name = fields.Char(required=True)
    specification_model = fields.Char(required=True)
    quantity = fields.Float(required=True)

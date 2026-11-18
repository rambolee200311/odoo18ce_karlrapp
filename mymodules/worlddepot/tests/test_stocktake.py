from odoo import fields
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestWorldDepotStocktake(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        owner = cls.env["res.partner"].create({"name": "Stocktake test owner", "is_company": True})
        cls.project = cls.env["project.project"].create({
            "name": "Stocktake test project",
            "owner": owner.id,
            "category": cls.env.ref("product.product_category_all").id,
            "warehouse": cls.env.ref("stock.warehouse0").id,
            "is_check_origin_doc": False,
        })
        cls.product = cls.env["product.product"].create({
            "name": "Stocktake actual result product",
            "default_code": "WD-STOCKTAKE-TEST-001",
            "type": "consu",
        })

    def test_customer_order_links_actual_results_without_inventory_operations(self):
        order = self.env["world.depot.stocktake.order"].create({
            "count_order_no": "WD-COUNT-001",
            "project_id": self.project.id,
            "owner_code": "OWNER-01",
            "warehouse_code": "WH-01",
            "plan_details_json": '[{"productCode":"PLAN-CODE","quantity":9}]',
            "plan_sn_list_json": '[{"productSN":"PLAN-SN"}]',
        })
        result = self.env["world.depot.stocktake.result"].create({
            "order_id": order.id,
            "product_id": self.product.id,
            "product_code": self.product.default_code,
            "product_name": self.product.name,
            "serial_number": "ACTUAL-SN-001",
            "quantity": 2,
            "operator_id": self.env.ref("base.user_admin").id,
            "operation_time": fields.Datetime.now(),
        })

        self.assertEqual(order.result_ids, result)
        self.assertEqual(result.order_id, order)
        self.assertEqual(result.quantity, 2)
        self.assertEqual(order.get_plan_details()[0]["quantity"], 9)
        self.assertEqual(order.get_plan_sn_list()[0]["productSN"], "PLAN-SN")

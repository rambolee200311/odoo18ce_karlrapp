import json
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.service.model import PG_CONCURRENCY_EXCEPTIONS_TO_RETRY
from odoo.tests import TransactionCase, tagged

from odoo.addons.ginlong_apis import services
from odoo.addons.ginlong_apis.controllers import ginlong_controller
from odoo.addons.worlddepot.controllers import api_logs, validator_token
from odoo.addons.ginlong_apis import idempotency, rate_limiter


class _CursorContext:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def commit(self):
        pass


class _LogModel:
    def __init__(self):
        self.values = []

    def sudo(self):
        return self

    def create(self, values):
        self.values.append(values)
        return SimpleNamespace(id=len(self.values))


class _LogEnvironment:
    def __init__(self, log_model):
        self.log_model = log_model

    def __getitem__(self, name):
        if name == "world.depot.api.log":
            return self.log_model
        raise AssertionError("Unexpected model access in API logger: %s" % name)


@tagged("post_install", "-at_install")
class TestGinlongAPI(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.owner = cls.env["res.partner"].create({"name": "Ginlong API test owner", "is_company": True})
        cls.warehouse = cls.env.ref("stock.warehouse0")
        cls.project = cls.env["project.project"].create({
            "name": "Ginlong API test project",
            "owner": cls.owner.id,
            "category": cls.env.ref("product.product_category_all").id,
            "warehouse": cls.warehouse.id,
            "is_check_origin_doc": False,
        })
        cls.product = cls.env["product.product"].create({
            "name": "Ginlong API test product",
            "default_code": "GINLONG-API-TEST-001",
            "type": "consu",
        })
        cls.recipient = cls.env["res.partner"].create({
            "name": "Ginlong API test recipient",
            "is_company": True,
            "source_project_id": cls.project.id,
        })
        cls.api_user = cls.env["world.depot.api.user"].create({
            "user_id": cls.env.ref("base.user_admin").id,
            "project": cls.project.id,
        })

    def _api01(self, reference="GINLONG-IN-001"):
        return {
            "owner": "OWNER-01",
            "action": "CREATE",
            "inboundOrderNo": reference,
            "warehouse": "WH-01",
            "businessType": "STANDARD",
            "remark": "inbound local simulation",
            "details": [{
                "productCode": self.product.default_code,
                "name": "Ginlong module name",
                "specificationModel": "GL-MODEL-1",
                "quantity": 12,
            }],
            "snList": [{
                "productSN": "GL-SN-0001",
                "quantity": 1,
                "palletCode": "GL-PALLET-01",
                "productCode": self.product.default_code,
                "productName": "Ginlong module name",
                "specificationModel": "GL-MODEL-1",
            }],
        }

    def _api03(self, reference="GINLONG-OUT-001"):
        return {
            "owner": "OWNER-01",
            "action": "CREATE",
            "outboundOrderNo": reference,
            "warehouse": "WH-01",
            "businessType": "STANDARD",
            "remark": "outbound local simulation",
            "customer": self.recipient.name,
            "address": "10 Example Road, Example City",
            "consignee": "Recipient Name",
            "contact": "Contact Name",
            "contactEmail": "contact@example.invalid",
            "shippingMethod": "EXTERNAL-RAW-VALUE",
            "details": [{
                "productCode": self.product.default_code,
                "productName": "Ginlong module name",
                "specificationModel": "GL-MODEL-1",
                "quantity": 8,
                "net_wt_machine": 1.1,
                "net_wt_total": 8.8,
                "pack_qty": 2,
                "pallet_qty": 1,
                "pallet_len": 1200,
                "pallet_wid": 800,
                "pallet_hgt": 1000,
                "unit_vol": 0.12,
                "pack_unit": "BOX",
                "pack_wt": 0.2,
                "pallet_total_wt": 9.0,
                "total_vol": 0.96,
                "carton_wt_total": 9.2,
                "gross_wt_total": 9.4,
                "order_no": "LINE-001",
                "unit": "PCS",
                "standard": "STD-1",
                "pack_mode": "MODE-1",
            }],
        }

    def test_api01_maps_order_pallet_product_and_serial_without_execution(self):
        result = services.api01(self.env, self.api_user, self._api01())
        self.assertTrue(result["success"])
        order = self.env["world.depot.inbound.order"].browse(result["data"]["id"])
        self.assertEqual(order.reference, "GINLONG-IN-001")
        self.assertEqual(order.ginlong_owner_code, "OWNER-01")
        self.assertEqual(order.ginlong_warehouse_code, "WH-01")
        self.assertEqual(order.ginlong_business_type, "STANDARD")
        self.assertEqual(order.remark, "inbound local simulation")
        self.assertEqual(len(order.inbound_order_product_ids), 1)
        line = order.inbound_order_product_ids
        product_row = line.inbound_order_product_pallet_ids
        self.assertEqual(product_row.product_id, self.product)
        self.assertEqual(product_row.quantity, 12)
        self.assertEqual(product_row.ginlong_product_name, "Ginlong module name")
        self.assertEqual(product_row.ginlong_specification_model, "GL-MODEL-1")
        serial = line.product_serial_number_ids
        self.assertEqual(serial.serial_number, "GL-SN-0001")
        self.assertEqual(serial.quantity, 1)
        self.assertEqual(serial.ginlong_quantity, 1)
        self.assertEqual(serial.ginlong_pallet_code, "GL-PALLET-01")
        self.assertEqual(serial.ginlong_product_code, self.product.default_code)
        self.assertEqual(serial.ginlong_product_name, "Ginlong module name")
        self.assertEqual(serial.ginlong_specification_model, "GL-MODEL-1")
        self.assertFalse(order.stock_picking_id)
        self.assertFalse(self.env["stock.picking"].search([("inbound_order_id", "=", order.id)]))

        services.api01(self.env, self.api_user, {
            "owner": "OWNER-01", "action": "DELETE", "inboundOrderNo": order.reference,
            "warehouse": "WH-01", "businessType": "STANDARD",
        })
        self.assertTrue(order.exists())
        self.assertEqual(order.state, "cancel")
        self.assertEqual(len(order.inbound_order_product_ids), 1)
        self.assertEqual(len(order.inbound_order_product_ids.product_serial_number_ids), 1)
        services.api01(self.env, self.api_user, {
            "owner": "OWNER-01", "action": "DELETE", "inboundOrderNo": order.reference,
            "warehouse": "WH-01", "businessType": "STANDARD",
        })
        self.assertTrue(order.exists())
        self.assertEqual(order.state, "cancel")
        self.assertEqual(len(order.inbound_order_product_ids), 1)

    def test_api03_maps_all_source_fields_without_execution(self):
        result = services.api03(self.env, self.api_user, self._api03())
        self.assertTrue(result["success"])
        order = self.env["world.depot.outbound.order"].browse(result["data"]["id"])
        self.assertEqual(order.reference, "GINLONG-OUT-001")
        self.assertEqual(order.remark, "outbound local simulation")
        self.assertEqual(order.ginlong_owner_code, "OWNER-01")
        self.assertEqual(order.ginlong_warehouse_code, "WH-01")
        self.assertEqual(order.ginlong_business_type, "STANDARD")
        self.assertEqual(order.ginlong_customer, self.recipient.name)
        self.assertEqual(order.ginlong_address, "10 Example Road, Example City")
        self.assertEqual(order.ginlong_consignee, "Recipient Name")
        self.assertEqual(order.ginlong_contact, "Contact Name")
        self.assertEqual(order.ginlong_contact_email, "contact@example.invalid")
        self.assertEqual(order.ginlong_shipping_method, "EXTERNAL-RAW-VALUE")
        line = order.outbound_order_product_ids
        self.assertEqual(line.product_id, self.product)
        self.assertEqual(line.quantity, 8)
        self.assertEqual(line.ginlong_product_name, "Ginlong module name")
        self.assertEqual(line.ginlong_specification_model, "GL-MODEL-1")
        for name in [
            "order_no", "unit", "net_wt_machine", "net_wt_total", "pack_qty", "pallet_qty",
            "pallet_len", "pallet_wid", "pallet_hgt", "unit_vol", "pack_unit", "pack_wt",
            "pallet_total_wt", "total_vol", "carton_wt_total", "gross_wt_total", "standard", "pack_mode",
        ]:
            self.assertTrue(getattr(line, "ginlong_" + name) or getattr(line, "ginlong_" + name) == 0.0, name)
        self.assertEqual(line.ginlong_pallet_len, 1200)
        self.assertEqual(line.pallets, 1)
        self.assertEqual(order.state, "new")
        self.assertFalse(order.picking_PICK)
        self.assertFalse(order.picking_Out)
        self.assertFalse(self.env["stock.picking"].search([("outbound_order_id", "=", order.id)]))

        services.api03(self.env, self.api_user, {
            "owner": "OWNER-01", "action": "DELETE", "outboundOrderNo": order.reference,
            "warehouse": "WH-01", "businessType": "STANDARD",
        })
        self.assertTrue(order.exists())
        self.assertEqual(order.state, "cancel")
        self.assertEqual(len(order.outbound_order_product_ids), 1)
        services.api03(self.env, self.api_user, {
            "owner": "OWNER-01", "action": "DELETE", "outboundOrderNo": order.reference,
            "warehouse": "WH-01", "businessType": "STANDARD",
        })
        self.assertTrue(order.exists())
        self.assertEqual(order.state, "cancel")
        self.assertEqual(len(order.outbound_order_product_ids), 1)

    def test_api05_is_independent_and_preserves_task_scope(self):
        payload = {
            "owner": "OWNER-01", "action": "CREATE", "countOrderNo": "COUNT-001",
            "warehouse": "WH-01", "remark": "count local simulation",
            "details": [{
                "productCode": self.product.default_code,
                "productName": "Ginlong module name",
                "specificationModel": "GL-MODEL-1",
                "quantity": 12,
            }],
            "snList": [{
                "productSN": "GL-SN-COUNT-01", "quantity": 1, "palletCode": "GL-PALLET-01",
                "productCode": self.product.default_code, "productName": "Ginlong module name",
                "specificationModel": "GL-MODEL-1",
            }],
        }
        result = services.api05(self.env, self.api_user, payload)
        task = self.env["ginlong.stocktake.task"].browse(result["data"]["id"])
        self.assertEqual(task.count_order_no, "COUNT-001")
        self.assertEqual(task.owner_code, "OWNER-01")
        self.assertEqual(task.warehouse_code, "WH-01")
        self.assertEqual(task.remark, "count local simulation")
        self.assertEqual(task.line_ids.product_code, self.product.default_code)
        self.assertEqual(task.line_ids.product_name, "Ginlong module name")
        self.assertEqual(task.line_ids.specification_model, "GL-MODEL-1")
        self.assertEqual(task.line_ids.quantity, 12)
        self.assertEqual(task.get_sn_list(), payload["snList"])
        self.assertNotIn("stock.quant", services.api05.__code__.co_names)

        services.api05(self.env, self.api_user, {
            "owner": "OWNER-01", "action": "DELETE", "countOrderNo": "COUNT-001", "warehouse": "WH-01",
        })
        self.assertTrue(task.exists())
        self.assertEqual(task.state, "cancel")
        self.assertEqual(len(task.line_ids), 1)
        services.api05(self.env, self.api_user, {
            "owner": "OWNER-01", "action": "DELETE", "countOrderNo": "COUNT-001", "warehouse": "WH-01",
        })
        self.assertTrue(task.exists())
        self.assertEqual(task.state, "cancel")

    def test_api07_creates_and_updates_native_product(self):
        unit = self.env.ref("uom.product_uom_unit")
        payload = {
            "owner": "OWNER-01", "productCode": "GINLONG-API07-001",
            "productName": "Ginlong API07 product", "specificationModel": "MODEL-07",
            "unit": unit.name, "productForm": "INVERTER", "power": "5kW",
            "nationalStandard": "STD-7", "certificationModel": "CERT-7",
            "weight": 7.5, "length": 400, "width": 300, "height": 200,
        }
        created = services.api07(self.env, self.api_user, payload)
        product = self.env["product.product"].browse(created["data"]["id"])
        self.assertEqual(product.default_code, "GINLONG-API07-001")
        self.assertEqual(product.name, "Ginlong API07 product")
        self.assertEqual(product.ginlong_owner_code, "OWNER-01")
        self.assertEqual(product.ginlong_specification_model, "MODEL-07")
        self.assertEqual(product.ginlong_unit, unit.name)
        self.assertEqual(product.ginlong_power, "5kW")
        self.assertEqual(product.ginlong_national_standard, "STD-7")
        self.assertEqual(product.ginlong_certification_model, "CERT-7")
        self.assertEqual(product.ginlong_product_form, "INVERTER")
        self.assertEqual(product.ginlong_weight, 7.5)
        self.assertEqual(product.ginlong_length, 400)
        self.assertEqual(product.ginlong_width, 300)
        self.assertEqual(product.ginlong_height, 200)

        payload.update({"productName": "Ginlong API07 product updated", "power": "6kW"})
        updated = services.api07(self.env, self.api_user, payload)
        self.assertEqual(updated["data"]["id"], product.id)
        self.assertEqual(product.name, "Ginlong API07 product updated")
        self.assertEqual(product.ginlong_power, "6kW")

        other_owner_payload = dict(payload, owner="OWNER-02")
        with self.assertRaises(ValidationError):
            services.api07(self.env, self.api_user, other_owner_payload)

    def test_api01_and_api03_update_existing_orders(self):
        inbound = services.api01(self.env, self.api_user, self._api01("GINLONG-IN-UPDATE"))
        inbound_order = self.env["world.depot.inbound.order"].browse(inbound["data"]["id"])
        services.api01(self.env, self.api_user, {
            "owner": "OWNER-02", "action": "UPDATE", "inboundOrderNo": inbound_order.reference,
            "warehouse": "WH-02", "businessType": "UPDATED", "remark": "updated inbound",
        })
        self.assertEqual(inbound_order.ginlong_owner_code, "OWNER-02")
        self.assertEqual(inbound_order.ginlong_warehouse_code, "WH-02")
        self.assertEqual(inbound_order.ginlong_business_type, "UPDATED")
        self.assertEqual(inbound_order.remark, "updated inbound")

        outbound = services.api03(self.env, self.api_user, self._api03("GINLONG-OUT-UPDATE"))
        outbound_order = self.env["world.depot.outbound.order"].browse(outbound["data"]["id"])
        services.api03(self.env, self.api_user, {
            "owner": "OWNER-02", "action": "UPDATE", "outboundOrderNo": outbound_order.reference,
            "warehouse": "WH-02", "businessType": "UPDATED", "remark": "updated outbound",
        })
        self.assertEqual(outbound_order.ginlong_owner_code, "OWNER-02")
        self.assertEqual(outbound_order.ginlong_warehouse_code, "WH-02")
        self.assertEqual(outbound_order.ginlong_business_type, "UPDATED")
        self.assertEqual(outbound_order.remark, "updated outbound")

    def test_api05_update_existing_task_without_stock_access(self):
        created = services.api05(self.env, self.api_user, {
            "owner": "OWNER-01", "action": "CREATE", "countOrderNo": "COUNT-UPDATE",
            "warehouse": "WH-01", "details": [{
                "productCode": self.product.default_code, "productName": "Before",
                "specificationModel": "MODEL", "quantity": 3,
            }], "snList": [],
        })
        task = self.env["ginlong.stocktake.task"].browse(created["data"]["id"])
        services.api05(self.env, self.api_user, {
            "owner": "OWNER-02", "action": "UPDATE", "countOrderNo": "COUNT-UPDATE",
            "warehouse": "WH-02", "remark": "updated",
        })
        self.assertEqual(task.owner_code, "OWNER-02")
        self.assertEqual(task.warehouse_code, "WH-02")
        self.assertEqual(task.remark, "updated")
        self.assertEqual(task.line_ids.product_name, "Before")

    def test_idempotency_replays_canonical_request_once(self):
        payload = self._api01("GINLONG-IDEM-001")
        calls = []

        def operation():
            calls.append(True)
            return {"success": True, "data": {"id": 123}}

        first = idempotency.execute(self.env, "API01", payload, operation)
        replay_payload = dict(reversed(list(payload.items())))
        replay = idempotency.execute(self.env, "API01", replay_payload, operation)
        self.assertEqual(first, replay)
        self.assertEqual(len(calls), 1)
        self.assertEqual(self.env["ginlong.api.idempotency"].search_count([
            ("api_code", "=", "API01"), ("business_key", "=", "GINLONG-IDEM-001"),
        ]), 1)
        self.assertEqual(
            idempotency._canonical_json({"a": 1, "b": [1, 2]}),
            idempotency._canonical_json({"b": [1, 2], "a": 1}),
        )
        self.assertNotEqual(
            idempotency._canonical_json({"items": [1, 2]}),
            idempotency._canonical_json({"items": [2, 1]}),
        )

    def test_idempotency_business_keys_and_different_content_reach_operation(self):
        self.assertEqual(idempotency._business_key("API01", {"inboundOrderNo": "IN-KEY"}), "IN-KEY")
        self.assertEqual(idempotency._business_key("API03", {"outboundOrderNo": "OUT-KEY"}), "OUT-KEY")
        self.assertEqual(idempotency._business_key("API05", {"countOrderNo": "COUNT-KEY"}), "COUNT-KEY")
        self.assertEqual(
            idempotency._business_key("API07", {"owner": "O1", "productCode": "P1"}),
            '["O1","P1"]',
        )
        self.assertNotEqual(
            idempotency._business_key("API07", {"owner": "O1", "productCode": "P1"}),
            idempotency._business_key("API07", {"owner": "O2", "productCode": "P1"}),
        )
        first_payload = {"inboundOrderNo": "IN-DIFF", "action": "CREATE", "remark": "first"}
        update_payload = {"inboundOrderNo": "IN-DIFF", "action": "UPDATE", "remark": "changed"}
        calls = []
        first = idempotency.execute(
            self.env, "API01", first_payload,
            lambda: calls.append("create") or {"success": True, "data": {"state": "new"}},
        )
        updated = idempotency.execute(
            self.env, "API01", update_payload,
            lambda: calls.append("update") or {"success": True, "data": {"state": "new", "remark": "changed"}},
        )
        self.assertTrue(first["success"] and updated["success"])
        self.assertEqual(calls, ["create", "update"])
        self.assertEqual(self.env["ginlong.api.idempotency"].search_count([
            ("api_code", "=", "API01"), ("business_key", "=", "IN-DIFF"),
        ]), 2)

        owner_calls = []
        for owner in ("OWNER-A", "OWNER-B"):
            owner_payload = {"owner": owner, "productCode": "SAME-PRODUCT-CODE", "action": "UPDATE"}
            result = idempotency.execute(
                self.env, "API07", owner_payload,
                lambda: owner_calls.append(owner) or {"success": True, "data": {"owner": owner}},
            )
            self.assertTrue(result["success"])
        self.assertEqual(owner_calls, ["OWNER-A", "OWNER-B"])
        self.assertEqual(self.env["ginlong.api.idempotency"].search_count([
            ("api_code", "=", "API07"), ("business_key", "ilike", "SAME-PRODUCT-CODE"),
        ]), 2)

    def test_idempotency_failure_rolls_back_and_allows_retry(self):
        payload = self._api01("GINLONG-IDEM-RETRY")

        def failed_operation():
            self.env["res.partner"].create({"name": "Ginlong rollback probe"})
            raise ValidationError("injected failure")

        with self.assertRaises(ValidationError):
            idempotency.execute(self.env, "API01", payload, failed_operation)
        self.assertEqual(self.env["res.partner"].search_count([("name", "=", "Ginlong rollback probe")]), 0)
        self.assertEqual(self.env["ginlong.api.idempotency"].search_count([
            ("api_code", "=", "API01"), ("business_key", "=", "GINLONG-IDEM-RETRY"),
        ]), 0)
        result = idempotency.execute(self.env, "API01", payload, lambda: {"success": True, "data": {"id": 456}})
        self.assertTrue(result["success"])

        false_payload = {"countOrderNo": "COUNT-FALSE", "action": "CREATE", "owner": "OWNER-01", "warehouse": "WH-01"}
        rejected = idempotency.execute(
            self.env, "API05", false_payload,
            lambda: self.env["res.partner"].create({"name": "Ginlong false-result probe"}) and {"success": False, "error": "rejected"},
        )
        self.assertFalse(rejected["success"])
        self.assertEqual(self.env["res.partner"].search_count([("name", "=", "Ginlong false-result probe")]), 0)
        self.assertEqual(self.env["ginlong.api.idempotency"].search_count([
            ("api_code", "=", "API05"), ("business_key", "=", "COUNT-FALSE"),
        ]), 0)

    def test_missing_business_key_does_not_create_success_record(self):
        cases = [
            ("API01", services.api01, {"owner": "OWNER-01", "action": "CREATE"}),
            ("API03", services.api03, {"owner": "OWNER-01", "action": "CREATE"}),
            ("API05", services.api05, {"owner": "OWNER-01", "action": "CREATE"}),
            ("API07", services.api07, {"owner": "OWNER-01", "productName": "missing-code"}),
        ]
        controller = ginlong_controller.GinlongSimulationController()
        for api_code, handler, payload in cases:
            fake_request = SimpleNamespace(
                httprequest=SimpleNamespace(data=json.dumps(payload).encode("utf-8")),
                env=self.env,
                api_user=self.api_user,
            )
            with patch.object(ginlong_controller, "request", fake_request):
                response = controller._dispatch(api_code, handler)
            self.assertFalse(json.loads(response.get_data(as_text=True))["success"])
            self.assertEqual(self.env["ginlong.api.idempotency"].search_count([("api_code", "=", api_code)]), 0)

    def test_database_concurrency_errors_are_left_for_odoo_http_retry(self):
        payload = self._api01("GINLONG-CONCURRENCY-RETRY")
        fake_request = SimpleNamespace(
            httprequest=SimpleNamespace(data=json.dumps(payload).encode("utf-8")),
            env=self.env,
            api_user=self.api_user,
        )
        controller = ginlong_controller.GinlongSimulationController()
        error_class = PG_CONCURRENCY_EXCEPTIONS_TO_RETRY[0]
        error = error_class("simulated Odoo concurrency conflict")
        with patch.object(ginlong_controller, "request", fake_request):
            with self.assertRaises(error_class):
                controller._dispatch("API01", lambda *_args: (_ for _ in ()).throw(error))
        self.assertEqual(self.env["ginlong.api.idempotency"].search_count([
            ("api_code", "=", "API01"), ("business_key", "=", "GINLONG-CONCURRENCY-RETRY"),
        ]), 0)

        logger_request = SimpleNamespace(
            httprequest=SimpleNamespace(
                data=json.dumps(payload).encode("utf-8"), remote_addr="127.0.0.1", path="/ginlong/sim/api01",
            ),
            env=SimpleNamespace(cr=SimpleNamespace(rollback=lambda: self.fail("logger must not rollback retryable transaction"))),
            registry=SimpleNamespace(cursor=_CursorContext),
        )

        @api_logs.api_logger
        def raise_concurrency_error():
            raise error_class("simulated logger concurrency conflict")

        with patch.object(api_logs, "request", logger_request):
            with self.assertRaises(error_class):
                raise_concurrency_error()

    def test_api_rate_defaults_and_configuration(self):
        settings = self.env["res.config.settings"].sudo()
        self.assertEqual(settings.get_ginlong_api_rate_limit("API01"), 10)
        self.assertEqual(settings.get_ginlong_api_rate_limit("API03"), 10)
        self.assertEqual(settings.get_ginlong_api_rate_limit("API05"), 10)
        self.assertEqual(settings.get_ginlong_api_rate_limit("API07"), 100)
        self.env["ir.config_parameter"].sudo().set_param("ginlong_apis.api07_rate_limit", "140")
        self.assertEqual(settings.get_ginlong_api_rate_limit("API07"), 140)

    def test_routes_use_worlddepot_token_and_api_log_decorators(self):
        token_value = "ginlong-api-test-token"
        self.env["world.depot.api.token"].create({
            "user_id": self.api_user.user_id.id,
            "token": token_value,
            "expires": fields.Datetime.now() + timedelta(hours=1),
        })
        fake_request = SimpleNamespace(
            httprequest=SimpleNamespace(headers={"Authorization": "Bearer " + token_value}),
            env=self.env,
            api_user=False,
            update_env=lambda user: None,
        )

        @validator_token.validate_token
        def authenticated_endpoint():
            return validator_token.request.api_user

        with patch.object(validator_token, "request", fake_request):
            authenticated_api_user = authenticated_endpoint()

        self.assertEqual(authenticated_api_user, self.api_user)
        self.assertIs(ginlong_controller.validate_token, validator_token.validate_token)
        self.assertIs(ginlong_controller.api_logger, api_logs.api_logger)
        controller = ginlong_controller.GinlongSimulationController
        for route_name in ("api01", "api03", "api05", "api07"):
            function = getattr(controller, route_name)
            wrapper_count = 0
            while function:
                wrapper_count += 1
                function = getattr(function, "__wrapped__", False)
            self.assertGreaterEqual(wrapper_count, 3)

    def test_api01_decorated_route_authenticates_and_logs_with_existing_logger(self):
        token_value = "ginlong-route-test-token"
        self.env["world.depot.api.token"].create({
            "user_id": self.api_user.user_id.id,
            "token": token_value,
            "expires": fields.Datetime.now() + timedelta(hours=1),
        })
        log_model = _LogModel()
        log_environment = _LogEnvironment(log_model)
        original_environment = api_logs.api.Environment

        def environment_factory(cr, uid, context, *args, **kwargs):
            if isinstance(cr, _CursorContext):
                return log_environment
            return original_environment(cr, uid, context, *args, **kwargs)

        def request_context(body, token):
            return SimpleNamespace(
                httprequest=SimpleNamespace(
                    data=body,
                    remote_addr="127.0.0.1",
                    path="/ginlong/sim/api01",
                    headers={"Authorization": "Bearer " + token},
                ),
                env=self.env,
                registry=SimpleNamespace(cursor=_CursorContext),
                api_user=False,
                update_env=lambda user: None,
            )

        body = json.dumps(self._api01("GINLONG-IN-ROUTE"), ensure_ascii=False).encode("utf-8")
        endpoint = ginlong_controller.GinlongSimulationController()
        valid_request = request_context(body, token_value)
        with patch.object(validator_token, "request", valid_request), \
                patch.object(api_logs, "request", valid_request), \
                patch.object(ginlong_controller, "request", valid_request), \
                patch.object(rate_limiter, "request", valid_request), \
                patch.object(api_logs.api, "Environment", side_effect=environment_factory), \
                patch.object(rate_limiter, "_reserve", return_value=True):
            response = endpoint.api01()

        response_body = json.loads(response.get_data(as_text=True))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response_body["success"], response_body)
        self.assertEqual(len(log_model.values), 1)
        log = log_model.values[0]
        self.assertEqual(log["request_path"], "/ginlong/sim/api01")
        self.assertEqual(log["project_id"], self.project.id)
        self.assertEqual(log["status"], "success")
        self.assertIn("GINLONG-IN-ROUTE", log["request_data"])
        self.assertNotIn(token_value, str(log))

        invalid_request = request_context(body, "invalid-token")
        existing = self.env["world.depot.inbound.order"].search([("reference", "=", "GINLONG-IN-ROUTE")])
        with patch.object(validator_token, "request", invalid_request), \
                patch.object(api_logs, "request", invalid_request), \
                patch.object(ginlong_controller, "request", invalid_request), \
                patch.object(api_logs.api, "Environment", side_effect=environment_factory):
            rejected = endpoint.api01()
        self.assertEqual(rejected.status_code, 401)
        self.assertEqual(existing, self.env["world.depot.inbound.order"].search([("reference", "=", "GINLONG-IN-ROUTE")]))

    def test_rate_limit_response_is_http_429_and_logged(self):
        endpoint = ginlong_controller.GinlongSimulationController()
        token_value = "ginlong-rate-limit-test-token"
        self.env["world.depot.api.token"].create({
            "user_id": self.api_user.user_id.id,
            "token": token_value,
            "expires": fields.Datetime.now() + timedelta(hours=1),
        })
        log_model = _LogModel()
        log_environment = _LogEnvironment(log_model)
        original_environment = api_logs.api.Environment

        def environment_factory(cr, uid, context, *args, **kwargs):
            if isinstance(cr, _CursorContext):
                return log_environment
            return original_environment(cr, uid, context, *args, **kwargs)

        request_context = SimpleNamespace(
            httprequest=SimpleNamespace(
                data=json.dumps(self._api01("GINLONG-RATE-429")).encode("utf-8"),
                remote_addr="127.0.0.1",
                path="/ginlong/sim/api01",
                headers={"Authorization": "Bearer " + token_value},
            ),
            env=self.env,
            registry=SimpleNamespace(cursor=_CursorContext),
            api_user=False,
            update_env=lambda user: None,
            _ginlong_rate_results={"API01": (False, fields.Datetime.now().replace(microsecond=0), 10)},
        )
        with patch.object(validator_token, "request", request_context), \
                patch.object(api_logs, "request", request_context), \
                patch.object(ginlong_controller, "request", request_context), \
                patch.object(rate_limiter, "request", request_context), \
                patch.object(api_logs.api, "Environment", side_effect=environment_factory):
            response = endpoint.api01()
        self.assertEqual(response.status_code, 429)
        self.assertTrue(response.headers.get("Retry-After"))
        self.assertEqual(log_model.values[0]["code"], "429")
        self.assertFalse(log_model.values[0]["success"])

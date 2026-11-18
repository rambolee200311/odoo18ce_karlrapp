import json
import threading
import time
import uuid
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from odoo import SUPERUSER_ID, api, fields
from odoo.exceptions import ValidationError
from odoo.sql_db import Cursor, db_connect
from odoo.service.model import PG_CONCURRENCY_EXCEPTIONS_TO_RETRY
from odoo.tests import TransactionCase, tagged

from odoo.addons.ginlong_apis import services
from odoo.addons.ginlong_apis.models import ginlong_callbacks
from odoo.addons.ginlong_apis.controllers import ginlong_controller
from odoo.addons.worlddepot.controllers import api_logs, validator_token
from odoo.addons.worlddepot.controllers.hoymiles.product_lookup import _resolve_product
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
        cls.owner.ginlong_owner_code = "OWNER-01"
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
            "ginlong_owner_code": "OWNER-01",
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

    def _cleanup_idempotency_probe(self, business_key, partner_name):
        with self._new_committed_cursor(self.env.cr.dbname) as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            env["ginlong.api.idempotency"].sudo().search([
                ("api_code", "=", "API07"), ("business_key", "=", business_key),
            ]).unlink()
            env["res.partner"].sudo().search([("name", "=", partner_name)]).unlink()

    def _new_committed_cursor(self, dbname):
        """Open a real DB transaction using this test's already loaded registry.

        TransactionCase puts the registry into test mode. Resolving Registry(dbname)
        from a worker thread can block on the test registry lock, even though the
        worker already has a separate database cursor. Seeding the cursor with a
        fresh ORM Transaction keeps the normal registry and cache while ensuring
        each thread has its own committed DB transaction.
        """
        cr = db_connect(dbname).cursor()
        cr.transaction = api.Transaction(self.env.registry)
        return cr

    def _run_concurrent_idempotency_probe(self, suffix, first_transaction_fails):
        dbname = self.env.cr.dbname
        suffix = "%s-%s" % (suffix, uuid.uuid4().hex)
        partner_name = "Ginlong tx probe %s" % suffix
        payload = {"owner": "GINLONG-TX-OWNER", "productCode": "GINLONG-TX-%s" % suffix}
        business_key = idempotency._business_key("API07", payload)
        first_operation_started = threading.Event()
        finish_first_operation = threading.Event()
        waiter_snapshot_ready = threading.Event()
        start_waiter_operation = threading.Event()
        waiter_entered_execute = threading.Event()
        output = {}
        errors = {}
        calls = []
        calls_lock = threading.Lock()

        def first_worker():
            try:
                output["first_stage"] = "opening cursor"
                with self._new_committed_cursor(dbname) as cr:
                    output["first_stage"] = "creating environment"
                    env = api.Environment(cr, SUPERUSER_ID, {})
                    output["first_stage"] = "executing idempotency"

                    def operation():
                        partner = env["res.partner"].sudo().create({"name": partner_name})
                        with calls_lock:
                            calls.append("first")
                        first_operation_started.set()
                        if not finish_first_operation.wait(10):
                            raise TimeoutError("test did not release first transaction")
                        if first_transaction_fails:
                            raise RuntimeError("injected business transaction failure")
                        return {"success": True, "data": {"partner_id": partner.id}}

                    output["first"] = idempotency.execute(env, "API07", payload, operation)
                    output["first_stage"] = "idempotency returned"
            except Exception as exc:
                errors["first"] = exc

        def waiter_worker():
            try:
                with self._new_committed_cursor(dbname) as cr:
                    env = api.Environment(cr, SUPERUSER_ID, {})
                    existing = env["ginlong.api.idempotency"].sudo().search([
                        ("api_code", "=", "API07"), ("business_key", "=", business_key),
                    ])
                    output["waiter_snapshot_count"] = len(existing)
                    waiter_snapshot_ready.set()
                    if not start_waiter_operation.wait(10):
                        raise TimeoutError("test did not start waiting request")
                    waiter_entered_execute.set()

                    def operation():
                        partner = env["res.partner"].sudo().create({"name": partner_name})
                        with calls_lock:
                            calls.append("waiter")
                        return {"success": True, "data": {"partner_id": partner.id}}

                    output["waiter"] = idempotency.execute(env, "API07", payload, operation)
            except Exception as exc:
                errors["waiter"] = exc

        # The test registry normally substitutes its rollback-only TestCursor.
        # The two worker threads need separate committed ORM transactions so
        # the unique constraint and savepoint recovery are exercised as in Odoo.
        try:
            with patch.object(
                self.env.registry,
                "cursor",
                side_effect=lambda *args, **kwargs: self._new_committed_cursor(dbname),
            ):
                first = threading.Thread(target=first_worker, name="ginlong-first-%s" % suffix)
                waiter = threading.Thread(target=waiter_worker, name="ginlong-waiter-%s" % suffix)
                first.start()
                if not first_operation_started.wait(10):
                    finish_first_operation.set()
                    first.join(10)
                    raise AssertionError(
                        "first transaction did not reach its business operation: stage=%r result=%r error=%r"
                        % (output.get("first_stage"), output.get("first"), errors.get("first"))
                    )
                waiter.start()
                if not waiter_snapshot_ready.wait(10):
                    start_waiter_operation.set()
                    finish_first_operation.set()
                    first.join(10)
                    waiter.join(10)
                    raise AssertionError("waiting transaction did not establish its pre-commit snapshot")
                start_waiter_operation.set()
                if not waiter_entered_execute.wait(10):
                    finish_first_operation.set()
                    first.join(10)
                    waiter.join(10)
                    raise AssertionError("waiting transaction did not enter idempotency execution")
                # Leave a short overlap so the second transaction reaches the same
                # unique key while the first transaction is still uncommitted.
                time.sleep(0.15)
                finish_first_operation.set()
                first.join(15)
                waiter.join(15)
                if first.is_alive() or waiter.is_alive():
                    raise AssertionError("concurrent idempotency transactions did not finish")

            self.assertEqual(output.get("waiter_snapshot_count"), 0)
            self.assertNotIn("waiter", errors, str(errors.get("waiter")))
            self.assertTrue(output["waiter"]["success"])
            if first_transaction_fails:
                # The failed first operation may itself receive the waiting
                # request's committed replay from idempotency.execute().
                self.assertTrue(
                    str(errors.get("first")) == "injected business transaction failure"
                    or output.get("first") == output["waiter"]
                )
            else:
                self.assertNotIn("first", errors, str(errors.get("first")))
            with self._new_committed_cursor(dbname) as cr:
                env = api.Environment(cr, SUPERUSER_ID, {})
                records = env["ginlong.api.idempotency"].sudo().search([
                    ("api_code", "=", "API07"), ("business_key", "=", business_key),
                ])
                partners = env["res.partner"].sudo().search([("name", "=", partner_name)])
                self.assertEqual(len(records), 1)
                self.assertEqual(len(partners), 1)
                self.assertEqual(json.loads(records.response_json), output["waiter"])
                self.assertEqual(output["waiter"]["data"]["partner_id"], partners.id)
            if first_transaction_fails:
                self.assertEqual(calls.count("first"), 1)
                self.assertEqual(calls.count("waiter"), 1)
            else:
                self.assertEqual(calls, ["first"])
                self.assertEqual(output.get("first"), output["waiter"])
        finally:
            self._cleanup_idempotency_probe(business_key, partner_name)

    def test_concurrent_duplicate_waiter_replays_committed_transaction(self):
        self._run_concurrent_idempotency_probe("COMMIT", first_transaction_fails=False)

    def test_concurrent_duplicate_waiter_takes_over_after_rollback(self):
        self._run_concurrent_idempotency_probe("ROLLBACK", first_transaction_fails=True)

    def test_commit_failure_rolls_back_business_and_idempotency_records(self):
        dbname = self.env.cr.dbname
        suffix = "COMMIT-FAIL-%s" % uuid.uuid4().hex
        partner_name = "Ginlong tx probe %s" % suffix
        payload = {"owner": "GINLONG-TX-OWNER", "productCode": "GINLONG-TX-%s" % suffix}
        business_key = idempotency._business_key("API07", payload)
        original_commit = Cursor.commit
        target_cursor = None

        def fail_target_commit(cursor):
            if cursor is target_cursor:
                cursor.flush()
                raise RuntimeError("injected cursor commit failure before database commit")
            return original_commit(cursor)

        try:
            with db_connect(dbname).cursor() as cr:
                target_cursor = cr
                env = api.Environment(cr, SUPERUSER_ID, {})

                def operation():
                    partner = env["res.partner"].sudo().create({"name": partner_name})
                    return {"success": True, "data": {"partner_id": partner.id}}

                response = idempotency.execute(env, "API07", payload, operation)
                self.assertTrue(response["success"])
                self.assertEqual(env["res.partner"].sudo().search_count([("name", "=", partner_name)]), 1)
                row = env["ginlong.api.idempotency"].sudo().search([
                    ("api_code", "=", "API07"), ("business_key", "=", business_key),
                ])
                self.assertEqual(json.loads(row.response_json), response)
                with patch.object(Cursor, "commit", new=fail_target_commit):
                    with self.assertRaisesRegex(RuntimeError, "injected cursor commit failure"):
                        cr.commit()
                cr.rollback()

            with db_connect(dbname).cursor() as cr:
                env = api.Environment(cr, SUPERUSER_ID, {})
                self.assertEqual(env["res.partner"].sudo().search_count([("name", "=", partner_name)]), 0)
                self.assertEqual(env["ginlong.api.idempotency"].sudo().search_count([
                    ("api_code", "=", "API07"), ("business_key", "=", business_key),
                ]), 0)
        finally:
            self._cleanup_idempotency_probe(business_key, partner_name)

    def test_response_discard_after_commit_replays_saved_result(self):
        dbname = self.env.cr.dbname
        suffix = "RESPONSE-LOST-%s" % uuid.uuid4().hex
        partner_name = "Ginlong tx probe %s" % suffix
        payload = {"owner": "GINLONG-TX-OWNER", "productCode": "GINLONG-TX-%s" % suffix}
        business_key = idempotency._business_key("API07", payload)
        operation_calls = []
        try:
            with db_connect(dbname).cursor() as cr:
                env = api.Environment(cr, SUPERUSER_ID, {})

                def operation():
                    partner = env["res.partner"].sudo().create({"name": partner_name})
                    operation_calls.append(partner.id)
                    return {"success": True, "data": {"partner_id": partner.id}}

                # The server-side response is intentionally discarded after
                # the independent ORM transaction commits.
                idempotency.execute(env, "API07", payload, operation)

            with db_connect(dbname).cursor() as cr:
                env = api.Environment(cr, SUPERUSER_ID, {})
                replay = idempotency.execute(
                    env, "API07", payload,
                    lambda: self.fail("replay must not repeat the business operation"),
                )
                partner = env["res.partner"].sudo().search([("name", "=", partner_name)])
                row = env["ginlong.api.idempotency"].sudo().search([
                    ("api_code", "=", "API07"), ("business_key", "=", business_key),
                ])
                self.assertEqual(len(operation_calls), 1)
                self.assertEqual(len(partner), 1)
                self.assertEqual(replay, json.loads(row.response_json))
                self.assertEqual(replay["data"]["partner_id"], partner.id)
        finally:
            self._cleanup_idempotency_probe(business_key, partner_name)

    def _api01(self, reference="GINLONG-IN-001"):
        return {
            "owner": "OWNER-01",
            "action": "Add",
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
            "action": "Add",
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

    def _create_actual_picking(self, order, incoming, suffix):
        product = self.env["product.product"].create({
            "name": "Actual callback product %s" % suffix,
            "default_code": "GINLONG-CB-%s" % suffix,
            "type": "consu",
            "tracking": "serial",
        })
        picking_type = self.warehouse.in_type_id if incoming else self.warehouse.out_type_id
        picking = self.env["stock.picking"].create({
            "picking_type_id": picking_type.id,
            "location_id": picking_type.default_location_src_id.id,
            "location_dest_id": picking_type.default_location_dest_id.id,
            "inbound_order_id" if incoming else "outbound_order_id": order.id,
        })
        move = self.env["stock.move"].create({
            "name": "Actual callback move %s" % suffix,
            "product_id": product.id,
            "product_uom_qty": 2,
            "product_uom": product.uom_id.id,
            "picking_id": picking.id,
            "location_id": picking.location_id.id,
            "location_dest_id": picking.location_dest_id.id,
        })
        lot = self.env["stock.lot"].create({
            "name": "ACTUAL-SN-%s" % suffix,
            "product_id": product.id,
            "company_id": picking.company_id.id,
        })
        package = self.env["stock.quant.package"].create({"name": "ACTUAL-PALLET-%s" % suffix})
        self.env["stock.move.line"].create({
            "picking_id": picking.id,
            "move_id": move.id,
            "product_id": product.id,
            "product_uom_id": product.uom_id.id,
            "location_id": picking.location_id.id,
            "location_dest_id": picking.location_dest_id.id,
            "quantity": 2,
            "lot_id": lot.id,
            "result_package_id": package.id,
        })
        return picking, product

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
            "owner": "OWNER-01", "action": "Del", "inboundOrderNo": order.reference,
            "warehouse": "WH-01", "businessType": "STANDARD",
        })
        self.assertTrue(order.exists())
        self.assertEqual(order.state, "cancel")
        self.assertEqual(len(order.inbound_order_product_ids), 1)
        self.assertEqual(len(order.inbound_order_product_ids.product_serial_number_ids), 1)
        services.api01(self.env, self.api_user, {
            "owner": "OWNER-01", "action": "Del", "inboundOrderNo": order.reference,
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
            "owner": "OWNER-01", "action": "Del", "outboundOrderNo": order.reference,
            "warehouse": "WH-01", "businessType": "STANDARD",
        })
        self.assertTrue(order.exists())
        self.assertEqual(order.state, "cancel")
        self.assertEqual(len(order.outbound_order_product_ids), 1)
        services.api03(self.env, self.api_user, {
            "owner": "OWNER-01", "action": "Del", "outboundOrderNo": order.reference,
            "warehouse": "WH-01", "businessType": "STANDARD",
        })
        self.assertTrue(order.exists())
        self.assertEqual(order.state, "cancel")
        self.assertEqual(len(order.outbound_order_product_ids), 1)

    def test_api05_stores_customer_instruction_in_worlddepot_without_stock_access(self):
        payload = {
            "owner": "OWNER-01", "action": "Add", "countOrderNo": "COUNT-001",
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
        task = self.env["world.depot.stocktake.order"].browse(result["data"]["id"])
        self.assertEqual(task.count_order_no, "COUNT-001")
        self.assertEqual(task.owner_code, "OWNER-01")
        self.assertEqual(task.warehouse_code, "WH-01")
        self.assertEqual(task.remark, "count local simulation")
        self.assertEqual(task.get_plan_details(), payload["details"])
        self.assertEqual(task.get_plan_sn_list(), payload["snList"])
        self.assertFalse(task.result_ids)
        self.assertNotIn("stock.quant", services.api05.__code__.co_names)

        actual = self.env["world.depot.stocktake.result"].create({
            "order_id": task.id,
            "product_id": self.product.id,
            "product_code": self.product.default_code,
            "product_name": self.product.name,
            "specification_model": "GL-MODEL-1",
            "serial_number": "GL-SN-ACTUAL-01",
            "quantity": 1,
            "pallet_code": "GL-PALLET-ACTUAL-01",
            "operator_id": self.env.ref("base.user_admin").id,
            "operation_time": fields.Datetime.now(),
        })
        self.assertEqual(actual.order_id, task)
        self.assertEqual(actual.serial_number, "GL-SN-ACTUAL-01")
        self.assertFalse(actual.ginlong_callback_selected)
        self.assertNotEqual(actual.serial_number, task.get_plan_sn_list()[0]["productSN"])

        services.api05(self.env, self.api_user, {
            "owner": "OWNER-01", "action": "Del", "countOrderNo": "COUNT-001", "warehouse": "WH-01",
        })
        self.assertTrue(task.exists())
        self.assertEqual(task.state, "cancel")
        self.assertEqual(task.get_plan_details()[0]["productName"], "Ginlong module name")
        self.assertTrue(actual.exists())
        services.api05(self.env, self.api_user, {
            "owner": "OWNER-01", "action": "Del", "countOrderNo": "COUNT-001", "warehouse": "WH-01",
        })
        self.assertTrue(task.exists())
        self.assertEqual(task.state, "cancel")

    def test_api07_creates_and_updates_native_product(self):
        unit = self.env.ref("uom.product_uom_unit")
        payload = {
            "action": "Add", "owner": "OWNER-01", "productCode": "GINLONG-API07-001",
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

        payload.update({"action": "Edit", "productName": "Ginlong API07 product updated", "power": "6kW"})
        updated = services.api07(self.env, self.api_user, payload)
        self.assertEqual(updated["data"]["id"], product.id)
        self.assertEqual(product.name, "Ginlong API07 product updated")
        self.assertEqual(product.ginlong_power, "6kW")

        other_owner_payload = dict(payload, owner="OWNER-02")
        other_created = services.api07(self.env, self.api_user, other_owner_payload)
        other_product = self.env["product.product"].browse(other_created["data"]["id"])
        self.assertNotEqual(other_product, product)
        self.assertEqual(other_product.default_code, product.default_code)
        self.assertEqual(other_product.ginlong_owner_code, "OWNER-02")

        other_owner_payload.update({"action": "Edit", "productName": "Owner 2 product updated"})
        other_updated = services.api07(self.env, self.api_user, other_owner_payload)
        self.assertEqual(other_updated["data"]["id"], other_product.id)
        self.assertEqual(product.name, "Ginlong API07 product updated")

        owner2 = self.env["res.partner"].create({
            "name": "Ginlong API test owner 2", "is_company": True,
            "ginlong_owner_code": "OWNER-02",
        })
        project2 = self.env["project.project"].create({
            "name": "Ginlong API test project 2", "owner": owner2.id,
            "category": self.env.ref("product.product_category_all").id,
            "warehouse": self.warehouse.id, "is_check_origin_doc": False,
        })
        self.assertEqual(_resolve_product(self.env, product.default_code, self.project), product)
        self.assertEqual(_resolve_product(self.env, product.default_code, project2), other_product)

        project2.owner.ginlong_owner_code = False
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            _resolve_product(self.env, product.default_code, project2)

        api01_payload = self._api01("GINLONG-IN-OWNER-02")
        api01_payload["owner"] = "OWNER-02"
        api01_payload["details"][0]["productCode"] = product.default_code
        api01_payload["snList"][0]["productCode"] = product.default_code
        inbound_result = services.api01(self.env, self.api_user, api01_payload)
        inbound = self.env["world.depot.inbound.order"].browse(inbound_result["data"]["id"])
        self.assertEqual(
            inbound.inbound_order_product_ids[0].inbound_order_product_pallet_ids[0].product_id,
            other_product,
        )

        api03_payload = self._api03("GINLONG-OUT-OWNER-02")
        api03_payload["owner"] = "OWNER-02"
        api03_payload["details"][0]["productCode"] = product.default_code
        outbound_result = services.api03(self.env, self.api_user, api03_payload)
        outbound = self.env["world.depot.outbound.order"].browse(outbound_result["data"]["id"])
        self.assertEqual(outbound.outbound_order_product_ids[0].product_id, other_product)

    def test_api02_receipt_details_persist_actual_inbound_data(self):
        result = services.api01(self.env, self.api_user, self._api01("GINLONG-RECEIPT-DETAIL"))
        order = self.env["world.depot.inbound.order"].browse(result["data"]["id"])
        picking, product = self._create_actual_picking(order, incoming=True, suffix="RECEIPT-DETAIL")
        line = picking.move_line_ids
        detail = self.env["ginlong.inbound.receipt.detail"].create({
            "order_id": order.id,
            "move_line_id": line.id,
            "receipt_status": "Y",
        })
        self.env.flush_all()
        self.env.invalidate_all()
        order = self.env["world.depot.inbound.order"].browse(order.id)
        detail = self.env["ginlong.inbound.receipt.detail"].browse(detail.id)
        self.assertIn(detail, order.ginlong_receipt_detail_ids)
        self.assertEqual(detail.product_id, product)
        self.assertEqual(detail.lot_id, line.lot_id)
        self.assertEqual(detail.quantity, 2)
        self.assertEqual(detail.package_id, line.result_package_id)
        self.assertEqual(detail.receipt_status, "Y")

    def test_api08_shipment_details_persist_actual_outbound_data(self):
        result = services.api03(self.env, self.api_user, self._api03("GINLONG-SHIPMENT-DETAIL"))
        order = self.env["world.depot.outbound.order"].browse(result["data"]["id"])
        picking, product = self._create_actual_picking(order, incoming=False, suffix="SHIPMENT-DETAIL")
        line = picking.move_line_ids
        detail = self.env["ginlong.outbound.shipment.detail"].create({
            "order_id": order.id,
            "move_line_id": line.id,
            "shipment_status": "Y",
        })
        self.env.flush_all()
        self.env.invalidate_all()
        order = self.env["world.depot.outbound.order"].browse(order.id)
        detail = self.env["ginlong.outbound.shipment.detail"].browse(detail.id)
        self.assertIn(detail, order.ginlong_shipment_detail_ids)
        self.assertEqual(detail.product_id, product)
        self.assertEqual(detail.lot_id, line.lot_id)
        self.assertEqual(detail.quantity, 2)
        self.assertEqual(detail.package_id, line.result_package_id)
        self.assertEqual(detail.shipment_status, "Y")

    def test_api06_uses_saved_actual_preparation_for_totals(self):
        self.assertEqual(ginlong_callbacks._decimal_string(12.34), "12.34")
        self.assertEqual(ginlong_callbacks._decimal_string(1.1234567), "1.123457")
        result = services.api03(self.env, self.api_user, self._api03("GINLONG-API06-TOTALS"))
        order = self.env["world.depot.outbound.order"].browse(result["data"]["id"])
        picking, product = self._create_actual_picking(order, incoming=False, suffix="API06-TOTALS")
        product.write({"weight": 1.5, "ginlong_weight": 2.5})
        line = picking.move_line_ids
        source_package = self.env["stock.quant.package"].create({"name": "API06-SOURCE-PALLET"})
        result_package = self.env["stock.quant.package"].create({"name": "API06-RESULT-PACKAGE"})
        line.write({
            "package_id": source_package.id,
            "result_package_id": result_package.id,
            "ginlong_operator_code": "picker-1",
            "ginlong_operation_time": fields.Datetime.now(),
        })
        picking.ginlong_callback_selected = True
        self.assertEqual(order.ginlong_pallet_qty_auto, 1)
        self.assertEqual(order.ginlong_pallet_qty, 1)
        self.assertEqual(order.ginlong_total_net_weight, 5)
        self.assertEqual(order.ginlong_total_weight, 5)

        order.write({
            "ginlong_pallet_qty_manual_enabled": True,
            "ginlong_pallet_qty_manual": 3,
            "ginlong_gross_weight_manual_enabled": True,
            "ginlong_gross_weight_manual": 8.75,
        })
        self.env.flush_all()
        self.env.invalidate_all()
        order = self.env["world.depot.outbound.order"].browse(order.id)
        self.assertEqual(order.ginlong_pallet_qty_auto, 1)
        self.assertEqual(order.ginlong_pallet_qty, 3)
        self.assertEqual(order.ginlong_total_net_weight, 5)
        self.assertEqual(order.ginlong_total_weight, 8.75)

        endpoint = "http://mock.invalid/API/WMS_JSON/api06-%s" % order.id
        self.env["ir.config_parameter"].sudo().set_param("ginlong_apis.api06_callback_url", endpoint)
        response = SimpleNamespace(
            status_code=200, text='{"returnStatus":"Y"}',
            json=lambda: {"returnStatus": "Y"},
        )
        with patch("odoo.addons.ginlong_apis.models.ginlong_callbacks.requests.post", return_value=response) as send:
            order.action_ginlong_api06()
        payload = send.call_args.kwargs["json"]
        self.assertEqual(payload["action"], "CREATE")
        self.assertEqual(payload["outboundOrderNo"], order.reference)
        self.assertEqual(payload["palletQty"], "3")
        self.assertEqual(payload["totalWeight"], "8.75")
        self.assertEqual(payload["snList"][0]["palletCode"], source_package.name)

    def test_api01_and_api03_update_existing_orders(self):
        inbound = services.api01(self.env, self.api_user, self._api01("GINLONG-IN-UPDATE"))
        inbound_order = self.env["world.depot.inbound.order"].browse(inbound["data"]["id"])
        inbound_picking, _inbound_product = self._create_actual_picking(
            inbound_order, incoming=True, suffix="API01-UPDATE-PICKING"
        )
        inbound_order.stock_picking_id = inbound_picking.id
        inbound_move_line = inbound_picking.move_line_ids
        services.api01(self.env, self.api_user, {
            "owner": "OWNER-02", "action": "Edit", "inboundOrderNo": inbound_order.reference,
            "warehouse": "WH-02", "businessType": "UPDATED", "remark": "updated inbound",
        })
        self.assertEqual(inbound_order.ginlong_owner_code, "OWNER-02")
        self.assertEqual(inbound_order.ginlong_warehouse_code, "WH-02")
        self.assertEqual(inbound_order.ginlong_business_type, "UPDATED")
        self.assertEqual(inbound_order.remark, "updated inbound")
        self.assertEqual(inbound_order.stock_picking_id, inbound_picking)
        self.assertTrue(inbound_picking.exists())
        self.assertEqual(inbound_picking.move_line_ids, inbound_move_line)
        self.assertEqual(inbound_move_line.quantity, 2)

        outbound = services.api03(self.env, self.api_user, self._api03("GINLONG-OUT-UPDATE"))
        outbound_order = self.env["world.depot.outbound.order"].browse(outbound["data"]["id"])
        outbound_picking, _outbound_product = self._create_actual_picking(
            outbound_order, incoming=False, suffix="API03-UPDATE-PICKING"
        )
        outbound_order.picking_PICK = outbound_picking.id
        outbound_move_line = outbound_picking.move_line_ids
        services.api03(self.env, self.api_user, {
            "owner": "OWNER-02", "action": "Edit", "outboundOrderNo": outbound_order.reference,
            "warehouse": "WH-02", "businessType": "UPDATED", "remark": "updated outbound",
        })
        self.assertEqual(outbound_order.ginlong_owner_code, "OWNER-02")
        self.assertEqual(outbound_order.ginlong_warehouse_code, "WH-02")
        self.assertEqual(outbound_order.ginlong_business_type, "UPDATED")
        self.assertEqual(outbound_order.remark, "updated outbound")
        self.assertEqual(outbound_order.picking_PICK, outbound_picking)
        self.assertTrue(outbound_picking.exists())
        self.assertEqual(outbound_picking.move_line_ids, outbound_move_line)
        self.assertEqual(outbound_move_line.quantity, 2)

    def test_api05_update_existing_customer_instruction_without_stock_access(self):
        created = services.api05(self.env, self.api_user, {
            "owner": "OWNER-01", "action": "Add", "countOrderNo": "COUNT-UPDATE",
            "warehouse": "WH-01", "details": [{
                "productCode": self.product.default_code, "productName": "Before",
                "specificationModel": "MODEL", "quantity": 3,
            }], "snList": [],
        })
        task = self.env["world.depot.stocktake.order"].browse(created["data"]["id"])
        services.api05(self.env, self.api_user, {
            "owner": "OWNER-02", "action": "Edit", "countOrderNo": "COUNT-UPDATE",
            "warehouse": "WH-02", "remark": "updated",
        })
        self.assertEqual(task.owner_code, "OWNER-02")
        self.assertEqual(task.warehouse_code, "WH-02")
        self.assertEqual(task.remark, "updated")
        self.assertEqual(task.get_plan_details()[0]["productName"], "Before")

    def test_callback_forms_are_persistent_and_have_no_transient_wizard(self):
        self.assertNotIn("ginlong.api.callback.wizard", self.env.registry.models)
        inbound_view = self.env.ref("ginlong_apis.view_inbound_order_form_ginlong_callbacks")
        outbound_view = self.env.ref("ginlong_apis.view_outbound_order_form_ginlong_callbacks")
        picking_view = self.env.ref("ginlong_apis.view_stock_picking_form_ginlong_callbacks")
        count_view = self.env.ref("ginlong_apis.view_world_depot_stocktake_order_form_ginlong_callback")
        for view in (inbound_view, outbound_view, picking_view, count_view):
            self.assertIn("Ginlong 回传数据", view.arch_db)
        self.assertIn("action_ginlong_api04", inbound_view.arch_db)
        self.assertIn("action_ginlong_api10", count_view.arch_db)
        self.assertIn("ginlong_callback_selected", inbound_view.arch_db)
        self.assertIn("ginlong_receipt_detail_ids", inbound_view.arch_db)
        self.assertIn("ginlong_shipment_detail_ids", outbound_view.arch_db)
        self.assertIn("ginlong_pallet_qty_manual", outbound_view.arch_db)

    def test_api02_uses_saved_receipt_details_and_logs_each_retry(self):
        result = services.api01(self.env, self.api_user, self._api01("GINLONG-CALLBACK-API02"))
        order = self.env["world.depot.inbound.order"].browse(result["data"]["id"])
        picking, _product = self._create_actual_picking(order, incoming=True, suffix="API02-PAYLOAD")
        detail = self.env["ginlong.inbound.receipt.detail"].create({
            "order_id": order.id, "move_line_id": picking.move_line_ids.id, "receipt_status": "Y",
        })
        endpoint = "http://mock.invalid/API/WMS_JSON/api02-%s" % order.id
        self.env["ir.config_parameter"].sudo().set_param("ginlong_apis.api02_callback_url", endpoint)
        failed_response = SimpleNamespace(
            status_code=500, text='{"returnStatus":"N","exceptionInfo":"retry"}',
            json=lambda: {"returnStatus": "N", "exceptionInfo": "retry"},
        )
        good_response = SimpleNamespace(
            status_code=200, text='{"returnStatus":"Y","exceptionInfo":"OK"}',
            json=lambda: {"returnStatus": "Y", "exceptionInfo": "OK"},
        )
        with patch(
            "odoo.addons.ginlong_apis.models.ginlong_callbacks.requests.post",
            side_effect=[failed_response, good_response],
        ) as send:
            failed_action = order.action_ginlong_api02()
            self.assertEqual(failed_action["params"]["type"], "danger")
            detail.receipt_status = "N"
            self.env.flush_all()
            self.env.invalidate_all()
            order = self.env["world.depot.inbound.order"].browse(order.id)
            detail = self.env["ginlong.inbound.receipt.detail"].browse(detail.id)
            action = order.action_ginlong_api02()
        self.assertEqual(send.call_count, 2)
        self.assertEqual(send.call_args_list[0].kwargs["json"]["receiptConfirmed"], "Y")
        self.assertEqual(send.call_args_list[1].kwargs["json"]["receiptConfirmed"], "N")
        self.assertEqual(send.call_args_list[0].kwargs["json"]["action"], "UPDATE")
        self.assertEqual(send.call_args_list[1].kwargs["json"]["action"], "UPDATE")
        self.assertEqual(action["tag"], "display_notification")
        logs = self.env["world.depot.api.log"].search([("request_path", "=", endpoint)], order="id")
        self.assertEqual(len(logs), 2)
        self.assertFalse(logs[0].success)
        self.assertTrue(logs[1].success)
        self.assertIn('"receiptConfirmed": "Y"', logs[0].request_data)
        self.assertIn('"receiptConfirmed": "N"', logs[1].request_data)

    def test_api02_and_api08_block_mixed_saved_detail_statuses(self):
        inbound_result = services.api01(
            self.env, self.api_user, self._api01("GINLONG-CALLBACK-API02-MIXED")
        )
        inbound = self.env["world.depot.inbound.order"].browse(inbound_result["data"]["id"])
        in_pick_1, _in_product_1 = self._create_actual_picking(
            inbound, incoming=True, suffix="API02-MIXED-1"
        )
        in_pick_2, _in_product_2 = self._create_actual_picking(
            inbound, incoming=True, suffix="API02-MIXED-2"
        )
        self.env["ginlong.inbound.receipt.detail"].create([
            {"order_id": inbound.id, "move_line_id": in_pick_1.move_line_ids.id, "receipt_status": "Y"},
            {"order_id": inbound.id, "move_line_id": in_pick_2.move_line_ids.id, "receipt_status": "N"},
        ])

        outbound_result = services.api03(
            self.env, self.api_user, self._api03("GINLONG-CALLBACK-API08-MIXED")
        )
        outbound = self.env["world.depot.outbound.order"].browse(outbound_result["data"]["id"])
        out_pick_1, _out_product_1 = self._create_actual_picking(
            outbound, incoming=False, suffix="API08-MIXED-1"
        )
        out_pick_2, _out_product_2 = self._create_actual_picking(
            outbound, incoming=False, suffix="API08-MIXED-2"
        )
        self.env["ginlong.outbound.shipment.detail"].create([
            {"order_id": outbound.id, "move_line_id": out_pick_1.move_line_ids.id, "shipment_status": "Y"},
            {"order_id": outbound.id, "move_line_id": out_pick_2.move_line_ids.id, "shipment_status": "N"},
        ])

        inbound_endpoint = "http://mock.invalid/API/WMS_JSON/api02-mixed"
        outbound_endpoint = "http://mock.invalid/API/WMS_JSON/api08-mixed"
        params = self.env["ir.config_parameter"].sudo()
        params.set_param("ginlong_apis.api02_callback_url", inbound_endpoint)
        params.set_param("ginlong_apis.api08_callback_url", outbound_endpoint)
        with patch(
            "odoo.addons.ginlong_apis.models.ginlong_callbacks.requests.post"
        ) as send:
            inbound_result = inbound.action_ginlong_api02()
            outbound_result = outbound.action_ginlong_api08()

        self.assertEqual(send.call_count, 0)
        self.assertEqual(inbound_result["params"]["type"], "danger")
        self.assertEqual(outbound_result["params"]["type"], "danger")
        logs = self.env["world.depot.api.log"].search([
            ("request_path", "in", [inbound_endpoint, outbound_endpoint]),
        ])
        self.assertEqual(len(logs), 2)
        self.assertTrue(all(not log.success for log in logs))
        self.assertTrue(all("状态不一致" in log.exception_details for log in logs))

    def test_callback_forms_expose_existing_order_and_picking_sources(self):
        inbound_result = services.api01(
            self.env, self.api_user, self._api01("GINLONG-CALLBACK-SOURCES-IN")
        )
        inbound = self.env["world.depot.inbound.order"].browse(inbound_result["data"]["id"])
        outbound_result = services.api03(
            self.env, self.api_user, self._api03("GINLONG-CALLBACK-SOURCES-OUT")
        )
        outbound = self.env["world.depot.outbound.order"].browse(outbound_result["data"]["id"])
        picking, _product = self._create_actual_picking(
            outbound, incoming=False, suffix="API06-SOURCE"
        )
        event_time = fields.Datetime.now()
        outbound.write({
            "state": "confirm",
            "status": "picking",
            "picking_PICK": picking.id,
            "picking_PICK_date": event_time,
        })
        self.env.flush_all()
        self.env.invalidate_all()
        inbound = self.env["world.depot.inbound.order"].browse(inbound.id)
        outbound = self.env["world.depot.outbound.order"].browse(outbound.id)

        inbound_arch = self.env.ref(
            "ginlong_apis.view_inbound_order_form_ginlong_callbacks"
        ).arch_db
        outbound_arch = self.env.ref(
            "ginlong_apis.view_outbound_order_form_ginlong_callbacks"
        ).arch_db
        self.assertIn('name="state"', inbound_arch)
        self.assertIn('name="status"', inbound_arch)
        self.assertIn('name="state"', outbound_arch)
        self.assertIn('name="status"', outbound_arch)
        self.assertIn('name="picking_PICK"', outbound_arch)
        self.assertIn('name="picking_PICK_date"', outbound_arch)
        self.assertEqual(inbound.state, "new")
        self.assertEqual(inbound.status, "planning")
        self.assertEqual(outbound.state, "confirm")
        self.assertEqual(outbound.status, "picking")
        self.assertEqual(outbound.picking_PICK, picking)
        self.assertEqual(outbound.picking_PICK_date, event_time)

    def test_api06_and_api08_send_saved_operation_data(self):
        result = services.api03(self.env, self.api_user, self._api03("GINLONG-CALLBACK-API06-08"))
        order = self.env["world.depot.outbound.order"].browse(result["data"]["id"])
        endpoint_06 = "http://mock.invalid/API/WMS_JSON/api06-%s" % order.id
        endpoint_08 = "http://mock.invalid/API/WMS_JSON/api08-%s" % order.id
        params = self.env["ir.config_parameter"].sudo()
        params.set_param("ginlong_apis.api06_callback_url", endpoint_06)
        params.set_param("ginlong_apis.api08_callback_url", endpoint_08)
        picking, product = self._create_actual_picking(order, incoming=False, suffix="API06-08-PAYLOAD")
        product.ginlong_weight = 1.25
        line = picking.move_line_ids
        line.write({
            "package_id": line.result_package_id.id,
            "ginlong_operator_code": "picker-08",
            "ginlong_operation_time": fields.Datetime.now(),
        })
        picking.ginlong_callback_selected = True
        self.env["ginlong.outbound.shipment.detail"].create({
            "order_id": order.id, "move_line_id": line.id, "shipment_status": "N",
        })
        response = SimpleNamespace(
            status_code=200, text='{"returnStatus":"Y","exceptionInfo":"OK"}',
            json=lambda: {"returnStatus": "Y", "exceptionInfo": "OK"},
        )
        with patch(
            "odoo.addons.ginlong_apis.models.ginlong_callbacks.requests.post",
            return_value=response,
        ) as send:
            order.action_ginlong_api06()
            order.action_ginlong_api08()

        self.assertEqual(send.call_count, 2)
        self.assertEqual(send.call_args_list[0].kwargs["json"]["action"], "CREATE")
        self.assertEqual(send.call_args_list[0].kwargs["json"]["palletQty"], "1")
        self.assertEqual(send.call_args_list[0].kwargs["json"]["totalWeight"], "2.5")
        self.assertEqual(send.call_args_list[1].kwargs["json"], {
            "outboundOrderNo": order.reference,
            "action": "CREATE",
            "shipmentConfirmed": "N",
        })
        log_06 = self.env["world.depot.api.log"].search([("request_path", "=", endpoint_06)], order="id desc", limit=1)
        log_08 = self.env["world.depot.api.log"].search([("request_path", "=", endpoint_08)], order="id desc", limit=1)
        self.assertTrue(log_06 and log_08)
        self.assertTrue(log_06.success)
        self.assertTrue(log_08.success)
        self.assertIn('"shipmentConfirmed": "N"', log_08.request_data)

    def test_api04_sends_saved_move_line_data_and_logs_response(self):
        result = services.api01(self.env, self.api_user, self._api01("GINLONG-CALLBACK-API04"))
        order = self.env["world.depot.inbound.order"].browse(result["data"]["id"])
        picking, product = self._create_actual_picking(order, incoming=True, suffix="API04-SAVED")
        picking.ginlong_callback_selected = True
        self._create_actual_picking(order, incoming=True, suffix="API04-UNSELECTED")
        line = picking.move_line_ids
        operation_time = fields.Datetime.now()
        line.write({
            "ginlong_operator_code": "actual.worker",
            "ginlong_operation_time": operation_time,
        })
        self.env.flush_all()
        self.env.invalidate_all()
        order = self.env["world.depot.inbound.order"].browse(order.id)
        picking = self.env["stock.picking"].browse(picking.id)
        line = picking.move_line_ids
        self.assertEqual(line.ginlong_operator_code, "actual.worker")
        self.assertEqual(line.ginlong_operation_time, operation_time)
        self.assertTrue(picking.ginlong_callback_selected)

        endpoint = "http://mock.invalid/API/WMS_JSON/api04-%s" % order.id
        self.env["ir.config_parameter"].sudo().set_param("ginlong_apis.api04_callback_url", endpoint)
        response = SimpleNamespace(
            status_code=200,
            text='{"returnStatus":"Y","exceptionInfo":"OK"}',
            json=lambda: {"returnStatus": "Y", "exceptionInfo": "OK"},
        )
        with patch("odoo.addons.ginlong_apis.models.ginlong_callbacks.requests.post", return_value=response) as send:
            action = order.action_ginlong_api04()

        self.assertEqual(action["tag"], "display_notification")
        self.assertEqual(action["params"]["type"], "success")
        send.assert_called_once()
        args, kwargs = send.call_args
        self.assertEqual(args, (endpoint,))
        self.assertEqual(kwargs["headers"], {"Content-Type": "application/json"})
        self.assertEqual(kwargs["timeout"], 15)
        payload = kwargs["json"]
        self.assertEqual(payload["owner"], "OWNER-01")
        self.assertEqual(payload["action"], "CREATE")
        self.assertEqual(payload["inboundOrderNo"], order.reference)
        self.assertEqual(payload["snList"], [{
            "productSN": "ACTUAL-SN-API04-SAVED",
            "quantity": 2,
            "palletCode": "ACTUAL-PALLET-API04-SAVED",
            "productCode": product.default_code,
            "operator": "actual.worker",
            "operationTime": fields.Datetime.to_string(operation_time),
        }])
        log = self.env["world.depot.api.log"].search([("request_path", "=", endpoint)], order="id desc", limit=1)
        self.assertTrue(log.success)
        self.assertIn('"action": "CREATE"', log.request_data)
        self.assertIn('"returnStatus":"Y"', log.response_data)

    def test_api04_failure_can_be_edited_and_retried_with_separate_logs(self):
        result = services.api01(self.env, self.api_user, self._api01("GINLONG-CALLBACK-RETRY"))
        order = self.env["world.depot.inbound.order"].browse(result["data"]["id"])
        picking, _product = self._create_actual_picking(order, incoming=True, suffix="API04-RETRY")
        picking.ginlong_callback_selected = True
        line = picking.move_line_ids
        line.write({
            "ginlong_operator_code": "initial.worker",
            "ginlong_operation_time": fields.Datetime.now(),
        })
        self.env.flush_all()
        self.env.invalidate_all()
        order = self.env["world.depot.inbound.order"].browse(order.id)
        picking = self.env["stock.picking"].browse(picking.id)
        line = picking.move_line_ids
        endpoint = "http://mock.invalid/API/WMS_JSON/retry-%s" % order.id
        self.env["ir.config_parameter"].sudo().set_param("ginlong_apis.api04_callback_url", endpoint)
        failed = SimpleNamespace(status_code=503, text='{"returnStatus":"N","exceptionInfo":"unavailable"}')
        succeeded = SimpleNamespace(
            status_code=200,
            text='{"returnStatus":"Y","exceptionInfo":"OK"}',
            json=lambda: {"returnStatus": "Y", "exceptionInfo": "OK"},
        )
        with patch(
            "odoo.addons.ginlong_apis.models.ginlong_callbacks.requests.post",
            side_effect=[failed, succeeded],
        ) as send:
            first_action = order.action_ginlong_api04()
            first_log = self.env["world.depot.api.log"].search([("request_path", "=", endpoint)], order="id desc", limit=1)
            first_error = first_log.exception_details
            line.write({"ginlong_operator_code": "corrected.worker"})
            self.env.flush_all()
            self.env.invalidate_all()
            order = self.env["world.depot.inbound.order"].browse(order.id)
            picking = self.env["stock.picking"].browse(picking.id)
            line = picking.move_line_ids
            self.assertEqual(line.ginlong_operator_code, "corrected.worker")
            second_action = order.action_ginlong_api04()

        self.assertEqual(first_action["params"]["type"], "danger")
        self.assertEqual(second_action["params"]["type"], "success")
        self.assertEqual(send.call_count, 2)
        logs = self.env["world.depot.api.log"].search([("request_path", "=", endpoint)], order="id")
        self.assertEqual(len(logs), 2)
        self.assertEqual(logs[0].exception_details, first_error)
        self.assertFalse(logs[0].success)
        self.assertTrue(logs[1].success)
        self.assertIn("initial.worker", logs[0].request_data)
        self.assertIn("corrected.worker", logs[1].request_data)

    def test_api10_persists_action_scope_and_uses_only_saved_actual_results(self):
        order = self.env["world.depot.stocktake.order"].create({
            "count_order_no": "COUNT-CALLBACK-PERSISTED",
            "project_id": self.project.id,
            "owner_code": "OWNER-COUNT",
            "warehouse_code": "WH-COUNT",
        })
        result_one = self.env["world.depot.stocktake.result"].create({
            "order_id": order.id,
            "product_id": self.product.id,
            "product_code": self.product.default_code,
            "product_name": self.product.name,
            "serial_number": "COUNT-SN-001",
            "quantity": 1,
            "pallet_code": "COUNT-PALLET-1",
            "operator_id": self.env.user.id,
            "operation_time": fields.Datetime.now(),
            "ginlong_operator_code": "counter.01",
            "ginlong_callback_selected": True,
        })
        result_two = self.env["world.depot.stocktake.result"].create({
            "order_id": order.id,
            "product_id": self.product.id,
            "product_code": self.product.default_code,
            "product_name": self.product.name,
            "serial_number": "COUNT-SN-002",
            "quantity": 1,
            "pallet_code": "COUNT-PALLET-2",
            "operator_id": self.env.user.id,
            "operation_time": fields.Datetime.now(),
            "ginlong_operator_code": "counter.02",
            "ginlong_callback_selected": False,
        })
        order.ginlong_api10_action = "Add"
        self.env.flush_all()
        self.env.invalidate_all()
        order = self.env["world.depot.stocktake.order"].browse(order.id)
        result_one = self.env["world.depot.stocktake.result"].browse(result_one.id)
        result_two = self.env["world.depot.stocktake.result"].browse(result_two.id)
        endpoint = "http://mock.invalid/API/WMS_JSON/api10-%s" % order.id
        self.env["ir.config_parameter"].sudo().set_param("ginlong_apis.api10_callback_url", endpoint)
        response = SimpleNamespace(
            status_code=200,
            text='{"returnStatus":"Y","exceptionInfo":"OK"}',
            json=lambda: {"returnStatus": "Y", "exceptionInfo": "OK"},
        )
        with patch("odoo.addons.ginlong_apis.models.ginlong_callbacks.requests.post", return_value=response) as send:
            order.action_ginlong_api10()
        self.env.flush_all()
        self.env.invalidate_all()
        order = self.env["world.depot.stocktake.order"].browse(order.id)
        self.assertEqual(order.ginlong_api10_action, "Add")
        self.assertTrue(result_one.ginlong_callback_selected)
        self.assertFalse(result_two.ginlong_callback_selected)
        payload = send.call_args.kwargs["json"]
        self.assertEqual(payload["action"], "Add")
        self.assertEqual([line["productSN"] for line in payload["snList"]], ["COUNT-SN-001"])

        order.ginlong_api10_action = "Del"
        result_one.ginlong_callback_selected = False
        result_two.ginlong_callback_selected = True
        self.env.flush_all()
        self.env.invalidate_all()
        order = self.env["world.depot.stocktake.order"].browse(order.id)
        result_one = self.env["world.depot.stocktake.result"].browse(result_one.id)
        result_two = self.env["world.depot.stocktake.result"].browse(result_two.id)
        with patch("odoo.addons.ginlong_apis.models.ginlong_callbacks.requests.post", return_value=response) as send_delete:
            order.action_ginlong_api10()
        payload = send_delete.call_args.kwargs["json"]
        self.assertEqual(payload["action"], "Del")
        self.assertEqual([line["productSN"] for line in payload["snList"]], ["COUNT-SN-002"])
        self.assertEqual(ginlong_callbacks._canonical_action("API10", "dEl"), "Del")

    def test_callback_logs_do_not_expose_endpoint_credentials(self):
        result = services.api01(self.env, self.api_user, self._api01("GINLONG-CALLBACK-URL-SECRET"))
        order = self.env["world.depot.inbound.order"].browse(result["data"]["id"])
        endpoint = "http://USERCRED123:PASSCRED456@mock.invalid/API/WMS_JSON/item?objectid=02&token=VERYSECRET&key=ALSOSECRET"
        ginlong_callbacks._write_api_log(
            order, "API02", endpoint, None,
            "echo USERCRED123 PASSCRED456 VERYSECRET ALSOSECRET", 502,
            "transport failed for USERCRED123 PASSCRED456 VERYSECRET ALSOSECRET",
        )
        log = self.env["world.depot.api.log"].search([
            ("request_path", "ilike", "/API/WMS_JSON/item")
        ], order="id desc", limit=1)
        self.assertTrue(log)
        self.assertIn("objectid=02", log.request_path)
        self.assertIn("token=%5BREDACTED%5D", log.request_path)
        self.assertIn("key=%5BREDACTED%5D", log.request_path)
        serialized_log = " ".join([
            log.request_path or "", log.response_data or "", log.exception_details or "", log.msg or "", log.data or "",
        ])
        for credential in ("USERCRED123", "PASSCRED456", "VERYSECRET", "ALSOSECRET"):
            self.assertNotIn(credential, serialized_log)

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
        first_payload = {"inboundOrderNo": "IN-DIFF", "action": "Add", "remark": "first"}
        update_payload = {"inboundOrderNo": "IN-DIFF", "action": "Add", "remark": "changed"}
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
            owner_payload = {"owner": owner, "productCode": "SAME-PRODUCT-CODE", "action": "Edit"}
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

        false_payload = {"countOrderNo": "COUNT-FALSE", "action": "Add", "owner": "OWNER-01", "warehouse": "WH-01"}
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
            ("API01", services.api01, {"owner": "OWNER-01", "action": "Add"}),
            ("API03", services.api03, {"owner": "OWNER-01", "action": "Add"}),
            ("API05", services.api05, {"owner": "OWNER-01", "action": "Add"}),
            ("API07", services.api07, {"action": "Add", "owner": "OWNER-01", "productName": "missing-code"}),
        ]
        controller = ginlong_controller.GinlongSimulationController()
        for api_code, handler, payload in cases:
            before_count = self.env["ginlong.api.idempotency"].search_count([("api_code", "=", api_code)])
            fake_request = SimpleNamespace(
                httprequest=SimpleNamespace(data=json.dumps(payload).encode("utf-8")),
                env=self.env,
                api_user=self.api_user,
            )
            with patch.object(ginlong_controller, "request", fake_request):
                response = controller._dispatch(api_code, handler)
            self.assertFalse(json.loads(response.get_data(as_text=True))["success"])
            self.assertEqual(
                self.env["ginlong.api.idempotency"].search_count([("api_code", "=", api_code)]),
                before_count,
            )

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

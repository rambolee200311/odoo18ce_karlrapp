"""Ginlong API 的 Odoo 事务、ORM、认证、限流和库存集成测试。"""

import json
import http.client
import socket
import threading
import time
import uuid
from copy import deepcopy
from datetime import timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import urlsplit

import requests
from psycopg2 import IntegrityError

from odoo import SUPERUSER_ID, api, fields
from odoo.exceptions import AccessError, ValidationError
from odoo.sql_db import Cursor, db_connect
from odoo.service.model import PG_CONCURRENCY_EXCEPTIONS_TO_RETRY
from odoo.tests import HttpCase, TransactionCase, tagged

from odoo.addons.ginlong_apis import services
from odoo.addons.ginlong_apis import errors as ginlong_errors
from odoo.addons.ginlong_apis.models import ginlong_callbacks
from odoo.addons.ginlong_apis.controllers import ginlong_controller
from odoo.addons.worlddepot.controllers import api_logs, validator_token
from odoo.addons.worlddepot.controllers.hoymiles.product_lookup import _resolve_product
from odoo.addons.ginlong_apis import idempotency, rate_limiter
from odoo.addons.ginlong_apis.product_identity import ginlong_internal_code
from odoo.addons.ginlong_apis.validators import required_validator, type_validator


class _LocalGinlongReceiver:
    """接收真实 loopback HTTP POST 的 Ginlong Mock，并保存每次请求证据。"""

    def __init__(self, responses=None, hold_responses=False):
        """启动本地接收端，可按顺序返回状态并延迟释放响应。"""
        self.records = []
        self.responses = list(responses or [])
        self.hold_responses = hold_responses
        self.response_release = threading.Event()
        if not hold_responses:
            self.response_release.set()
        self.received_condition = threading.Condition()
        receiver = self

        class Handler(BaseHTTPRequestHandler):
            """读取 JSON POST 并向测试线程发布请求到达信号。"""

            def do_POST(self):
                """保存请求头和 JSON，并返回预设的 Ginlong 响应。"""
                length = int(self.headers.get("Content-Length", "0"))
                raw_body = self.rfile.read(length)
                try:
                    body = json.loads(raw_body.decode("utf-8"))
                except (UnicodeDecodeError, ValueError):
                    body = None
                with receiver.received_condition:
                    receiver.records.append({
                        "path": self.path,
                        "headers": dict(self.headers.items()),
                        "raw_body": raw_body,
                        "body": body,
                    })
                    if receiver.responses:
                        status, response_body, delay = receiver.responses.pop(0)
                    else:
                        status, response_body, delay = 200, {
                            "returnStatus": "Y",
                            "exceptionInfo": "OK",
                            "operationTime": "2026-11-19 12:00:00",
                        }, 0
                    receiver.received_condition.notify_all()
                if receiver.hold_responses:
                    receiver.response_release.wait(10)
                if delay:
                    time.sleep(delay)
                encoded = json.dumps(response_body, ensure_ascii=False).encode("utf-8")
                try:
                    self.send_response(status)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(encoded)))
                    self.end_headers()
                    self.wfile.write(encoded)
                except (BrokenPipeError, ConnectionResetError):
                    # 超时验收中客户端会主动断开；记录到达仍是有效的外发证据。
                    pass

            def log_message(self, _format, *_args):
                """抑制测试 HTTP Server 的默认终端日志。"""
                return

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    @property
    def url(self):
        """返回本地 Mock HTTP 接收端根地址。"""
        host, port = self.server.server_address
        return "http://%s:%s" % (host, port)

    def wait_for_count(self, count, timeout=5):
        """等待指定数量的真实 HTTP 请求到达接收端。"""
        with self.received_condition:
            return self.received_condition.wait_for(lambda: len(self.records) >= count, timeout=timeout)

    def close(self):
        """停止本地接收线程并释放监听端口。"""
        self.response_release.set()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


class _CursorContext:
    """为并发事务测试封装独立数据库游标的上下文管理器。"""

    def __enter__(self):
        """进入游标上下文并返回自身。"""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """退出上下文，不拦截异常，事务提交/回滚由外层处理。"""
        return False

    def commit(self):
        """供 Odoo 测试游标兼容调用；游标实际提交由包装层控制。"""
        pass


class _LogModel:
    """保存测试调用的 API 日志创建参数，便于断言日志内容。"""

    def __init__(self):
        """初始化空日志记录列表。"""
        self.values = []

    def sudo(self):
        """模拟 Odoo 模型的 sudo 链式调用。"""
        return self

    def create(self, values):
        """保存一条模拟日志并返回含新 ID 的轻量记录对象。"""
        self.values.append(values)
        return SimpleNamespace(id=len(self.values))


class _LogEnvironment:
    """仅提供 API 日志模型访问的测试环境替身。"""

    def __init__(self, log_model):
        """将日志模型替身绑定到环境中。"""
        self.log_model = log_model

    def __getitem__(self, name):
        """返回被测试的日志模型，拒绝任何未预期模型访问。"""
        if name == "world.depot.api.log":
            return self.log_model
        raise AssertionError("Unexpected model access in API logger: %s" % name)


@tagged("post_install", "-at_install")
class TestGinlongAPI(TransactionCase):
    """覆盖 Ginlong API 的 ORM 映射、事务、回传、限流及库存查询。"""

    @classmethod
    def setUpClass(cls):
        """建立各项 API 测试共用的货主、项目、收货方、用户和产品。"""
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
        cls.recipient = cls.env["res.partner"].create({
            "name": "Ginlong API test recipient",
            "is_company": True,
            "source_project_id": cls.project.id,
        })
        cls.api_user = cls.env["world.depot.api.user"].create({
            "user_id": cls.env.ref("base.user_admin").id,
            "project": cls.project.id,
        })
        product_result = services.api07(cls.env, cls.api_user, {
            "action": "Add", "owner": "OWNER-01", "productCode": "GINLONG-API-TEST-001",
            "productName": "Ginlong API test product", "specificationModel": "GL-MODEL-1",
            "unit": cls.env.ref("uom.product_uom_unit").name,
            "productForm": "成品", "power": "5kW", "weight": 2.5,
        })
        cls.product = cls.env["product.product"].browse(product_result["data"]["id"])

    def _cleanup_idempotency_probe(self, business_key, partner_name):
        """用独立提交事务清除并发测试创建的幂等行和联系人夹具。"""
        with self._new_committed_cursor(self.env.cr.dbname) as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            env["ginlong.api.idempotency"].sudo().search([
                ("api_code", "=", "API07"), ("business_key", "=", business_key),
            ]).unlink()
            env["res.partner"].sudo().search([("name", "=", partner_name)]).unlink()

    def _new_committed_cursor(self, dbname):
        """通过当前已加载的 Odoo Registry 打开真实独立事务。

        参数：
            dbname: 当前 Odoo 测试数据库名。

        返回：
            具有新 ORM Transaction 的数据库游标。

        说明：
            并发线程复用已加载 Registry，避免重新加载同一数据库时等待测试运行器锁。
        """
        cr = db_connect(dbname).cursor()
        cr.transaction = api.Transaction(self.env.registry)
        return cr

    def _run_concurrent_idempotency_probe(self, suffix, first_transaction_fails):
        """验证相同请求的并发等待方在首事务提交或回滚后的处理结果。"""
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
            """在独立事务中执行首个请求，并按测试场景控制其提交或失败。"""
            try:
                output["first_stage"] = "opening cursor"
                with self._new_committed_cursor(dbname) as cr:
                    output["first_stage"] = "creating environment"
                    env = api.Environment(cr, SUPERUSER_ID, {})
                    output["first_stage"] = "executing idempotency"

                    def operation():
                        """创建业务记录并保持首事务未结束，以便另一线程竞争相同幂等键。"""
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
            """在独立事务中读取提交前快照，再执行相同请求验证等待方行为。"""
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
                        """模拟等待请求的业务处理，并记录是否发生重复执行。"""
                        partner = env["res.partner"].sudo().create({"name": partner_name})
                        with calls_lock:
                            calls.append("waiter")
                        return {"success": True, "data": {"partner_id": partner.id}}

                    output["waiter"] = idempotency.execute(env, "API07", payload, operation)
            except Exception as exc:
                errors["waiter"] = exc

        # 测试主线程使用回滚专用 TestCursor；工作线程使用独立提交事务验证唯一约束竞争和保存点恢复。
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
                # 保留短暂重叠，使第二个事务在第一个事务尚未提交时竞争同一唯一键。
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
                # 首个操作失败时，execute 可能直接把等待方已提交的重放结果返回给首个调用。
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
        """验证首事务提交时，并发重复请求复用已提交的成功结果。"""
        self._run_concurrent_idempotency_probe("COMMIT", first_transaction_fails=False)

    def test_concurrent_duplicate_waiter_takes_over_after_rollback(self):
        """验证首事务回滚后，等待中的重复请求可以接手并完成处理。"""
        self._run_concurrent_idempotency_probe("ROLLBACK", first_transaction_fails=True)

    def test_commit_failure_rolls_back_business_and_idempotency_records(self):
        """验证提交失败会同时回滚业务记录和幂等结果。"""
        dbname = self.env.cr.dbname
        suffix = "COMMIT-FAIL-%s" % uuid.uuid4().hex
        partner_name = "Ginlong tx probe %s" % suffix
        payload = {"owner": "GINLONG-TX-OWNER", "productCode": "GINLONG-TX-%s" % suffix}
        business_key = idempotency._business_key("API07", payload)
        original_commit = Cursor.commit
        target_cursor = None

        def fail_target_commit(cursor):
            """仅对目标游标注入提交异常，其他游标仍使用原始提交方法。"""
            if cursor is target_cursor:
                cursor.flush()
                raise RuntimeError("injected cursor commit failure before database commit")
            return original_commit(cursor)

        try:
            with db_connect(dbname).cursor() as cr:
                target_cursor = cr
                env = api.Environment(cr, SUPERUSER_ID, {})

                def operation():
                    """创建临时联系人并返回成功结果，供提交失败回滚断言使用。"""
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
        """验证业务提交后响应丢失时，重试能够复用已保存结果。"""
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
                    """创建临时联系人并计数，验证响应丢失后重放不重复执行。"""
                    partner = env["res.partner"].sudo().create({"name": partner_name})
                    operation_calls.append(partner.id)
                    return {"success": True, "data": {"partner_id": partner.id}}

                # 独立 ORM 事务提交后故意丢弃服务端响应，以模拟响应在网络中丢失。
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
        """生成数量为 12 的 API01 测试请求，每个 SN 行表示一件产品。"""
        return {
            "owner": "OWNER-01",
            "action": "Add",
            "inboundOrderNo": reference,
            "warehouse": "WH-01",
            "businessType": "保税_海外收货入库",
            "remark": "inbound local simulation",
            "details": [{
                "productCode": self.product.ginlong_product_code,
                "productName": "Ginlong module name",
                "specificationModel": "GL-MODEL-1",
                "quantity": 12,
            }],
            "snList": [{
                "productSN": "%s-SN-%02d" % (reference, serial_index),
                "quantity": 1,
                "palletCode": "GL-PALLET-01",
                "productCode": self.product.ginlong_product_code,
                "productName": "Ginlong module name",
                "specificationModel": "GL-MODEL-1",
            } for serial_index in range(1, 13)],
        }

    def _api03(self, reference="GINLONG-OUT-001"):
        """生成含收货方及一条完整出库产品行的 API03 测试请求。"""
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
                "productCode": self.product.ginlong_product_code,
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
        """为回传测试建立关联 Order 的实际作业行、SN、托盘和 Picking。

        参数：
            order: 对应入库或出库 WorldDepot Order。
            incoming: True 建立入库 Picking，False 建立出库 Picking。
            suffix: 用于隔离夹具编码的唯一后缀。

        返回：
            新建 Picking 与其产品变体。
        """
        product = self.env["product.product"].create({
            "name": "Actual callback product %s" % suffix,
            "default_code": "GINLONG-CB-%s" % suffix,
            "ginlong_product_code": "GINLONG-CB-%s" % suffix,
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
        """验证 API01 映射入库单、托盘、产品及 SN，且不创建实际执行记录。"""
        result = services.api01(self.env, self.api_user, self._api01())
        self.assertTrue(result["success"])
        order = self.env["world.depot.inbound.order"].browse(result["data"]["id"])
        self.assertEqual(order.reference, "GINLONG-IN-001")
        self.assertEqual(order.ginlong_owner_id, self.owner)
        self.assertEqual(order.ginlong_owner_code, "OWNER-01")
        self.assertEqual(order.ginlong_warehouse_code, "WH-01")
        self.assertEqual(order.ginlong_business_type, "保税_海外收货入库")
        self.assertEqual(order.remark, "inbound local simulation")
        self.assertEqual(len(order.inbound_order_product_ids), 1)
        line = order.inbound_order_product_ids
        product_row = line.inbound_order_product_pallet_ids
        self.assertEqual(product_row.product_id, self.product)
        self.assertEqual(product_row.quantity, 12)
        self.assertEqual(product_row.ginlong_product_name, "Ginlong module name")
        self.assertEqual(product_row.ginlong_specification_model, "GL-MODEL-1")
        serials = line.product_serial_number_ids
        self.assertEqual(len(serials), 12)
        self.assertEqual(set(serials.mapped("serial_number")), {
            "GINLONG-IN-001-SN-%02d" % serial_index for serial_index in range(1, 13)
        })
        self.assertEqual(set(serials.mapped("quantity")), {1.0})
        self.assertEqual(set(serials.mapped("ginlong_quantity")), {1.0})
        self.assertEqual(set(serials.mapped("ginlong_pallet_code")), {"GL-PALLET-01"})
        self.assertEqual(set(serials.mapped("ginlong_product_code")), {self.product.ginlong_product_code})
        self.assertEqual(set(serials.mapped("ginlong_product_name")), {"Ginlong module name"})
        self.assertEqual(set(serials.mapped("ginlong_specification_model")), {"GL-MODEL-1"})
        self.assertFalse(order.stock_picking_id)
        self.assertFalse(self.env["stock.picking"].search([("inbound_order_id", "=", order.id)]))

        services.api01(self.env, self.api_user, {
            "owner": "OWNER-01", "action": "Del", "inboundOrderNo": order.reference,
            "warehouse": "WH-01", "businessType": "STANDARD",
        })
        self.assertTrue(order.exists())
        self.assertEqual(order.state, "cancel")
        self.assertEqual(len(order.inbound_order_product_ids), 1)
        self.assertEqual(len(order.inbound_order_product_ids.product_serial_number_ids), 12)
        services.api01(self.env, self.api_user, {
            "owner": "OWNER-01", "action": "Del", "inboundOrderNo": order.reference,
            "warehouse": "WH-01", "businessType": "STANDARD",
        })
        self.assertTrue(order.exists())
        self.assertEqual(order.state, "cancel")
        self.assertEqual(len(order.inbound_order_product_ids), 1)

    def test_api01_creates_owner_by_code_and_reuses_it_for_later_orders(self):
        """验证 API01 按货主编码自动建档并在后续订单中复用。"""
        owner_code = "OWNER-API01-AUTO-CREATE"
        product_code = "GINLONG-API01-AUTO-OWNER-PRODUCT"
        product = self.env["product.product"].create({
            "name": "Ginlong API01 auto-owner product",
            "default_code": ginlong_internal_code(owner_code, product_code),
            "ginlong_owner_code": owner_code,
            "ginlong_product_code": product_code,
            "type": "consu",
        })
        first_payload = self._api01("GINLONG-IN-AUTO-OWNER-1")
        first_payload["owner"] = owner_code
        first_payload["details"][0]["productCode"] = product_code
        # 本用例只验证货主建档；产品为非 SN 管理，不伪造 SN 或托盘预报行。
        first_payload.pop("snList")
        first_result = services.api01(self.env, self.api_user, first_payload)
        first_order = self.env["world.depot.inbound.order"].browse(first_result["data"]["id"])

        owners = self.env["res.partner"].with_context(active_test=False).search([
            ("ginlong_owner_code", "=", owner_code),
        ])
        self.assertEqual(len(owners), 1)
        self.assertEqual(owners.name, owner_code)
        self.assertEqual(first_order.ginlong_owner_id, owners)
        self.assertEqual(
            first_order.inbound_order_product_ids[0].inbound_order_product_pallet_ids[0].product_id,
            product,
        )

        second_payload = dict(first_payload, inboundOrderNo="GINLONG-IN-AUTO-OWNER-2")
        second_result = services.api01(self.env, self.api_user, second_payload)
        second_order = self.env["world.depot.inbound.order"].browse(second_result["data"]["id"])
        self.assertEqual(second_order.ginlong_owner_id, owners)
        self.assertEqual(
            self.env["res.partner"].with_context(active_test=False).search_count([
                ("ginlong_owner_code", "=", owner_code),
            ]),
            1,
        )

    def test_api03_maps_all_source_fields_without_execution(self):
        """验证 API03 将已提供字段映射到出库单且不执行仓库作业。"""
        result = services.api03(self.env, self.api_user, self._api03())
        self.assertTrue(result["success"])
        order = self.env["world.depot.outbound.order"].browse(result["data"]["id"])
        self.assertEqual(order.reference, "GINLONG-OUT-001")
        self.assertEqual(order.ginlong_owner_id, self.owner)
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

    def test_api03_requires_existing_owner_and_owner_product_pair(self):
        """验证 API03 要求货主及 owner+productCode 组合已存在。"""
        unknown_owner_payload = self._api03("GINLONG-OUT-UNKNOWN-OWNER")
        unknown_owner_payload["owner"] = "OWNER-API03-UNKNOWN"
        with self.assertRaisesRegex(ValidationError, "owner code OWNER-API03-UNKNOWN was not found"):
            services.api03(self.env, self.api_user, unknown_owner_payload)
        self.assertFalse(self.env["world.depot.outbound.order"].search([
            ("reference", "=", "GINLONG-OUT-UNKNOWN-OWNER"),
        ]))
        self.assertFalse(self.env["res.partner"].with_context(active_test=False).search([
            ("ginlong_owner_code", "=", "OWNER-API03-UNKNOWN"),
        ]))

        other_owner = self.env["res.partner"].create({
            "name": "Ginlong API03 owner without requested product",
            "is_company": True,
            "ginlong_owner_code": "OWNER-API03-NO-PRODUCT",
        })
        missing_pair_payload = self._api03("GINLONG-OUT-MISSING-OWNER-PRODUCT")
        missing_pair_payload["owner"] = other_owner.ginlong_owner_code
        with self.assertRaisesRegex(ValidationError, "was not found for Ginlong owner OWNER-API03-NO-PRODUCT"):
            services.api03(self.env, self.api_user, missing_pair_payload)
        self.assertFalse(self.env["world.depot.outbound.order"].search([
            ("reference", "=", "GINLONG-OUT-MISSING-OWNER-PRODUCT"),
        ]))
        self.assertFalse(self.env["product.product"].search([
            ("ginlong_product_code", "=", self.product.ginlong_product_code),
            ("ginlong_owner_code", "=", other_owner.ginlong_owner_code),
        ]))

        existing_order_result = services.api03(
            self.env, self.api_user, self._api03("GINLONG-OUT-OWNER-CHANGE"),
        )
        existing_order = self.env["world.depot.outbound.order"].browse(existing_order_result["data"]["id"])
        owner_change_payload = {
            "owner": other_owner.ginlong_owner_code,
            "action": "Edit",
            "outboundOrderNo": existing_order.reference,
            "warehouse": "WH-02",
            "businessType": "UPDATED",
        }
        with self.assertRaisesRegex(ValidationError, "was not found for Ginlong owner OWNER-API03-NO-PRODUCT"):
            services.api03(self.env, self.api_user, owner_change_payload)
        self.assertEqual(existing_order.ginlong_owner_id, self.owner)
        self.assertEqual(existing_order.outbound_order_product_ids.product_id, self.product)

    def test_api03_rejected_owner_product_pair_returns_and_logs_business_error(self):
        """验证 API03 拒绝无效货主产品组合，并返回和记录业务错误。"""
        owner = self.env["res.partner"].create({
            "name": "Ginlong API03 logged owner",
            "is_company": True,
            "ginlong_owner_code": "OWNER-API03-LOG",
        })
        payload = self._api03("GINLONG-OUT-LOGGED-REJECTION")
        payload["owner"] = owner.ginlong_owner_code
        payload["details"][0]["productCode"] = "GINLONG-PRODUCT-NOT-REGISTERED"
        token_value = "ginlong-api03-rejected-pair-token"
        self.env["world.depot.api.token"].create({
            "user_id": self.api_user.user_id.id,
            "token": token_value,
            "expires": fields.Datetime.now() + timedelta(hours=1),
        })
        log_model = _LogModel()
        log_environment = _LogEnvironment(log_model)
        original_environment = api_logs.api.Environment

        def environment_factory(cr, uid, context, *args, **kwargs):
            """将日志测试游标映射到轻量日志环境，其余请求保留原始 Odoo Environment。"""
            if isinstance(cr, _CursorContext):
                return log_environment
            return original_environment(cr, uid, context, *args, **kwargs)

        fake_request = SimpleNamespace(
            httprequest=SimpleNamespace(
                data=json.dumps(payload).encode("utf-8"),
                remote_addr="127.0.0.1",
                path="/api/ginlong/TPL_Pending_Delivery_Note",
                headers={"Authorization": "Bearer " + token_value},
            ),
            env=self.env,
            registry=SimpleNamespace(cursor=_CursorContext),
            api_user=False,
            update_env=lambda user: None,
        )
        endpoint = ginlong_controller.GinlongSimulationController()
        with patch.object(validator_token, "request", fake_request), \
                patch.object(api_logs, "request", fake_request), \
                patch.object(ginlong_controller, "request", fake_request), \
                patch.object(rate_limiter, "request", fake_request), \
                patch.object(rate_limiter, "_reserve", return_value=True), \
                patch.object(api_logs.api, "Environment", side_effect=environment_factory):
            response = endpoint.api03()

        response_body = json.loads(response.get_data(as_text=True))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response_body), {"returnStatus", "exceptionInfo", "operationTime"})
        self.assertEqual(response_body["returnStatus"], "N")
        self.assertTrue(response_body["exceptionInfo"].startswith("BUS01: "))
        self.assertEqual(len(log_model.values), 1)
        self.assertEqual(log_model.values[0]["status"], "error")
        self.assertFalse(log_model.values[0]["success"])
        self.assertEqual(log_model.values[0]["code"], "BUS01")
        self.assertIn("Product code", log_model.values[0]["msg"])
        self.assertNotEqual(log_model.values[0]["msg"], "业务处理失败")
        self.assertIn("Product code", response_body["exceptionInfo"])
        self.assertLessEqual(len(response_body["exceptionInfo"]), 40)
        self.assertIn("OWNER-API03-LOG", log_model.values[0]["exception_details"])
        self.assertIn("GINLONG-PRODUCT-NOT-REGISTERED", log_model.values[0]["request_data"])
        self.assertFalse(self.env["world.depot.outbound.order"].search([
            ("reference", "=", "GINLONG-OUT-LOGGED-REJECTION"),
        ]))

    def test_api05_stores_customer_instruction_in_worlddepot_without_stock_access(self):
        """验证 API05 只保存客户盘点指令，不访问库存台账。"""
        payload = {
            "owner": "OWNER-01", "action": "Add", "countOrderNo": "COUNT-001",
            "warehouse": "WH-01", "remark": "count local simulation",
            "details": [{
                "productCode": self.product.ginlong_product_code,
                "productName": "Ginlong module name",
                "specificationModel": "GL-MODEL-1",
                "quantity": 12,
            }],
            "snList": [{
                "productSN": "GL-SN-COUNT-%02d" % serial_index,
                "quantity": 1,
                "palletCode": "GL-PALLET-01",
                "productCode": self.product.ginlong_product_code,
                "productName": "Ginlong module name",
                "specificationModel": "GL-MODEL-1",
            } for serial_index in range(1, 13)],
        }
        result = services.api05(self.env, self.api_user, payload)
        task = self.env["world.depot.stocktake.order"].browse(result["data"]["id"])
        self.assertEqual(task.count_order_no, "COUNT-001")
        self.assertEqual(task.owner_code, "OWNER-01")
        self.assertEqual(task.warehouse_code, "WH-01")
        self.assertEqual(task.remark, "count local simulation")
        self.assertEqual(task.get_plan_details(), payload["details"])
        self.assertEqual(task.get_plan_sn_list(), payload["snList"])
        self.assertEqual(len(task.get_plan_sn_list()), 12)
        self.assertEqual({row["quantity"] for row in task.get_plan_sn_list()}, {1})
        self.assertFalse(task.result_ids)
        self.assertNotIn("stock.quant", services.api05.__code__.co_names)

        actual = self.env["world.depot.stocktake.result"].create({
            "order_id": task.id,
            "product_id": self.product.id,
            "product_code": self.product.ginlong_product_code,
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
        self.assertNotIn(actual.serial_number, {row["productSN"] for row in task.get_plan_sn_list()})

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
        """验证 API07 在 Odoo 原生产品模板和变体上创建及更新档案。"""
        unit = self.env.ref("uom.product_uom_unit")
        payload = {
            "action": "Add", "owner": "OWNER-01", "productCode": "GINLONG-API07-001",
            "productName": "Ginlong API07 product", "specificationModel": "MODEL-07",
            "unit": unit.name, "productForm": "成品", "power": "5kW",
            "nationalStandard": "STD-7", "certificationModel": "CERT-7",
            "weight": 7.5, "length": 400, "width": 300, "height": 200,
        }
        missing_edit = dict(payload, action="Edit", productCode="GINLONG-API07-MISSING")
        with self.assertRaises(ginlong_errors.GinlongAPIError) as missing_edit_error:
            services.api07(self.env, self.api_user, missing_edit)
        self.assertEqual(missing_edit_error.exception.error_code, "BUS03")
        self.assertFalse(self.env["product.product"].sudo().search([
            ("ginlong_owner_code", "=", "OWNER-01"),
            ("ginlong_product_code", "=", "GINLONG-API07-MISSING"),
        ]))

        missing_unit_payload = dict(
            payload, action="Add", productCode="GINLONG-API07-MISSING-UNIT",
            unit="GINLONG-NO-SUCH-UOM",
        )
        missing_unit_result = services.api07(self.env, self.api_user, missing_unit_payload)
        auto_unit_product = self.env["product.product"].browse(missing_unit_result["data"]["id"])
        auto_unit = self.env["uom.uom"].search([
            ("name", "=", "GINLONG-NO-SUCH-UOM"),
            ("category_id", "=", self.env.ref("uom.product_uom_categ_unit").id),
        ])
        self.assertEqual(len(auto_unit), 1)
        self.assertEqual(auto_unit.uom_type, "smaller")
        self.assertEqual(auto_unit.factor, 1.0)
        self.assertEqual(auto_unit.factor_inv, 1.0)
        self.assertEqual(auto_unit.rounding, self.env.ref("uom.product_uom_unit").rounding)
        self.assertEqual(auto_unit_product.uom_id, auto_unit)
        self.assertEqual(auto_unit_product.ginlong_product_code, "GINLONG-API07-MISSING-UNIT")

        duplicate_unit_name = "GINLONG-API07-DUPLICATE-UOM"
        duplicate_unit_categories = self.env["uom.category"].create([
            {"name": "Ginlong API07 UoM category A"},
            {"name": "Ginlong API07 UoM category B"},
        ])
        self.env["uom.uom"].create([
            {
                "name": duplicate_unit_name, "category_id": duplicate_unit_categories[0].id,
                "uom_type": "reference", "factor": 1.0, "rounding": 1.0,
            },
            {
                "name": duplicate_unit_name, "category_id": duplicate_unit_categories[1].id,
                "uom_type": "reference", "factor": 1.0, "rounding": 1.0,
            },
        ])
        ambiguous_unit_payload = dict(
            payload, action="Add", productCode="GINLONG-API07-AMBIGUOUS-UNIT",
            unit=duplicate_unit_name,
        )
        with self.assertRaises(ginlong_errors.GinlongAPIError) as ambiguous_unit_error:
            services.api07(self.env, self.api_user, ambiguous_unit_payload)
        self.assertEqual(ambiguous_unit_error.exception.error_code, "BUS05")
        self.assertTrue(ambiguous_unit_error.exception.exception_info.startswith(
            "BUS05: Odoo计量单位名称不唯一: "
        ))
        self.assertLessEqual(len(ambiguous_unit_error.exception.exception_info), 40)
        self.assertIn("GINLONG-API07-DUPLICATE-UOM", ambiguous_unit_error.exception.diagnostic_message)
        self.assertFalse(self.env["product.product"].sudo().search([
            ("ginlong_owner_code", "=", "OWNER-01"),
            ("ginlong_product_code", "=", "GINLONG-API07-AMBIGUOUS-UNIT"),
        ]))

        created = services.api07(self.env, self.api_user, payload)
        product = self.env["product.product"].browse(created["data"]["id"])
        self.assertEqual(created["data"]["productCode"], "GINLONG-API07-001")
        self.assertEqual(product.ginlong_product_code, "GINLONG-API07-001")
        self.assertEqual(product.default_code, ginlong_internal_code("OWNER-01", "GINLONG-API07-001"))
        self.assertEqual(product.name, "Ginlong API07 product")
        self.assertEqual(product.ginlong_owner_code, "OWNER-01")
        template = product.product_tmpl_id
        self.assertEqual(template.ginlong_specification_model, "MODEL-07")
        self.assertEqual(template.ginlong_unit, unit.name)
        self.assertEqual(template.ginlong_power, "5kW")
        self.assertEqual(template.ginlong_national_standard, "STD-7")
        self.assertEqual(template.ginlong_certification_model, "CERT-7")
        self.assertEqual(template.ginlong_product_form, "成品")
        self.assertEqual(template.tracking, "serial")
        self.assertTrue(template.is_storable)
        self.assertEqual(template.ginlong_weight, 7.5)
        self.assertEqual(template.ginlong_length, 400)
        self.assertEqual(template.ginlong_width, 300)
        self.assertEqual(template.ginlong_height, 200)

        # 重复 Add 不论内容是否改变都应失败，且不能覆盖第一次创建的共享产品档案。
        with self.assertRaises(ginlong_errors.GinlongAPIError) as duplicate_error:
            services.api07(self.env, self.api_user, payload)
        self.assertEqual(duplicate_error.exception.error_code, "IDM07")
        self.assertEqual(
            duplicate_error.exception.exception_info,
            "IDM07: 重复新增，冲突键(owner, productCode)",
        )
        changed_add = dict(payload, action="Add", productName="Must not overwrite", weight=99)
        with self.assertRaises(ginlong_errors.GinlongAPIError) as changed_duplicate_error:
            services.api07(self.env, self.api_user, changed_add)
        self.assertEqual(changed_duplicate_error.exception.error_code, "IDM07")
        self.assertEqual(template.name, "Ginlong API07 product")
        self.assertEqual(template.ginlong_weight, 7.5)

        # Edit 必须更新原有模板/变体；同一 owner 重复发送相同 Edit 仍可再次执行。
        edit_payload = dict(
            payload, action="Edit", productName="Ginlong API07 updated product",
            specificationModel="MODEL-07-UPDATED", power="6kW", weight=8.5,
        )
        updated = services.api07(self.env, self.api_user, edit_payload)
        self.assertEqual(updated["data"]["id"], product.id)
        repeated_edit = services.api07(self.env, self.api_user, edit_payload)
        self.assertEqual(repeated_edit["data"]["id"], product.id)
        self.assertEqual(template.name, "Ginlong API07 updated product")
        self.assertEqual(template.ginlong_specification_model, "MODEL-07-UPDATED")
        self.assertEqual(template.ginlong_power, "6kW")
        self.assertEqual(template.ginlong_weight, 8.5)

        other_owner_payload = dict(edit_payload, owner="OWNER-02", action="Add")
        other_created = services.api07(self.env, self.api_user, other_owner_payload)
        other_product = self.env["product.product"].browse(other_created["data"]["id"])
        self.assertNotEqual(other_product, product)
        self.assertEqual(other_product.product_tmpl_id, template)
        self.assertEqual(other_product.ginlong_product_code, product.ginlong_product_code)
        self.assertEqual(other_product.default_code, ginlong_internal_code("OWNER-02", "GINLONG-API07-001"))
        self.assertNotEqual(other_product.default_code, product.default_code)
        self.assertEqual(other_product.ginlong_owner_code, "OWNER-02")
        self.assertEqual(len(template.product_variant_ids), 2)
        self.assertEqual(set(template.attribute_line_ids.mapped("value_ids.name")), {"OWNER-01", "OWNER-02"})

        other_owner_payload.update({
            "action": "Edit", "productName": "Owner 2 product updated",
            "specificationModel": "OWNER-2-UPDATED-MODEL",
        })
        owner2_updated = services.api07(self.env, self.api_user, other_owner_payload)
        self.assertEqual(owner2_updated["data"]["id"], other_product.id)
        self.assertEqual(template.name, "Owner 2 product updated")
        self.assertEqual(template.ginlong_specification_model, "OWNER-2-UPDATED-MODEL")
        self.assertEqual(product.name, template.name)
        self.assertEqual(other_product.name, template.name)
        self.assertEqual(other_product.ginlong_owner_code, "OWNER-02")

        conflicting_form = dict(other_owner_payload, action="Edit", productForm="原材料")
        with self.assertRaises(ginlong_errors.GinlongAPIError) as form_conflict:
            services.api07(self.env, self.api_user, conflicting_form)
        self.assertEqual(form_conflict.exception.error_code, "BUS02")
        self.assertEqual(form_conflict.exception.exception_info, "BUS02: 同productCode的productForm必须一致")
        self.assertIn("ginlong_product_form, tracking", form_conflict.exception.diagnostic_message)
        self.assertEqual(template.name, "Owner 2 product updated")
        self.assertEqual(template.ginlong_specification_model, "OWNER-2-UPDATED-MODEL")
        self.assertEqual(template.ginlong_product_form, "成品")
        self.assertEqual(template.tracking, "serial")

        invalid_form = dict(payload, productCode="GINLONG-API07-INVALID-FORM", productForm="包装物")
        with self.assertRaises(ginlong_errors.GinlongAPIError) as invalid_form_error:
            services.api07(self.env, self.api_user, invalid_form)
        self.assertEqual(invalid_form_error.exception.error_code, "BUS06")
        self.assertEqual(
            invalid_form_error.exception.exception_info,
            "BUS06: productForm仅支持原材料/半成品/成品",
        )
        self.assertIn("包装物", invalid_form_error.exception.diagnostic_message)
        self.assertFalse(self.env["product.product"].search([
            ("ginlong_product_code", "=", "GINLONG-API07-INVALID-FORM"),
        ]))

        owner2 = self.env["res.partner"].create({
            "name": "Ginlong API test owner 2", "is_company": True,
            "ginlong_owner_code": "OWNER-02",
        })
        project2 = self.env["project.project"].create({
            "name": "Ginlong API test project 2", "owner": owner2.id,
            "category": self.env.ref("product.product_category_all").id,
            "warehouse": self.warehouse.id, "is_check_origin_doc": False,
        })
        self.assertEqual(_resolve_product(self.env, product.ginlong_product_code, self.project), product)
        self.assertEqual(_resolve_product(self.env, product.ginlong_product_code, project2), other_product)

        project2.owner.ginlong_owner_code = False
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            _resolve_product(self.env, product.ginlong_product_code, project2)
        project2.owner.ginlong_owner_code = "OWNER-02"

        api01_payload = self._api01("GINLONG-IN-OWNER-02")
        api01_payload["owner"] = "OWNER-02"
        api01_payload["details"][0]["productCode"] = product.ginlong_product_code
        for serial_row in api01_payload["snList"]:
            serial_row["productCode"] = product.ginlong_product_code
        inbound_result = services.api01(self.env, self.api_user, api01_payload)
        inbound = self.env["world.depot.inbound.order"].browse(inbound_result["data"]["id"])
        self.assertEqual(inbound.ginlong_owner_id, owner2)
        self.assertEqual(
            inbound.inbound_order_product_ids[0].inbound_order_product_pallet_ids[0].product_id,
            other_product,
        )

        api03_payload = self._api03("GINLONG-OUT-OWNER-02")
        api03_payload["owner"] = "OWNER-02"
        api03_payload["details"][0]["productCode"] = product.ginlong_product_code
        outbound_result = services.api03(self.env, self.api_user, api03_payload)
        outbound = self.env["world.depot.outbound.order"].browse(outbound_result["data"]["id"])
        self.assertEqual(outbound.ginlong_owner_id, owner2)
        self.assertEqual(outbound.outbound_order_product_ids[0].product_id, other_product)

    def test_api07_orphaned_success_record_does_not_block_new_product_lifecycle(self):
        """验证遗留成功幂等记录不阻止当前无有效产品时开启新生命周期。"""
        product_code = "GINLONG-API07-ORPHAN-%s" % uuid.uuid4().hex
        payload = {
            "action": "Add", "owner": "OWNER-01", "productCode": product_code,
            "productName": "Original orphan product", "specificationModel": "ORPHAN-MODEL",
            "unit": self.env.ref("uom.product_uom_unit").name, "productForm": "原材料",
        }
        stale_result = {
            "success": True, "returnStatus": "Y", "exceptionInfo": "OK",
            "operationTime": "2000-01-01 00:00:00",
            "data": {"id": 999, "productCode": product_code},
        }
        idempotency.execute(
            self.env, "API07", payload, lambda: dict(stale_result), direction="inbound",
        )
        self.assertTrue(idempotency.has_successful_once_for_business_key(self.env, "API07", payload))

        result = idempotency.execute(
            self.env, "API07", payload,
            lambda: services.api07(self.env, self.api_user, payload),
            direction="inbound",
            lifecycle_resolver=lambda current_env: services.lifecycle_event_key(
                current_env,
                current_env["world.depot.api.user"].sudo().browse(self.api_user.id),
                "API07", payload,
            ),
        )
        self.assertTrue(result["success"])
        product = self.env["product.product"].sudo().with_context(active_test=False).search([
            ("ginlong_owner_code", "=", payload["owner"]),
            ("ginlong_product_code", "=", product_code),
        ])
        self.assertEqual(len(product), 1)
        self.assertNotEqual(product.id, stale_result["data"]["id"])

        for duplicate_payload in (
            payload,
            dict(payload, productName="Changed payload must not create"),
        ):
            with self.assertRaises(ginlong_errors.GinlongAPIError) as duplicate:
                services.api07(self.env, self.api_user, duplicate_payload)
            self.assertEqual(duplicate.exception.error_code, "IDM07")
            self.assertEqual(
                duplicate.exception.exception_info,
                "IDM07: 重复新增，冲突键(owner, productCode)",
            )

        self.assertTrue(product.exists())
        row = self.env["ginlong.api.idempotency"].sudo().search([
            ("api_code", "=", "API07"),
            ("business_key", "=", '["%s","%s"]' % (payload["owner"], product_code)),
        ])
        self.assertEqual(len(row), 2)
        self.assertTrue(all(item.state == "succeeded" for item in row))
        self.assertIn(stale_result, [json.loads(item.response_json) for item in row])
        self.assertIn(result, [json.loads(item.response_json) for item in row])

    def test_api07_product_form_sets_template_sn_tracking_and_rejects_other_values(self):
        """验证 productForm 决定模板级 SN tracking，其他枚举值被拒绝。"""
        unit = self.env.ref("uom.product_uom_unit")
        for product_form, tracking in (("原材料", "none"), ("半成品", "serial"), ("成品", "serial")):
            result = services.api07(self.env, self.api_user, {
                "action": "Add", "owner": "OWNER-01", "productCode": "FORM-%s" % product_form,
                "productName": "Product form %s" % product_form,
                "specificationModel": "FORM-MODEL", "unit": unit.name,
                "productForm": product_form,
            })
            product = self.env["product.product"].browse(result["data"]["id"])
            self.assertEqual(product.product_tmpl_id.tracking, tracking)
            self.assertEqual(product.product_tmpl_id.ginlong_product_form, product_form)

    def test_api07_http_response_exposes_only_ginlong_protocol_fields(self):
        """验证 API07 成功、失败和限流响应都不暴露 Odoo 通用字段。"""
        protocol_fields = {"returnStatus", "exceptionInfo", "operationTime"}
        success = ginlong_controller.GinlongSimulationController._success_body(
            "API07", {"success": True, "data": {"id": 123, "productCode": "INTERNAL-PRODUCT"}},
        )
        self.assertEqual(set(success), protocol_fields)
        self.assertEqual(success["returnStatus"], "Y")
        self.assertEqual(success["exceptionInfo"], "OK")

        failure = ginlong_controller.GinlongSimulationController._failure_body(
            "API07", ginlong_errors.make_error("IDM07", owner="OWNER-1", productCode="P-1"),
        )
        self.assertEqual(set(failure), protocol_fields)
        self.assertEqual(failure["returnStatus"], "N")
        self.assertEqual(failure["exceptionInfo"], "IDM07: 重复新增，冲突键(owner, productCode)")

        limited = ginlong_controller.GinlongSimulationController._json_response(
            {"success": False, "code": 429, "error": "Rate limit exceeded"}, status=429,
        )
        limited.headers["Retry-After"] = "1"
        fake_request = SimpleNamespace()
        with patch.object(ginlong_controller, "request", fake_request):
            response = ginlong_controller.ginlong_error_response(
                "API07", strict_success=True,
            )(lambda: limited)()
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.headers.get("Retry-After"), "1")
        limited_body = json.loads(response.get_data(as_text=True))
        self.assertEqual(set(limited_body), protocol_fields)
        self.assertTrue(limited_body["exceptionInfo"].startswith("RATE01: "))

    def test_ginlong_error_catalog_uses_stable_configured_codes(self):
        """验证通用错误目录包含组件码、配置消息和受限协议长度。"""
        expected = {
            "REQ01": "字段错误: test",
            "TYP01": "类型错误字段: test",
            "IDM01": "幂等事件正在处理中",
            "IDM02": "重复新增，冲突键: inboundOrderNo",
            "IDM07": "重复新增，冲突键(owner, productCode)",
            "AUTH01": "API认证失败",
            "RATE01": "API请求频率超限",
            "RATE02": "限流服务暂不可用",
            "BUS01": "业务处理失败",
            "BUS02": "同productCode的productForm必须一致",
            "BUS03": "API07 Edit目标产品不存在",
            "BUS05": "Odoo计量单位名称不唯一: HTTP-UNKNOWN-UOM",
            "BUS06": "productForm仅支持原材料/半成品/成品",
            "SYS01": "系统处理失败",
        }
        for error_code, message in expected.items():
            error = ginlong_errors.make_error(
                error_code, owner="OWNER-A", productCode="P-01",
                unit="HTTP-UNKNOWN-UOM", details="test", key="inboundOrderNo",
                api_code="API01", action="add", business_key="IN-1",
            )
            with self.subTest(error_code=error_code):
                self.assertEqual(error.public_message, message)
                self.assertTrue(error.exception_info.startswith(error_code + ": "))
                self.assertLessEqual(len(error.exception_info), 40)
                self.assertEqual(error.to_log_values()["code"], error_code)
                self.assertEqual(error.to_log_values()["message"], message)

        required_error = ginlong_errors.make_error("REQ01", details="owner is missing")
        self.assertEqual(
            required_error.exception_info,
            "REQ01: 缺失字段: owner",
        )
        self.assertLessEqual(len(required_error.exception_info), 40)
        multiple_required_error = ginlong_errors.make_error(
            "REQ01", details="owner is missing; productForm is missing",
        )
        self.assertEqual(
            multiple_required_error.exception_info,
            "REQ01: 缺失字段: owner, productForm",
        )
        self.assertIn("owner is missing; productForm is missing", multiple_required_error.diagnostic_message)
        long_required_error = ginlong_errors.make_error(
            "REQ01",
            details=(
                "owner is missing; productForm is missing; specificationModel is missing; "
                "details[0].productCode is missing"
            ),
        )
        self.assertEqual(
            long_required_error.exception_info,
            "REQ01: 缺失字段: owner, productForm, ...",
        )
        self.assertLessEqual(len(long_required_error.exception_info), 40)
        self.assertIn("details[0].productCode is missing", long_required_error.diagnostic_message)

        single_type_error = ginlong_errors.make_error(
            "TYP01", details="weight must be a decimal number",
        )
        self.assertEqual(single_type_error.exception_info, "TYP01: 类型错误字段: weight")
        multiple_type_error = ginlong_errors.make_error(
            "TYP01", details="weight must be decimal; length must be decimal",
        )
        self.assertEqual(
            multiple_type_error.exception_info,
            "TYP01: 类型错误字段: weight, length",
        )
        long_type_error = ginlong_errors.make_error(
            "TYP01",
            details=(
                "weight must be decimal; length must be decimal; "
                "details[0].productCode must be decimal"
            ),
        )
        self.assertEqual(
            long_type_error.exception_info,
            "TYP01: 类型错误字段: weight, length, ...",
        )
        self.assertLessEqual(len(long_type_error.exception_info), 40)
        self.assertIn("details[0].productCode must be decimal", long_type_error.diagnostic_message)

        business_error = ginlong_errors.make_error(
            "BUS01",
            message="产品编码不存在\napi_secret=private-value Bearer private-token",
            details="Product lookup failed; api_secret=private-value",
        )
        self.assertIn("产品编码不存在", business_error.public_message)
        self.assertNotIn("private-value", business_error.public_message)
        self.assertNotIn("private-token", business_error.public_message)
        self.assertNotIn("\n", business_error.public_message)
        self.assertNotIn("private-value", business_error.diagnostic_message)
        self.assertLessEqual(len(business_error.exception_info), 40)

    def test_outer_error_wrapper_preserves_business_reason(self):
        """验证未进入业务 Handler 的 Odoo UserError 仍返回安全的具体业务原因。"""
        fake_request = SimpleNamespace(ginlong_api_code=None, ginlong_api_error_log=None)

        @ginlong_controller.ginlong_error_response("API07")
        def endpoint():
            """模拟被路由包装器兜底的业务拒绝。"""
            raise ValidationError("Product form is not supported")

        with patch.object(ginlong_controller, "request", fake_request):
            response = endpoint()

        body = json.loads(response.get_data(as_text=True))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(body), {"returnStatus", "exceptionInfo", "operationTime"})
        self.assertEqual(body["returnStatus"], "N")
        self.assertEqual(body["exceptionInfo"], "BUS01: Product form is not supported")
        self.assertEqual(fake_request.ginlong_api_error_log["code"], "BUS01")
        self.assertEqual(
            fake_request.ginlong_api_error_log["message"], "Product form is not supported",
        )

    def test_existing_ginlong_product_identity_is_owner_variant_and_raw_code_is_preserved(self):
        """验证货主专属变体与原始 Ginlong productCode 均被保留。"""
        owner_attribute = self.env.ref("ginlong_apis.product_attribute_ginlong_owner")
        products = self.env["product.product"].with_context(active_test=False).search([
            ("ginlong_owner_code", "!=", False),
        ])
        self.assertTrue(products)
        for product in products:
            with self.subTest(product=product.id):
                self.assertTrue(product.ginlong_product_code)
                self.assertEqual(
                    product.default_code,
                    ginlong_internal_code(product.ginlong_owner_code, product.ginlong_product_code),
                )
                owner_line = product.product_tmpl_id.attribute_line_ids.filtered(
                    lambda line: line.attribute_id == owner_attribute
                )
                self.assertEqual(len(owner_line), 1)
                owner_value = owner_line.value_ids.filtered(lambda value: value.name == product.ginlong_owner_code)
                self.assertEqual(len(owner_value), 1)
                product_ptavs = product.product_template_attribute_value_ids.filtered(
                    lambda value: value.product_attribute_value_id == owner_value
                )
                self.assertEqual(len(product_ptavs), 1)

    def test_api02_receipt_details_persist_actual_inbound_data(self):
        """验证 API02 收货明细持久化关联实际入库数据。"""
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
        """验证 API08 发货明细持久化关联实际出库数据。"""
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
        """验证 API06 汇总值来自已保存的实际备货数据及人工覆盖值。"""
        self.assertEqual(ginlong_callbacks._decimal_string(12.34), "12.34")
        self.assertEqual(ginlong_callbacks._decimal_string(1.1234567), "1.123457")
        result = services.api03(self.env, self.api_user, self._api03("GINLONG-API06-TOTALS"))
        order = self.env["world.depot.outbound.order"].browse(result["data"]["id"])
        picking, product = self._create_actual_picking(order, incoming=False, suffix="API06-TOTALS")
        product.product_tmpl_id.write({"weight": 1.5, "ginlong_weight": 2.5})
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
            status_code=200, text='{"returnStatus":"Y","exceptionInfo":"OK","operationTime":"2026-06-01 14:30:25"}',
            json=lambda: {"returnStatus": "Y", "exceptionInfo": "OK", "operationTime": "2026-06-01 14:30:25"},
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
        """验证 API01 和 API03 按契约更新既有订单。"""
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
        self.assertEqual(inbound_order.ginlong_owner_id.ginlong_owner_code, "OWNER-02")
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
            "owner": "OWNER-01", "action": "Edit", "outboundOrderNo": outbound_order.reference,
            "warehouse": "WH-02", "businessType": "UPDATED", "remark": "updated outbound",
        })
        self.assertEqual(outbound_order.ginlong_owner_code, "OWNER-01")
        self.assertEqual(outbound_order.ginlong_owner_id.ginlong_owner_code, "OWNER-01")
        self.assertEqual(outbound_order.ginlong_warehouse_code, "WH-02")
        self.assertEqual(outbound_order.ginlong_business_type, "UPDATED")
        self.assertEqual(outbound_order.remark, "updated outbound")
        self.assertEqual(outbound_order.picking_PICK, outbound_picking)
        self.assertTrue(outbound_picking.exists())
        self.assertEqual(outbound_picking.move_line_ids, outbound_move_line)
        self.assertEqual(outbound_move_line.quantity, 2)

    def test_api05_update_existing_customer_instruction_without_stock_access(self):
        """验证 API05 更新客户盘点指令但不访问库存。"""
        created = services.api05(self.env, self.api_user, {
            "owner": "OWNER-01", "action": "Add", "countOrderNo": "COUNT-UPDATE",
            "warehouse": "WH-01", "details": [{
                "productCode": self.product.ginlong_product_code, "productName": "Before",
                "specificationModel": "MODEL", "quantity": 0,
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
        """验证五个回传入口使用持久化表单字段而非临时 Wizard。"""
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
        """验证 API02 从已保存收货明细生成报文，并为每次重试追加日志。"""
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
            status_code=200, text='{"returnStatus":"Y","exceptionInfo":"OK","operationTime":"2026-06-01 14:30:25"}',
            json=lambda: {"returnStatus": "Y", "exceptionInfo": "OK", "operationTime": "2026-06-01 14:30:25"},
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
        self.assertEqual(logs[0].source_record, order)
        self.assertEqual(logs[1].source_record, order)
        self.assertIn('"receiptConfirmed": "Y"', logs[0].request_data)
        self.assertIn('"receiptConfirmed": "N"', logs[1].request_data)

    def test_api02_and_api08_block_mixed_saved_detail_statuses(self):
        """验证 API02 和 API08 在明细状态混合时阻止生成订单级结果。"""
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
        """验证回传表单暴露已有 Order 和 Picking 数据来源。"""
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
        """验证 API06 和 API08 只发送已保存的实际作业数据。"""
        result = services.api03(self.env, self.api_user, self._api03("GINLONG-CALLBACK-API06-08"))
        order = self.env["world.depot.outbound.order"].browse(result["data"]["id"])
        endpoint_06 = "http://mock.invalid/API/WMS_JSON/api06-%s" % order.id
        endpoint_08 = "http://mock.invalid/API/WMS_JSON/api08-%s" % order.id
        params = self.env["ir.config_parameter"].sudo()
        params.set_param("ginlong_apis.api06_callback_url", endpoint_06)
        params.set_param("ginlong_apis.api08_callback_url", endpoint_08)
        picking, product = self._create_actual_picking(order, incoming=False, suffix="API06-08-PAYLOAD")
        product.product_tmpl_id.ginlong_weight = 1.25
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
            status_code=200, text='{"returnStatus":"Y","exceptionInfo":"OK","operationTime":"2026-06-01 14:30:25"}',
            json=lambda: {"returnStatus": "Y", "exceptionInfo": "OK", "operationTime": "2026-06-01 14:30:25"},
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
        """验证 API04 从已保存 move line 取数并记录响应。"""
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
            text='{"returnStatus":"Y","exceptionInfo":"OK","operationTime":"2026-06-01 14:30:25"}',
            json=lambda: {"returnStatus": "Y", "exceptionInfo": "OK", "operationTime": "2026-06-01 14:30:25"},
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
            "productCode": product.ginlong_product_code,
            "operator": "actual.worker",
            "operationTime": fields.Datetime.to_string(operation_time),
        }])
        log = self.env["world.depot.api.log"].search([("request_path", "=", endpoint)], order="id desc", limit=1)
        self.assertTrue(log.success)
        self.assertIn('"action": "CREATE"', log.request_data)
        self.assertIn('"returnStatus":"Y"', log.response_data)

    def test_api04_failure_can_be_edited_and_retried_with_separate_logs(self):
        """验证 API04 失败后可修改数据重试且日志分别追加。"""
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
            text='{"returnStatus":"Y","exceptionInfo":"OK","operationTime":"2026-06-01 14:30:25"}',
            json=lambda: {"returnStatus": "Y", "exceptionInfo": "OK", "operationTime": "2026-06-01 14:30:25"},
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
        """验证 API10 持久化 Action 范围并且只读取已保存实盘结果。"""
        order = self.env["world.depot.stocktake.order"].create({
            "count_order_no": "COUNT-CALLBACK-PERSISTED",
            "project_id": self.project.id,
            "owner_code": "OWNER-COUNT",
            "warehouse_code": "WH-COUNT",
        })
        result_one = self.env["world.depot.stocktake.result"].create({
            "order_id": order.id,
            "product_id": self.product.id,
            "product_code": self.product.ginlong_product_code,
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
            "product_code": self.product.ginlong_product_code,
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
            text='{"returnStatus":"Y","exceptionInfo":"OK","operationTime":"2026-06-01 14:30:25"}',
            json=lambda: {"returnStatus": "Y", "exceptionInfo": "OK", "operationTime": "2026-06-01 14:30:25"},
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
        """验证回传日志不会泄露 Endpoint 凭据。"""
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
        """验证相同规范化请求只执行一次并复用成功结果。"""
        # API01/03/05 的重复 Add 是业务冲突；此处用 API07 验证通用 once 请求的并发/重试重放能力。
        payload = {"owner": "IDEM-OWNER", "productCode": "GINLONG-IDEM-001", "action": "Add"}
        calls = []

        def operation():
            """记录业务处理调用次数并返回结果，用于断言规范化请求只执行一次。"""
            calls.append(True)
            return {"success": True, "data": {"id": 123}}

        first = idempotency.execute(self.env, "API07", payload, operation)
        replay_payload = dict(reversed(list(payload.items())))
        replay = idempotency.execute(self.env, "API07", replay_payload, operation)
        self.assertEqual(first, replay)
        self.assertEqual(len(calls), 1)
        self.assertEqual(self.env["ginlong.api.idempotency"].search_count([
            ("api_code", "=", "API07"),
            ("business_key", "=", idempotency._business_key("API07", payload)),
        ]), 1)
        self.assertEqual(
            idempotency._canonical_json({"a": 1, "b": [1, 2]}),
            idempotency._canonical_json({"b": [1, 2], "a": 1}),
        )
        self.assertNotEqual(
            idempotency._canonical_json({"items": [1, 2]}),
            idempotency._canonical_json({"items": [2, 1]}),
        )

    def test_idempotency_business_keys_and_api01_duplicate_add_rejection(self):
        """验证业务键配置及 API01 Add 的同键重复请求拒绝策略。"""
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
        self.assertTrue(first["success"])
        with self.assertRaises(ginlong_errors.GinlongAPIError) as duplicate:
            idempotency.execute(
                self.env, "API01", update_payload,
                lambda: calls.append("update") or {"success": True, "data": {"state": "new", "remark": "changed"}},
            )
        self.assertEqual(duplicate.exception.error_code, "IDM02")
        self.assertEqual(calls, ["create"])
        self.assertEqual(self.env["ginlong.api.idempotency"].search_count([
            ("api_code", "=", "API01"), ("business_key", "=", "IN-DIFF"),
        ]), 1)

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
        ]), 0)

    def test_idempotency_failure_rolls_back_and_allows_retry(self):
        """验证失败请求回滚幂等记录，后续请求可以安全重试。"""
        payload = self._api01("GINLONG-IDEM-RETRY")

        def failed_operation():
            """先创建临时联系人再抛出校验异常，以验证失败事务整体回滚。"""
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
        """验证缺少业务键时不会创建成功幂等记录。"""
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
            failure_body = json.loads(response.get_data(as_text=True))
            self.assertEqual(set(failure_body), {"returnStatus", "exceptionInfo", "operationTime"})
            self.assertEqual(failure_body["returnStatus"], "N")
            self.assertTrue(failure_body["exceptionInfo"].startswith(("REQ01: ", "REQ02: ")))
            self.assertEqual(
                self.env["ginlong.api.idempotency"].search_count([("api_code", "=", api_code)]),
                before_count,
            )

    def test_database_concurrency_errors_are_left_for_odoo_http_retry(self):
        """验证数据库并发异常交由 Odoo HTTP 事务机制处理。"""
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
            """抛出数据库并发异常，验证日志装饰器不会吞掉 Odoo 可重试错误。"""
            raise error_class("simulated logger concurrency conflict")

        with patch.object(api_logs, "request", logger_request):
            with self.assertRaises(error_class):
                raise_concurrency_error()

    def test_api_rate_defaults_and_configuration(self):
        """验证四个入站 API 的默认限流值和后台配置读取。"""
        settings = self.env["res.config.settings"].sudo()
        self.assertEqual(settings.get_ginlong_api_rate_limit("API01"), 10)
        self.assertEqual(settings.get_ginlong_api_rate_limit("API03"), 10)
        self.assertEqual(settings.get_ginlong_api_rate_limit("API05"), 10)
        self.assertEqual(settings.get_ginlong_api_rate_limit("API07"), 100)
        self.env["ir.config_parameter"].sudo().set_param("ginlong_apis.api07_rate_limit", "140")
        self.assertEqual(settings.get_ginlong_api_rate_limit("API07"), 140)

    def test_routes_use_worlddepot_token_and_api_log_decorators(self):
        """验证 Ginlong 路由复用 WorldDepot Token 和 API 日志装饰器。"""
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
            """返回 Token 装饰器认证后写入请求上下文的 API 用户。"""
            return validator_token.request.api_user

        with patch.object(validator_token, "request", fake_request):
            authenticated_api_user = authenticated_endpoint()

        self.assertEqual(authenticated_api_user, self.api_user)
        self.assertIs(ginlong_controller.validate_token, validator_token.validate_token)
        self.assertIs(ginlong_controller.api_logger, api_logs.api_logger)
        controller = ginlong_controller.GinlongSimulationController
        for route_name in ("api01", "api03", "api05", "api07", "api09"):
            function = getattr(controller, route_name)
            wrapper_count = 0
            while function:
                wrapper_count += 1
                function = getattr(function, "__wrapped__", False)
            self.assertGreaterEqual(wrapper_count, 3)
        api09_route = controller.api09.original_routing
        self.assertEqual(api09_route["routes"], ["/api/ginlong/TPL_Stock_Query"])
        self.assertEqual(api09_route["methods"], ["POST"])
        self.assertEqual(api09_route["type"], "http")

    def test_api01_decorated_route_authenticates_and_logs_with_existing_logger(self):
        """验证 API01 路由沿用现有认证与日志链路。"""
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
            """为日志装饰器提供轻量日志环境，并让业务事务使用原 Odoo Environment。"""
            if isinstance(cr, _CursorContext):
                return log_environment
            return original_environment(cr, uid, context, *args, **kwargs)

        def request_context(body, token):
            """构造带请求体和 Bearer Token 的 API01 测试请求上下文。"""
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
        # Ginlong API01 只返回协议三字段；内部 success 标记只保存在业务/幂等结果中。
        self.assertEqual(set(response_body), {"returnStatus", "exceptionInfo", "operationTime"})
        self.assertEqual(response_body["returnStatus"], "Y")
        self.assertEqual(response_body["exceptionInfo"], "OK")
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
        rejected_body = json.loads(rejected.get_data(as_text=True))
        self.assertEqual(set(rejected_body), {"returnStatus", "exceptionInfo", "operationTime"})
        self.assertTrue(rejected_body["exceptionInfo"].startswith("AUTH01: "))
        self.assertEqual(existing, self.env["world.depot.inbound.order"].search([("reference", "=", "GINLONG-IN-ROUTE")]))

    def test_rate_limit_response_is_http_429_and_logged(self):
        """验证超限请求返回 HTTP 429 并写入现有日志。"""
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
            """将日志游标映射到轻量环境，其他模型环境继续委托给 Odoo。"""
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
        body = json.loads(response.get_data(as_text=True))
        self.assertEqual(set(body), {"returnStatus", "exceptionInfo", "operationTime"})
        self.assertTrue(body["exceptionInfo"].startswith("RATE01: "))
        self.assertEqual(log_model.values[0]["code"], "RATE01")
        self.assertEqual(log_model.values[0]["msg"], "API请求频率超限")
        self.assertFalse(log_model.values[0]["success"])

    def test_api09_returns_owner_scoped_physical_stock_read_only(self):
        """验证 API09 按货主返回实际物理库存且查询只读。"""
        other_owner = self.env["res.partner"].create({
            "name": "Ginlong API09 second owner partner",
            "is_company": True,
            "ginlong_owner_code": "OWNER-02",
        })
        other_owner_product = self.env["product.product"].create({
            "name": "Ginlong API09 same-code second owner",
            "default_code": ginlong_internal_code("OWNER-02", self.product.ginlong_product_code),
            "ginlong_owner_code": "OWNER-02",
            "ginlong_product_code": self.product.ginlong_product_code,
            "type": "consu",
        })
        self.product.product_tmpl_id.is_storable = True
        other_owner_product.product_tmpl_id.is_storable = True
        second_product_same_owner = self.env["product.product"].create({
            "name": "Ginlong API09 second item same owner",
            "default_code": ginlong_internal_code("OWNER-01", "GINLONG-API09-SECOND-001"),
            "ginlong_owner_code": "OWNER-01",
            "ginlong_product_code": "GINLONG-API09-SECOND-001",
            "type": "consu",
        })
        second_product_same_owner.product_tmpl_id.is_storable = True
        second_location = self.env["stock.location"].create({
            "name": "Ginlong API09 internal test location",
            "location_id": self.warehouse.lot_stock_id.id,
            "usage": "internal",
            "company_id": self.env.company.id,
        })
        quant_model = self.env["stock.quant"].sudo()
        quant_model.create({
            "product_id": self.product.id,
            "location_id": self.warehouse.lot_stock_id.id,
            "owner_id": self.owner.id,
            "quantity": 3.25,
            "reserved_quantity": 1.0,
        })
        quant_model.create({
            "product_id": self.product.id,
            "location_id": second_location.id,
            "owner_id": self.owner.id,
            "quantity": 2.5,
            "reserved_quantity": 0.5,
        })
        quant_model.create({
            "product_id": other_owner_product.id,
            "location_id": self.warehouse.lot_stock_id.id,
            "owner_id": other_owner.id,
            "quantity": 9.75,
            "reserved_quantity": 9.0,
        })
        quant_model.create({
            "product_id": second_product_same_owner.id,
            "location_id": self.warehouse.lot_stock_id.id,
            "owner_id": self.owner.id,
            "quantity": 7.125,
            "reserved_quantity": 0.125,
        })

        quant_domain = [("location_id", "child_of", self.warehouse.view_location_id.id)]
        before_quants = quant_model.search(quant_domain).read(["quantity", "reserved_quantity", "write_date"])
        before_moves = self.env["stock.move"].sudo().search_count([])
        owner_one = services.api09(self.env, {"owner": "OWNER-01", "warehouse": self.warehouse.code})
        owner_two = services.api09(self.env, {"owner": "OWNER-02", "warehouse": self.warehouse.code})
        empty_owner = services.api09(self.env, {"owner": "OWNER-EMPTY", "warehouse": self.warehouse.code})
        after_quants = quant_model.search(quant_domain).read(["quantity", "reserved_quantity", "write_date"])

        self.assertEqual(set(owner_one), {
            "returnStatus", "exceptionInfo", "operationTime", "owner", "warehouse", "inventoryList",
        })
        self.assertEqual(owner_one["returnStatus"], "Y")
        self.assertEqual(owner_one["exceptionInfo"], "OK")
        self.assertEqual(owner_one["owner"], "OWNER-01")
        self.assertEqual(owner_one["warehouse"], self.warehouse.code)
        self.assertEqual(owner_one["inventoryList"], [
            {"productCode": self.product.ginlong_product_code, "quantity": 5.75},
            {"productCode": second_product_same_owner.ginlong_product_code, "quantity": 7.13},
        ])
        self.assertTrue(all(isinstance(row["quantity"], float) for row in owner_one["inventoryList"]))
        self.assertEqual(owner_two["inventoryList"], [{"productCode": self.product.ginlong_product_code, "quantity": 9.75}])
        self.assertEqual(empty_owner["inventoryList"], [])
        self.assertEqual(before_quants, after_quants)
        self.assertEqual(before_moves, self.env["stock.move"].sudo().search_count([]))

    def test_cc005_api09_reads_inventory_from_completed_standard_pickings(self):
        """验证 API09 库存夹具只由标准入库 Picking 过账产生。"""
        owner_b = self.env["res.partner"].create({
            "name": "Ginlong CC005 owner B",
            "is_company": True,
            "ginlong_owner_code": "CC005-OWNER-B",
        })

        def api07_product(owner_code, code, name):
            """通过 API07 建立指定货主的 Ginlong 产品变体并返回 ORM 记录。"""
            result = services.api07(self.env, self.api_user, {
                "action": "Add",
                "owner": owner_code,
                "productCode": code,
                "productName": name,
                "specificationModel": "CC005-MODEL",
                "unit": self.env.ref("uom.product_uom_unit").name,
                "productForm": "原材料",
                "weight": 1,
            })
            return self.env["product.product"].browse(result["data"]["id"])

        product_a1 = api07_product("OWNER-01", "CC005-P001", "CC005 product 1")
        product_b1 = api07_product("CC005-OWNER-B", "CC005-P001", "CC005 product 1")
        product_a2 = api07_product("OWNER-01", "CC005-P002", "CC005 product 2 owner A")
        products = (
            (self.owner, product_a1, 100),
            (owner_b, product_b1, 300),
            (self.owner, product_a2, 200),
        )
        self.assertEqual(product_a1.product_tmpl_id, product_b1.product_tmpl_id)
        self.assertNotEqual(product_a1, product_b1)
        self.assertTrue(all(product.product_tmpl_id.is_storable for _owner, product, _qty in products))

        before_picking_ids = set(self.env["stock.picking"].search([]).ids)
        for owner, product, quantity in products:
            picking = self.env["stock.picking"].create({
                "picking_type_id": self.warehouse.in_type_id.id,
                "location_id": self.warehouse.in_type_id.default_location_src_id.id,
                "location_dest_id": self.warehouse.lot_stock_id.id,
                "move_ids": [(0, 0, {
                    "name": "Ginlong CC005 receipt %s" % product.ginlong_product_code,
                    "product_id": product.id,
                    "product_uom_qty": quantity,
                    "product_uom": product.uom_id.id,
                    "location_id": self.warehouse.in_type_id.default_location_src_id.id,
                    "location_dest_id": self.warehouse.lot_stock_id.id,
                })],
            })
            picking.action_confirm()
            lines = picking.move_line_ids
            self.assertTrue(lines, "Standard receipt confirmation must create detailed operations")
            lines.write({"quantity": quantity, "owner_id": owner.id})
            picking.move_ids.picked = True
            picking.button_validate()
            self.assertEqual(picking.state, "done")

        created_pickings = self.env["stock.picking"].search([]).filtered(
            lambda picking: picking.id not in before_picking_ids
        )
        self.assertEqual(len(created_pickings), 3)
        internal_locations = self.env["stock.location"].search([
            ("id", "child_of", self.warehouse.view_location_id.id),
            ("usage", "=", "internal"),
        ])
        relevant_quants = self.env["stock.quant"].search([
            ("product_id", "in", (product_a1 | product_b1 | product_a2).ids),
            ("location_id", "in", internal_locations.ids),
        ])
        before_query_quants = relevant_quants.read(["quantity", "reserved_quantity", "write_date"])
        before_query_moves = self.env["stock.move"].search_count([
            ("product_id", "in", (product_a1 | product_b1 | product_a2).ids),
        ])
        result_a = services.api09(self.env, {"owner": "OWNER-01", "warehouse": self.warehouse.code})
        result_b = services.api09(self.env, {"owner": "CC005-OWNER-B", "warehouse": self.warehouse.code})
        self.assertEqual(result_a["inventoryList"], [
            {"productCode": "CC005-P001", "quantity": 100.0},
            {"productCode": "CC005-P002", "quantity": 200.0},
        ])
        self.assertEqual(result_b["inventoryList"], [
            {"productCode": "CC005-P001", "quantity": 300.0},
        ])
        self.assertEqual(set(created_pickings.mapped("state")), {"done"})
        after_query_quants = relevant_quants.read(["quantity", "reserved_quantity", "write_date"])
        after_query_moves = self.env["stock.move"].search_count([
            ("product_id", "in", (product_a1 | product_b1 | product_a2).ids),
        ])
        self.assertEqual(before_query_quants, after_query_quants)
        self.assertEqual(before_query_moves, after_query_moves)

    def test_api09_unknown_owner_does_not_return_other_owner_inventory(self):
        """验证未知货主请求不会泄露其他货主库存。"""
        other_owner = self.env["res.partner"].create({
            "name": "Ginlong API09 existing different owner",
            "is_company": True,
            "ginlong_owner_code": "OWNER-EXISTS",
        })
        other_owner_product = self.env["product.product"].create({
            "name": "Ginlong API09 inventory belonging to another owner",
            "default_code": "GINLONG-API09-OTHER-OWNER",
            "ginlong_owner_code": "OWNER-EXISTS",
            "ginlong_product_code": "GINLONG-API09-OTHER-OWNER",
            "type": "consu",
        })
        other_owner_product.product_tmpl_id.is_storable = True
        self.env["stock.quant"].sudo().create({
            "product_id": other_owner_product.id,
            "location_id": self.warehouse.lot_stock_id.id,
            "owner_id": other_owner.id,
            "quantity": 12,
        })

        response = services.api09(self.env, {
            "owner": "OWNER-DOES-NOT-EXIST",
            "warehouse": self.warehouse.code,
        })

        self.assertEqual(response["owner"], "OWNER-DOES-NOT-EXIST")
        self.assertEqual(response["inventoryList"], [])

    def test_api09_cross_owner_warehouse_inventory_matrix(self):
        """验证 API09 在货主、仓库和产品维度正确隔离库存。"""
        owner_b = self.env["res.partner"].create({
            "name": "Ginlong API09 matrix owner B",
            "is_company": True,
            "ginlong_owner_code": "OWNER-B",
        })
        warehouse_b = self.env["stock.warehouse"].create({
            "name": "Ginlong API09 matrix warehouse B",
            "code": "WHB",
            "company_id": self.env.company.id,
        })
        product_a = self.env["product.product"].create({
            "name": "Ginlong API09 matrix owner A product",
            "default_code": ginlong_internal_code(self.owner.ginlong_owner_code, "P001"),
            "ginlong_owner_code": self.owner.ginlong_owner_code,
            "ginlong_product_code": "P001",
            "type": "consu",
        })
        product_b = self.env["product.product"].create({
            "name": "Ginlong API09 matrix owner B product",
            "default_code": ginlong_internal_code(owner_b.ginlong_owner_code, "P001"),
            "ginlong_owner_code": owner_b.ginlong_owner_code,
            "ginlong_product_code": "P001",
            "type": "consu",
        })
        product_b_second = self.env["product.product"].create({
            "name": "Ginlong API09 matrix owner B second product",
            "default_code": ginlong_internal_code(owner_b.ginlong_owner_code, "P002"),
            "ginlong_owner_code": owner_b.ginlong_owner_code,
            "ginlong_product_code": "P002",
            "type": "consu",
        })
        for product in (product_a, product_b, product_b_second):
            product.product_tmpl_id.is_storable = True

        quant_model = self.env["stock.quant"].sudo()
        quant_model.create({
            "product_id": product_a.id,
            "location_id": self.warehouse.lot_stock_id.id,
            "owner_id": self.owner.id,
            "quantity": 100,
        })
        quant_model.create({
            "product_id": product_a.id,
            "location_id": warehouse_b.lot_stock_id.id,
            "owner_id": self.owner.id,
            "quantity": 200,
        })
        quant_model.create({
            "product_id": product_b.id,
            "location_id": self.warehouse.lot_stock_id.id,
            "owner_id": owner_b.id,
            "quantity": 300,
        })
        quant_model.create({
            "product_id": product_b_second.id,
            "location_id": warehouse_b.lot_stock_id.id,
            "owner_id": owner_b.id,
            "quantity": 400,
        })

        combinations = (
            (self.owner.ginlong_owner_code, self.warehouse.code, "P001", 100.0),
            (self.owner.ginlong_owner_code, warehouse_b.code, "P001", 200.0),
            (owner_b.ginlong_owner_code, self.warehouse.code, "P001", 300.0),
            (owner_b.ginlong_owner_code, warehouse_b.code, "P002", 400.0),
        )
        for owner_code, warehouse_code, product_code, quantity in combinations:
            with self.subTest(owner=owner_code, warehouse=warehouse_code):
                result = services.api09(self.env, {
                    "owner": owner_code,
                    "warehouse": warehouse_code,
                })
                self.assertEqual(result["inventoryList"], [{
                    "productCode": product_code,
                    "quantity": quantity,
                }])

        owner_without_stock = self.env["res.partner"].create({
            "name": "Ginlong API09 owner without inventory",
            "is_company": True,
            "ginlong_owner_code": "OWNER-NO-STOCK",
        })
        empty_inventory = services.api09(self.env, {
            "owner": owner_without_stock.ginlong_owner_code,
            "warehouse": self.warehouse.code,
        })
        self.assertEqual(empty_inventory["inventoryList"], [])

        unknown_owner_result = services.api09(self.env, {
            "owner": "OWNER-DOES-NOT-EXIST",
            "warehouse": self.warehouse.code,
        })
        self.assertEqual(unknown_owner_result["inventoryList"], [])
        with self.assertRaises(ValidationError):
            services.api09(self.env, {
                "owner": self.owner.ginlong_owner_code,
                "warehouse": "NO-WH",
            })
        with self.assertRaises(ValidationError):
            services.api09(self.env, {
                "owner": "OWNER-DOES-NOT-EXIST",
                "warehouse": "NO-WH",
            })

    def test_api09_validates_required_fields(self):
        """验证 API09 在库存 ORM 查询前拒绝缺失或空白请求字段。"""
        cases = (
            ({"warehouse": self.warehouse.code}, ValueError),
            ({"owner": "OWNER-01"}, ValueError),
            ({"owner": "", "warehouse": self.warehouse.code}, ValueError),
            ({"owner": None, "warehouse": self.warehouse.code}, ValueError),
            # false 有值，不属于必填空值；无效编码由后续 Odoo 业务匹配拒绝。
            ({"owner": False, "warehouse": self.warehouse.code}, ValidationError),
            ({"owner": "   ", "warehouse": self.warehouse.code}, ValueError),
            ({"owner": "OWNER-01", "warehouse": ""}, ValueError),
            ({"owner": "OWNER-01", "warehouse": None}, ValueError),
            ({"owner": "OWNER-01", "warehouse": False}, ValidationError),
            ({"owner": "OWNER-01", "warehouse": "   "}, ValueError),
        )
        for payload, expected_error in cases:
            with self.subTest(payload=payload), self.assertRaises(expected_error):
                services.api09(self.env, payload)

    def test_api09_route_uses_existing_token_and_api_logger(self):
        """验证 API09 路由复用现有 Token 认证和 API 日志。"""
        token_value = "ginlong-api09-test-token"
        self.env["world.depot.api.token"].create({
            "user_id": self.api_user.user_id.id,
            "token": token_value,
            "expires": fields.Datetime.now() + timedelta(hours=1),
        })
        log_model = _LogModel()
        log_environment = _LogEnvironment(log_model)
        original_environment = api_logs.api.Environment

        def environment_factory(cr, uid, context, *args, **kwargs):
            """为 API09 日志断言提供轻量日志环境，其余情况使用原 ORM 环境。"""
            if isinstance(cr, _CursorContext):
                return log_environment
            return original_environment(cr, uid, context, *args, **kwargs)

        self.product.product_tmpl_id.is_storable = True
        self.env["stock.quant"].sudo().create({
            "product_id": self.product.id,
            "location_id": self.warehouse.lot_stock_id.id,
            "owner_id": self.owner.id,
            "quantity": 23,
        })
        fake_request = SimpleNamespace(
            httprequest=SimpleNamespace(
                data=json.dumps({"owner": "OWNER-01", "warehouse": self.warehouse.code}).encode(),
                remote_addr="127.0.0.1",
                path="/api/ginlong/TPL_Stock_Query",
                headers={"Authorization": "Bearer " + token_value, "Content-Type": "application/json"},
            ),
            env=self.env,
            registry=SimpleNamespace(cursor=_CursorContext),
            api_user=False,
            update_env=lambda user: None,
        )
        endpoint = ginlong_controller.GinlongSimulationController()
        with patch.object(validator_token, "request", fake_request), \
                patch.object(api_logs, "request", fake_request), \
                patch.object(ginlong_controller, "request", fake_request), \
                patch.object(api_logs.api, "Environment", side_effect=environment_factory):
            response = endpoint.api09()

        response_body = json.loads(response.get_data(as_text=True))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_body["returnStatus"], "Y")
        self.assertEqual(response_body["owner"], "OWNER-01")
        self.assertEqual(response_body["warehouse"], self.warehouse.code)
        self.assertEqual(response_body["inventoryList"], [
            {"productCode": self.product.ginlong_product_code, "quantity": 23.0},
        ])
        self.assertEqual(len(log_model.values), 1)
        self.assertEqual(log_model.values[0]["request_path"], "/api/ginlong/TPL_Stock_Query")
        self.assertTrue(log_model.values[0]["success"])
        self.assertNotIn(token_value, str(log_model.values[0]))

        fake_request.httprequest.data = json.dumps({
            "owner": "OWNER-01",
            "warehouse": "WAREHOUSE-DOES-NOT-EXIST",
        }).encode()
        with patch.object(validator_token, "request", fake_request), \
                patch.object(api_logs, "request", fake_request), \
                patch.object(ginlong_controller, "request", fake_request), \
                patch.object(api_logs.api, "Environment", side_effect=environment_factory):
            unknown_warehouse = endpoint.api09()
        unknown_warehouse_body = json.loads(unknown_warehouse.get_data(as_text=True))
        self.assertEqual(unknown_warehouse.status_code, 400)
        self.assertEqual(
            set(unknown_warehouse_body), {"returnStatus", "exceptionInfo", "operationTime"},
        )
        self.assertNotIn("inventoryList", unknown_warehouse_body)
        self.assertTrue(unknown_warehouse_body["exceptionInfo"].startswith("BUS01: "))
        self.assertEqual(len(log_model.values), 2)
        self.assertFalse(log_model.values[-1]["success"])

        fake_request.api_user = False
        fake_request.httprequest.headers["Authorization"] = "Bearer invalid-api09-token"
        with patch.object(validator_token, "request", fake_request), \
                patch.object(api_logs, "request", fake_request), \
                patch.object(ginlong_controller, "request", fake_request), \
                patch.object(api_logs.api, "Environment", side_effect=environment_factory), \
                patch.object(ginlong_controller.services, "api09") as query:
            unauthorized = endpoint.api09()
        self.assertEqual(unauthorized.status_code, 401)
        unauthorized_body = json.loads(unauthorized.get_data(as_text=True))
        self.assertEqual(set(unauthorized_body), {"returnStatus", "exceptionInfo", "operationTime"})
        self.assertTrue(unauthorized_body["exceptionInfo"].startswith("AUTH01: "))
        query.assert_not_called()
        self.assertEqual(len(log_model.values), 3)
        self.assertEqual(log_model.values[-1]["code"], "AUTH01")

        fake_request.httprequest.headers["Authorization"] = "Bearer " + token_value
        fake_request.httprequest.data = json.dumps({"owner": "OWNER-01"}).encode()
        with patch.object(validator_token, "request", fake_request), \
                patch.object(api_logs, "request", fake_request), \
                patch.object(ginlong_controller, "request", fake_request), \
                patch.object(api_logs.api, "Environment", side_effect=environment_factory):
            invalid_request = endpoint.api09()
        self.assertEqual(invalid_request.status_code, 400)
        self.assertEqual(len(log_model.values), 4)
        self.assertEqual(log_model.values[-1]["code"], "REQ01")
        self.assertEqual(log_model.values[-1]["status"], "error")
        self.assertFalse(log_model.values[-1].get("source_record"))

    def test_ginlong_management_actions_logs_acl_and_source_navigation(self):
        """验证 Ginlong 管理入口、API隔离、只读权限和来源单据导航。"""
        log_model = self.env["world.depot.api.log"]
        self.assertEqual(log_model._fields["source_record"].type, "reference")
        self.assertEqual(log_model._fields["ginlong_api_code"].type, "selection")
        model_record = self.env["ir.model"].sudo().search([("model", "=", "world.depot.api.log")], limit=1)
        manager_acl = self.env["ir.model.access"].sudo().search([
            ("model_id", "=", model_record.id),
            ("group_id", "=", self.env.ref("stock.group_stock_manager").id),
        ], limit=1)
        self.assertTrue(manager_acl.perm_read)
        self.assertFalse(manager_acl.perm_write)
        self.assertFalse(manager_acl.perm_create)
        self.assertFalse(manager_acl.perm_unlink)
        ordinary_user = self.env["res.users"].with_context(no_reset_password=True).create({
            "name": "Ginlong API log reader denied",
            "login": "ginlong-log-denied-%s" % uuid.uuid4().hex,
            "groups_id": [(6, 0, [self.env.ref("base.group_user").id])],
        })
        manager_user = self.env["res.users"].with_context(no_reset_password=True).create({
            "name": "Ginlong API log manager",
            "login": "ginlong-log-manager-%s" % uuid.uuid4().hex,
            "groups_id": [(6, 0, [
                self.env.ref("base.group_user").id,
                self.env.ref("stock.group_stock_manager").id,
            ])],
        })
        with self.assertRaises(AccessError):
            log_model.with_user(ordinary_user).check_access("read")
        log_model.with_user(manager_user).check_access("read")

        idempotency_model = self.env["ginlong.api.idempotency"]
        idempotency_manager_acl = self.env["ir.model.access"].sudo().search([
            ("model_id", "=", self.env["ir.model"]._get(idempotency_model._name).id),
            ("group_id", "=", self.env.ref("stock.group_stock_manager").id),
        ], limit=1)
        self.assertTrue(idempotency_manager_acl.perm_read)
        self.assertFalse(idempotency_manager_acl.perm_write)
        self.assertFalse(idempotency_manager_acl.perm_create)
        self.assertFalse(idempotency_manager_acl.perm_unlink)

        isolated_key = "GINLONG-MANAGEMENT-%s" % uuid.uuid4().hex
        ginlong_log = log_model.sudo().create({
            "request_time": fields.Datetime.now(),
            "request_path": "/api/ginlong/TPL_Product_Master",
            "request_data": json.dumps({"owner": "OWNER-A", "productCode": isolated_key}),
            "status": "success",
            "success": True,
        })
        other_client_log = log_model.sudo().create({
            "request_time": fields.Datetime.now(),
            "request_path": "/hoymiles/api/product/master",
            "request_data": json.dumps({"owner": "OTHER-CLIENT", "productCode": isolated_key}),
            "status": "success",
            "success": True,
        })
        self.assertEqual(ginlong_log.ginlong_api_code, "API07")
        expected_log_business_key = json.dumps(
            ["OWNER-A", isolated_key], ensure_ascii=False, separators=(",", ":"),
        )
        self.assertEqual(ginlong_log.ginlong_business_key, expected_log_business_key)
        self.assertFalse(other_client_log.ginlong_api_code)
        self.assertFalse(other_client_log.ginlong_business_key)
        visible_logs = log_model.with_user(manager_user).search([
            ("id", "in", [ginlong_log.id, other_client_log.id]),
        ])
        self.assertEqual(visible_logs.ids, [ginlong_log.id])
        visible_logs_by_business_key = log_model.with_user(manager_user).search([
            ("ginlong_business_key", "=", expected_log_business_key),
        ])
        self.assertEqual(visible_logs_by_business_key.ids, [ginlong_log.id])

        ginlong_idempotency = idempotency_model.sudo().create({
            "api_code": "API07", "direction": "inbound", "action": "add",
            "business_key": isolated_key, "request_fingerprint": "a" * 64,
            "state": "succeeded", "attempt_count": 1,
            "response_json": json.dumps({"success": True, "data": {"id": 123}}),
        })
        other_api_idempotency = idempotency_model.sudo().create({
            "api_code": "API11", "direction": "inbound", "action": "add",
            "business_key": isolated_key, "request_fingerprint": "b" * 64,
            "state": "succeeded", "attempt_count": 1, "response_json": "{}",
        })
        visible_idempotency = idempotency_model.with_user(manager_user).search([
            ("id", "in", [ginlong_idempotency.id, other_api_idempotency.id]),
        ])
        self.assertEqual(visible_idempotency.ids, [ginlong_idempotency.id])
        with self.assertRaises(AccessError):
            visible_idempotency.write({"state": "failed"})
        with self.assertRaises(AccessError):
            visible_idempotency.unlink()
        with self.assertRaises(AccessError):
            visible_idempotency.read(["response_json"])
        with self.assertRaises(AccessError):
            log_model.with_user(manager_user).browse(ginlong_log.id).write({"msg": "tampered"})
        with self.assertRaises(AccessError):
            log_model.with_user(manager_user).browse(ginlong_log.id).unlink()

        root_menu = self.env.ref("ginlong_apis.menu_ginlong_root")
        self.assertFalse(root_menu.parent_id)
        self.assertTrue(self.env["ir.module.module"].sudo().search([
            ("name", "=", "ginlong_apis"),
        ], limit=1).application)
        self.assertEqual(self.env.ref("ginlong_apis.menu_ginlong_logs").parent_id, root_menu)
        self.assertEqual(self.env.ref("ginlong_apis.menu_ginlong_idempotency").parent_id, root_menu)
        self.assertEqual(self.env.ref("ginlong_apis.action_ginlong_inbound_orders").res_model, "world.depot.inbound.order")
        self.assertEqual(self.env.ref("ginlong_apis.action_ginlong_outbound_orders").res_model, "world.depot.outbound.order")
        self.assertEqual(self.env.ref("ginlong_apis.action_ginlong_stocktake_orders").res_model, "world.depot.stocktake.order")
        self.assertEqual(self.env.ref("ginlong_apis.action_ginlong_products").res_model, "product.product")
        self.assertEqual(self.env.ref("ginlong_apis.action_ginlong_settings").res_model, "res.config.settings")
        logs_action = self.env.ref("ginlong_apis.action_ginlong_api_logs")
        self.assertEqual(logs_action.res_model, "world.depot.api.log")
        self.assertIn("ginlong_api_code", logs_action.domain)
        self.assertIn("API10", logs_action.domain)
        logs_search_view = self.env.ref("ginlong_apis.view_ginlong_api_log_search")
        self.assertIn("ginlong_business_key", logs_search_view.arch_db)
        self.assertIn("request_data", logs_search_view.arch_db)
        self.assertIn("request_time", logs_search_view.arch_db)
        idempotency_action = self.env.ref("ginlong_apis.action_ginlong_api_idempotency")
        self.assertEqual(idempotency_action.res_model, "ginlong.api.idempotency")
        self.assertIn("API10", idempotency_action.domain)
        self.assertEqual(idempotency_action.search_view_id, self.env.ref("ginlong_apis.view_ginlong_api_idempotency_search"))
        settings_view = self.env.ref("ginlong_apis.res_config_settings_view_form_ginlong_apis")
        self.assertIn("Ginlong APIs", settings_view.arch_db)

        order = self.env["world.depot.inbound.order"].browse(
            services.api01(self.env, self.api_user, self._api01("GINLONG-API09-LOG-SOURCE"))["data"]["id"]
        )
        ginlong_callbacks._write_api_log(
            order, "API02", "http://mock.invalid/API/WMS_JSON/TPL_Receipt_Confirmation",
            {"inboundOrderNo": order.reference}, "{}", 500, "mock failure",
        )
        log = log_model.sudo().search([("source_record", "=", "%s,%s" % (order._name, order.id))], limit=1)
        self.assertTrue(log)
        self.assertFalse(log.success)
        self.assertEqual(log.action_open_source_record()["res_model"], order._name)
        self.assertEqual(log.action_open_source_record()["res_id"], order.id)

    def _required_validator_api01_payload(self):
        """构造符合当前 API01 Add 字段规则的最小报文。"""
        return {
            "owner": "OWNER-01",
            "action": "Add",
            "inboundOrderNo": "VALIDATOR-IN-001",
            "warehouse": "KRWH",
            "businessType": "Purchase",
            "details": [{
                "productCode": "P-01",
                "productName": "测试产品",
                "specificationModel": "MODEL-01",
                "quantity": 0,
            }],
        }

    def test_required_validator_rejects_missing_null_and_blank_but_accepts_zero(self):
        """验证必填空值、嵌套路径、零值和原始报文只读行为。"""
        for marker, value in (("missing", None), ("null", None), ("empty", ""), ("spaces", "   ")):
            payload = self._required_validator_api01_payload()
            if marker == "missing":
                del payload["owner"]
            else:
                payload["owner"] = value
            original = deepcopy(payload)
            with self.subTest(marker=marker), self.assertRaises(required_validator.RequiredFieldError) as error:
                required_validator.validate_required("API01", payload)
            self.assertIn("owner", str(error.exception))
            self.assertEqual(payload, original)

        nested_payload = self._required_validator_api01_payload()
        del nested_payload["details"][0]["productCode"]
        nested_original = deepcopy(nested_payload)
        with self.assertRaises(required_validator.RequiredFieldError) as nested_error:
            required_validator.validate_required("API01", nested_payload)
        self.assertIn("details[0].productCode", str(nested_error.exception))
        self.assertEqual(nested_payload, nested_original)

        zero_payload = self._required_validator_api01_payload()
        original = deepcopy(zero_payload)
        required_validator.validate_required("API01", zero_payload)
        type_validator.validate_field_types("API01", zero_payload)
        self.assertEqual(zero_payload, original)

        false_payload = self._required_validator_api01_payload()
        false_payload["details"][0]["quantity"] = False
        false_original = deepcopy(false_payload)
        required_validator.validate_required("API01", false_payload)
        with self.assertRaises(type_validator.FieldTypeValidationError) as type_error:
            type_validator.validate_field_types("API01", false_payload)
        self.assertIn("details[0].quantity", str(type_error.exception))
        self.assertEqual(false_payload, false_original)

    def test_optional_configured_decimal_skips_only_missing_null_and_empty(self):
        """验证 V3.2 可选 Decimal 与嵌套 Decimal 空值处理和错误路径。"""
        for marker, value in (("missing", None), ("null", None), ("empty", "")):
            payload = {
                "action": "Add",
                "owner": "OWNER-01",
                "productCode": "P-OPTIONAL-01",
                "productName": "可选重量产品",
                "specificationModel": "MODEL-OPTIONAL",
                "unit": "台",
                "productForm": "成品",
            }
            if marker != "missing":
                payload["weight"] = value
            original = deepcopy(payload)
            with self.subTest(marker=marker):
                required_validator.validate_required("API07", payload)
                type_validator.validate_field_types("API07", payload)
                self.assertEqual(payload, original)

        for value in (0, 0.25, "1.250000"):
            payload = {
                "action": "Add",
                "owner": "OWNER-01",
                "productCode": "P-OPTIONAL-02",
                "productName": "可选重量产品",
                "specificationModel": "MODEL-OPTIONAL",
                "unit": "台",
                "productForm": "成品",
                "weight": value,
            }
            original = deepcopy(payload)
            required_validator.validate_required("API07", payload)
            type_validator.validate_field_types("API07", payload)
            self.assertEqual(payload, original)

        invalid_payload = {
            "action": "Add",
            "owner": "OWNER-01",
            "productCode": "P-OPTIONAL-03",
            "productName": "可选重量产品",
            "specificationModel": "MODEL-OPTIONAL",
            "unit": "台",
            "productForm": "成品",
            "weight": "abc",
        }
        original = deepcopy(invalid_payload)
        with self.assertRaises(type_validator.FieldTypeValidationError) as error:
            type_validator.validate_field_types("API07", invalid_payload)
        self.assertIn("weight", str(error.exception))
        self.assertEqual(invalid_payload, original)

        nested_payload = self._required_validator_api01_payload()
        nested_payload["snList"] = [{"quantity": ""}]
        nested_original = deepcopy(nested_payload)
        required_validator.validate_required("API01", nested_payload)
        type_validator.validate_field_types("API01", nested_payload)
        self.assertEqual(nested_payload, nested_original)
        nested_payload["snList"][0]["quantity"] = 0
        type_validator.validate_field_types("API01", nested_payload)
        nested_payload["snList"][0]["quantity"] = "abc"
        with self.assertRaises(type_validator.FieldTypeValidationError) as nested_error:
            type_validator.validate_field_types("API01", nested_payload)
        self.assertIn("snList[0].quantity", str(nested_error.exception))

    def test_required_nested_datetime_and_generic_optional_non_text_types(self):
        """验证必填 DateTime 与通用可选 DECIMAL、DateTime、BOOLEAN 规则。"""
        valid_api04 = {
            "owner": "OWNER-01",
            "action": "CREATE",
            "inboundOrderNo": "IN-DATETIME-01",
            "snList": [{
                "productSN": "SN-01",
                "quantity": 1,
                "palletCode": "PALLET-01",
                "productCode": "P-01",
                "operator": "KR",
                "operationTime": "2026-11-19 12:30:45",
            }],
        }
        valid_original = deepcopy(valid_api04)
        required_validator.validate_required("API04", valid_api04)
        type_validator.validate_field_types("API04", valid_api04)
        self.assertEqual(valid_api04, valid_original)

        for value in (None, "", "   "):
            payload = deepcopy(valid_api04)
            payload["snList"][0]["operationTime"] = value
            original = deepcopy(payload)
            with self.subTest(datetime_value=value), self.assertRaises(required_validator.RequiredFieldError):
                required_validator.validate_required("API04", payload)
            self.assertEqual(payload, original)

        invalid_date = deepcopy(valid_api04)
        invalid_date["snList"][0]["operationTime"] = "2026-02-30 12:30:45"
        invalid_original = deepcopy(invalid_date)
        with self.assertRaises(type_validator.FieldTypeValidationError) as invalid_date_error:
            type_validator.validate_field_types("API04", invalid_date)
        self.assertIn("snList[0].operationTime", str(invalid_date_error.exception))
        self.assertEqual(invalid_date, invalid_original)

        # 用符合 field_rules.json 结构的最小通用规则覆盖当前协议未配置的可选 BOOLEAN。
        generic_rules = {"apis": {"API_TEST": {"request": {
            "fields": [
                {"name": "amount", "required": False, "q_type": "DECIMAL", "precision": 18, "scale": 6},
                {"name": "occurredAt", "required": False, "q_type": "DateTime", "format": "%Y-%m-%d %H:%M:%S"},
                {"name": "enabled", "required": False, "q_type": "BOOLEAN"},
                {"name": "requiredEnabled", "required": True, "q_type": "BOOLEAN"},
            ],
            "collections": [{
                "name": "details",
                "validate_on": ["*"],
                "items": {"fields": [
                    {"name": "amount", "required": False, "q_type": "DECIMAL", "precision": 18, "scale": 6},
                    {"name": "occurredAt", "required": False, "q_type": "DateTime", "format": "%Y-%m-%d %H:%M:%S"},
                    {"name": "enabled", "required": False, "q_type": "BOOLEAN"},
                ]},
            }],
        }}}}
        with patch.object(type_validator, "get_field_rules", return_value=generic_rules), \
                patch.object(required_validator, "get_field_rules", return_value=generic_rules):
            required_boolean = {"requiredEnabled": False}
            required_boolean_original = deepcopy(required_boolean)
            required_validator.validate_required("API_TEST", required_boolean)
            type_validator.validate_field_types("API_TEST", required_boolean)
            self.assertEqual(required_boolean, required_boolean_original)
            for invalid_required_boolean in ({}, {"requiredEnabled": None}, {"requiredEnabled": ""},
                                             {"requiredEnabled": "   "}):
                with self.subTest(required_boolean=invalid_required_boolean), self.assertRaises(
                        required_validator.RequiredFieldError):
                    required_validator.validate_required("API_TEST", invalid_required_boolean)

            for payload in (
                {"details": [{}]},
                {"amount": None, "occurredAt": None, "enabled": None, "details": [{
                    "amount": None, "occurredAt": None, "enabled": None,
                }]},
                {"amount": "", "occurredAt": "", "enabled": "", "details": [{
                    "amount": "", "occurredAt": "", "enabled": "",
                }]},
            ):
                original = deepcopy(payload)
                type_validator.validate_field_types("API_TEST", payload)
                self.assertEqual(payload, original)

            valid_optional_values = {
                "amount": 0,
                "occurredAt": "2026-11-19 12:30:45",
                "enabled": False,
                "details": [{
                    "amount": "1.250000",
                    "occurredAt": "2026-11-19 12:30:45",
                    "enabled": True,
                }],
            }
            original = deepcopy(valid_optional_values)
            type_validator.validate_field_types("API_TEST", valid_optional_values)
            self.assertEqual(valid_optional_values, original)

            invalid_optional_values = {
                "amount": "abc",
                "occurredAt": "not-a-date",
                "enabled": "false",
                "details": [{
                    "amount": "abc",
                    "occurredAt": "2026-02-30 12:30:45",
                    "enabled": 0,
                }],
            }
            original = deepcopy(invalid_optional_values)
            with self.assertRaises(type_validator.FieldTypeValidationError) as generic_error:
                type_validator.validate_field_types("API_TEST", invalid_optional_values)
            for path in (
                "amount", "occurredAt", "enabled", "details[0].amount",
                "details[0].occurredAt", "details[0].enabled",
            ):
                self.assertIn(path, str(generic_error.exception))
            self.assertEqual(invalid_optional_values, original)

            whitespace_value = {"amount": "   ", "details": []}
            with self.assertRaises(type_validator.FieldTypeValidationError):
                type_validator.validate_field_types("API_TEST", whitespace_value)

    def test_inbound_add_delete_once_and_edit_always_reexecutes(self):
        """验证新增/删除重放安全、编辑重复提交仍执行且 API09 不建持久记录。"""
        once_cases = [
            ("API01", {"inboundOrderNo": "IDEM-IN-DEL", "action": "Del"}),
            ("API03", {"outboundOrderNo": "IDEM-OUT-DEL", "action": "Del"}),
            ("API05", {"countOrderNo": "IDEM-COUNT-DEL", "action": "Del"}),
            ("API07", {"owner": "IDEM-OWNER", "productCode": "IDEM-PRODUCT", "action": "Add"}),
        ]
        for api_code, payload in once_cases:
            with self.subTest(api=api_code, action=payload["action"]):
                calls = []
                operation = lambda: calls.append(1) or {"success": True, "data": {"executed": len(calls)}}
                first = idempotency.execute(self.env, api_code, payload, operation)
                replay = idempotency.execute(self.env, api_code, payload, operation)
                self.assertEqual(first, replay)
                self.assertEqual(calls, [1])

        # API01 Add 对成功业务键采用冲突返回；不能把旧成功结果当作本次新操作成功。
        api01_add = {"inboundOrderNo": "IDEM-IN-ADD", "action": "Add"}
        add_calls = []
        idempotency.execute(
            self.env, "API01", api01_add,
            lambda: add_calls.append("first") or {"success": True, "data": {"created": True}},
        )
        for duplicate_payload in (api01_add, dict(api01_add, remark="changed")):
            with self.subTest(api="API01", duplicate=duplicate_payload):
                with self.assertRaises(ginlong_errors.GinlongAPIError) as duplicate:
                    idempotency.execute(
                        self.env, "API01", duplicate_payload,
                        lambda: add_calls.append("duplicate") or {"success": True},
                    )
                self.assertEqual(duplicate.exception.error_code, "IDM02")
        self.assertEqual(add_calls, ["first"])
        self.assertEqual(self.env["ginlong.api.idempotency"].search_count([
            ("api_code", "=", "API01"), ("business_key", "=", "IDEM-IN-ADD"),
        ]), 1)

        edit_cases = [
            ("API03", {"outboundOrderNo": "IDEM-OUT-EDIT", "action": "Edit"}),
            ("API05", {"countOrderNo": "IDEM-COUNT-EDIT", "action": "Edit"}),
            ("API07", {"owner": "IDEM-OWNER", "productCode": "IDEM-PRODUCT-EDIT", "action": "Edit"}),
        ]
        for api_code, payload in edit_cases:
            with self.subTest(api=api_code, action=payload["action"]):
                calls = []
                operation = lambda: calls.append(1) or {"success": True, "data": {"executed": len(calls)}}
                first = idempotency.execute(self.env, api_code, payload, operation)
                repeated_same_content = idempotency.execute(self.env, api_code, payload, operation)
                self.assertNotEqual(first, repeated_same_content)
                self.assertEqual(calls, [1, 1])
                self.assertEqual(self.env["ginlong.api.idempotency"].search_count([
                    ("api_code", "=", api_code), ("business_key", "=", idempotency._business_key(api_code, payload)),
                ]), 0)

        query_payload = {"owner": "IDEM-OWNER", "warehouse": "KRWH"}
        query_calls = []
        for _attempt in range(2):
            idempotency.execute(
                self.env, "API09", query_payload,
                lambda: query_calls.append(True) or {"inventoryList": []},
            )
        self.assertEqual(len(query_calls), 2)
        self.assertEqual(self.env["ginlong.api.idempotency"].search_count([
            ("api_code", "=", "API09"), ("business_key", "ilike", "IDEM-OWNER"),
        ]), 0)

    def test_outbound_failed_unknown_success_and_changed_payload_are_separate_events(self):
        """验证出站失败/未知状态可重试，同事件成功复用，内容版本独立发送。"""
        payload = {"action": "CREATE", "outboundOrderNo": "IDEM-OUTBOUND-STATE"}
        context = {"source": {
            "model": "world.depot.outbound.order", "id": 991001,
            "business_key": "IDEM-OUTBOUND-STATE", "write_date": "2026-11-19 12:00:00",
        }}
        calls = []
        outcomes = [
            {"state": "failed", "status_code": 503, "response_text": "unavailable", "error": "HTTP 503"},
            {"state": "succeeded", "status_code": 200, "response_text": '{"returnStatus":"Y"}', "error": False},
        ]

        def attempt():
            """逐次返回注入的远端结果，验证重试仅在失败后执行。"""
            calls.append(True)
            return outcomes.pop(0)

        failed = idempotency.execute(self.env, "API06", payload, attempt, direction="outbound", context=context)
        succeeded = idempotency.execute(self.env, "API06", payload, attempt, direction="outbound", context=context)
        replay = idempotency.execute(
            self.env, "API06", payload,
            lambda: self.fail("successful outbound event must not be sent again"),
            direction="outbound", context=context,
        )
        self.assertEqual(failed["state"], "failed")
        self.assertEqual(succeeded, replay)
        self.assertEqual(len(calls), 2)
        row = self.env["ginlong.api.idempotency"].search([
            ("api_code", "=", "API06"), ("business_key", "like", "API06:picking_completed:%"),
            ("request_fingerprint", "=", idempotency._fingerprint(payload)),
        ], limit=1)
        self.assertTrue(row)
        self.assertEqual(row.direction, "outbound")
        self.assertEqual(row.state, "succeeded")
        self.assertEqual(row.attempt_count, 2)
        self.assertTrue(row.event_key)

        changed_payload = dict(payload, palletQty="2")
        changed = idempotency.execute(
            self.env, "API06", changed_payload,
            lambda: {"state": "unknown", "status_code": None, "response_text": "", "error": "timeout"},
            direction="outbound", context=context,
        )
        self.assertEqual(changed["state"], "unknown")
        changed_row = self.env["ginlong.api.idempotency"].search([
            ("api_code", "=", "API06"),
            ("request_fingerprint", "=", idempotency._fingerprint(changed_payload)),
        ], limit=1)
        self.assertEqual(changed_row.state, "unknown")
        self.assertNotEqual(row.event_key, changed_row.event_key)
        self.assertEqual(self.env["ginlong.api.idempotency"].search_count([
            ("api_code", "=", "API06"), ("business_key", "like", "API06:picking_completed:%"),
        ]), 2)

    def test_concurrent_outbound_duplicate_posts_only_once(self):
        """通过独立 ORM 事务和本地 HTTP 接收端验证并发回传只发送一次。"""
        receiver = _LocalGinlongReceiver(hold_responses=True)
        dbname = self.env.cr.dbname
        suffix = uuid.uuid4().hex
        payload = {"action": "CREATE", "outboundOrderNo": "CONCURRENT-%s" % suffix}
        context = {"source": {
            "model": "world.depot.outbound.order", "id": 990000 + int(suffix[:5], 16),
            "business_key": "CONCURRENT-%s" % suffix, "write_date": "2026-11-19 12:00:00",
        }}
        second_started = threading.Event()
        output = {}
        errors = {}
        calls = []
        event_key = idempotency._outbound_event_key("API06", payload, context, idempotency._api_rules("API06"))

        def worker(name):
            """在自己的 ORM 事务中竞争同一出站事件，并记录发送结果或异常。"""
            try:
                with self._new_committed_cursor(dbname) as cr:
                    env = api.Environment(cr, SUPERUSER_ID, {})
                    if name == "second":
                        second_started.set()

                    def send_once():
                        """向 loopback 接收端真实 POST 一次并返回通用出站结果。"""
                        calls.append(name)
                        response = requests.post(
                            receiver.url + "/API06", json=payload,
                            headers={"Content-Type": "application/json"}, timeout=8,
                        )
                        return {
                            "state": "succeeded" if response.status_code == 200 else "failed",
                            "status_code": response.status_code,
                            "response_text": response.text,
                            "error": False if response.status_code == 200 else "HTTP %s" % response.status_code,
                        }

                    output[name] = idempotency.execute(
                        env, "API06", payload, send_once, direction="outbound", context=context,
                    )
            except Exception as error:
                errors[name] = error

        try:
            # Odoo 测试模式会把 Registry.cursor 路由到当前测试游标；并发场景需各自拥有可提交游标。
            cursor_factory = lambda *args, **kwargs: self._new_committed_cursor(dbname)
            cursor_patch = patch.object(self.env.registry, "cursor", side_effect=cursor_factory)
            cursor_patch.start()
            first = threading.Thread(target=worker, args=("first",), name="ginlong-outbound-first-%s" % suffix)
            second = threading.Thread(target=worker, args=("second",), name="ginlong-outbound-second-%s" % suffix)
            first.start()
            self.assertTrue(receiver.wait_for_count(1, timeout=10), "first HTTP POST did not reach Mock receiver")
            second.start()
            self.assertTrue(second_started.wait(5), "second transaction did not start")
            # 首请求仍未响应并持有唯一键事务；让竞争事务进入 INSERT 后再释放首响应。
            time.sleep(0.4)
            receiver.response_release.set()
            first.join(10)
            second.join(10)
            self.assertFalse(first.is_alive(), "first outbound worker remained blocked")
            self.assertFalse(second.is_alive(), "second outbound worker remained blocked")
            self.assertFalse(errors, str(errors))
            self.assertEqual(len(receiver.records), 1)
            self.assertEqual(calls, ["first"])
            self.assertEqual(output["first"], output["second"])
            with self._new_committed_cursor(dbname) as cr:
                env = api.Environment(cr, SUPERUSER_ID, {})
                row = env["ginlong.api.idempotency"].sudo().search([
                    ("api_code", "=", "API06"), ("event_key", "=", event_key),
                ], limit=1)
                self.assertTrue(row)
                self.assertEqual(row.state, "succeeded")
                self.assertEqual(row.attempt_count, 1)
                self.assertEqual(json.loads(row.response_json), output["first"])
        finally:
            if "cursor_patch" in locals():
                cursor_patch.stop()
            receiver.close()
            with self._new_committed_cursor(dbname) as cr:
                env = api.Environment(cr, SUPERUSER_ID, {})
                env["ginlong.api.idempotency"].sudo().search([
                    ("api_code", "=", "API06"), ("event_key", "=", event_key),
                ]).unlink()
                cr.commit()

    def test_all_five_callbacks_send_real_http_and_replay_successful_events(self):
        """用真实本地 HTTP 接收端逐项验证 API02/04/06/08/10 报文和幂等日志。"""
        receiver = _LocalGinlongReceiver()
        suffix = uuid.uuid4().hex[:10]
        params = self.env["ir.config_parameter"].sudo()

        inbound_result = services.api01(self.env, self.api_user, self._api01("OUTBOUND-%s-IN" % suffix))
        inbound = self.env["world.depot.inbound.order"].browse(inbound_result["data"]["id"])
        inbound_picking, inbound_product = self._create_actual_picking(
            inbound, incoming=True, suffix="HTTP-%s-IN" % suffix,
        )
        inbound_picking.ginlong_callback_selected = True
        inbound_line = inbound_picking.move_line_ids
        inbound_line.write({
            "ginlong_operator_code": "http.receiving.operator",
            "ginlong_operation_time": fields.Datetime.now(),
        })
        self.env["ginlong.inbound.receipt.detail"].create({
            "order_id": inbound.id, "move_line_id": inbound_line.id, "receipt_status": "Y",
        })

        outbound_result = services.api03(self.env, self.api_user, self._api03("OUTBOUND-%s-OUT" % suffix))
        outbound = self.env["world.depot.outbound.order"].browse(outbound_result["data"]["id"])
        outbound_picking, outbound_product = self._create_actual_picking(
            outbound, incoming=False, suffix="HTTP-%s-OUT" % suffix,
        )
        outbound_picking.ginlong_callback_selected = True
        outbound_line = outbound_picking.move_line_ids
        outbound_line.write({
            "package_id": outbound_line.result_package_id.id,
            "ginlong_operator_code": "http.picking.operator",
            "ginlong_operation_time": fields.Datetime.now(),
        })
        outbound_product.product_tmpl_id.ginlong_weight = 2.5
        self.env["ginlong.outbound.shipment.detail"].create({
            "order_id": outbound.id, "move_line_id": outbound_line.id, "shipment_status": "Y",
        })

        count_order = self.env["world.depot.stocktake.order"].create({
            "count_order_no": "OUTBOUND-%s-COUNT" % suffix,
            "project_id": self.project.id, "owner_code": "OWNER-01", "warehouse_code": self.warehouse.code,
            "ginlong_api10_action": "Add",
        })
        self.env["world.depot.stocktake.result"].create({
            "order_id": count_order.id,
            "product_id": self.product.id,
            "product_code": self.product.ginlong_product_code,
            "product_name": self.product.name,
            "specification_model": "GL-MODEL-1",
            "serial_number": "HTTP-COUNT-SN-%s" % suffix,
            "quantity": 1,
            "pallet_code": "HTTP-COUNT-PALLET-%s" % suffix,
            "operator_id": self.env.user.id,
            "operation_time": fields.Datetime.now(),
            "ginlong_operator_code": "http.counter",
            "ginlong_callback_selected": True,
        })

        callback_specs = [
            ("API02", inbound, "action_ginlong_api02"),
            ("API04", inbound, "action_ginlong_api04"),
            ("API06", outbound, "action_ginlong_api06"),
            ("API08", outbound, "action_ginlong_api08"),
            ("API10", count_order, "action_ginlong_api10"),
        ]
        try:
            for api_code, order, method_name in callback_specs:
                endpoint = receiver.url + "/%s" % api_code
                params.set_param("ginlong_apis.%s_callback_url" % api_code.lower(), endpoint)
                first = getattr(order, method_name)()
                second = getattr(order, method_name)()
                self.assertEqual(first["params"]["type"], "success")
                self.assertEqual(second["params"]["type"], "success")

            self.assertEqual(len(receiver.records), 5)
            received = {record["path"].strip("/"): record for record in receiver.records}
            self.assertEqual(set(received), {"API02", "API04", "API06", "API08", "API10"})
            for record in receiver.records:
                self.assertEqual(record["headers"].get("Content-Type"), "application/json")
                self.assertIsInstance(record["body"], dict)
            self.assertEqual(received["API02"]["body"], {
                "inboundOrderNo": inbound.reference, "action": "UPDATE", "receiptConfirmed": "Y",
            })
            self.assertEqual(received["API04"]["body"]["action"], "CREATE")
            self.assertEqual(received["API04"]["body"]["snList"][0]["productCode"], inbound_product.ginlong_product_code)
            self.assertEqual(received["API06"]["body"]["action"], "CREATE")
            self.assertEqual(received["API06"]["body"]["snList"][0]["operator"], "http.picking.operator")
            self.assertEqual(received["API08"]["body"], {
                "outboundOrderNo": outbound.reference, "action": "CREATE", "shipmentConfirmed": "Y",
            })
            self.assertEqual(received["API10"]["body"]["action"], "Add")
            self.assertEqual(received["API10"]["body"]["snList"][0]["productSN"], "HTTP-COUNT-SN-%s" % suffix)

            for api_code, order, _method_name in callback_specs:
                endpoint = receiver.url + "/%s" % api_code
                logs = self.env["world.depot.api.log"].search([("request_path", "=", endpoint)], order="id")
                self.assertEqual(len(logs), 2, api_code)
                self.assertTrue(all(log.success for log in logs), api_code)
                self.assertEqual(logs[0].source_record, order, api_code)
                source_key = getattr(order, "reference", False) or getattr(order, "count_order_no", False)
                event_context = {"source": {
                    "model": order._name, "id": order.id, "business_key": source_key,
                    "write_date": fields.Datetime.to_string(order.write_date) if order.write_date else "",
                }}
                event_key = idempotency._outbound_event_key(
                    api_code, received[api_code]["body"], event_context,
                    idempotency._api_rules(api_code),
                )
                row = self.env["ginlong.api.idempotency"].search([
                    ("api_code", "=", api_code), ("direction", "=", "outbound"),
                    ("event_key", "=", event_key),
                ], limit=1)
                self.assertTrue(row, api_code)
                self.assertEqual(row.attempt_count, 1, api_code)
                self.assertEqual(row.state, "succeeded", api_code)
        finally:
            receiver.close()

    def test_outbound_timeout_is_unknown_then_retried_over_http_and_cached(self):
        """模拟对端已收到但响应超时，验证 unknown 重试、成功缓存和逐次日志。"""
        receiver = _LocalGinlongReceiver(responses=[
            (200, {"returnStatus": "Y", "exceptionInfo": "OK", "operationTime": "2026-11-19 12:00:00"}, 0.5),
        ])
        result = services.api01(self.env, self.api_user, self._api01("OUTBOUND-TIMEOUT-%s" % uuid.uuid4().hex[:8]))
        order = self.env["world.depot.inbound.order"].browse(result["data"]["id"])
        picking, _product = self._create_actual_picking(order, incoming=True, suffix="OUTBOUND-TIMEOUT")
        self.env["ginlong.inbound.receipt.detail"].create({
            "order_id": order.id, "move_line_id": picking.move_line_ids.id, "receipt_status": "Y",
        })
        endpoint = receiver.url + "/API02"
        self.env["ir.config_parameter"].sudo().set_param("ginlong_apis.api02_callback_url", endpoint)
        api_code = "API02"
        event_payload = ginlong_callbacks._build_payload(api_code, order)
        event_context = {"source": {
            "model": order._name, "id": order.id, "business_key": order.reference,
            "write_date": fields.Datetime.to_string(order.write_date),
        }}
        event_key = idempotency._outbound_event_key(
            api_code, event_payload, event_context, idempotency._api_rules(api_code),
        )
        try:
            def short_timeout_http_post(url, json, headers, timeout):
                """绕过 Odoo 测试层最小请求超时，使用真实 socket 触发可控响应超时。"""
                parts = urlsplit(url)
                connection = http.client.HTTPConnection(parts.hostname, parts.port, timeout=timeout)
                path = parts.path or "/"
                if parts.query:
                    path += "?" + parts.query
                request_body = __import__("json").dumps(json, ensure_ascii=False).encode("utf-8")
                try:
                    connection.request("POST", path, body=request_body, headers=headers)
                    response = connection.getresponse()
                    response_text = response.read().decode("utf-8")
                except (socket.timeout, TimeoutError) as error:
                    connection.close()
                    raise requests.Timeout(str(error)) from error
                connection.close()
                return SimpleNamespace(
                    status_code=response.status,
                    text=response_text,
                    json=lambda: __import__("json").loads(response_text),
                )

            with patch(
                "odoo.addons.ginlong_apis.models.ginlong_callbacks.requests.post",
                side_effect=short_timeout_http_post,
            ), patch("odoo.addons.ginlong_apis.models.ginlong_callbacks._HTTP_TIMEOUT", 0.1):
                first = order.action_ginlong_api02()
            self.assertEqual(first["params"]["type"], "danger")
            self.assertTrue(receiver.wait_for_count(1, timeout=2), "timed-out HTTP request was not received")
            row = self.env["ginlong.api.idempotency"].search([
                ("api_code", "=", api_code), ("event_key", "=", event_key),
            ], limit=1)
            self.assertEqual(row.state, "unknown")
            self.assertEqual(row.attempt_count, 1)

            time.sleep(0.55)
            second = order.action_ginlong_api02()
            third = order.action_ginlong_api02()
            self.assertEqual(second["params"]["type"], "success")
            self.assertEqual(third["params"]["type"], "success")
            self.assertEqual(len(receiver.records), 2)
            self.env.invalidate_all()
            row = self.env["ginlong.api.idempotency"].search([
                ("api_code", "=", api_code), ("event_key", "=", event_key),
            ], limit=1)
            self.assertEqual(row.state, "succeeded")
            self.assertEqual(row.attempt_count, 2)
            logs = self.env["world.depot.api.log"].search([("request_path", "=", endpoint)], order="id")
            self.assertEqual(len(logs), 3)
            self.assertFalse(logs[0].success)
            self.assertTrue(logs[1].success and logs[2].success)
        finally:
            receiver.close()

    def test_outbound_http_failure_retries_same_event_then_caches_success(self):
        """真实 HTTP 验证明确失败后以同一报文重试，并缓存随后成功结果。"""
        receiver = _LocalGinlongReceiver(responses=[
            (503, {"returnStatus": "N", "exceptionInfo": "Retry later", "operationTime": "2026-11-19 12:00:00"}, 0),
            (200, {"returnStatus": "Y", "exceptionInfo": "OK", "operationTime": "2026-11-19 12:00:01"}, 0),
        ])
        result = services.api01(
            self.env, self.api_user,
            self._api01("OUTBOUND-FAILURE-%s" % uuid.uuid4().hex[:8]),
        )
        order = self.env["world.depot.inbound.order"].browse(result["data"]["id"])
        picking, _product = self._create_actual_picking(order, incoming=True, suffix="OUTBOUND-FAILURE")
        self.env["ginlong.inbound.receipt.detail"].create({
            "order_id": order.id, "move_line_id": picking.move_line_ids.id, "receipt_status": "Y",
        })
        endpoint = receiver.url + "/API02"
        self.env["ir.config_parameter"].sudo().set_param("ginlong_apis.api02_callback_url", endpoint)
        payload = ginlong_callbacks._build_payload("API02", order)
        context = {"source": {
            "model": order._name, "id": order.id, "business_key": order.reference,
            "write_date": fields.Datetime.to_string(order.write_date),
        }}
        event_key = idempotency._outbound_event_key(
            "API02", payload, context, idempotency._api_rules("API02"),
        )
        try:
            first = order.action_ginlong_api02()
            second = order.action_ginlong_api02()
            third = order.action_ginlong_api02()
            self.assertEqual(first["params"]["type"], "danger")
            self.assertEqual(second["params"]["type"], "success")
            self.assertEqual(third["params"]["type"], "success")
            self.assertEqual(len(receiver.records), 2)
            self.assertEqual(receiver.records[0]["body"], payload)
            self.assertEqual(receiver.records[1]["body"], payload)
            self.assertEqual(receiver.records[0]["headers"].get("Content-Type"), "application/json")
            row = self.env["ginlong.api.idempotency"].search([
                ("api_code", "=", "API02"), ("event_key", "=", event_key),
            ], limit=1)
            self.assertEqual(row.state, "succeeded")
            self.assertEqual(row.attempt_count, 2)
            logs = self.env["world.depot.api.log"].search([("request_path", "=", endpoint)], order="id")
            self.assertEqual(len(logs), 3)
            self.assertFalse(logs[0].success)
            self.assertTrue(logs[1].success and logs[2].success)
        finally:
            receiver.close()


    def test_ginlong_effective_identity_constraints_and_archived_product_restore(self):
        """验证有效身份约束、取消释放全局单号及归档产品恢复原变体。"""
        marker = uuid.uuid4().hex
        second_owner = self.env["res.partner"].create({
            "name": "Ginlong lifecycle owner %s" % marker,
            "is_company": True,
            "ginlong_owner_code": "LIFECYCLE-OWNER-%s" % marker,
        })
        second_project = self.env["project.project"].create({
            "name": "Ginlong lifecycle project %s" % marker,
            "owner": second_owner.id,
            "category": self.env.ref("product.product_category_all").id,
            "warehouse": self.warehouse.id,
            "is_check_origin_doc": False,
        })
        second_api_user = self.env["world.depot.api.user"].create({
            "user_id": self.api_user.user_id.id,
            "project": second_project.id,
        })

        order_payload = self._api01("GINLONG-LIFECYCLE-%s" % marker)
        first = services.api01(self.env, self.api_user, order_payload)
        old_order = self.env["world.depot.inbound.order"].browse(first["data"]["id"])
        self.assertEqual(old_order.ginlong_effective_reference, order_payload["inboundOrderNo"])
        with self.assertRaises(ginlong_errors.GinlongAPIError) as cross_project_conflict:
            services.api01(self.env, second_api_user, order_payload)
        self.assertEqual(cross_project_conflict.exception.error_code, "IDM02")
        self.assertFalse(self.env["world.depot.inbound.order"].search([
            ("reference", "=", order_payload["inboundOrderNo"]),
            ("project", "=", second_project.id),
        ]))

        # API03/API05 也按模型全局单号判重；project 仍决定新记录归属和 Delete/Edit 范围。
        outbound_payload = {
            "owner": "OWNER-01", "action": "Add", "outboundOrderNo": "GINLONG-LIFECYCLE-OUT-%s" % marker,
            "warehouse": self.warehouse.code, "businessType": "STANDARD",
            "customer": self.recipient.name,
            "details": [{
                "productCode": self.product.ginlong_product_code,
                "productName": self.product.name,
                "specificationModel": self.product.product_tmpl_id.ginlong_specification_model,
                "quantity": 1, "net_wt_machine": 1, "net_wt_total": 1, "pack_qty": 1,
                "pallet_qty": 1, "pallet_len": 1, "pallet_wid": 1, "pallet_hgt": 1,
                "unit_vol": 1, "pack_unit": "BOX", "pack_wt": 1, "pallet_total_wt": 1,
                "total_vol": 1, "carton_wt_total": 1, "gross_wt_total": 1,
            }],
        }
        services.api03(self.env, self.api_user, outbound_payload)
        with self.assertRaises(ginlong_errors.GinlongAPIError) as outbound_cross_project_conflict:
            services.api03(self.env, second_api_user, outbound_payload)
        self.assertEqual(outbound_cross_project_conflict.exception.error_code, "IDM02")
        self.assertFalse(self.env["world.depot.outbound.order"].search([
            ("reference", "=", outbound_payload["outboundOrderNo"]),
            ("project", "=", second_project.id),
        ]))

        stocktake_payload = {
            "owner": "OWNER-01", "action": "Add", "countOrderNo": "GINLONG-LIFECYCLE-COUNT-%s" % marker,
            "warehouse": self.warehouse.code,
            "details": [{
                "productCode": self.product.ginlong_product_code,
                "productName": self.product.name,
                "specificationModel": self.product.product_tmpl_id.ginlong_specification_model,
                "quantity": 1,
            }],
            "snList": [{
                "productSN": "GINLONG-LIFECYCLE-SN-%s" % marker, "quantity": 1,
                "palletCode": "GINLONG-LIFECYCLE-PALLET-%s" % marker,
                "productCode": self.product.ginlong_product_code,
                "productName": self.product.name,
                "specificationModel": self.product.product_tmpl_id.ginlong_specification_model,
            }],
        }
        services.api05(self.env, self.api_user, stocktake_payload)
        with self.assertRaises(ginlong_errors.GinlongAPIError) as stocktake_cross_project_conflict:
            services.api05(self.env, second_api_user, stocktake_payload)
        self.assertEqual(stocktake_cross_project_conflict.exception.error_code, "IDM02")
        self.assertFalse(self.env["world.depot.stocktake.order"].search([
            ("count_order_no", "=", stocktake_payload["countOrderNo"]),
            ("project_id", "=", second_project.id),
        ]))

        product_payload = {
            "action": "Add", "owner": "OWNER-01",
            "productCode": self.product.ginlong_product_code,
            "productName": self.product.name,
            "specificationModel": self.product.product_tmpl_id.ginlong_specification_model,
            "unit": self.product.product_tmpl_id.ginlong_unit,
            "productForm": self.product.product_tmpl_id.ginlong_product_form,
        }
        with self.assertRaises(ginlong_errors.GinlongAPIError) as product_cross_project_conflict:
            services.api07(self.env, second_api_user, product_payload)
        self.assertEqual(product_cross_project_conflict.exception.error_code, "IDM07")

        old_order.write({"state": "cancel"})
        self.assertFalse(old_order.ginlong_effective_reference)
        re_added = services.api01(self.env, self.api_user, order_payload)
        new_order = self.env["world.depot.inbound.order"].browse(re_added["data"]["id"])
        self.assertNotEqual(old_order, new_order)
        self.assertEqual(new_order.ginlong_effective_reference, order_payload["inboundOrderNo"])
        self.assertEqual(self.env["world.depot.inbound.order"].search_count([
            ("reference", "=", order_payload["inboundOrderNo"]), ("state", "!=", "cancel"),
        ]), 1)
        with self.assertRaises(IntegrityError):
            with self.env.cr.savepoint():
                self.env["world.depot.inbound.order"].sudo().create({
                    "project": second_project.id,
                    "reference": order_payload["inboundOrderNo"],
                })

        outbound_key = "GINLONG-LIFECYCLE-OUT-DB-%s" % marker
        self.env["world.depot.outbound.order"].sudo().create({
            "project": self.project.id, "unload_company": self.recipient.id,
            "reference": outbound_key,
        })
        with self.assertRaises(IntegrityError):
            with self.env.cr.savepoint():
                self.env["world.depot.outbound.order"].sudo().create({
                    "project": second_project.id, "unload_company": self.recipient.id,
                    "reference": outbound_key,
                })

        stocktake_key = "GINLONG-LIFECYCLE-COUNT-DB-%s" % marker
        stocktake_values = {
            "count_order_no": stocktake_key, "project_id": self.project.id,
            "owner_code": "OWNER-01", "warehouse_code": self.warehouse.code,
        }
        self.env["world.depot.stocktake.order"].sudo().create(stocktake_values)
        with self.assertRaises(IntegrityError):
            with self.env.cr.savepoint():
                self.env["world.depot.stocktake.order"].sudo().create(dict(
                    stocktake_values, project_id=second_project.id,
                ))

        restore_payload = {
            "action": "Add", "owner": "OWNER-01",
            "productCode": "GINLONG-ARCHIVE-%s" % marker,
            "productName": "Ginlong archived product %s" % marker,
            "specificationModel": "ARCHIVE-MODEL",
            "unit": self.env.ref("uom.product_uom_unit").name,
            "productForm": "原材料",
            "weight": 0,
        }
        created = services.api07(self.env, self.api_user, restore_payload)
        archived_product = self.env["product.product"].browse(created["data"]["id"])
        original_id = archived_product.id
        archived_product.write({"active": False})
        self.assertFalse(archived_product.ginlong_effective_identity)
        restored = services.api07(self.env, self.api_user, restore_payload)
        self.assertEqual(restored["data"]["id"], original_id)
        self.assertTrue(archived_product.active)
        self.assertTrue(archived_product.ginlong_effective_identity)
        archived_product.write({"active": False})
        # 只省略契约中的可选重量；报文指纹改变，但不改写模板的已保存重量事实。
        changed_restore_payload = dict(restore_payload)
        changed_restore_payload.pop("weight")
        restored_with_changes = services.api07(self.env, self.api_user, changed_restore_payload)
        self.assertEqual(restored_with_changes["data"]["id"], original_id)
        self.assertTrue(archived_product.active)
        self.assertEqual(archived_product.ginlong_weight, 0)
        with self.assertRaises(ginlong_errors.GinlongAPIError) as active_product_conflict:
            services.api07(self.env, self.api_user, changed_restore_payload)
        self.assertEqual(active_product_conflict.exception.error_code, "IDM07")

        duplicate_variant = services.api07(self.env, self.api_user, dict(
            restore_payload,
            productCode="GINLONG-ARCHIVE-DUPLICATE-%s" % marker,
            productName="Ginlong duplicate-key variant %s" % marker,
        ))
        duplicate_variant_record = self.env["product.product"].browse(duplicate_variant["data"]["id"])
        with self.assertRaises(IntegrityError):
            with self.env.cr.savepoint():
                duplicate_variant_record.write({"ginlong_product_code": restore_payload["productCode"]})

    def test_concurrent_effective_add_conflict_is_mapped_by_fresh_orm_state(self):
        """用独立事务竞争四类有效键，确认唯一冲突被映射为业务重复错误。"""
        dbname = self.env.cr.dbname
        marker = uuid.uuid4().hex
        owner_code = "CONCURRENT-OWNER-%s" % marker
        product_code = "CONCURRENT-RAW-%s" % marker
        api_user_id = False
        refs = {
            "API01": "CONCURRENT-IN-%s" % marker,
            "API03": "CONCURRENT-OUT-%s" % marker,
            "API05": "CONCURRENT-COUNT-%s" % marker,
            "API07": "CONCURRENT-PRODUCT-%s" % marker,
        }
        payloads = {
            "API01": {
                "owner": owner_code, "action": "Add", "inboundOrderNo": refs["API01"],
                "warehouse": "KRWH", "businessType": "STANDARD",
                "details": [{
                    "productCode": product_code, "productName": "Concurrent material",
                    "specificationModel": "CONCURRENT-MODEL", "quantity": 1,
                }],
            },
            "API03": {
                "owner": owner_code, "action": "Add", "outboundOrderNo": refs["API03"],
                "warehouse": "KRWH", "businessType": "STANDARD", "customer": "Concurrent recipient %s" % marker,
                "details": [{
                    "productCode": product_code, "productName": "Concurrent material",
                    "specificationModel": "CONCURRENT-MODEL", "quantity": 1,
                    "net_wt_machine": 1, "net_wt_total": 1, "pack_qty": 1, "pallet_qty": 1,
                    "pallet_len": 1, "pallet_wid": 1, "pallet_hgt": 1, "unit_vol": 1,
                    "pack_unit": "BOX", "pack_wt": 1, "pallet_total_wt": 1, "total_vol": 1,
                    "carton_wt_total": 1, "gross_wt_total": 1,
                }],
            },
            "API05": {
                "owner": owner_code, "action": "Add", "countOrderNo": refs["API05"],
                "warehouse": "KRWH", "details": [{
                    "productCode": product_code, "productName": "Concurrent material",
                    "specificationModel": "CONCURRENT-MODEL", "quantity": 1,
                }], "snList": [{
                    "productSN": product_code, "quantity": 1, "palletCode": "CONCURRENT-COUNT-PALLET",
                    "productCode": product_code, "productName": "Concurrent material",
                    "specificationModel": "CONCURRENT-MODEL",
                }],
            },
            "API07": {
                "owner": owner_code, "action": "Add", "productCode": refs["API07"],
                "productName": "Concurrent product", "specificationModel": "CONCURRENT-PRODUCT-MODEL",
                "unit": "台", "productForm": "原材料",
            },
        }
        handlers = {
            "API01": services.api01,
            "API03": services.api03,
            "API05": services.api05,
            "API07": services.api07,
        }
        fixture_ids = {}
        scenario_keys = {api_code: [] for api_code in payloads}

        try:
            with self._new_committed_cursor(dbname) as cr:
                env = api.Environment(cr, SUPERUSER_ID, {})
                owner = env["res.partner"].sudo().create({
                    "name": owner_code, "is_company": True, "ginlong_owner_code": owner_code,
                })
                warehouse = env.ref("stock.warehouse0")
                project = env["project.project"].sudo().create({
                    "name": "Ginlong concurrent project %s" % marker,
                    "owner": owner.id,
                    "category": env.ref("product.product_category_all").id,
                    "warehouse": warehouse.id,
                    "is_check_origin_doc": False,
                })
                recipient = env["res.partner"].sudo().create({
                    "name": "Concurrent recipient %s" % marker,
                    "is_company": True, "source_project_id": project.id,
                })
                api_user = env["world.depot.api.user"].sudo().create({
                    "user_id": env.ref("base.user_admin").id, "project": project.id,
                })
                common_product = services.api07(env, api_user, {
                    "action": "Add", "owner": owner_code, "productCode": product_code,
                    "productName": "Concurrent material", "specificationModel": "CONCURRENT-MODEL",
                    "unit": env.ref("uom.product_uom_unit").name, "productForm": "原材料",
                })
                fixture_ids = {
                    "owner": owner.id, "project": project.id, "recipient": recipient.id,
                    "api_user": api_user.id,
                    "common_product": common_product["data"]["id"],
                }
                api_user_id = api_user.id
                cr.commit()

            # 每种接口使用独立业务键，避免上一轮成功记录影响下一轮并发场景。
            for api_code, base_payload in payloads.items():
                for different_payload in (False, True):
                    payload = deepcopy(base_payload)
                    case_suffix = "DIFF" if different_payload else "SAME"
                    key_field = {
                        "API01": "inboundOrderNo",
                        "API03": "outboundOrderNo",
                        "API05": "countOrderNo",
                        "API07": "productCode",
                    }[api_code]
                    payload[key_field] = "%s-%s" % (payload[key_field], case_suffix)
                    scenario_keys[api_code].append(payload[key_field])
                    gate = threading.Barrier(2)
                    gate_state = threading.local()
                    outcomes = []
                    outcome_lock = threading.Lock()

                    def worker(worker_index):
                        """在独立 ORM 事务中经过同一生命周期适配器并竞争业务写入。"""
                        worker_payload = deepcopy(payload)
                        if different_payload and worker_index == 2:
                            # 两个并发 Add 使用同一业务键，但只有第二个报文的非键字段不同。
                            if api_code == "API07":
                                worker_payload["productName"] += " changed"
                            else:
                                worker_payload["remark"] = "concurrent payload variant"
                        try:
                            with self._new_committed_cursor(dbname) as cr:
                                env = api.Environment(cr, SUPERUSER_ID, {})
                                api_user_record = env["world.depot.api.user"].sudo().browse(api_user_id)

                                def resolve_lifecycle(current_env):
                                    """先完成有效记录检查，再同步两事务进入业务处理。"""
                                    current_user = current_env["world.depot.api.user"].sudo().browse(api_user_id)
                                    event_key = services.lifecycle_event_key(
                                        current_env, current_user, api_code, worker_payload,
                                    )
                                    # 竞争屏障只用于同步第一次有效性检查；完整性冲突后的新 ORM 复查不能再次等待。
                                    if not getattr(gate_state, "passed", False):
                                        gate.wait(timeout=10)
                                        gate_state.passed = True
                                    return event_key

                                result = idempotency.execute(
                                    env, api_code, worker_payload,
                                    lambda: handlers[api_code](env, api_user_record, worker_payload),
                                    lifecycle_resolver=resolve_lifecycle,
                                )
                                cr.commit()
                                item = ("success", result)
                        except ginlong_errors.GinlongAPIError as error:
                            item = ("error", error.error_code, str(error))
                        except Exception as error:  # 测试须将未预期的数据库/系统错误暴露为失败断言。
                            item = ("unexpected", repr(error))
                        with outcome_lock:
                            outcomes.append(item)

                    with patch.object(
                        self.env.registry,
                        "cursor",
                        side_effect=lambda *args, **kwargs: self._new_committed_cursor(dbname),
                    ):
                        threads = [
                            threading.Thread(target=worker, args=(index,), name="ginlong-effective-%s-%s" % (api_code, index))
                            for index in (1, 2)
                        ]
                        for thread in threads:
                            thread.start()
                        for thread in threads:
                            thread.join(20)
                    self.assertFalse(any(thread.is_alive() for thread in threads), api_code)
                    self.assertEqual([item[0] for item in outcomes].count("success"), 1, (api_code, outcomes))
                    self.assertEqual([item[0] for item in outcomes].count("error"), 1, (api_code, outcomes))
                    self.assertFalse([item for item in outcomes if item[0] == "unexpected"], (api_code, outcomes))
                    expected_duplicate = "IDM07" if api_code == "API07" else "IDM02"
                    self.assertTrue(
                        any(item[0] == "error" and item[1] == expected_duplicate for item in outcomes),
                        (api_code, outcomes),
                    )

                    with self._new_committed_cursor(dbname) as cr:
                        env = api.Environment(cr, SUPERUSER_ID, {})
                        if api_code == "API01":
                            active_count = env["world.depot.inbound.order"].sudo().search_count([
                                ("reference", "=", payload[key_field]), ("state", "!=", "cancel"),
                            ])
                        elif api_code == "API03":
                            active_count = env["world.depot.outbound.order"].sudo().search_count([
                                ("reference", "=", payload[key_field]), ("state", "!=", "cancel"),
                            ])
                        elif api_code == "API05":
                            active_count = env["world.depot.stocktake.order"].sudo().search_count([
                                ("count_order_no", "=", payload[key_field]), ("state", "!=", "cancel"),
                            ])
                        else:
                            active_count = env["product.product"].sudo().search_count([
                                ("ginlong_owner_code", "=", owner_code),
                                ("ginlong_product_code", "=", payload[key_field]), ("active", "=", True),
                            ])
                        self.assertEqual(active_count, 1, api_code)

        finally:
            # 仅移除本测试随机前缀下由测试自身提交的业务和幂等夹具。
            with self._new_committed_cursor(dbname) as cr:
                env = api.Environment(cr, SUPERUSER_ID, {})
                env["world.depot.inbound.order"].sudo().search([
                    ("reference", "in", scenario_keys["API01"]),
                ]).unlink()
                env["world.depot.outbound.order"].sudo().search([
                    ("reference", "in", scenario_keys["API03"]),
                ]).unlink()
                env["world.depot.stocktake.order"].sudo().search([
                    ("count_order_no", "in", scenario_keys["API05"]),
                ]).unlink()
                variants = env["product.product"].sudo().with_context(active_test=False).search([
                    ("ginlong_product_code", "in", [product_code] + scenario_keys["API07"]),
                ])
                templates = variants.mapped("product_tmpl_id")
                if variants:
                    variants.unlink()
                if templates:
                    templates.unlink()
                for api_code in ("API01", "API03", "API05"):
                    for code in scenario_keys[api_code]:
                        env["ginlong.api.idempotency"].sudo().search([
                            ("api_code", "=", api_code),
                            ("business_key", "=", code),
                        ]).unlink()
                for api_code in ("API07",):
                    for code in [product_code] + scenario_keys[api_code]:
                        key = idempotency._canonical_json([owner_code, code])
                        env["ginlong.api.idempotency"].sudo().search([
                            ("api_code", "=", api_code), ("business_key", "=", key),
                        ]).unlink()
                if fixture_ids:
                    env["world.depot.api.user"].sudo().browse(fixture_ids.get("api_user")).unlink()
                    env["project.project"].sudo().browse(fixture_ids.get("project")).unlink()
                    env["res.partner"].sudo().browse(fixture_ids.get("recipient")).unlink()
                    env["res.partner"].sudo().browse(fixture_ids.get("owner")).unlink()
                cr.commit()


@tagged("post_install", "-at_install")
class TestGinlongHttpAPI(HttpCase):
    """通过 Odoo HTTP Server 验收真实 Ginlong 入站路由及 ORM 副作用。"""

    # 外部 HTTP 请求及 api_logger/限流均需要写 ORM，不能使用 HttpCase 的只读请求游标。
    readonly_enabled = False

    @classmethod
    def setUpClass(cls):
        """建立真实 HTTP 请求所需的 API 用户、货主、项目、Token 和产品。"""
        super().setUpClass()
        suffix = uuid.uuid4().hex[:10]
        cls.http_suffix = suffix
        cls.http_token = "ginlong-http-token-%s" % suffix
        cls.http_owner = cls.env["res.partner"].create({
            "name": "Ginlong HTTP owner %s" % suffix, "is_company": True,
            "ginlong_owner_code": "HTTP-OWNER-%s" % suffix,
        })
        cls.http_warehouse = cls.env.ref("stock.warehouse0")
        cls.http_project = cls.env["project.project"].create({
            "name": "Ginlong HTTP project %s" % suffix,
            "owner": cls.http_owner.id,
            "category": cls.env.ref("product.product_category_all").id,
            "warehouse": cls.http_warehouse.id,
            "is_check_origin_doc": False,
        })
        cls.http_api_user = cls.env["world.depot.api.user"].create({
            "user_id": cls.env.ref("base.user_admin").id,
            "project": cls.http_project.id,
        })
        cls.http_recipient = cls.env["res.partner"].create({
            "name": "Ginlong HTTP recipient %s" % suffix,
            "is_company": True,
            "source_project_id": cls.http_project.id,
        })
        cls.env["world.depot.api.token"].create({
            "user_id": cls.http_api_user.user_id.id,
            "token": cls.http_token,
            "expires": fields.Datetime.now() + timedelta(hours=1),
        })
        product_result = services.api07(cls.env, cls.http_api_user, {
            "action": "Add", "owner": cls.http_owner.ginlong_owner_code,
            "productCode": "HTTP-PRODUCT-%s" % suffix,
            "productName": "Ginlong HTTP product %s" % suffix,
            "specificationModel": "HTTP-MODEL", "unit": cls.env.ref("uom.product_uom_unit").name,
            "productForm": "原材料",
        })
        cls.http_product = cls.env["product.product"].browse(product_result["data"]["id"])
        serial_product_result = services.api07(cls.env, cls.http_api_user, {
            "action": "Add", "owner": cls.http_owner.ginlong_owner_code,
            "productCode": "HTTP-SERIAL-PRODUCT-%s" % suffix,
            "productName": "Ginlong HTTP serial product %s" % suffix,
            "specificationModel": "HTTP-SERIAL-MODEL", "unit": cls.env.ref("uom.product_uom_unit").name,
            "productForm": "成品",
        })
        cls.http_serial_product = cls.env["product.product"].browse(serial_product_result["data"]["id"])
        second_serial_product_result = services.api07(cls.env, cls.http_api_user, {
            "action": "Add", "owner": cls.http_owner.ginlong_owner_code,
            "productCode": "HTTP-SECOND-SERIAL-PRODUCT-%s" % suffix,
            "productName": "Ginlong HTTP second serial product %s" % suffix,
            "specificationModel": "HTTP-SECOND-SERIAL-MODEL",
            "unit": cls.env.ref("uom.product_uom_unit").name,
            "productForm": "半成品",
        })
        cls.http_second_serial_product = cls.env["product.product"].browse(
            second_serial_product_result["data"]["id"]
        )

    def setUp(self):
        """为当前 HTTP 测试生成唯一日志标识并初始化请求记录。"""
        super().setUp()
        self.http_test_marker = "GINLONG-HTTP-%s" % uuid.uuid4().hex
        self.http_log_markers = [self.http_test_marker]
        self._rate_limited_http_posts = 0

    def tearDown(self):
        """使用 ORM 清除独立事务写入的测试日志和共享限流计数。"""
        dbname = self.env.cr.dbname
        with db_connect(dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            env["world.depot.api.log"].sudo().search([
                ("request_data", "ilike", self.http_test_marker),
            ]).unlink()
            env["ginlong.api.idempotency"].sudo().search([
                ("business_key", "ilike", self.http_test_marker),
            ]).unlink()
            env["ginlong.api.rate.counter"].sudo().search([
                ("api_user_id", "=", self.http_api_user.id),
            ]).unlink()
            cr.commit()
        super().tearDown()

    def _post(self, path, payload):
        """通过 Odoo HTTP 测试 Server POST Ginlong JSON 并携带真实 Bearer Token。"""
        return self.url_open(
            path,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer %s" % self.http_token,
            },
        )

    def _post_with_rate_reset(self, path, payload):
        """执行真实 HTTP 请求后用 ORM 清除测试用户限流计数，隔离后续断言。"""
        # 固定一秒窗口的限流状态由独立提交事务持久化；测试内连续清除并发碰到窗口边界时，
        # 仍可能短暂观察到当前窗口计数。每 9 次请求跨过完整窗口，避免业务断言被 429 污染。
        if self._rate_limited_http_posts and self._rate_limited_http_posts % 9 == 0:
            time.sleep(1.1)
        self._rate_limited_http_posts += 1
        response = self._post(path, payload)
        # 同一测试需连续覆盖多个合法/非法输入；逐次重置测试计数，避免把限流误当成业务结果。
        with db_connect(self.env.cr.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            env["ginlong.api.rate.counter"].sudo().search([
                ("api_user_id", "=", self.http_api_user.id),
            ]).unlink()
            cr.commit()
        return response

    def _committed_api_logs(self, marker):
        """使用当前测试环境 ORM 读取 HTTP 请求已提交的 API 日志。"""
        self.env.invalidate_all()
        logs = self.env["world.depot.api.log"].sudo().search([
            ("request_data", "ilike", marker),
        ], order="id")
        return logs.read(["code", "msg", "exception_details", "response_data", "status", "success"])

    def _assert_sn_business_rejection(self, response, marker, expected_message):
        """断言 SN 业务错误使用 Ginlong 响应并留下完整日志诊断。"""
        self.assertEqual(response.status_code, 200)
        body = json.loads(response.text)
        self.assertEqual(set(body), {"returnStatus", "exceptionInfo", "operationTime"})
        self.assertEqual(body["returnStatus"], "N")
        self.assertTrue(body["exceptionInfo"].startswith("BUS01: "), body["exceptionInfo"])
        self.assertIn(expected_message, body["exceptionInfo"])
        self.assertLessEqual(len(body["exceptionInfo"]), 40)
        logs = self._committed_api_logs(marker)
        matching = [log for log in logs if log["code"] == "BUS01"]
        self.assertTrue(matching, marker)
        self.assertTrue(any(
            expected_message in (log["msg"] or "")
            or expected_message in (log["exception_details"] or "")
            for log in matching
        ), matching)
        self.assertTrue(all(log["exception_details"] for log in matching))
        return body

    def _assert_no_successful_sn_order(self, api_code, business_key, model_name, marker):
        """确认失败请求没有创建单据或成功幂等记录。"""
        self.env.invalidate_all()
        self.assertFalse(self.env[model_name].sudo().search([
            ("reference" if api_code == "API01" else "count_order_no", "=", business_key),
        ]))
        self.assertFalse(self.env["ginlong.api.idempotency"].sudo().search([
            ("api_code", "=", api_code), ("business_key", "=", business_key),
            ("state", "=", "succeeded"),
        ]))
        logs = self._committed_api_logs(marker)
        self.assertTrue(any(not log["success"] for log in logs), marker)

    def _stock_side_effect_snapshot(self, details):
        """通过 ORM 快照订单涉及的库存对象，供拒绝路径原子性断言使用。

        参数：
            details: Ginlong 明细列表，用于定位对应的 Odoo 产品。

        返回：
            全局库存记录 ID 集合及相关产品的库存数据快照。
        """
        self.env.invalidate_all()
        product_codes = {
            row.get("productCode") for row in details
            if isinstance(row, dict) and row.get("productCode")
        }
        products = self.env["product.product"].sudo().with_context(active_test=False).search([
            ("ginlong_product_code", "in", list(product_codes)),
        ]) if product_codes else self.env["product.product"].sudo().browse()
        product_ids = products.ids

        # 全局 ID 用于发现意外新建/删除的库存对象；字段快照用于发现相关既有对象被更改。
        global_model_ids = {}
        for model_name in (
            "stock.quant", "stock.lot", "stock.quant.package", "stock.picking",
            "stock.move", "stock.move.line",
        ):
            model = self.env[model_name].sudo().with_context(active_test=False)
            global_model_ids[model_name] = tuple(model.search([], order="id").ids)

        def rows(model_name, domain, field_names):
            """读取指定库存记录的稳定 ORM 字段快照。"""
            model = self.env[model_name].sudo().with_context(active_test=False)
            records = model.search(domain, order="id")
            fields_to_read = ["id"] + [name for name in field_names if name in model._fields]

            def freeze(value):
                """将 read() 返回的关系列表转换为可比较的不可变值。"""
                if isinstance(value, list):
                    return tuple(freeze(item) for item in value)
                if isinstance(value, dict):
                    return tuple(sorted((key, freeze(item)) for key, item in value.items()))
                return value

            return tuple(
                tuple((name, freeze(value)) for name, value in sorted(record.items()))
                for record in records.read(fields_to_read)
            )

        domain = [("product_id", "in", product_ids)] if product_ids else [("id", "=", 0)]
        quant_rows = rows("stock.quant", domain, (
            "product_id", "location_id", "lot_id", "package_id", "owner_id", "quantity",
            "reserved_quantity", "in_date", "company_id", "write_date",
        ))
        lot_rows = rows("stock.lot", domain, ("name", "product_id", "company_id", "write_date"))
        move_rows = rows("stock.move", domain, (
            "state", "product_uom_qty", "quantity", "picking_id", "location_id",
            "location_dest_id", "write_date",
        ))
        move_line_rows = rows("stock.move.line", domain, (
            "quantity", "lot_id", "package_id", "result_package_id", "picking_id",
            "location_id", "location_dest_id", "write_date",
        ))
        moves = self.env["stock.move"].sudo().with_context(active_test=False).search(domain)
        picking_ids = moves.mapped("picking_id").ids
        picking_rows = rows("stock.picking", [("id", "in", picking_ids)] if picking_ids else [("id", "=", 0)], (
            "state", "date_done", "move_ids", "location_id", "location_dest_id", "write_date",
        ))
        related_package_ids = set(
            self.env["stock.quant"].sudo().search(domain).mapped("package_id").ids
            + self.env["stock.move.line"].sudo().search(domain).mapped("package_id").ids
            + self.env["stock.move.line"].sudo().search(domain).mapped("result_package_id").ids
        )
        package_rows = rows(
            "stock.quant.package",
            [("id", "in", sorted(related_package_ids))] if related_package_ids else [("id", "=", 0)],
            ("name", "package_type_id", "company_id", "write_date"),
        )
        return {
            "global_model_ids": global_model_ids,
            "product_ids": tuple(products.ids),
            "quants": quant_rows,
            "lots": lot_rows,
            "moves": move_rows,
            "move_lines": move_line_rows,
            "pickings": picking_rows,
            "packages": package_rows,
        }

    def test_http_api01_sn_consistency_by_product_tracking(self):
        """真实 HTTP 验证 API01 按 tracking 校验 SN、产品、数量、完整度和重复编号。"""
        marker = self.http_test_marker
        path = "/api/ginlong/TPL_Pending_Receipt_Note"

        def detail(product, quantity):
            """构造一条协议完整的入库产品明细。"""
            return {
                "productCode": product.ginlong_product_code,
                "productName": product.name,
                "specificationModel": product.product_tmpl_id.ginlong_specification_model,
                "quantity": quantity,
            }

        def serial(product, serial_number, quantity=1, pallet_code=None):
            """构造一条可关联产品并参与数量汇总的 SN 记录。"""
            return {
                "productSN": serial_number, "quantity": quantity,
                "palletCode": pallet_code or marker + "-PALLET",
                "productCode": product.ginlong_product_code,
                "productName": product.name,
                "specificationModel": product.product_tmpl_id.ginlong_specification_model,
            }

        def payload(order_no, details, sn_list=None, include_sn_list=True):
            """构造独立单号的 API01 Add；`include_sn_list=False` 表示字段省略。"""
            result = {
                "owner": self.http_owner.ginlong_owner_code, "action": "Add",
                "inboundOrderNo": order_no, "warehouse": self.http_warehouse.code,
                "businessType": "保税_海外收货入库", "details": details,
            }
            if include_sn_list:
                result["snList"] = sn_list or []
            return result

        valid_no = marker + "-API01-SN-VALID"
        pallets = [marker + "-PALLET-A", marker + "-PALLET-B", marker + "-PALLET-C"]
        valid_sn_rows = []
        for pallet_index, pallet_code in enumerate(pallets):
            # 每个托盘同时保存原材料分托数量、成品单件 SN 和半成品单件 SN。
            valid_sn_rows.append(serial(
                self.http_product, self.http_product.ginlong_product_code, 3, pallet_code,
            ))
            for product, product_prefix in (
                (self.http_serial_product, "FG"),
                (self.http_second_serial_product, "SF"),
            ):
                for serial_index in (1, 2):
                    valid_sn_rows.append(serial(
                        product,
                        "%s-%s-%s-%02d" % (
                            marker, product_prefix, chr(ord("A") + pallet_index), serial_index,
                        ),
                        pallet_code=pallet_code,
                    ))
        valid_payload = payload(valid_no, [
            detail(self.http_serial_product, 6),
            detail(self.http_second_serial_product, 6),
            detail(self.http_product, 9),
        ], valid_sn_rows)
        valid_response = self._post_with_rate_reset(path, valid_payload)
        valid_body = json.loads(valid_response.text)
        self.assertEqual(valid_response.status_code, 200)
        self.assertEqual(valid_body["returnStatus"], "Y")
        self.env.invalidate_all()
        order = self.env["world.depot.inbound.order"].sudo().search([("reference", "=", valid_no)])
        self.assertEqual(len(order), 1)
        saved_products = order.inbound_order_product_ids.mapped("inbound_order_product_pallet_ids")
        self.assertEqual(len(saved_products), 3)
        self.assertEqual(sum(saved_products.filtered(
            lambda row: row.product_id == self.http_serial_product
        ).mapped("quantity")), 6)
        self.assertEqual(sum(saved_products.filtered(
            lambda row: row.product_id == self.http_second_serial_product
        ).mapped("quantity")), 6)
        self.assertEqual(sum(saved_products.filtered(
            lambda row: row.product_id == self.http_product
        ).mapped("quantity")), 9)
        serials_by_product = {
            self.http_serial_product: order.inbound_order_product_ids.filtered(
                lambda row: self.http_serial_product in row.inbound_order_product_pallet_ids.product_id
            ).mapped("product_serial_number_ids"),
            self.http_second_serial_product: order.inbound_order_product_ids.filtered(
                lambda row: self.http_second_serial_product in row.inbound_order_product_pallet_ids.product_id
            ).mapped("product_serial_number_ids"),
            self.http_product: order.inbound_order_product_ids.filtered(
                lambda row: self.http_product in row.inbound_order_product_pallet_ids.product_id
            ).mapped("product_serial_number_ids"),
        }
        self.assertEqual(len(serials_by_product[self.http_serial_product]), 6)
        self.assertEqual(len(serials_by_product[self.http_second_serial_product]), 6)
        self.assertEqual(len(serials_by_product[self.http_product]), 3)
        self.assertEqual(sum(serials_by_product[self.http_product].mapped("quantity")), 9)
        self.assertEqual(set(serials_by_product[self.http_product].mapped("serial_number")), {
            self.http_product.ginlong_product_code,
        })
        saved_serials = order.inbound_order_product_ids.mapped("product_serial_number_ids")
        self.assertEqual(len(saved_serials), 15)
        self.assertEqual(len(set(saved_serials.mapped("serial_number"))), 13)
        self.assertEqual(set(saved_serials.mapped("quantity")), {1.0, 3.0})
        self.assertEqual(set(saved_serials.mapped("ginlong_quantity")), {1.0, 3.0})
        pallet_counts = {
            pallet_code: len(saved_serials.filtered(lambda row: row.ginlong_pallet_code == pallet_code))
            for pallet_code in set(saved_serials.mapped("ginlong_pallet_code"))
        }
        self.assertEqual(pallet_counts, {
            pallets[0]: 5,
            pallets[1]: 5,
            pallets[2]: 5,
        })
        self.assertGreater(len(set(
            serials_by_product[self.http_serial_product].mapped("ginlong_pallet_code")
        )), 1)
        self.assertTrue(all(
            row.ginlong_product_code == self.http_serial_product.ginlong_product_code
            for row in serials_by_product[self.http_serial_product]
        ))
        self.assertTrue(all(
            row.ginlong_product_code == self.http_second_serial_product.ginlong_product_code
            for row in serials_by_product[self.http_second_serial_product]
        ))
        self.assertTrue(all(
            row.ginlong_product_code == self.http_product.ginlong_product_code
            for row in serials_by_product[self.http_product]
        ))
        self.assertEqual(set(saved_serials.mapped("ginlong_pallet_code")), {
            *pallets,
        })
        product_pallet_quantities = {
            (product_code, pallet_code): sum(rows.filtered(
                lambda row: row.ginlong_product_code == product_code
                and row.ginlong_pallet_code == pallet_code
            ).mapped("ginlong_quantity"))
            for product_code in (
                self.http_product.ginlong_product_code,
                self.http_serial_product.ginlong_product_code,
                self.http_second_serial_product.ginlong_product_code,
            )
            for pallet_code in pallets
            for rows in [saved_serials]
        }
        self.assertEqual(product_pallet_quantities, {
            (self.http_product.ginlong_product_code, pallet_code): 3 for pallet_code in pallets
        } | {
            (self.http_serial_product.ginlong_product_code, pallet_code): 2 for pallet_code in pallets
        } | {
            (self.http_second_serial_product.ginlong_product_code, pallet_code): 2 for pallet_code in pallets
        })

        # 保税类型允许非 SN 原材料只提交订单总量，不要求虚构托盘分配。
        raw_no = marker + "-API01-SN-RAW-OMITTED"
        raw_response = self._post_with_rate_reset(path, payload(
            raw_no, [detail(self.http_product, 3)], include_sn_list=False,
        ))
        self.assertEqual(json.loads(raw_response.text)["returnStatus"], "Y")
        self.env.invalidate_all()
        raw_order = self.env["world.depot.inbound.order"].sudo().search([("reference", "=", raw_no)])
        self.assertEqual(len(raw_order), 1)
        raw_product_rows = raw_order.inbound_order_product_ids.mapped("inbound_order_product_pallet_ids")
        self.assertEqual(sum(raw_product_rows.mapped("quantity")), 3)
        self.assertFalse(raw_order.ginlong_sn_list_json)
        self.assertFalse(raw_order.inbound_order_product_ids.product_serial_number_ids)

        # 明细含 SN 产品时，已提供的 SN 清单只需覆盖 SN 产品；原材料仍可仅保留总量。
        mixed_no = marker + "-API01-SN-RAW-OMITTED-MIXED"
        mixed_response = self._post_with_rate_reset(path, payload(
            mixed_no,
            [detail(self.http_serial_product, 1), detail(self.http_product, 3)],
            [serial(self.http_serial_product, marker + "-MIXED-ONE-SN")],
        ))
        self.assertEqual(json.loads(mixed_response.text)["returnStatus"], "Y")
        self.env.invalidate_all()
        mixed_order = self.env["world.depot.inbound.order"].sudo().search([
            ("reference", "=", mixed_no),
        ])
        self.assertEqual(len(mixed_order), 1)
        self.assertEqual(len(mixed_order.inbound_order_product_ids.product_serial_number_ids), 1)
        self.assertFalse(mixed_order.inbound_order_product_ids.filtered(
            lambda line: self.http_product in line.inbound_order_product_pallet_ids.product_id
        ).product_serial_number_ids)

        bad_cases = [
            ("MISSING-LIST", [detail(self.http_serial_product, 2)], None, False, "SN清单缺失"),
            ("RAW-PSEUDO-SN-MISMATCH", [detail(self.http_product, 3)], [serial(
                self.http_product, marker + "-WRONG-RAW-SN", 3, marker + "-RAW-PALLET-A",
            )], True, "非SN行productSN须等于productCode"),
            ("RAW-PALLET-QTY-MISMATCH", [detail(self.http_product, 6)], [
                serial(self.http_product, self.http_product.ginlong_product_code, 2, marker + "-RAW-PALLET-A"),
                serial(self.http_product, self.http_product.ginlong_product_code, 3, marker + "-RAW-PALLET-B"),
            ], True, "SN数量不一致"),
            ("SHORT", [detail(self.http_serial_product, 2)], [serial(
                self.http_serial_product, marker + "-SHORT-SN", 1,
            )], True, "SN数量不一致"),
            ("EXCESS", [detail(self.http_serial_product, 2)], [
                serial(self.http_serial_product, marker + "-EXCESS-1", 1),
                serial(self.http_serial_product, marker + "-EXCESS-2", 1),
                serial(self.http_serial_product, marker + "-EXCESS-3", 1),
            ], True, "SN数量不一致"),
            ("SN-ROW-QUANTITY", [detail(self.http_serial_product, 3)], [
                serial(
                    self.http_serial_product, marker + "-SN-ROW-QTY", 3,
                    marker + "-SN-QTY-PALLET",
                ),
            ], True, "SN数量≠1"),
            ("PRODUCT-MISMATCH", [detail(self.http_serial_product, 1)], [
                serial(self.http_product, marker + "-WRONG-PRODUCT", 1),
            ], True, "SN产品不匹配"),
            ("PARTIAL", [detail(self.http_serial_product, 1), detail(self.http_second_serial_product, 1)], [
                serial(self.http_serial_product, marker + "-PARTIAL-SN", 1),
            ], True, "SN记录缺失"),
            ("DUPLICATE", [detail(self.http_serial_product, 2)], [
                serial(self.http_serial_product, "DUP-" + "D" * 80, 1, marker + "-DUP-PALLET-A"),
                serial(self.http_serial_product, "DUP-" + "D" * 80, 1, marker + "-DUP-PALLET-B"),
            ], True, "SN重复"),
            ("INCOMPLETE", [detail(self.http_serial_product, 1)], [{
                "quantity": 1, "productCode": self.http_serial_product.ginlong_product_code,
            }], True, "SN字段缺失: snList.productSN"),
        ]
        for suffix, details, sn_list, include_sn_list, expected in bad_cases:
            order_no = "%s-API01-SN-%s" % (marker, suffix)
            request_payload = payload(order_no, details, sn_list, include_sn_list)
            stock_before = self._stock_side_effect_snapshot(details)
            response = self._post_with_rate_reset(path, request_payload)
            body = self._assert_sn_business_rejection(response, order_no, expected)
            if suffix == "SN-ROW-QUANTITY":
                # 响应受 40 字符限制，检查产品码/托盘码尾部；完整编码必须保留在诊断日志。
                product_code = self.http_serial_product.ginlong_product_code
                pallet_code = marker + "-SN-QTY-PALLET"
                self.assertIn("P=…" + product_code[-11:], body["exceptionInfo"])
                self.assertIn("T=…" + pallet_code[-8:], body["exceptionInfo"])
                diagnostic = "productCode=%s, productSN=%s, palletCode=%s" % (
                    product_code, marker + "-SN-ROW-QTY", pallet_code,
                )
                self.assertTrue(any(
                    diagnostic in (log["exception_details"] or "")
                    for log in self._committed_api_logs(order_no)
                ), order_no)
            if suffix == "DUPLICATE":
                self.assertTrue(body["exceptionInfo"].endswith("..."))
            self._assert_no_successful_sn_order(
                "API01", order_no, "world.depot.inbound.order", order_no,
            )
            self.assertEqual(
                self._stock_side_effect_snapshot(details), stock_before,
                "API01 拒绝请求不得创建或修改库存、SN、托盘或 Picking 记录: %s" % order_no,
            )

    def test_http_api05_sn_consistency_by_product_tracking(self):
        """真实 HTTP 验证 API05 按 tracking 校验客户盘点指令的 SN 清单。"""
        marker = self.http_test_marker
        path = "/api/ginlong/TPL_Stocktake_Order"

        def detail(product, quantity):
            """构造一条协议完整的客户盘点计划明细。"""
            return {
                "productCode": product.ginlong_product_code, "productName": product.name,
                "specificationModel": product.product_tmpl_id.ginlong_specification_model,
                "quantity": quantity,
            }

        def serial(product, serial_number, quantity=1, pallet_code=None):
            """构造 API05 要求字段齐全的计划 SN 记录。"""
            return {
                "productSN": serial_number, "quantity": quantity,
                "palletCode": pallet_code or marker + "-PALLET",
                "productCode": product.ginlong_product_code,
                "productName": product.name,
                "specificationModel": product.product_tmpl_id.ginlong_specification_model,
            }

        def payload(count_no, details, sn_list=None, include_sn_list=True):
            """构造独立盘点单号的 API05 Add 请求。"""
            result = {
                "owner": self.http_owner.ginlong_owner_code, "action": "Add",
                "countOrderNo": count_no, "warehouse": self.http_warehouse.code,
                "details": details,
            }
            if include_sn_list:
                result["snList"] = sn_list or []
            return result

        valid_no = marker + "-API05-SN-VALID"
        pallets = [marker + "-COUNT-PALLET-A", marker + "-COUNT-PALLET-B", marker + "-COUNT-PALLET-C"]
        valid_sn_rows = []
        for pallet_index, pallet_code in enumerate(pallets):
            # 盘点计划同样逐托盘保存原材料数量和两类产品的真实 SN 行。
            valid_sn_rows.append(serial(
                self.http_product, self.http_product.ginlong_product_code, 3, pallet_code,
            ))
            for product, product_prefix in (
                (self.http_serial_product, "FG"),
                (self.http_second_serial_product, "SF"),
            ):
                for serial_index in (1, 2):
                    valid_sn_rows.append(serial(
                        product,
                        "%s-COUNT-%s-%s-%02d" % (
                            marker, product_prefix, chr(ord("A") + pallet_index), serial_index,
                        ),
                        pallet_code=pallet_code,
                    ))
        valid_payload = payload(valid_no, [
            detail(self.http_serial_product, 6),
            detail(self.http_second_serial_product, 6),
            detail(self.http_product, 9),
        ], valid_sn_rows)
        valid_response = self._post_with_rate_reset(path, valid_payload)
        valid_body = json.loads(valid_response.text)
        self.assertEqual(valid_response.status_code, 200)
        self.assertEqual(valid_body["returnStatus"], "Y")
        self.env.invalidate_all()
        task = self.env["world.depot.stocktake.order"].sudo().search([
            ("count_order_no", "=", valid_no),
        ])
        self.assertEqual(len(task), 1)
        self.assertEqual(task.get_plan_details(), valid_payload["details"])
        self.assertEqual(task.get_plan_sn_list(), valid_payload["snList"])
        plan_sn_rows = task.get_plan_sn_list()
        self.assertEqual(len(plan_sn_rows), 15)
        self.assertEqual(len({row["productSN"] for row in plan_sn_rows}), 13)
        self.assertEqual({row["quantity"] for row in plan_sn_rows}, {1, 3})
        self.assertEqual({row["palletCode"] for row in plan_sn_rows}, {
            marker + "-COUNT-PALLET-A", marker + "-COUNT-PALLET-B", marker + "-COUNT-PALLET-C",
        })
        detail_quantities = {
            row["productCode"]: row["quantity"] for row in valid_payload["details"]
        }
        sn_quantities = {}
        for row in plan_sn_rows:
            sn_quantities[row["productCode"]] = sn_quantities.get(row["productCode"], 0) + row["quantity"]
        self.assertEqual(sn_quantities, {
            self.http_serial_product.ginlong_product_code: detail_quantities[
                self.http_serial_product.ginlong_product_code
            ],
            self.http_second_serial_product.ginlong_product_code: detail_quantities[
                self.http_second_serial_product.ginlong_product_code
            ],
            self.http_product.ginlong_product_code: detail_quantities[
                self.http_product.ginlong_product_code
            ],
        })
        raw_pallet_rows = [row for row in plan_sn_rows if row["productCode"] == self.http_product.ginlong_product_code]
        self.assertEqual(len(raw_pallet_rows), 3)
        self.assertEqual({row["productSN"] for row in raw_pallet_rows}, {
            self.http_product.ginlong_product_code,
        })
        self.assertEqual({row["quantity"] for row in raw_pallet_rows}, {3})
        self.assertEqual({row["palletCode"] for row in raw_pallet_rows}, set(pallets))
        plan_quantities_by_product_pallet = {
            (product_code, pallet_code): sum(
                row["quantity"] for row in plan_sn_rows
                if row["productCode"] == product_code and row["palletCode"] == pallet_code
            )
            for product_code in detail_quantities
            for pallet_code in pallets
        }
        self.assertEqual(plan_quantities_by_product_pallet, {
            (self.http_product.ginlong_product_code, pallet_code): 3 for pallet_code in pallets
        } | {
            (self.http_serial_product.ginlong_product_code, pallet_code): 2 for pallet_code in pallets
        } | {
            (self.http_second_serial_product.ginlong_product_code, pallet_code): 2 for pallet_code in pallets
        })
        self.assertGreater(len({
            row["palletCode"] for row in plan_sn_rows
            if row["productCode"] == self.http_serial_product.ginlong_product_code
        }), 1)
        self.assertFalse(task.result_ids)

        raw_no = marker + "-API05-SN-RAW-ZERO-OMITTED"
        raw_response = self._post_with_rate_reset(path, payload(
            raw_no, [detail(self.http_product, 0)], include_sn_list=False,
        ))
        self.assertEqual(json.loads(raw_response.text)["returnStatus"], "Y")
        self.env.invalidate_all()
        raw_task = self.env["world.depot.stocktake.order"].sudo().search([
            ("count_order_no", "=", raw_no),
        ])
        self.assertEqual(len(raw_task), 1)
        self.assertEqual(raw_task.get_plan_sn_list(), [])

        bad_cases = [
            ("MISSING-LIST", [detail(self.http_serial_product, 2)], None, False, "SN清单缺失"),
            ("MISSING-LIST-RAW", [detail(self.http_product, 3)], None, False, "原材料托盘明细缺失"),
            ("RAW-PSEUDO-SN-MISMATCH", [detail(self.http_product, 3)], [serial(
                self.http_product, marker + "-COUNT-WRONG-RAW-SN", 3,
                marker + "-COUNT-RAW-PALLET-A",
            )], True, "非SN行productSN须等于productCode"),
            ("RAW-PALLET-QTY-MISMATCH", [detail(self.http_product, 6)], [
                serial(
                    self.http_product, self.http_product.ginlong_product_code, 2,
                    marker + "-COUNT-RAW-PALLET-A",
                ),
                serial(
                    self.http_product, self.http_product.ginlong_product_code, 3,
                    marker + "-COUNT-RAW-PALLET-B",
                ),
            ], True, "SN数量不一致"),
            ("SHORT", [detail(self.http_serial_product, 2)], [serial(
                self.http_serial_product, marker + "-COUNT-SHORT", 1,
            )], True, "SN数量不一致"),
            ("EXCESS", [detail(self.http_serial_product, 2)], [
                serial(self.http_serial_product, marker + "-COUNT-EXCESS-1", 1),
                serial(self.http_serial_product, marker + "-COUNT-EXCESS-2", 1),
                serial(self.http_serial_product, marker + "-COUNT-EXCESS-3", 1),
            ], True, "SN数量不一致"),
            ("SN-ROW-QUANTITY", [detail(self.http_serial_product, 3)], [
                serial(
                    self.http_serial_product, marker + "-COUNT-SN-ROW-QTY", 3,
                    marker + "-COUNT-SN-QTY-PALLET",
                ),
            ], True, "SN数量≠1"),
            ("PRODUCT-MISMATCH", [detail(self.http_serial_product, 1)], [
                serial(self.http_product, marker + "-COUNT-WRONG-PRODUCT", 1),
            ], True, "SN产品不匹配"),
            ("PARTIAL", [detail(self.http_serial_product, 1), detail(self.http_second_serial_product, 1)], [
                serial(self.http_serial_product, marker + "-COUNT-PARTIAL-SN", 1),
            ], True, "SN记录缺失"),
            ("DUPLICATE", [detail(self.http_serial_product, 2)], [
                serial(
                    self.http_serial_product, "COUNT-DUP-" + "D" * 78, 1,
                    marker + "-COUNT-DUP-PALLET-A",
                ),
                serial(
                    self.http_serial_product, "COUNT-DUP-" + "D" * 78, 1,
                    marker + "-COUNT-DUP-PALLET-B",
                ),
            ], True, "SN重复"),
        ]
        for suffix, details, sn_list, include_sn_list, expected in bad_cases:
            count_no = "%s-API05-SN-%s" % (marker, suffix)
            stock_before = self._stock_side_effect_snapshot(details)
            response = self._post_with_rate_reset(
                path, payload(count_no, details, sn_list, include_sn_list),
            )
            body = self._assert_sn_business_rejection(response, count_no, expected)
            if suffix == "SN-ROW-QUANTITY":
                # API05 共用同一 SN 一致性校验器，故须显示精简定位并在日志保留完整值。
                product_code = self.http_serial_product.ginlong_product_code
                pallet_code = marker + "-COUNT-SN-QTY-PALLET"
                self.assertIn("P=…" + product_code[-11:], body["exceptionInfo"])
                self.assertIn("T=…" + pallet_code[-8:], body["exceptionInfo"])
                diagnostic = "productCode=%s, productSN=%s, palletCode=%s" % (
                    product_code, marker + "-COUNT-SN-ROW-QTY", pallet_code,
                )
                self.assertTrue(any(
                    diagnostic in (log["exception_details"] or "")
                    for log in self._committed_api_logs(count_no)
                ), count_no)
            if suffix == "DUPLICATE":
                self.assertTrue(body["exceptionInfo"].endswith("..."))
            self._assert_no_successful_sn_order(
                "API05", count_no, "world.depot.stocktake.order", count_no,
            )
            self.assertEqual(
                self._stock_side_effect_snapshot(details), stock_before,
                "API05 拒绝请求不得创建或修改库存、SN、托盘或 Picking 记录: %s" % count_no,
            )

        incomplete_no = marker + "-API05-SN-INCOMPLETE"
        incomplete_payload = payload(incomplete_no, [detail(self.http_serial_product, 1)], [{
            "quantity": 1, "palletCode": marker + "-COUNT-PALLET",
            "productCode": self.http_serial_product.ginlong_product_code,
            "productName": self.http_serial_product.name,
            "specificationModel": self.http_serial_product.product_tmpl_id.ginlong_specification_model,
        }])
        incomplete_stock_before = self._stock_side_effect_snapshot(incomplete_payload["details"])
        response = self._post_with_rate_reset(path, incomplete_payload)
        body = json.loads(response.text)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["returnStatus"], "N")
        self.assertTrue(body["exceptionInfo"].startswith("REQ01: "))
        self.assertIn("snList[0].productSN", body["exceptionInfo"])
        self.assertLessEqual(len(body["exceptionInfo"]), 40)
        self._assert_no_successful_sn_order(
            "API05", incomplete_no, "world.depot.stocktake.order", incomplete_no,
        )
        self.assertEqual(
            self._stock_side_effect_snapshot(incomplete_payload["details"]), incomplete_stock_before,
            "API05 必填校验拒绝不得创建或修改库存、SN、托盘或 Picking 记录",
        )

    def test_http_api01_sn_identity_is_product_scoped_and_orders_can_reference_it(self):
        """验证 SN 键包含产品编码、不同订单可引用同一 SN，且托盘不参与键。"""
        marker = self.http_test_marker
        path = "/api/ginlong/TPL_Pending_Receipt_Note"
        shared_sn = marker + "-SHARED-SN"

        def detail(product):
            """生成一件序列号产品的订单明细。"""
            return {
                "productCode": product.ginlong_product_code,
                "productName": product.name,
                "specificationModel": product.product_tmpl_id.ginlong_specification_model,
                "quantity": 1,
            }

        def serial(product, pallet_code):
            """生成使用同一 SN、但由产品编码和托盘分别区分的 SN 行。"""
            return {
                "productSN": shared_sn,
                "quantity": 1,
                "palletCode": pallet_code,
                "productCode": product.ginlong_product_code,
                "productName": product.name,
                "specificationModel": product.product_tmpl_id.ginlong_specification_model,
            }

        def post_order(order_no, details, sn_list):
            """经真实 API01 HTTP 路由提交独立业务单号。"""
            return self._post_with_rate_reset(path, {
                "owner": self.http_owner.ginlong_owner_code,
                "action": "Add",
                "inboundOrderNo": order_no,
                "warehouse": self.http_warehouse.code,
                "businessType": "保税_海外收货入库",
                "details": details,
                "snList": sn_list,
            })

        first_no = marker + "-SN-IDENTITY-FIRST"
        first_response = post_order(first_no, [
            detail(self.http_serial_product),
            detail(self.http_second_serial_product),
        ], [
            serial(self.http_serial_product, marker + "-PALLET-A"),
            serial(self.http_second_serial_product, marker + "-PALLET-B"),
        ])
        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(json.loads(first_response.text)["returnStatus"], "Y")
        self.env.invalidate_all()
        first_order = self.env["world.depot.inbound.order"].sudo().search([
            ("reference", "=", first_no),
        ])
        first_serials = first_order.inbound_order_product_ids.mapped("product_serial_number_ids")
        self.assertEqual(len(first_order), 1)
        self.assertEqual(len(first_serials), 2)
        self.assertEqual(set(first_serials.mapped("serial_number")), {shared_sn})
        self.assertEqual(set(first_serials.mapped("ginlong_product_code")), {
            self.http_serial_product.ginlong_product_code,
            self.http_second_serial_product.ginlong_product_code,
        })
        self.assertEqual(set(first_serials.mapped("ginlong_pallet_code")), {
            marker + "-PALLET-A", marker + "-PALLET-B",
        })

        # API01 明细保存的是业务单据中的 SN 引用；新业务单号可再次引用同一产品 SN。
        second_no = marker + "-SN-IDENTITY-SECOND"
        second_response = post_order(second_no, [detail(self.http_serial_product)], [
            serial(self.http_serial_product, marker + "-PALLET-C"),
        ])
        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(json.loads(second_response.text)["returnStatus"], "Y")
        self.env.invalidate_all()
        second_order = self.env["world.depot.inbound.order"].sudo().search([
            ("reference", "=", second_no),
        ])
        self.assertEqual(len(second_order), 1)
        self.assertEqual(
            second_order.inbound_order_product_ids.product_serial_number_ids.serial_number,
            shared_sn,
        )
        self.assertEqual(second_order.inbound_order_product_ids.product_serial_number_ids.ginlong_pallet_code,
                         marker + "-PALLET-C")
        self.assertEqual(self.env["world.depot.inbound.order"].sudo().search_count([
            ("reference", "in", [first_no, second_no]),
        ]), 2)

    def test_http_api01_non_bonded_ignores_sn_list_and_logs_original_request(self):
        """验证非保税 API01 Add 忽略 snList 业务内容，但 API 日志保留原始报文。"""
        marker = self.http_test_marker
        path = "/api/ginlong/TPL_Pending_Receipt_Note"
        cases = [
            ("MISSING", None, False),
            ("NULL", None, True),
            ("STRING", "not-an-array", True),
            ("OBJECT", {"unexpected": "shape"}, True),
            ("BAD-ROW", [{"productSN": "", "quantity": "invalid"}], True),
        ]

        for suffix, sn_list, include_sn_list in cases:
            order_no = "%s-API01-NON-BONDED-%s" % (marker, suffix)
            request_payload = {
                "owner": self.http_owner.ginlong_owner_code,
                "action": "Add",
                "inboundOrderNo": order_no,
                "warehouse": self.http_warehouse.code,
                "businessType": "STANDARD",
                "details": [{
                    "productCode": self.http_product.ginlong_product_code,
                    "productName": self.http_product.name,
                    "specificationModel": self.http_product.product_tmpl_id.ginlong_specification_model,
                    "quantity": 3,
                }],
            }
            if include_sn_list:
                request_payload["snList"] = sn_list

            response = self._post_with_rate_reset(path, request_payload)
            self.assertEqual(response.status_code, 200)
            body = json.loads(response.text)
            self.assertEqual(set(body), {"returnStatus", "exceptionInfo", "operationTime"})
            self.assertEqual(body["returnStatus"], "Y", (suffix, body))
            self.assertEqual(body["exceptionInfo"], "OK")

            self.env.invalidate_all()
            order = self.env["world.depot.inbound.order"].sudo().search([
                ("reference", "=", order_no),
            ])
            self.assertEqual(len(order), 1)
            product_rows = order.inbound_order_product_ids.mapped("inbound_order_product_pallet_ids")
            self.assertEqual(len(product_rows), 1)
            self.assertEqual(product_rows.product_id, self.http_product)
            self.assertEqual(product_rows.quantity, 3)
            self.assertFalse(order.ginlong_sn_list_json)
            self.assertFalse(order.inbound_order_product_ids.product_serial_number_ids)

            # 业务单据忽略 snList，API 日志仍须能还原收到的完整请求。
            logs = self.env["world.depot.api.log"].sudo().search([
                ("request_path", "=", path), ("request_data", "ilike", order_no),
            ])
            self.assertEqual(len(logs), 1)
            self.assertEqual(json.loads(logs.request_data), request_payload)
            successful_attempts = self.env["ginlong.api.idempotency"].sudo().search([
                ("api_code", "=", "API01"), ("business_key", "=", order_no),
                ("state", "=", "succeeded"),
            ])
            self.assertEqual(len(successful_attempts), 1)

    def test_http_api05_accepts_existing_and_unreceived_serial_references(self):
        """验证 API05 可引用已有 stock.lot 或尚未入库的 SN，且不同产品可同 SN。"""
        marker = self.http_test_marker
        path = "/api/ginlong/TPL_Stocktake_Order"
        existing_sn = marker + "-EXISTING-STOCK-SN"
        unreceived_sn = marker + "-UNRECEIVED-SN"
        self.env["stock.lot"].sudo().create({
            "name": existing_sn,
            "product_id": self.http_serial_product.id,
            "company_id": self.env.company.id,
        })

        def detail(product, quantity):
            """生成一条产品盘点范围。"""
            return {
                "productCode": product.ginlong_product_code,
                "productName": product.name,
                "specificationModel": product.product_tmpl_id.ginlong_specification_model,
                "quantity": quantity,
            }

        def serial(product, serial_number, pallet_code):
            """生成盘点任务中的单件 SN 引用。"""
            return {
                "productSN": serial_number,
                "quantity": 1,
                "palletCode": pallet_code,
                "productCode": product.ginlong_product_code,
                "productName": product.name,
                "specificationModel": product.product_tmpl_id.ginlong_specification_model,
            }

        count_no = marker + "-COUNT-REFERENCE"
        payload = {
            "owner": self.http_owner.ginlong_owner_code,
            "action": "Add",
            "countOrderNo": count_no,
            "warehouse": self.http_warehouse.code,
            "details": [detail(self.http_serial_product, 2)],
            "snList": [
                serial(self.http_serial_product, existing_sn, marker + "-COUNT-PALLET-A"),
                serial(self.http_serial_product, unreceived_sn, marker + "-COUNT-PALLET-B"),
            ],
        }
        response = self._post_with_rate_reset(path, payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.text)["returnStatus"], "Y")
        self.env.invalidate_all()
        task = self.env["world.depot.stocktake.order"].sudo().search([
            ("count_order_no", "=", count_no),
        ])
        self.assertEqual(len(task), 1)
        self.assertEqual(task.get_plan_sn_list(), payload["snList"])
        self.assertEqual({row["productSN"] for row in task.get_plan_sn_list()}, {
            existing_sn, unreceived_sn,
        })
        self.assertEqual(self.env["stock.lot"].sudo().search_count([
            ("name", "=", existing_sn), ("product_id", "=", self.http_serial_product.id),
        ]), 1)
        self.assertEqual(self.env["stock.lot"].sudo().search_count([
            ("name", "=", unreceived_sn),
        ]), 0)

        # 相同 SN 可被不同 productCode 标识，重复判定不跨产品编码。
        shared_sn = marker + "-CROSS-PRODUCT-SN"
        cross_product_no = marker + "-COUNT-CROSS-PRODUCT"
        cross_product_payload = {
            "owner": self.http_owner.ginlong_owner_code,
            "action": "Add",
            "countOrderNo": cross_product_no,
            "warehouse": self.http_warehouse.code,
            "details": [
                detail(self.http_serial_product, 1),
                detail(self.http_second_serial_product, 1),
            ],
            "snList": [
                serial(self.http_serial_product, shared_sn, marker + "-CROSS-PRODUCT-PALLET-A"),
                serial(self.http_second_serial_product, shared_sn, marker + "-CROSS-PRODUCT-PALLET-B"),
            ],
        }
        cross_response = self._post_with_rate_reset(path, cross_product_payload)
        self.assertEqual(cross_response.status_code, 200)
        self.assertEqual(json.loads(cross_response.text)["returnStatus"], "Y")
        self.env.invalidate_all()
        cross_task = self.env["world.depot.stocktake.order"].sudo().search([
            ("count_order_no", "=", cross_product_no),
        ])
        self.assertEqual(cross_task.get_plan_sn_list(), cross_product_payload["snList"])
        self.assertEqual(len({row["productCode"] for row in cross_task.get_plan_sn_list()}), 2)
        self.assertEqual(len({row["productSN"] for row in cross_task.get_plan_sn_list()}), 1)

    def test_http_api01_add_duplicate_error_delete_authentication_and_validation(self):
        """真实 HTTP 验证 API01 首次 Add 成功、重复 Add 错误及其他核心行为。"""
        marker = self.http_test_marker
        reference = marker + "-IN"
        payload = {
            "owner": self.http_owner.ginlong_owner_code, "action": "Add",
            "inboundOrderNo": reference, "warehouse": self.http_warehouse.code,
            "businessType": "STANDARD", "remark": marker,
            "details": [{
                "productCode": self.http_product.ginlong_product_code,
                "productName": self.http_product.name,
                "specificationModel": "HTTP-MODEL", "quantity": 2,
            }],
        }
        first_response = self._post("/api/ginlong/TPL_Pending_Receipt_Note", payload)
        second_response = self._post("/api/ginlong/TPL_Pending_Receipt_Note", payload)
        first, second = json.loads(first_response.text), json.loads(second_response.text)
        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)
        # API01 成功响应只遵循 Ginlong V3.2 字段；内部 Odoo ID 留在 ORM 和幂等结果中。
        protocol_fields = {"returnStatus", "exceptionInfo", "operationTime"}
        self.assertEqual(set(first), protocol_fields)
        self.assertEqual(set(second), protocol_fields)
        self.assertEqual(first["returnStatus"], "Y")
        self.assertEqual(second["returnStatus"], "N")
        self.assertEqual(first["exceptionInfo"], "OK")
        self.assertEqual(second["exceptionInfo"], "IDM02: 重复新增，冲突键: inboundOrderNo")
        self.assertTrue(first["operationTime"])
        self.assertTrue(second["operationTime"])
        self.env.invalidate_all()
        order = self.env["world.depot.inbound.order"].search([("reference", "=", reference)])
        self.assertEqual(len(order), 1)
        self.assertEqual(order.ginlong_owner_id, self.http_owner)
        idem = self.env["ginlong.api.idempotency"].search([
            ("api_code", "=", "API01"), ("business_key", "=", reference),
        ])
        self.assertEqual(len(idem), 1)
        self.assertEqual(idem.state, "succeeded")
        # 保留内部处理结果供审计和数据关联；对外重复 Add 不重放该成功响应。
        saved_result = json.loads(idem.response_json)
        self.assertTrue(saved_result["success"])
        self.assertEqual(saved_result["data"]["id"], order.id)
        logs = self._committed_api_logs(marker)
        success_logs = [log for log in logs if log["success"]]
        duplicate_logs = [log for log in logs if log["code"] == "IDM02"]
        self.assertEqual(len(success_logs), 1)
        self.assertEqual(len(duplicate_logs), 1)
        for log in success_logs:
            logged_response = json.loads(log["response_data"])
            self.assertEqual(set(logged_response), protocol_fields)
            self.assertEqual(logged_response["returnStatus"], "Y")
        duplicate_log = duplicate_logs[0]
        self.assertFalse(duplicate_log["success"])
        self.assertIn(reference, duplicate_log["exception_details"])
        duplicate_response = json.loads(duplicate_log["response_data"])
        self.assertEqual(set(duplicate_response), protocol_fields)
        self.assertEqual(duplicate_response["returnStatus"], "N")

        delete_payload = {
            "owner": self.http_owner.ginlong_owner_code, "action": "Del",
            "inboundOrderNo": reference, "warehouse": self.http_warehouse.code,
            "businessType": "STANDARD", "remark": marker,
        }
        delete_first = self._post("/api/ginlong/TPL_Pending_Receipt_Note", delete_payload)
        delete_second = self._post("/api/ginlong/TPL_Pending_Receipt_Note", delete_payload)
        self.assertEqual(delete_first.status_code, 200)
        self.assertEqual(json.loads(delete_first.text), json.loads(delete_second.text))
        self.env.invalidate_all()
        self.assertTrue(order.exists())
        self.assertEqual(order.state, "cancel")

        # 取消后先用相同报文开启新生命周期，再取消并用不同报文再次创建。
        same_payload_re_add = self._post("/api/ginlong/TPL_Pending_Receipt_Note", payload)
        self.assertEqual(json.loads(same_payload_re_add.text)["returnStatus"], "Y")
        self.env.invalidate_all()
        same_lifecycle_order = self.env["world.depot.inbound.order"].search([
            ("reference", "=", reference), ("state", "!=", "cancel"),
        ])
        self.assertEqual(len(same_lifecycle_order), 1)
        second_delete = self._post("/api/ginlong/TPL_Pending_Receipt_Note", delete_payload)
        self.assertEqual(json.loads(second_delete.text)["returnStatus"], "Y")
        self.env.invalidate_all()
        self.assertEqual(same_lifecycle_order.state, "cancel")

        re_add_payload = deepcopy(payload)
        re_add_payload["remark"] = marker + " after delete"
        re_add_payload["details"][0]["quantity"] = 9
        re_add_response = self._post("/api/ginlong/TPL_Pending_Receipt_Note", re_add_payload)
        re_add_body = json.loads(re_add_response.text)
        self.assertEqual(re_add_response.status_code, 200)
        self.assertEqual(re_add_body["returnStatus"], "Y")
        self.assertEqual(re_add_body["exceptionInfo"], "OK")
        repeated_re_add = self._post("/api/ginlong/TPL_Pending_Receipt_Note", re_add_payload)
        self.assertEqual(json.loads(repeated_re_add.text)["returnStatus"], "N")
        self.assertEqual(json.loads(repeated_re_add.text)["exceptionInfo"],
                         "IDM02: 重复新增，冲突键: inboundOrderNo")
        self.env.invalidate_all()
        self.assertTrue(order.exists())
        self.assertEqual(order.state, "cancel")
        self.assertEqual(order.remark, marker)
        lifecycle_orders = self.env["world.depot.inbound.order"].search([
            ("reference", "=", reference),
        ], order="id")
        self.assertEqual(len(lifecycle_orders), 3)
        self.assertEqual(lifecycle_orders[0].state, "cancel")
        self.assertEqual(lifecycle_orders[1].state, "cancel")
        self.assertEqual(lifecycle_orders[2].state, "new")
        self.assertEqual(lifecycle_orders[2].remark, marker + " after delete")
        self.assertEqual(self.env["ginlong.api.idempotency"].search_count([
            ("api_code", "=", "API01"), ("business_key", "=", reference), ("action", "=", "add"),
        ]), 3)
        self.assertEqual(self.env["ginlong.api.idempotency"].search_count([
            ("api_code", "=", "API01"), ("business_key", "=", reference), ("action", "=", "del"),
        ]), 2)

        invalid = deepcopy(payload)
        invalid["inboundOrderNo"] = marker + "-INVALID"
        invalid["details"][0].pop("productName")
        invalid_response = self._post("/api/ginlong/TPL_Pending_Receipt_Note", invalid)
        self.assertEqual(invalid_response.status_code, 200)
        invalid_body = json.loads(invalid_response.text)
        self.assertEqual(set(invalid_body), {"returnStatus", "exceptionInfo", "operationTime"})
        self.assertEqual(invalid_body["returnStatus"], "N")
        self.assertTrue(invalid_body["exceptionInfo"].startswith("REQ01: "))
        self.env.invalidate_all()
        self.assertFalse(self.env["world.depot.inbound.order"].search([
            ("reference", "=", marker + "-INVALID"),
        ]))

        invalid_type = deepcopy(payload)
        invalid_type["inboundOrderNo"] = marker + "-INVALID-TYPE"
        invalid_type["details"][0]["quantity"] = "not-a-number"
        type_response = self._post("/api/ginlong/TPL_Pending_Receipt_Note", invalid_type)
        type_body = json.loads(type_response.text)
        self.assertEqual(type_response.status_code, 200)
        self.assertEqual(set(type_body), {"returnStatus", "exceptionInfo", "operationTime"})
        self.assertEqual(type_body["returnStatus"], "N")
        self.assertTrue(type_body["exceptionInfo"].startswith("TYP01: "))
        self.env.invalidate_all()
        self.assertFalse(self.env["world.depot.inbound.order"].search([
            ("reference", "=", marker + "-INVALID-TYPE"),
        ]))

        invalid_auth = self.url_open(
            "/api/ginlong/TPL_Pending_Receipt_Note",
            data=json.dumps(dict(payload, inboundOrderNo=marker + "-AUTH")).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": "Bearer invalid-token"},
        )
        self.assertEqual(invalid_auth.status_code, 401)
        invalid_auth_body = json.loads(invalid_auth.text)
        self.assertEqual(set(invalid_auth_body), {"returnStatus", "exceptionInfo", "operationTime"})
        self.assertTrue(invalid_auth_body["exceptionInfo"].startswith("AUTH01: "))
        self.env.invalidate_all()
        self.assertFalse(self.env["world.depot.inbound.order"].search([
            ("reference", "=", marker + "-AUTH"),
        ]))
        error_logs = self._committed_api_logs(marker)
        for expected_code in ("REQ01", "TYP01", "AUTH01"):
            self.assertTrue(any(log["code"] == expected_code for log in error_logs), expected_code)
        for log in error_logs:
            if not log["success"]:
                self.assertEqual(set(json.loads(log["response_data"])), {
                    "returnStatus", "exceptionInfo", "operationTime",
                })
                self.assertNotIn("Traceback", log["response_data"] or "")

    def test_http_api03_valid_owner_product_add_edit_delete_and_rejection(self):
        """真实 HTTP 验证 API03 的货主产品组合、编辑重复和无效组合回滚。"""
        marker = self.http_test_marker
        reference = marker + "-OUT"
        payload = {
            "owner": self.http_owner.ginlong_owner_code, "action": "Add",
            "outboundOrderNo": reference, "warehouse": self.http_warehouse.code,
            "businessType": "STANDARD", "remark": marker,
            "details": [{
                "productCode": self.http_product.ginlong_product_code,
                "productName": self.http_product.name,
                "specificationModel": "HTTP-MODEL", "quantity": 2,
                "net_wt_machine": 1, "net_wt_total": 2, "pack_qty": 1,
                "pallet_qty": 1, "pallet_len": 1, "pallet_wid": 1, "pallet_hgt": 1,
                "unit_vol": 1, "pack_unit": "BOX", "pack_wt": 1,
                "pallet_total_wt": 1, "total_vol": 1, "carton_wt_total": 1,
                "gross_wt_total": 1,
            }],
        }
        first_response = self._post_with_rate_reset("/api/ginlong/TPL_Pending_Delivery_Note", payload)
        duplicate_response = self._post_with_rate_reset("/api/ginlong/TPL_Pending_Delivery_Note", payload)
        first, duplicate = json.loads(first_response.text), json.loads(duplicate_response.text)
        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(duplicate_response.status_code, 400)
        self.assertTrue(first["success"])
        self.assertEqual(duplicate["returnStatus"], "N")
        self.assertEqual(duplicate["exceptionInfo"],
                         "IDM02: 重复新增，冲突键: outboundOrderNo")
        self.env.invalidate_all()
        order = self.env["world.depot.outbound.order"].search([("reference", "=", reference)])
        self.assertEqual(len(order), 1)
        self.assertEqual(order.outbound_order_product_ids.product_id, self.http_product)
        self.assertEqual(order.unload_company, self.http_recipient)

        edit = dict(payload, action="Edit", productName=self.http_product.name)
        first_edit = self._post_with_rate_reset("/api/ginlong/TPL_Pending_Delivery_Note", edit)
        repeated_edit = self._post_with_rate_reset("/api/ginlong/TPL_Pending_Delivery_Note", edit)
        self.assertEqual(first_edit.status_code, 200)
        self.assertEqual(repeated_edit.status_code, 200)
        self.assertTrue(json.loads(first_edit.text)["success"])
        self.assertTrue(json.loads(repeated_edit.text)["success"])

        invalid_pair = deepcopy(payload)
        invalid_pair.update({"owner": marker + "-UNKNOWN-OWNER", "outboundOrderNo": marker + "-REJECT"})
        invalid_pair["details"][0]["productCode"] = marker + "-UNKNOWN-PRODUCT"
        rejected = self._post_with_rate_reset("/api/ginlong/TPL_Pending_Delivery_Note", invalid_pair)
        self.assertEqual(rejected.status_code, 400)
        rejected_body = json.loads(rejected.text)
        self.assertEqual(set(rejected_body), {"returnStatus", "exceptionInfo", "operationTime"})
        self.assertEqual(rejected_body["returnStatus"], "N")
        self.assertTrue(rejected_body["exceptionInfo"].startswith("BUS01: "))
        self.assertIn("Ginlong owner code", rejected_body["exceptionInfo"])
        self.assertNotEqual(rejected_body["exceptionInfo"], "BUS01: 业务处理失败")
        self.env.invalidate_all()
        self.assertFalse(self.env["world.depot.outbound.order"].search([
            ("reference", "=", marker + "-REJECT"),
        ]))
        self.assertFalse(self.env["res.partner"].with_context(active_test=False).search([
            ("ginlong_owner_code", "=", marker + "-UNKNOWN-OWNER"),
        ]))

        retry_owner_code = invalid_pair["owner"]
        retry_product_code = invalid_pair["details"][0]["productCode"]
        self.env["res.partner"].create({
            "name": retry_owner_code, "is_company": True, "ginlong_owner_code": retry_owner_code,
        })
        services.api07(self.env, self.http_api_user, {
            "action": "Add", "owner": retry_owner_code, "productCode": retry_product_code,
            "productName": self.http_product.name, "specificationModel": "HTTP-MODEL",
            "unit": self.env.ref("uom.product_uom_unit").name, "productForm": "原材料",
        })
        retried = self._post_with_rate_reset("/api/ginlong/TPL_Pending_Delivery_Note", invalid_pair)
        repeated_retry = self._post_with_rate_reset("/api/ginlong/TPL_Pending_Delivery_Note", invalid_pair)
        self.assertEqual(retried.status_code, 200)
        self.assertTrue(json.loads(retried.text)["success"])
        self.assertEqual(repeated_retry.status_code, 400)
        self.assertEqual(json.loads(repeated_retry.text)["exceptionInfo"],
                         "IDM02: 重复新增，冲突键: outboundOrderNo")
        self.env.invalidate_all()
        rejected_order = self.env["world.depot.outbound.order"].search([
            ("reference", "=", marker + "-REJECT"),
        ])
        self.assertEqual(len(rejected_order), 1)
        self.assertEqual(rejected_order.outbound_order_product_ids.product_id.ginlong_owner_code, retry_owner_code)
        self.assertEqual(self.env["ginlong.api.idempotency"].search_count([
            ("api_code", "=", "API03"), ("business_key", "=", marker + "-REJECT"),
        ]), 1)

        delete = {
            "owner": self.http_owner.ginlong_owner_code, "action": "Del",
            "outboundOrderNo": reference, "warehouse": self.http_warehouse.code,
            "businessType": "STANDARD", "remark": marker,
        }
        delete_first = self._post_with_rate_reset("/api/ginlong/TPL_Pending_Delivery_Note", delete)
        delete_replay = self._post_with_rate_reset("/api/ginlong/TPL_Pending_Delivery_Note", delete)
        self.assertEqual(delete_first.status_code, 200)
        self.assertEqual(json.loads(delete_first.text), json.loads(delete_replay.text))
        self.env.invalidate_all()
        self.assertTrue(order.exists())
        self.assertEqual(order.state, "cancel")

        same_payload_re_add = self._post_with_rate_reset(
            "/api/ginlong/TPL_Pending_Delivery_Note", payload,
        )
        self.assertTrue(json.loads(same_payload_re_add.text)["success"])
        second_delete = self._post_with_rate_reset("/api/ginlong/TPL_Pending_Delivery_Note", delete)
        self.assertEqual(json.loads(second_delete.text)["returnStatus"], "Y")
        self.env.invalidate_all()
        intermediate_orders = self.env["world.depot.outbound.order"].search([
            ("reference", "=", reference),
        ], order="id")
        self.assertEqual(len(intermediate_orders), 2)
        self.assertEqual(intermediate_orders[1].state, "cancel")

        re_add = dict(payload, remark=marker + " after cancel")
        re_add_response = self._post_with_rate_reset("/api/ginlong/TPL_Pending_Delivery_Note", re_add)
        self.assertTrue(json.loads(re_add_response.text)["success"])
        repeated_re_add = self._post_with_rate_reset("/api/ginlong/TPL_Pending_Delivery_Note", re_add)
        self.assertEqual(repeated_re_add.status_code, 400)
        self.assertEqual(json.loads(repeated_re_add.text)["exceptionInfo"],
                         "IDM02: 重复新增，冲突键: outboundOrderNo")
        self.env.invalidate_all()
        lifecycle_orders = self.env["world.depot.outbound.order"].search([
            ("reference", "=", reference),
        ], order="id")
        self.assertEqual(len(lifecycle_orders), 3)
        self.assertEqual(lifecycle_orders[0].state, "cancel")
        self.assertEqual(lifecycle_orders[1].state, "cancel")
        self.assertNotEqual(lifecycle_orders[2].state, "cancel")

    def test_http_api05_add_repeatable_edit_and_delete(self):
        """真实 HTTP 验证 API05 指令 Add/重复 Edit/Delete 的 ORM 结果。"""
        marker = self.http_test_marker
        count_order_no = marker + "-COUNT"
        # 本用例验证盘点指令幂等，使用 SN 管理产品构造满足既有 API05 规则的有效报文。
        payload = {
            "owner": self.http_owner.ginlong_owner_code, "action": "Add",
            "countOrderNo": count_order_no, "warehouse": self.http_warehouse.code,
            "remark": marker,
            "details": [{
                "productCode": self.http_serial_product.ginlong_product_code,
                "productName": self.http_serial_product.name,
                "specificationModel": self.http_serial_product.product_tmpl_id.ginlong_specification_model,
                "quantity": 2,
            }],
            # 每条 productSN 代表单件；两件明细由两条 quantity=1 的 SN 记录汇总。
            "snList": [{
                "productSN": marker + "-SN-01", "quantity": 1, "palletCode": marker + "-PALLET",
                "productCode": self.http_serial_product.ginlong_product_code,
                "productName": self.http_serial_product.name,
                "specificationModel": self.http_serial_product.product_tmpl_id.ginlong_specification_model,
            }, {
                "productSN": marker + "-SN-02", "quantity": 1, "palletCode": marker + "-PALLET",
                "productCode": self.http_serial_product.ginlong_product_code,
                "productName": self.http_serial_product.name,
                "specificationModel": self.http_serial_product.product_tmpl_id.ginlong_specification_model,
            }],
        }
        first_response = self._post("/api/ginlong/TPL_Stocktake_Order", payload)
        duplicate_response = self._post("/api/ginlong/TPL_Stocktake_Order", payload)
        first, duplicate = json.loads(first_response.text), json.loads(duplicate_response.text)
        self.assertEqual(first_response.status_code, 200)
        self.assertTrue(first["success"])
        self.assertEqual(duplicate["returnStatus"], "N")
        self.assertEqual(duplicate["exceptionInfo"], "IDM02: 重复新增，冲突键: countOrderNo")
        self.env.invalidate_all()
        order = self.env["world.depot.stocktake.order"].search([("count_order_no", "=", count_order_no)])
        self.assertEqual(len(order), 1)
        self.assertEqual(order.get_plan_details(), payload["details"])
        self.assertEqual(order.get_plan_sn_list(), payload["snList"])
        edit = dict(payload, action="Edit", remark=marker + "-EDIT")
        edit_first = self._post("/api/ginlong/TPL_Stocktake_Order", edit)
        edit_second = self._post("/api/ginlong/TPL_Stocktake_Order", edit)
        self.assertTrue(json.loads(edit_first.text)["success"])
        self.assertTrue(json.loads(edit_second.text)["success"])
        self.env.invalidate_all()
        self.assertEqual(order.remark, marker + "-EDIT")
        delete = {
            "owner": self.http_owner.ginlong_owner_code, "action": "Del",
            "countOrderNo": count_order_no, "warehouse": self.http_warehouse.code,
            "remark": marker,
        }
        delete_first = self._post("/api/ginlong/TPL_Stocktake_Order", delete)
        delete_second = self._post("/api/ginlong/TPL_Stocktake_Order", delete)
        self.assertEqual(json.loads(delete_first.text), json.loads(delete_second.text))
        self.env.invalidate_all()
        self.assertTrue(order.exists())
        self.assertEqual(order.state, "cancel")

        same_payload_re_add = self._post("/api/ginlong/TPL_Stocktake_Order", payload)
        self.assertTrue(json.loads(same_payload_re_add.text)["success"])
        second_delete = self._post("/api/ginlong/TPL_Stocktake_Order", delete)
        self.assertEqual(json.loads(second_delete.text)["returnStatus"], "Y")
        self.env.invalidate_all()
        lifecycles = self.env["world.depot.stocktake.order"].search([
            ("count_order_no", "=", count_order_no),
        ], order="id")
        self.assertEqual(len(lifecycles), 2)
        self.assertEqual(lifecycles[0].state, "cancel")
        self.assertEqual(lifecycles[1].state, "cancel")

        re_add_payload = dict(payload, remark=marker + " re-added with changed payload")
        re_add_response = self._post("/api/ginlong/TPL_Stocktake_Order", re_add_payload)
        self.assertTrue(json.loads(re_add_response.text)["success"])
        repeat_re_add = self._post("/api/ginlong/TPL_Stocktake_Order", re_add_payload)
        self.assertEqual(json.loads(repeat_re_add.text)["returnStatus"], "N")
        self.env.invalidate_all()
        lifecycles = self.env["world.depot.stocktake.order"].search([
            ("count_order_no", "=", count_order_no),
        ], order="id")
        self.assertEqual(len(lifecycles), 3)
        self.assertEqual(lifecycles[0].state, "cancel")
        self.assertEqual(lifecycles[1].state, "cancel")
        self.assertNotEqual(lifecycles[2].state, "cancel")

    def test_http_api07_add_duplicate_rejection_and_repeatable_edit(self):
        """真实 HTTP 验证 API07 重复 Add 拒绝、Edit 可重复执行和跨货主新增。"""
        marker = self.http_test_marker
        payload = {
            "action": "Add", "owner": self.http_owner.ginlong_owner_code,
            # 使用 setUpClass 已通过 ORM 建立并提交的档案，确保独立 HTTP 请求可见。
            "productCode": self.http_product.ginlong_product_code,
            "productName": self.http_product.name,
            "specificationModel": self.http_product.product_tmpl_id.ginlong_specification_model,
            "unit": self.http_product.product_tmpl_id.ginlong_unit,
            "productForm": self.http_product.product_tmpl_id.ginlong_product_form,
            # Add 重复预检查会在业务更新前拒绝；该可选文本字段仅用于隔离本测试日志。
            "certificationModel": marker,
        }
        protocol_fields = {"returnStatus", "exceptionInfo", "operationTime"}
        original_name = self.http_product.product_tmpl_id.name

        # 字段校验失败必须在幂等及产品业务查询前返回具体缺失路径。
        missing_owner_payload = dict(payload, productCode=marker + "-MISSING-OWNER")
        missing_owner_payload.pop("owner")
        missing_owner_response = self._post(
            "/api/ginlong/TPL_Product_Master", missing_owner_payload,
        )
        missing_owner_body = json.loads(missing_owner_response.text)
        self.assertEqual(missing_owner_response.status_code, 200)
        self.assertEqual(set(missing_owner_body), protocol_fields)
        self.assertEqual(missing_owner_body["returnStatus"], "N")
        self.assertEqual(
            missing_owner_body["exceptionInfo"],
            "REQ01: 缺失字段: owner",
        )
        self.env.invalidate_all()
        self.assertFalse(self.env["product.product"].sudo().search([
            ("ginlong_owner_code", "=", self.http_owner.ginlong_owner_code),
            ("ginlong_product_code", "=", marker + "-MISSING-OWNER"),
        ]))
        self.assertFalse(self.env["ginlong.api.idempotency"].sudo().search([
            ("api_code", "=", "API07"), ("business_key", "ilike", marker + "-MISSING-OWNER"),
        ]))

        multiple_missing_payload = dict(missing_owner_payload, productCode=marker + "-MISSING-TWO")
        multiple_missing_payload.pop("productForm")
        multiple_missing_response = self._post(
            "/api/ginlong/TPL_Product_Master", multiple_missing_payload,
        )
        multiple_missing_body = json.loads(multiple_missing_response.text)
        self.assertEqual(multiple_missing_response.status_code, 200)
        self.assertEqual(set(multiple_missing_body), protocol_fields)
        self.assertEqual(multiple_missing_body["returnStatus"], "N")
        self.assertEqual(
            multiple_missing_body["exceptionInfo"],
            "REQ01: 缺失字段: owner, productForm",
        )
        self.assertFalse(self.env["product.product"].sudo().search([
            ("ginlong_product_code", "=", marker + "-MISSING-TWO"),
        ]))
        self.assertFalse(self.env["ginlong.api.idempotency"].sudo().search([
            ("api_code", "=", "API07"), ("business_key", "ilike", marker + "-MISSING-TWO"),
        ]))

        mixed_validation_payload = dict(
            multiple_missing_payload,
            productCode=marker + "-MISSING-AND-TYPE",
            weight="invalid-weight",
        )
        mixed_validation_response = self._post(
            "/api/ginlong/TPL_Product_Master", mixed_validation_payload,
        )
        mixed_validation_body = json.loads(mixed_validation_response.text)
        self.assertEqual(mixed_validation_response.status_code, 200)
        self.assertEqual(mixed_validation_body["returnStatus"], "N")
        self.assertEqual(
            mixed_validation_body["exceptionInfo"],
            "REQ01: 缺失字段: owner, productForm",
        )
        self.assertFalse(self.env["product.product"].sudo().search([
            ("ginlong_product_code", "=", marker + "-MISSING-AND-TYPE"),
        ]))
        self.assertFalse(self.env["ginlong.api.idempotency"].sudo().search([
            ("api_code", "=", "API07"), ("business_key", "ilike", marker + "-MISSING-AND-TYPE"),
        ]))

        multiple_type_payload = dict(
            payload,
            productCode=marker + "-MULTI-TYPE",
            weight="invalid-weight",
            length="invalid-length",
        )
        multiple_type_response = self._post(
            "/api/ginlong/TPL_Product_Master", multiple_type_payload,
        )
        multiple_type_body = json.loads(multiple_type_response.text)
        self.assertEqual(multiple_type_response.status_code, 200)
        self.assertEqual(multiple_type_body["returnStatus"], "N")
        self.assertEqual(
            multiple_type_body["exceptionInfo"],
            "TYP01: 类型错误字段: weight, length",
        )
        self.assertFalse(self.env["product.product"].sudo().search([
            ("ginlong_product_code", "=", marker + "-MULTI-TYPE"),
        ]))
        self.assertFalse(self.env["ginlong.api.idempotency"].sudo().search([
            ("api_code", "=", "API07"), ("business_key", "ilike", marker + "-MULTI-TYPE"),
        ]))

        duplicate_response = self._post("/api/ginlong/TPL_Product_Master", payload)
        changed_add = dict(payload, productName=marker + " changed duplicate", weight=99)
        changed_duplicate_response = self._post("/api/ginlong/TPL_Product_Master", changed_add)
        duplicate = json.loads(duplicate_response.text)
        changed_duplicate = json.loads(changed_duplicate_response.text)
        self.assertEqual(duplicate_response.status_code, 200)
        self.assertEqual(changed_duplicate_response.status_code, 200)
        self.assertEqual(set(duplicate), protocol_fields)
        self.assertEqual(set(changed_duplicate), protocol_fields)
        for rejected in (duplicate, changed_duplicate):
            self.assertEqual(rejected["returnStatus"], "N")
            self.assertEqual(
                rejected["exceptionInfo"], "IDM07: 重复新增，冲突键(owner, productCode)",
            )
        self.env.invalidate_all()
        self.assertEqual(self.http_product.product_tmpl_id.name, original_name)

        edit = dict(
            payload, action="Edit", productName=marker + " edited product",
            specificationModel="HTTP-EDITED-MODEL-" + self.http_suffix,
        )
        edit.pop("certificationModel")
        edit_first = self._post("/api/ginlong/TPL_Product_Master", edit)
        edit_second = self._post("/api/ginlong/TPL_Product_Master", edit)
        self.assertEqual(edit_first.status_code, 200)
        self.assertEqual(edit_second.status_code, 200)
        self.assertEqual(set(json.loads(edit_first.text)), protocol_fields)
        self.assertEqual(set(json.loads(edit_second.text)), protocol_fields)
        self.assertEqual(json.loads(edit_first.text)["returnStatus"], "Y")
        self.assertEqual(json.loads(edit_second.text)["returnStatus"], "Y")
        self.env.invalidate_all()
        self.assertEqual(self.http_product.product_tmpl_id.name, marker + " edited product")
        self.assertEqual(
            self.http_product.product_tmpl_id.ginlong_specification_model,
            "HTTP-EDITED-MODEL-" + self.http_suffix,
        )

        second_owner_add = dict(
            edit,
            # 用本测试唯一标记作为第二货主编码，便于测试清理器按原始请求体删除日志。
            owner=marker + "-OWNER-B",
            productName=self.http_product.name,
            action="Add",
        )
        second_owner_response = self._post("/api/ginlong/TPL_Product_Master", second_owner_add)
        second_owner_body = json.loads(second_owner_response.text)
        self.assertEqual(second_owner_response.status_code, 200)
        self.assertEqual(set(second_owner_body), protocol_fields)
        self.assertEqual(second_owner_body["returnStatus"], "Y")

        # 同一 productCode 的 productForm 是共享模板属性，冲突时对外说明修正方向并确认事务未改写档案。
        template = self.http_product.product_tmpl_id
        original_form = template.ginlong_product_form
        original_tracking = template.tracking
        conflicting_form = "成品" if original_form != "成品" else "原材料"
        form_conflict_response = self._post(
            "/api/ginlong/TPL_Product_Master",
            dict(second_owner_add, action="Edit", productForm=conflicting_form),
        )
        form_conflict_body = json.loads(form_conflict_response.text)
        self.assertEqual(form_conflict_response.status_code, 200)
        self.assertEqual(set(form_conflict_body), protocol_fields)
        self.assertEqual(form_conflict_body["returnStatus"], "N")
        self.assertEqual(
            form_conflict_body["exceptionInfo"],
            "BUS02: 同productCode的productForm必须一致",
        )
        self.env.invalidate_all()
        self.assertEqual(template.ginlong_product_form, original_form)
        self.assertEqual(template.tracking, original_tracking)

        missing_edit_code = marker + "-MISSING-EDIT"
        missing_edit = dict(edit, action="Edit", productCode=missing_edit_code)
        missing_edit_response = self._post("/api/ginlong/TPL_Product_Master", missing_edit)
        missing_edit_body = json.loads(missing_edit_response.text)
        self.assertEqual(missing_edit_response.status_code, 200)
        self.assertEqual(set(missing_edit_body), protocol_fields)
        self.assertEqual(missing_edit_body["returnStatus"], "N")
        self.assertEqual(missing_edit_body["exceptionInfo"], "BUS03: API07 Edit目标产品不存在")
        self.env.invalidate_all()
        self.assertFalse(self.env["product.product"].sudo().search([
            ("ginlong_owner_code", "=", self.http_owner.ginlong_owner_code),
            ("ginlong_product_code", "=", missing_edit_code),
        ]))

        invalid_product_code = marker + "-INVALID-FORM"
        invalid_form = dict(payload, productCode=invalid_product_code, productForm="包装物")
        rejected = self._post("/api/ginlong/TPL_Product_Master", invalid_form)
        rejected_body = json.loads(rejected.text)
        self.assertEqual(rejected.status_code, 200)
        self.assertEqual(set(rejected_body), protocol_fields)
        self.assertEqual(rejected_body["returnStatus"], "N")
        self.assertEqual(
            rejected_body["exceptionInfo"],
            "BUS06: productForm仅支持原材料/半成品/成品",
        )
        with db_connect(self.env.cr.dbname).cursor() as cr:
            verify_env = api.Environment(cr, SUPERUSER_ID, {})
            self.assertFalse(verify_env["product.product"].search([
                ("ginlong_owner_code", "=", self.http_owner.ginlong_owner_code),
                ("ginlong_product_code", "=", invalid_product_code),
            ]))

        unknown_unit = "GINLONG-NO-UOM-%s" % self.http_suffix
        unknown_unit_code = "HTTP-UNKNOWN-UOM-%s" % self.http_suffix
        self.assertFalse(self.env["uom.uom"].sudo().search([("name", "=", unknown_unit)]))
        unknown_unit_payload = dict(
            payload, productCode=unknown_unit_code,
            productName=marker + " unknown unit product", unit=unknown_unit,
        )
        unknown_unit_response = self._post("/api/ginlong/TPL_Product_Master", unknown_unit_payload)
        unknown_unit_body = json.loads(unknown_unit_response.text)
        self.assertEqual(unknown_unit_response.status_code, 200)
        self.assertEqual(set(unknown_unit_body), protocol_fields)
        self.assertEqual(unknown_unit_body["returnStatus"], "Y")
        self.assertEqual(unknown_unit_body["exceptionInfo"], "OK")
        self.env.invalidate_all()
        auto_unit = self.env["uom.uom"].sudo().search([
            ("name", "=", unknown_unit),
            ("category_id", "=", self.env.ref("uom.product_uom_categ_unit").id),
        ])
        auto_unit_product = self.env["product.product"].sudo().search([
            ("ginlong_owner_code", "=", self.http_owner.ginlong_owner_code),
            ("ginlong_product_code", "=", unknown_unit_code),
        ])
        self.assertEqual(len(auto_unit), 1)
        self.assertEqual(auto_unit.uom_type, "smaller")
        self.assertEqual(auto_unit.factor, 1.0)
        self.assertEqual(auto_unit.factor_inv, 1.0)
        self.assertEqual(auto_unit.rounding, self.env.ref("uom.product_uom_unit").rounding)
        self.assertEqual(len(auto_unit_product), 1)
        self.assertEqual(auto_unit_product.uom_id, auto_unit)
        unit_log = self.env["world.depot.api.log"].sudo().search([
            ("request_data", "ilike", unknown_unit_code),
        ], order="id desc", limit=1)
        self.assertEqual(unit_log.status, "success")
        self.assertTrue(unit_log.success)
        self.assertEqual(json.loads(unit_log.response_data), unknown_unit_body)

        invalid_auth = self.url_open(
            "/api/ginlong/TPL_Product_Master",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": "Bearer invalid-token"},
        )
        invalid_auth_body = json.loads(invalid_auth.text)
        self.assertEqual(invalid_auth.status_code, 401)
        self.assertEqual(set(invalid_auth_body), protocol_fields)
        self.assertEqual(invalid_auth_body["returnStatus"], "N")
        self.assertTrue(invalid_auth_body["exceptionInfo"].startswith("AUTH01: "))

        logs = self._committed_api_logs(marker)
        duplicate_logs = [log for log in logs if log["code"] == "IDM07"]
        self.assertEqual(len(duplicate_logs), 2)
        for log in duplicate_logs:
            self.assertEqual(log["msg"], "重复新增，冲突键(owner, productCode)")
            self.assertIn(payload["owner"], log["exception_details"])
            self.assertIn(payload["productCode"], log["exception_details"])
            self.assertNotIn("Traceback", log["exception_details"] or "")
            self.assertEqual(set(json.loads(log["response_data"])), protocol_fields)
        self.assertTrue(any(log["code"] == "AUTH01" for log in logs))
        required_logs = [log for log in logs if log["code"] == "REQ01"]
        self.assertEqual(len(required_logs), 3)
        required_messages = {log["msg"] for log in required_logs}
        self.assertIn("缺失字段: owner", required_messages)
        self.assertIn("缺失字段: owner, productForm", required_messages)
        mixed_logs = [log for log in required_logs if "Type errors:" in log["exception_details"]]
        self.assertEqual(len(mixed_logs), 1)
        self.assertIn(
            "owner is missing; productForm is missing",
            mixed_logs[0]["exception_details"],
        )
        self.assertIn("weight must be a decimal number", mixed_logs[0]["exception_details"])
        for required_log in required_logs:
            self.assertIn("Required fields:", required_log["exception_details"])
            self.assertEqual(set(json.loads(required_log["response_data"])), protocol_fields)
        type_logs = [log for log in logs if log["code"] == "TYP01"]
        self.assertEqual(len(type_logs), 1)
        self.assertEqual(type_logs[0]["msg"], "类型错误字段: weight, length")
        self.assertIn("weight must be a decimal number", type_logs[0]["exception_details"])
        self.assertIn("length must be a decimal number", type_logs[0]["exception_details"])
        conflict_logs = [log for log in logs if log["code"] == "BUS02"]
        self.assertEqual(len(conflict_logs), 1)
        self.assertEqual(conflict_logs[0]["msg"], "同productCode的productForm必须一致")
        self.assertIn("ginlong_product_form, tracking", conflict_logs[0]["exception_details"])
        self.assertEqual(set(json.loads(conflict_logs[0]["response_data"])), protocol_fields)
        missing_edit_logs = [log for log in logs if log["code"] == "BUS03"]
        self.assertEqual(len(missing_edit_logs), 1)
        self.assertEqual(missing_edit_logs[0]["msg"], "API07 Edit目标产品不存在")
        self.assertIn(missing_edit_code, missing_edit_logs[0]["exception_details"])
        product_form_logs = [log for log in logs if log["code"] == "BUS06"]
        self.assertEqual(len(product_form_logs), 1)
        self.assertEqual(product_form_logs[0]["msg"], "productForm仅支持原材料/半成品/成品")
        self.assertIn("包装物", product_form_logs[0]["exception_details"])
        self.assertEqual(set(json.loads(product_form_logs[0]["response_data"])), protocol_fields)

    def test_http_api07_first_add_commits_product_and_idempotency_before_duplicate_conflict(self):
        """验证首次 HTTP Add 落库并记录幂等结果，随后相同或变更 Add 均返回 IDM07。"""
        marker = self.http_test_marker
        owner_code = self.http_owner.ginlong_owner_code
        product_code = "HTTP-ADD-%s" % self.http_suffix
        payload = {
            "action": "Add",
            "owner": owner_code,
            "productCode": product_code,
            "productName": marker + " fresh API07 product",
            "specificationModel": "HTTP-ADD-MODEL",
            "unit": self.env.ref("uom.product_uom_unit").name,
            "productForm": "原材料",
            "weight": 0,
        }
        protocol_fields = {"returnStatus", "exceptionInfo", "operationTime"}

        first_response = self._post("/api/ginlong/TPL_Product_Master", payload)
        first_body = json.loads(first_response.text)
        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(set(first_body), protocol_fields)
        self.assertEqual(first_body["returnStatus"], "Y")
        self.assertEqual(first_body["exceptionInfo"], "OK")

        self.env.invalidate_all()
        product = self.env["product.product"].sudo().with_context(active_test=False).search([
            ("ginlong_owner_code", "=", owner_code),
            ("ginlong_product_code", "=", product_code),
        ])
        self.assertEqual(len(product), 1)
        original_name = product.name
        business_key = json.dumps([owner_code, product_code], ensure_ascii=False, separators=(",", ":"))
        idempotency = self.env["ginlong.api.idempotency"].sudo().search([
            ("api_code", "=", "API07"),
            ("direction", "=", "inbound"),
            ("business_key", "=", business_key),
            ("action", "=", "add"),
        ])
        self.assertEqual(len(idempotency), 1)
        self.assertEqual(idempotency.state, "succeeded")
        self.assertEqual(idempotency.attempt_count, 1)
        self.assertTrue(json.loads(idempotency.response_json)["success"])
        original_fingerprint = idempotency.request_fingerprint
        original_response_json = idempotency.response_json

        same_duplicate = self._post("/api/ginlong/TPL_Product_Master", payload)
        changed_payload = dict(payload, productName=marker + " changed duplicate", weight=99)
        changed_duplicate = self._post("/api/ginlong/TPL_Product_Master", changed_payload)
        for response in (same_duplicate, changed_duplicate):
            body = json.loads(response.text)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(set(body), protocol_fields)
            self.assertEqual(body["returnStatus"], "N")
            self.assertEqual(
                body["exceptionInfo"],
                "IDM07: 重复新增，冲突键(owner, productCode)",
            )

        self.env.invalidate_all()
        product = self.env["product.product"].sudo().with_context(active_test=False).search([
            ("ginlong_owner_code", "=", owner_code),
            ("ginlong_product_code", "=", product_code),
        ])
        self.assertEqual(len(product), 1)
        self.assertEqual(product.name, original_name)
        idempotency = self.env["ginlong.api.idempotency"].sudo().search([
            ("api_code", "=", "API07"),
            ("direction", "=", "inbound"),
            ("business_key", "=", business_key),
            ("action", "=", "add"),
        ])
        self.assertEqual(len(idempotency), 1)
        self.assertEqual(idempotency.state, "succeeded")
        self.assertEqual(idempotency.attempt_count, 1)
        self.assertEqual(idempotency.request_fingerprint, original_fingerprint)
        self.assertEqual(idempotency.response_json, original_response_json)

        logs = self._committed_api_logs(marker)
        self.assertEqual(len(logs), 3)
        self.assertTrue(any(log["success"] for log in logs))
        duplicate_logs = [log for log in logs if log["code"] == "IDM07"]
        self.assertEqual(len(duplicate_logs), 2)
        for log in duplicate_logs:
            self.assertEqual(log["msg"], "重复新增，冲突键(owner, productCode)")
            self.assertEqual(set(json.loads(log["response_data"])), protocol_fields)

    def test_http_api07_archived_product_add_restores_same_variant_lifecycle(self):
        """通过真实 Ginlong HTTP 路由验证归档产品复用原变体并开启新幂等周期。"""
        marker = self.http_test_marker
        owner_code = self.http_owner.ginlong_owner_code
        product_code = "HTTP-ARCHIVE-%s" % self.http_suffix
        payload = {
            "action": "Add",
            "owner": owner_code,
            "productCode": product_code,
            "productName": marker + " archived API07 product",
            "specificationModel": "HTTP-ARCHIVE-MODEL",
            "unit": self.env.ref("uom.product_uom_unit").name,
            "productForm": "原材料",
            "weight": 0,
        }
        protocol_fields = {"returnStatus", "exceptionInfo", "operationTime"}

        first = self._post("/api/ginlong/TPL_Product_Master", payload)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(json.loads(first.text)["returnStatus"], "Y")
        self.env.invalidate_all()
        product = self.env["product.product"].sudo().with_context(active_test=False).search([
            ("ginlong_owner_code", "=", owner_code),
            ("ginlong_product_code", "=", product_code),
        ])
        self.assertEqual(len(product), 1)
        original_id = product.id

        active_duplicate = self._post("/api/ginlong/TPL_Product_Master", payload)
        active_duplicate_body = json.loads(active_duplicate.text)
        self.assertEqual(active_duplicate.status_code, 200)
        self.assertEqual(active_duplicate_body["returnStatus"], "N")
        self.assertTrue(active_duplicate_body["exceptionInfo"].startswith("IDM07:"))

        def set_archived(archived):
            """在 HttpCase 当前 ORM 事务切换归档状态，供后续真实 HTTP 请求读取。"""
            self.env["product.product"].sudo().browse(original_id).write({
                "active": not archived,
            })

        set_archived(True)
        same_readd = self._post("/api/ginlong/TPL_Product_Master", payload)
        same_readd_body = json.loads(same_readd.text)
        self.assertEqual(same_readd.status_code, 200)
        self.assertEqual(set(same_readd_body), protocol_fields)
        self.assertEqual(same_readd_body["returnStatus"], "Y")
        self.env.invalidate_all()
        restored = self.env["product.product"].sudo().with_context(active_test=False).browse(original_id)
        self.assertTrue(restored.active)

        duplicate = self._post("/api/ginlong/TPL_Product_Master", payload)
        duplicate_body = json.loads(duplicate.text)
        self.assertEqual(duplicate.status_code, 200)
        self.assertEqual(duplicate_body["returnStatus"], "N")
        self.assertTrue(duplicate_body["exceptionInfo"].startswith("IDM07:"))

        # 改变指纹但不改写模板事实：省略可选 weight，验证历史成功行不会拦截新周期。
        set_archived(True)
        changed_payload = dict(payload)
        changed_payload.pop("weight")
        changed_readd = self._post("/api/ginlong/TPL_Product_Master", changed_payload)
        changed_readd_body = json.loads(changed_readd.text)
        self.assertEqual(changed_readd.status_code, 200)
        self.assertEqual(set(changed_readd_body), protocol_fields)
        self.assertEqual(changed_readd_body["returnStatus"], "Y")

        changed_duplicate = self._post("/api/ginlong/TPL_Product_Master", changed_payload)
        self.assertEqual(json.loads(changed_duplicate.text)["returnStatus"], "N")
        self.env.invalidate_all()
        products = self.env["product.product"].sudo().with_context(active_test=False).search([
            ("ginlong_owner_code", "=", owner_code),
            ("ginlong_product_code", "=", product_code),
        ])
        self.assertEqual(len(products), 1)
        self.assertEqual(products.id, original_id)
        self.assertTrue(products.active)
        business_key = json.dumps([owner_code, product_code], ensure_ascii=False, separators=(",", ":"))
        lifecycle_rows = self.env["ginlong.api.idempotency"].sudo().search([
            ("api_code", "=", "API07"),
            ("direction", "=", "inbound"),
            ("business_key", "=", business_key),
            ("action", "=", "add"),
        ], order="id")
        self.assertEqual(len(lifecycle_rows), 3)
        self.assertTrue(all(row.state == "succeeded" and row.attempt_count == 1 for row in lifecycle_rows))
        self.assertEqual(len(set(lifecycle_rows.mapped("event_key"))), 3)
        self.assertEqual(len(set(lifecycle_rows.mapped("request_fingerprint"))), 2)

        logs = self._committed_api_logs(marker)
        self.assertEqual(len(logs), 6)
        self.assertEqual(len([row for row in logs if row["code"] == "IDM07"]), 3)
        self.assertTrue(all(set(json.loads(row["response_data"])) == protocol_fields for row in logs))

    def test_http_api01_active_order_conflict_precedes_old_idempotency_row(self):
        """真实 HTTP 验证有效订单冲突优先于历史幂等记录并保持数据不变。"""
        marker = self.http_test_marker
        reference = marker + "-IDEMPOTENCY"
        payload = {
            "owner": self.http_owner.ginlong_owner_code,
            "action": "Add",
            "inboundOrderNo": reference,
            "warehouse": self.http_warehouse.code,
            "businessType": "STANDARD",
            "remark": marker,
            "details": [{
                "productCode": self.http_product.ginlong_product_code,
                "productName": self.http_product.name,
                "specificationModel": "HTTP-MODEL",
                "quantity": 1,
            }],
        }
        first = self._post("/api/ginlong/TPL_Pending_Receipt_Note", payload)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(json.loads(first.text)["returnStatus"], "Y")
        self.env.invalidate_all()
        record = self.env["ginlong.api.idempotency"].sudo().search([
            ("api_code", "=", "API01"), ("business_key", "=", reference),
        ])
        self.assertEqual(len(record), 1)
        record.write({"state": "processing", "response_json": "{}"})

        repeated = self._post("/api/ginlong/TPL_Pending_Receipt_Note", payload)
        repeated_body = json.loads(repeated.text)
        self.assertEqual(repeated.status_code, 200)
        self.assertEqual(set(repeated_body), {"returnStatus", "exceptionInfo", "operationTime"})
        self.assertEqual(repeated_body["returnStatus"], "N")
        # 业务 Order 已存在且有效时，适配器先按业务唯一键返回重复 Add 冲突。
        self.assertEqual(repeated_body["exceptionInfo"], "IDM02: 重复新增，冲突键: inboundOrderNo")
        self.env.invalidate_all()
        self.assertEqual(self.env["world.depot.inbound.order"].search_count([
            ("reference", "=", reference),
        ]), 1)
        record = self.env["ginlong.api.idempotency"].sudo().search([
            ("api_code", "=", "API01"), ("business_key", "=", reference),
        ])
        self.assertEqual(record.state, "processing")

        logs = self._committed_api_logs(marker)
        idempotency_logs = [log for log in logs if log["code"] == "IDM02"]
        self.assertEqual(len(idempotency_logs), 1)
        self.assertEqual(idempotency_logs[0]["msg"], "重复新增，冲突键: inboundOrderNo")
        self.assertIn(reference, idempotency_logs[0]["exception_details"])

    def test_http_api01_rate_rejection_and_storage_failure_are_distinct(self):
        """真实 HTTP 验证限流拒绝与共享计数存储故障使用不同错误码。"""
        marker = self.http_test_marker
        payload = {
            "owner": self.http_owner.ginlong_owner_code,
            "action": "Add",
            "inboundOrderNo": marker + "-RATE-DENIED",
            "warehouse": self.http_warehouse.code,
            "businessType": "STANDARD",
            "remark": marker,
            "details": [{
                "productCode": self.http_product.ginlong_product_code,
                "productName": self.http_product.name,
                "specificationModel": "HTTP-MODEL",
                "quantity": 1,
            }],
        }
        with patch.object(rate_limiter, "_reserve", return_value=False):
            denied = self._post("/api/ginlong/TPL_Pending_Receipt_Note", payload)
        denied_body = json.loads(denied.text)
        self.assertEqual(denied.status_code, 429)
        self.assertTrue(denied.headers.get("Retry-After"))
        self.assertEqual(set(denied_body), {"returnStatus", "exceptionInfo", "operationTime"})
        self.assertEqual(denied_body["exceptionInfo"], "RATE01: API请求频率超限")

        storage_payload = dict(payload, inboundOrderNo=marker + "-RATE-STORAGE")
        with patch.object(rate_limiter, "_reserve", side_effect=RuntimeError("private-storage-detail")):
            unavailable = self._post("/api/ginlong/TPL_Pending_Receipt_Note", storage_payload)
        unavailable_body = json.loads(unavailable.text)
        self.assertEqual(unavailable.status_code, 503)
        self.assertEqual(set(unavailable_body), {"returnStatus", "exceptionInfo", "operationTime"})
        self.assertEqual(unavailable_body["exceptionInfo"], "RATE02: 限流服务暂不可用")
        self.assertNotIn("private-storage-detail", unavailable.text)

        self.env.invalidate_all()
        for order_no in (payload["inboundOrderNo"], storage_payload["inboundOrderNo"]):
            self.assertEqual(self.env["world.depot.inbound.order"].search_count([
                ("reference", "=", order_no),
            ]), 0)
        logs = self._committed_api_logs(marker)
        self.assertTrue(any(log["code"] == "RATE01" and log["msg"] == "API请求频率超限" for log in logs))
        storage_logs = [log for log in logs if log["code"] == "RATE02"]
        self.assertEqual(len(storage_logs), 1)
        self.assertEqual(storage_logs[0]["msg"], "限流服务暂不可用")
        self.assertIn("private-storage-detail", storage_logs[0]["exception_details"])

    def test_http_api07_unexpected_business_error_is_sanitized_and_logged(self):
        """真实 HTTP 验证未预期业务异常返回 SYS01 且日志保留诊断。"""
        marker = self.http_test_marker
        product_code = marker + "-SYSTEM-ERROR"
        payload = {
            "action": "Add",
            "owner": self.http_owner.ginlong_owner_code,
            "productCode": product_code,
            "productName": marker + " system error product",
            "specificationModel": "HTTP-SYSTEM-MODEL",
            "unit": self.env.ref("uom.product_uom_unit").name,
            "productForm": "原材料",
        }
        with patch.object(services, "api07", side_effect=RuntimeError("private-system-detail")):
            response = self._post("/api/ginlong/TPL_Product_Master", payload)
        body = json.loads(response.text)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(body), {"returnStatus", "exceptionInfo", "operationTime"})
        self.assertEqual(body["exceptionInfo"], "SYS01: 系统处理失败")
        self.assertNotIn("private-system-detail", response.text)
        self.assertNotIn("Traceback", response.text)
        self.env.invalidate_all()
        self.assertFalse(self.env["product.product"].search([
            ("ginlong_owner_code", "=", self.http_owner.ginlong_owner_code),
            ("ginlong_product_code", "=", product_code),
        ]))
        logs = self._committed_api_logs(marker)
        system_logs = [log for log in logs if log["code"] == "SYS01"]
        self.assertEqual(len(system_logs), 1)
        self.assertEqual(system_logs[0]["msg"], "系统处理失败")
        self.assertIn("private-system-detail", system_logs[0]["exception_details"])
        self.assertNotIn("Traceback", system_logs[0]["exception_details"] or "")

    def test_ginlong_api_logger_exception_fallback_uses_protocol_response(self):
        """验证日志装饰器兜底不向 Ginlong 泄露内部异常文本或通用字段。"""
        fake_env = SimpleNamespace(
            uid=SUPERUSER_ID,
            context={},
            cr=SimpleNamespace(dbname=self.env.cr.dbname, rollback=lambda: None),
        )
        fake_request = SimpleNamespace(
            httprequest=SimpleNamespace(
                data=b"{}", remote_addr="127.0.0.1", path="/api/ginlong/test",
            ),
            env=fake_env,
            registry=SimpleNamespace(cursor=_CursorContext),
            api_user=False,
        )
        log_model = _LogModel()
        log_environment = _LogEnvironment(log_model)
        original_environment = api_logs.api.Environment

        def environment_factory(cr, uid, context, *args, **kwargs):
            """仅将日志游标映射到记录器替身。"""
            if isinstance(cr, _CursorContext):
                return log_environment
            return original_environment(cr, uid, context, *args, **kwargs)

        @api_logs.api_logger
        def unexpected_failure():
            """模拟统一路由包装器之外的未预期错误。"""
            raise RuntimeError("private-fallback-detail")

        with patch.object(api_logs, "request", fake_request), \
                patch.object(api_logs.api, "Environment", side_effect=environment_factory):
            response = unexpected_failure()
        body = json.loads(response.get_data(as_text=True))
        self.assertEqual(response.status_code, 500)
        self.assertEqual(set(body), {"returnStatus", "exceptionInfo", "operationTime"})
        self.assertEqual(body["exceptionInfo"], "SYS01: 系统处理失败")
        self.assertNotIn("private-fallback-detail", response.get_data(as_text=True))
        self.assertEqual(len(log_model.values), 1)
        self.assertEqual(log_model.values[0]["code"], "SYS01")
        self.assertEqual(log_model.values[0]["msg"], "系统处理失败")
        self.assertIn("private-fallback-detail", log_model.values[0]["exception_details"])

    def test_http_api09_queries_by_codes_and_never_persists_idempotency(self):
        """真实 HTTP 验证 API09 编码查询、未授权 Token 和无持久幂等记录。"""
        owner_code = self.http_test_marker + "-OWNER"
        owner = self.env["res.partner"].create({
            "name": "Ginlong API09 HTTP owner", "is_company": True,
            "ginlong_owner_code": owner_code,
        })
        reference_count = self.env["ginlong.api.idempotency"].search_count([("api_code", "=", "API09")])
        payload = {"owner": owner_code, "warehouse": self.http_warehouse.code}
        first = self._post("/api/ginlong/TPL_Stock_Query", payload)
        second = self._post("/api/ginlong/TPL_Stock_Query", payload)
        first_body, second_body = json.loads(first.text), json.loads(second.text)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first_body["owner"], owner_code)
        self.assertEqual(first_body["warehouse"], self.http_warehouse.code)
        self.assertEqual(first_body["inventoryList"], [])
        self.assertEqual(second_body["inventoryList"], [])
        self.assertEqual(
            self.env["ginlong.api.idempotency"].search_count([("api_code", "=", "API09")]),
            reference_count,
        )
        missing_owner = self._post("/api/ginlong/TPL_Stock_Query", {
            "owner": owner_code + "-UNKNOWN", "warehouse": self.http_warehouse.code,
        })
        self.assertEqual(missing_owner.status_code, 200)
        self.assertEqual(json.loads(missing_owner.text)["inventoryList"], [])
        missing_warehouse = self._post("/api/ginlong/TPL_Stock_Query", {
            "owner": owner_code, "warehouse": owner_code + "-UNKNOWN-WH",
        })
        self.assertEqual(missing_warehouse.status_code, 400)
        self.assertFalse(json.loads(missing_warehouse.text).get("inventoryList"))

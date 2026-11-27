"""使用 Odoo ORM 只读核对 API01 HVR 订单、货主、产品、日志和幂等记录。"""

import json


RUN = "HVR01-20261121"


def verify_api01_hvr():
    """输出本轮 API01 人工验收证据摘要，不显示 Token 或密钥。"""
    print("=== HVR01 货主（ORM） ===")
    owners = env["res.partner"].sudo().with_context(active_test=False).search([
        ("ginlong_owner_code", "like", RUN + "%"),
    ], order="ginlong_owner_code,id")
    auto_owner = owners.filtered(lambda owner: owner.ginlong_owner_code == RUN + "-OWNER-AUTO")
    for owner in owners:
        print(json.dumps({"id": owner.id, "name": owner.name,
                          "ginlong_owner_code": owner.ginlong_owner_code,
                          "auto_created_case": owner == auto_owner}, ensure_ascii=False))

    print("=== HVR01 产品变体（ORM） ===")
    products = env["product.product"].sudo().with_context(active_test=False).search([
        ("ginlong_product_code", "like", RUN + "%"),
    ], order="ginlong_product_code,ginlong_owner_code,id")
    for product in products:
        print(json.dumps({
            "id": product.id,
            "template_id": product.product_tmpl_id.id,
            "owner_code": product.ginlong_owner_code,
            "product_code": product.ginlong_product_code,
            "default_code": product.default_code,
            "template_name": product.product_tmpl_id.name,
        }, ensure_ascii=False, sort_keys=True))

    print("=== HVR01 入库订单与实际执行隔离（ORM） ===")
    orders = env["world.depot.inbound.order"].sudo().search([
        ("reference", "like", RUN + "%"),
    ], order="reference,id")
    for order in orders:
        detail_rows = []
        for pallet in order.inbound_order_product_ids:
            for line in pallet.inbound_order_product_pallet_ids:
                detail_rows.append({
                    "product_id": line.product_id.id,
                    "owner_code": line.product_id.ginlong_owner_code,
                    "product_code": line.ginlong_product_code,
                    "quantity": line.quantity,
                })
        print(json.dumps({
            "id": order.id,
            "reference": order.reference,
            "state": order.state,
            "project_id": order.project.id,
            "project_owner_id": order.project.owner.id,
            "ginlong_owner_id": order.ginlong_owner_id.id,
            "ginlong_owner_code": order.ginlong_owner_code,
            "warehouse_code": order.ginlong_warehouse_code,
            "details": detail_rows,
            "sn_count": sum(len(line.product_serial_number_ids)
                             for line in order.inbound_order_product_ids),
            "stock_picking_id": order.stock_picking_id.id or None,
            "linked_picking_count": env["stock.picking"].sudo().search_count([
                ("inbound_order_id", "=", order.id),
            ]),
        }, ensure_ascii=False, sort_keys=True))

    print("=== HVR01 幂等记录（ORM；不输出响应报文） ===")
    for row in env["ginlong.api.idempotency"].sudo().search([
        ("api_code", "=", "API01"), ("business_key", "like", RUN + "%"),
    ], order="business_key,action,id"):
        print(json.dumps({"id": row.id, "action": row.action,
                          "business_key": row.business_key, "state": row.state,
                          "attempt_count": row.attempt_count,
                          "fingerprint": row.request_fingerprint}, ensure_ascii=False))

    print("=== HVR01 API 日志（ORM） ===")
    for log in env["world.depot.api.log"].sudo().search([
        ("request_path", "=", "/api/ginlong/TPL_Pending_Receipt_Note"),
        ("request_data", "ilike", RUN),
    ], order="request_time,id"):
        print(json.dumps({"id": log.id, "request_time": str(log.request_time or ""),
                          "status": log.status, "success": log.success,
                          "code": log.code, "message": log.msg,
                          "business_key": log.ginlong_business_key,
                          "response": log.response_data,
                          "source_record": str(log.source_record or "")}, ensure_ascii=False))


verify_api01_hvr()

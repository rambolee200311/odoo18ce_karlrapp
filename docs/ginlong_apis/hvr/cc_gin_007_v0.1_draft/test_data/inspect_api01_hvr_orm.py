"""通过 Odoo ORM 只读核对 CC-GIN-007 的产品前置条件和 API01 预报结果。"""

import json
import os


OWNER_CODE = os.environ.get("GINLONG_HVR_OWNER", "HVR01-20261121-OWNER-A")
ORDER_NO = os.environ.get("GINLONG_HVR_ORDER_NO")
PRODUCT_CODES = (
    "HVR01-20261121-PROD-COMMON",
    "HVR01-20261122-PROD-SERIAL",
    "HVR01-20261122-PROD-SEMIFINISHED",
)


def inspect(env):
    """读取货主、产品 tracking，以及可选订单预报行并输出 JSON。

    参数：
        env: Odoo shell 自动提供的 Environment。

    返回：
        None；结果写到标准输出，不创建、修改或删除任何 ORM 记录。
    """
    partner_model = env["res.partner"].sudo().with_context(active_test=False)
    product_model = env["product.product"].sudo().with_context(active_test=False)
    owners = partner_model.search([("ginlong_owner_code", "=", OWNER_CODE)])
    products = product_model.search([
        ("ginlong_owner_code", "=", OWNER_CODE),
        ("ginlong_product_code", "in", PRODUCT_CODES),
    ])
    output = {
        "owner_code": OWNER_CODE,
        "owner_matches": len(owners),
        "products": [
            {
                "productCode": product.ginlong_product_code,
                "productName": product.product_tmpl_id.name,
                "productForm": product.product_tmpl_id.ginlong_product_form,
                "tracking": product.tracking,
                "variant_id": product.id,
                "template_id": product.product_tmpl_id.id,
            }
            for product in products
        ],
        "order": None,
    }

    if ORDER_NO:
        orders = env["world.depot.inbound.order"].sudo().search([
            ("reference", "=", ORDER_NO),
        ])
        if len(orders) != 1:
            output["order"] = {"reference": ORDER_NO, "matches": len(orders)}
        else:
            order = orders
            detail_rows = []
            for order_line in order.inbound_order_product_ids:
                for product_row in order_line.inbound_order_product_pallet_ids:
                    detail_rows.append({
                        "productCode": product_row.ginlong_product_code
                        or product_row.product_id.ginlong_product_code,
                        "productName": product_row.ginlong_product_name
                        or product_row.product_id.display_name,
                        "quantity": product_row.quantity,
                        "wms_order_pallet_no": order_line.pallet_no,
                    })
            forecast_rows = [
                {
                    "productCode": row.ginlong_product_code,
                    "productSN": row.serial_number,
                    "quantity": row.ginlong_quantity,
                    "palletCode": row.ginlong_pallet_code,
                    "productName": row.ginlong_product_name,
                    "specificationModel": row.ginlong_specification_model,
                }
                for row in order.inbound_order_product_ids.mapped("product_serial_number_ids")
            ]
            output["order"] = {
                "id": order.id,
                "reference": order.reference,
                "owner_code": order.ginlong_owner_code,
                "business_type": order.ginlong_business_type,
                "forecast_sn_json_present": bool(order.ginlong_sn_list_json),
                "details": detail_rows,
                "forecast_sn_rows": forecast_rows,
                "linked_picking_id": order.stock_picking_id.id or None,
            }

    print(json.dumps(output, ensure_ascii=False, indent=2, default=str))


# Odoo shell 暴露 env；此文件只运行只读 ORM 查询。
inspect(env)

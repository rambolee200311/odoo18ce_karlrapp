"""使用 Odoo ORM 输出 API07 HVR 的产品、日志及幂等证据摘要。"""

import json


RUN = "HVR07-20261119"


def verify_api07_hvr():
    """只读列出本轮 HVR 标记的 API07 产品与处理证据。"""
    owners = env["res.partner"].sudo().search([
        ("ginlong_owner_code", "in", [RUN + "-OWNER-A", RUN + "-OWNER-B"]),
    ], order="ginlong_owner_code,id")
    print("=== 测试货主（ORM） ===")
    for owner in owners:
        print(json.dumps({"id": owner.id, "name": owner.name,
                          "ginlong_owner_code": owner.ginlong_owner_code}, ensure_ascii=False))

    projects = env["project.project"].sudo().search([("name", "=", RUN + " API07 HVR Project")])
    print("=== 测试项目（ORM） ===")
    for project in projects:
        print(json.dumps({"id": project.id, "name": project.name,
                          "owner_id": project.owner.id, "warehouse_id": project.warehouse.id},
                         ensure_ascii=False))

    test_login_users = env["res.users"].sudo().search([("login", "=", "hvr_api07_manual")])
    api_users = env["world.depot.api.user"].sudo().search([
        ("user_id", "in", test_login_users.ids + [env.ref("base.public_user").id]),
        "|", ("project", "in", projects.ids), ("project", "=", False),
    ], order="id")
    print("=== 测试 API User 与 Token（ORM；不显示 Token 值） ===")
    tokens = env["world.depot.api.token"].sudo().search([
        ("user_id", "in", api_users.mapped("user_id").ids),
    ], order="id")
    for api_user in api_users:
        user_tokens = tokens.filtered(lambda token: token.user_id == api_user.user_id)
        print(json.dumps({
            "api_user_id": api_user.id,
            "user_id": api_user.user_id.id,
            "login": api_user.user_id.login,
            "project_id": api_user.project.id or None,
            "token_count": len(user_tokens),
            "token_ids": user_tokens.ids,
            "token_expires": [str(token.expires or "") for token in user_tokens],
            "token_values_printed": False,
        }, ensure_ascii=False, sort_keys=True))

    print("=== 测试单位（ORM） ===")
    test_units = env["uom.uom"].sudo().search(
        [("name", "in", ["台", "个", RUN + "-UNIT-ALT"])], order="name,id"
    )
    for unit in test_units:
        print(json.dumps({"id": unit.id, "name": unit.name, "category_id": unit.category_id.id,
                          "category": unit.category_id.name}, ensure_ascii=False))
    unit_category = test_units.filtered(lambda unit: unit.name == "台")[:1].category_id
    if unit_category:
        compatible_units = env["uom.uom"].sudo().search(
            [("category_id", "=", unit_category.id)], order="id"
        )
        print("台所在类别的全部单位：%s" % json.dumps(
            [{"id": unit.id, "name": unit.name} for unit in compatible_units],
            ensure_ascii=False,
        ))

    products = env["product.product"].sudo().with_context(active_test=False).search([
        ("ginlong_product_code", "like", RUN + "-%"),
    ], order="ginlong_product_code,ginlong_owner_code,id")
    print("=== 产品模板与货主变体（ORM） ===")
    for product in products:
        template = product.product_tmpl_id
        variant_attributes = [{
            "attribute": value.product_attribute_value_id.attribute_id.name,
            "value": value.product_attribute_value_id.name,
        } for value in product.product_template_attribute_value_ids]
        print(json.dumps({
            "variant_id": product.id,
            "template_id": template.id,
            "template_name": template.name,
            "owner_code": product.ginlong_owner_code,
            "native_variant_attributes": variant_attributes,
            "product_code": product.ginlong_product_code,
            "default_code": product.default_code,
            "specification_model": template.ginlong_specification_model,
            "unit": template.ginlong_unit,
            "product_form": template.ginlong_product_form,
            "tracking": template.tracking,
            "weight": template.ginlong_weight,
        }, ensure_ascii=False, sort_keys=True))

    print("=== API07 幂等记录（ORM） ===")
    idempotency_rows = env["ginlong.api.idempotency"].sudo().search([
        ("api_code", "=", "API07"), ("business_key", "ilike", RUN),
    ], order="id")
    for row in idempotency_rows:
        print(json.dumps({
            "id": row.id,
            "action": row.action,
            "business_key": row.business_key,
            "state": row.state,
            "attempt_count": row.attempt_count,
            "request_fingerprint": row.request_fingerprint,
            "response": row.response_json,
        }, ensure_ascii=False, sort_keys=True))

    print("=== API07 日志（ORM） ===")
    logs = env["world.depot.api.log"].sudo().search([
        ("request_path", "=", "/api/ginlong/TPL_Product_Master"),
        ("request_data", "ilike", RUN),
    ], order="request_time,id")
    for log in logs:
        print(json.dumps({
            "id": log.id,
            "request_time": str(log.request_time or ""),
            "request_path": log.request_path,
            "status": log.status,
            "success": log.success,
            "code": log.code,
            "message": log.msg,
            "request": log.request_data,
            "response": log.response_data,
            "exception": log.exception_details,
            "source_record": str(log.source_record or ""),
        }, ensure_ascii=False, sort_keys=True))


verify_api07_hvr()

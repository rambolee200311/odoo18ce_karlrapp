"""通过 Odoo ORM 重置 API01 HVR 数据；检测到非测试引用时立即停止。"""

from pathlib import Path

from odoo.exceptions import UserError


RUN = "HVR01-20261121"
PROJECT_NAME = RUN + " API01 HVR Project"
OWNER_CODES = [RUN + "-OWNER-A", RUN + "-OWNER-B", RUN + "-OWNER-AUTO"]
LOGINS = ["hvr_api01_manual", "hvr_api01_no_project"]
DATA_DIR = Path.cwd() / "docs/ginlong_apis/hvr/api01/test_data"
ENV_FILE = DATA_DIR / ".api01_hvr.env"


def _read_env_file():
    """读取本地准备文件以精确定位 Token，不打印任何敏感字段。"""
    if not ENV_FILE.exists():
        raise UserError("未找到 .api01_hvr.env；为保护非 HVR 凭据，停止重置")
    values = {}
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
    if not values.get("API01_TOKEN") or not values.get("API01_NO_PROJECT_TOKEN"):
        raise UserError("HVR 凭据文件缺少 Token 标识；停止重置")
    return values


def reset_api01_hvr():
    """仅删除带 HVR01 前缀且无库存/非测试引用的记录。"""
    local = _read_env_file()
    project = env["project.project"].sudo().search([("name", "=", PROJECT_NAME)], limit=2)
    if len(project) > 1:
        raise UserError("HVR01 测试项目重复，停止重置")
    test_project = project[:1]
    users = env["res.users"].sudo().search([("login", "in", LOGINS)], limit=3)
    if len(users) > len(LOGINS):
        raise UserError("HVR01 登录用户重复，停止重置")
    expected_names = {
        "hvr_api01_manual": RUN + " API01 HVR 人工验收用户",
        "hvr_api01_no_project": RUN + " API01 无项目权限测试用户",
    }
    if any(user.name != expected_names.get(user.login) for user in users):
        raise UserError("HVR01 登录名被其他用户占用，停止重置")

    partner_model = env["res.partner"].sudo().with_context(active_test=False)
    owners = partner_model.search([("ginlong_owner_code", "in", OWNER_CODES)])
    other_projects = env["project.project"].sudo().search([
        ("owner", "in", owners.ids), ("id", "not in", test_project.ids or [0]),
    ])
    if other_projects:
        raise UserError("测试货主被其他项目引用，停止重置")

    order_model = env["world.depot.inbound.order"].sudo()
    test_orders = order_model.search([("reference", "like", RUN + "%")])
    if test_project:
        project_orders = order_model.search([("project", "=", test_project.id)])
        if project_orders - test_orders:
            raise UserError("HVR01 项目中存在非 HVR 入库单，停止重置")
    if test_orders.filtered(lambda order: order.stock_picking_id):
        raise UserError("HVR01 入库单已关联 stock.picking；为保护库存历史，停止重置")
    linked_pickings = env["stock.picking"].sudo().search([
        ("inbound_order_id", "in", test_orders.ids),
    ])
    if linked_pickings:
        raise UserError("HVR01 入库单存在关联 Picking，停止重置")

    products = env["product.product"].sudo().with_context(active_test=False).search([
        ("ginlong_product_code", "like", RUN + "%"),
    ])
    templates = products.mapped("product_tmpl_id")
    for template in templates:
        other_variants = template.with_context(active_test=False).product_variant_ids.filtered(
            lambda product: not product.ginlong_product_code
            or not product.ginlong_product_code.startswith(RUN + "-")
        )
        if other_variants:
            raise UserError("HVR01 产品模板包含非测试变体，停止重置")
    if products and env["stock.move"].sudo().search_count([("product_id", "in", products.ids)]):
        raise UserError("HVR01 产品已有库存移动，停止重置")
    if products and env["stock.quant"].sudo().search_count([("product_id", "in", products.ids)]):
        raise UserError("HVR01 产品已有库存数量记录，停止重置")

    if owners:
        owner_domain = ["|", ("ginlong_owner_id", "in", owners.ids),
                        ("ginlong_owner_code", "in", OWNER_CODES)]
        if order_model.search_count(owner_domain + [("id", "not in", test_orders.ids or [0])]):
            raise UserError("测试货主仍关联非 HVR 入库单，停止重置")
        if env["world.depot.outbound.order"].sudo().search_count(owner_domain):
            raise UserError("测试货主仍关联出库单，停止重置")
        if env["stock.quant"].sudo().search_count([("owner_id", "in", owners.ids)]):
            raise UserError("测试货主已有库存记录，停止重置")
        if "owner_id" in env["stock.move.line"]._fields and env["stock.move.line"].sudo().search_count([
            ("owner_id", "in", owners.ids),
        ]):
            raise UserError("测试货主已被库存作业行引用，停止重置")

    if test_project:
        test_api_users = env["world.depot.api.user"].sudo().search([("project", "=", test_project.id)])
    else:
        test_api_users = env["world.depot.api.user"].sudo().browse()
    if users:
        user_api_users = env["world.depot.api.user"].sudo().search([("user_id", "in", users.ids)])
        if user_api_users - test_api_users and any(
            record.project and record.project != test_project for record in user_api_users
        ):
            raise UserError("HVR01 登录用户关联了其他项目 API User，停止重置")
        test_api_users |= user_api_users

    tokens = env["world.depot.api.token"].sudo().search([("token", "in", [
        local["API01_TOKEN"], local["API01_NO_PROJECT_TOKEN"],
    ])])
    logs = env["world.depot.api.log"].sudo().search([
        ("request_path", "=", "/api/ginlong/TPL_Pending_Receipt_Note"),
        ("request_data", "ilike", RUN),
    ])
    idempotency = env["ginlong.api.idempotency"].sudo().search([
        ("api_code", "=", "API01"), ("business_key", "ilike", RUN),
    ])
    owner_attribute = env.ref("ginlong_apis.product_attribute_ginlong_owner")
    owner_values = env["product.attribute.value"].sudo().search([
        ("attribute_id", "=", owner_attribute.id), ("name", "in", OWNER_CODES),
    ])

    # 先删除无 Picking 的测试订单，再移除其来源日志和幂等记录，最后删除专用主数据。
    test_orders.unlink()
    tokens.unlink()
    logs.unlink()
    idempotency.unlink()
    test_api_users.unlink()
    users.write({"active": False})
    templates.unlink()
    used_owner_values = env["product.template.attribute.line"].sudo().search([
        ("value_ids", "in", owner_values.ids),
    ]) if owner_values else env["product.template.attribute.line"].sudo().browse()
    if used_owner_values:
        raise UserError("HVR01 货主属性仍被其他模板使用；停止删除该属性值")
    owner_values.unlink()
    if test_project:
        test_project.unlink()
    # OWNER-AUTO 是 API01 自动创建的联系人；其余两个联系人由本脚本建立。
    remaining_owner_refs = env["project.project"].sudo().search_count([("owner", "in", owners.ids)])
    if remaining_owner_refs:
        raise UserError("测试货主仍被项目引用，停止删除联系人")
    owners.unlink()
    env.cr.commit()
    ENV_FILE.unlink(missing_ok=True)
    print("API01 HVR 专用订单、产品、认证、日志和幂等记录已通过 ORM 重置。")
    print("未执行 SQL；发现非 HVR 引用、库存移动或 Picking 时会提前停止。")


reset_api01_hvr()
